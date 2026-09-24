import copy
import tempfile
import unittest
from pathlib import Path
from packaging_cycle import PackagingCycle, CycleJournal, DEFAULTS
from vision_core import SopFlowEngine


class CycleTests(unittest.TestCase):
    def setUp(self):
        self.events=[]
        self.cfg={**DEFAULTS,'enabled':True,'stable_sec':.3,'final_sec':.3,'final_step_numbers':[1,2]}
        steps=[dict(id=i,step_no=i,name=str(i),enabled=True,required=True,min_consecutive_hits=2,hold_ms=200,
                    samples=[{'sample_role':'OK'}]) for i in (1,2)]
        self.p=PackagingCycle(SopFlowEngine(steps,{'enabled':True,'strict_order':True}),self.cfg,
                              lambda *args:self.events.append(args))
        self.t=0

    def frame(self,kind='present',ok=(),ng=False,n=1):
        signals={'vacant':kind=='clear','presence':kind in ('present','ready'), 'ready':kind=='ready'}
        rules=[{'id':i,'pass':i in ok,'hard_reject':ng and i==2,'matched':str(i) if i in ok else None,
                'items':[{'sample_role':'OK','matched':i in ok}]} for i in (1,2)]
        for _ in range(n):
            self.t+=.2
            s=self.p.update(signals,rules,now=self.t)
        return s

    def start(self):
        self.frame('clear',n=4);self.frame('ready',n=4)
        self.assertEqual(self.p.state,'ACTIVE')

    def complete(self):
        self.start();self.frame(ok=(1,),n=4);self.frame(ok=(1,2),n=6)
        self.assertEqual(self.p.state,'READY_TO_REMOVE')

    def test_start_requires_clear_then_stable_empty_box(self):
        self.frame('ready',n=8);self.assertEqual(self.p.state,'WAIT_CLEAR')
        self.frame('clear',n=4);self.frame('ready');self.frame('unknown');self.frame('ready')
        self.assertEqual(self.p.state,'WAIT_READY')
        self.frame('ready',n=4);self.assertEqual(self.p.state,'ACTIVE')

    def test_one_box_one_cycle(self):
        self.complete();cycle=self.p.cycle_id
        self.frame(ok=(1,2),n=20)
        self.assertEqual(self.p.cycle_id,cycle)
        self.assertEqual(sum(e[2]=='START' for e in self.events),1)
        self.assertEqual(sum(e[2]=='FINAL_VERIFIED' for e in self.events),1)
        self.frame('clear',n=4)
        self.assertEqual(self.p.last_result,'OK')
        self.assertEqual(self.p.state,'WAIT_READY')
        self.frame('clear',n=10);self.assertEqual(sum(e[2]=='REMOVED' for e in self.events),1)

    def test_early_removal_is_incomplete(self):
        self.start();self.frame(ok=(1,),n=4);self.frame('clear',n=4)
        self.assertEqual(self.p.last_result,'INCOMPLETE')

    def test_mismatch_does_not_mean_removed(self):
        self.complete();cycle=self.p.cycle_id
        self.frame('unknown',n=20)
        self.assertEqual(self.p.cycle_id,cycle)
        self.assertFalse(any(e[2]=='REMOVED' for e in self.events))
        self.assertFalse(self.p.summary()['complete'])

    def test_final_visible_item_taken_away(self):
        self.complete();self.frame(ok=(2,),n=2)
        self.assertEqual(self.p.state,'ACTIVE')
        self.frame('clear',n=4);self.assertEqual(self.p.last_result,'INCOMPLETE')

    def test_covered_step_can_be_excluded_from_final(self):
        self.p.cfg['final_step_numbers']=[2]
        self.start();self.frame(ok=(1,),n=4);self.frame(ok=(2,),n=6)
        self.assertEqual(self.p.state,'READY_TO_REMOVE')

    def test_wrong_order_alarms_and_ng_overrides(self):
        self.start();self.frame(ok=(2,),n=4)
        self.assertTrue(self.p.summary()['alarm']['active'])
        self.p.acknowledge();self.frame(ok=(1,),n=4);self.frame(ok=(1,2),ng=True,n=4)
        self.assertNotEqual(self.p.state,'READY_TO_REMOVE')

    def test_interrupt_discards_incomplete_progress(self):
        self.complete();self.p.interrupt()
        self.assertEqual(self.p.state,'WAIT_CLEAR')
        self.assertIsNone(self.p.cycle_id)
        self.frame('ready',n=5);self.assertEqual(self.p.state,'WAIT_CLEAR')
        self.assertEqual(self.events[-1][1],'INTERRUPTED')

    def test_gap_does_not_complete_hold(self):
        self.start();self.frame(ok=(1,))
        self.t+=5;self.frame(ok=(1,))
        self.assertEqual(self.p.state,'WAIT_CLEAR')

    def test_storage_failure_never_passes(self):
        def fail(*args):raise OSError('disk full')
        self.p.record=fail
        self.frame('clear',n=4);self.frame('ready',n=4)
        self.assertEqual(self.p.state,'FAULT')
        self.assertFalse(self.p.summary()['complete'])

    def test_conflicting_signals_never_arm(self):
        self.frame('clear',n=4)
        for _ in range(8):
            self.t+=.2
            self.p.update({'vacant':True,'ready':True,'presence':True},[],now=self.t)
        self.assertEqual(self.p.state,'WAIT_READY')

    def test_fixture_mode(self):
        self.p.cfg['mode']='fixture'
        self.frame('clear',n=4)
        self.frame(ok=(1,),n=8)
        self.assertEqual(self.p.state,'ACTIVE')
        self.frame(ok=(1,2),n=6);self.assertEqual(self.p.state,'READY_TO_REMOVE')
        self.frame('clear',n=4);self.assertEqual(self.p.last_result,'OK')

    def test_journal_restart_preserves_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'journal.sqlite'
            j=CycleJournal(path);j.record('x',1,'READY','FINAL_VERIFIED',{'score':.99},b'raw',b'result')
            k=CycleJournal(path);k.recover(1)
            with k.connect() as db:
                self.assertEqual(db.execute('SELECT status FROM cycles').fetchone()[0],'INTERRUPTED')
                self.assertEqual(db.execute('SELECT raw FROM events').fetchone()[0],b'raw')

if __name__=='__main__':unittest.main(verbosity=2)
