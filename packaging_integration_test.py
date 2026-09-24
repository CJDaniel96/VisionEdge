"""Real templates -> Edge runtime -> cycle journal. Uses only synthetic images."""
import tempfile
from pathlib import Path
import numpy as np
import cv2
import server as base
import edge_runtime as er
from packaging_cycle import CycleJournal


def seed(base):
    client=base.app.test_client()
    pid=client.post('/api/products',json={'serial':'PACK-TEST'}).json['id']
    rng=np.random.default_rng(42)
    empty=rng.integers(0,255,(200,320,3),dtype=np.uint8)
    box=empty.copy();box[30:180,40:280]=rng.integers(0,255,(150,240,3),dtype=np.uint8)
    a=box.copy();a[80:120,75:115]=rng.integers(0,255,(40,40,3),dtype=np.uint8)
    ab=a.copy();ab[80:120,195:235]=rng.integers(0,255,(40,40,3),dtype=np.uint8)
    wrong=box.copy();wrong[80:120,195:235]=a[80:120,75:115]
    ids={}
    for name,img,x,y,w,h in [('vacant',empty,40,30,240,150),('ready',box,65,65,180,75),('presence',box,40,30,24,24),('A',a,75,80,40,40),('B',ab,195,80,40,40)]:
        d=client.post(f'/api/products/{pid}/regions/append',json={'label':name,'x':x,'y':y,'w':w,'h':h,'threshold':.99,'search_margin':0,'source_image_b64':base.cv2_to_b64(img)})
        assert d.status_code==200,d.json
        ids[name]=d.json['region']['id']
    cfg=dict(enabled=True,mode='box',vacant_region_id=ids['vacant'],ready_region_id=ids['ready'],presence_region_id=ids['presence'],margin=4,stable_sec=.3,final_sec=.3,final_step_numbers=[1,2])
    steps=[dict(name=name,enabled=True,required=True,min_consecutive_hits=2,hold_ms=200,samples=[dict(source_region_id=ids[name],sample_role='OK')]) for name in ('A','B')]
    data={'config':{'enabled':True},'steps':steps,'packaging':cfg,'final_logic_mode':'ANY'}
    saved=client.post(f'/api/products/{pid}/sop-definition',json=data)
    assert saved.status_code==200,saved.json
    return pid,dict(clear=empty,ready=box,A=a,AB=ab,wrong=wrong),data


def main():
    old_db,old_dir=base.DB_PATH,er.EDGE_RUNTIME_DIR
    with tempfile.TemporaryDirectory() as td:
        try:
            root=Path(td);base.DB_PATH=str(root/'products.sqlite');er.EDGE_RUNTIME_DIR=root
            base.init_db();base.init_stream_schema();base.vc.ensure_runtime_revision(base.DB_PATH)
            pid,frames,data=seed(base)
            rt=er.EdgeRuntime(base,root/'edge.ini');rt.cfg.product_id=pid;rt.cfg.min_free_mb=0;rt._prepare_inference()
            tick=[0.0];rt.packaging.now_fn=lambda:tick[0]
            def run(name,n):
                for _ in range(n):
                    tick[0]+=.2
                    result=rt._process_inference(frames[name])
                return result
            run('ready',5);assert rt.packaging.state=='WAIT_CLEAR'
            run('clear',5);assert rt.packaging.state=='WAIT_READY',rt.packaging.summary()
            run('ready',5);assert rt.packaging.state=='ACTIVE',rt.packaging.summary()
            run('wrong',5);assert rt.engine.summary()['done_count']==0,'A in wrong position must not pass'
            run('A',5);assert rt.engine.summary()['done_count']==1,rt.engine.summary()
            run('AB',8);assert rt.packaging.state=='READY_TO_REMOVE',rt.packaging.summary()
            assert not rt.update_config({'width':640})['success'],'config must be locked during a box'
            run('clear',5);assert rt.packaging.last_result=='OK'
            journal=CycleJournal(root/'packaging_history.sqlite3')
            with journal.connect() as db:
                assert db.execute('SELECT status FROM cycles').fetchone()[0]=='OK'
                events=db.execute('SELECT kind,raw,result FROM events').fetchall()
                assert [e[0] for e in events]==['START','STEP_1','STEP_2','FINAL_VERIFIED','REMOVED']
                assert all(cv2.imdecode(np.frombuffer(e[1],np.uint8),1) is not None for e in events)
            # Invalid settings cannot replace the last valid definition.
            bad={**data,'packaging':{**data['packaging'],'presence_region_id':999999}}
            client=base.app.test_client()
            assert client.post(f'/api/products/{pid}/sop-definition',json=bad).status_code==400
            assert client.get(f'/api/products/{pid}/sop-definition').json['packaging']['presence_region_id']==data['packaging']['presence_region_id']
            # Constrained, undersized ROI never falls back to global search.
            reg=dict(rt.packaging_templates['presence']);reg.update(x=318,y=198,search_margin=1)
            gray=cv2.cvtColor(frames['ready'],cv2.COLOR_BGR2GRAY)
            match=base.vc._match_one_template(gray,*gray.shape,reg,cv2.TM_CCOEFF_NORMED)
            assert not match['pass'] and match.get('error')
            rt._release_inference()
            print('PACKAGING_INTEGRATION PASS: actual matching, position gate, complete cycle, evidence, config rollback, constrained ROI')
        finally:
            base.DB_PATH=old_db;er.EDGE_RUNTIME_DIR=old_dir

if __name__=='__main__':main()
