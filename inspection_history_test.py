"""Real template matching + durable evidence tests; no camera hardware required."""
import tempfile
import threading
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import cv2
import numpy as np
from flask import Flask
import server as base
import vision_core as vc
from inspection_history import InspectionHistory, register_inspections


class HistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_db = base.DB_PATH
        base.DB_PATH = str(Path(self.tmp.name)/'product.sqlite')
        base.init_db(); base.init_stream_schema()
        vc.ensure_runtime_revision(base.DB_PATH)
        client = base.app.test_client()
        self.pid = client.post('/api/products', json={'serial':'TEST'}).json['id']
        self.frame = np.random.default_rng(3).integers(0,255,(120,160,3),dtype=np.uint8)
        response = client.post(f'/api/products/{self.pid}/regions', json={
            'image_b64':base.cv2_to_b64(self.frame),
            'regions':[dict(label='part',x=20,y=20,w=40,h=40,threshold=.8,search_margin=0)]})
        self.assertEqual(response.status_code,200)
        mgr=vc.CacheManager(base.DB_PATH,self.pid);mgr.initial_load()
        self.ready=True
        self.edge=SimpleNamespace(control_lock=threading.RLock(),lock=threading.RLock(),
            cfg=SimpleNamespace(product_id=self.pid),active_revision=mgr._version,
            latest_raw=self.frame.copy(),product=base._load_product_dict(self.pid),
            status=lambda:{'inference_ready':self.ready},_method=lambda:cv2.TM_CCOEFF_NORMED,
            _storage_ok=lambda:True)
        self.app=Flask(__name__)
        self.path=Path(self.tmp.name)/'history.sqlite'
        self.store=register_inspections(self.app,self.edge,base,self.path)
        self.client=self.app.test_client()

    def tearDown(self):
        base.DB_PATH=self.old_db
        self.tmp.cleanup()

    def capture(self,sn='A',token=None):
        return self.client.post('/api/edge/inspection',json={'sn':sn,'request_id':token or str(uuid.uuid4())})

    def test_evidence_and_idempotence(self):
        token=str(uuid.uuid4())
        response=self.capture(token=token)
        self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(response.json['attempt']['verdict'],'OK')
        self.assertEqual(self.capture(token=token).json['attempt']['id'],token)
        self.assertEqual(len(self.client.get('/api/edge/history').json['items']),1)
        self.assertIsNotNone(cv2.imdecode(np.frombuffer(self.client.get(f'/api/edge/history/{token}/raw').data,np.uint8),1))
        self.assertEqual(self.client.get(f'/api/edge/history/{token}/metadata').json['scope'],'snapshot_only')
        self.assertEqual(InspectionHistory(self.path).state()['active']['sn'],'A')

    def test_lock_retake_close(self):
        active=self.capture().json['active']
        self.assertEqual(self.capture('B').status_code,409)
        self.assertEqual(self.capture().status_code,200)
        self.assertEqual(len(self.client.get('/api/edge/history').json['items']),2)
        self.assertEqual(self.client.post('/api/edge/config',json={}).status_code,409)
        self.assertEqual(self.client.post('/api/edge/inspection',json={'action':'close','cycle_id':'wrong'}).status_code,409)
        self.assertEqual(self.client.post('/api/edge/inspection',json={'action':'close','cycle_id':active['id']}).status_code,200)
        self.assertEqual(self.capture('B').status_code,200)

    def test_unknown_is_not_ng(self):
        self.edge.latest_raw=np.zeros_like(self.frame)
        self.assertEqual(self.capture().json['attempt']['verdict'],'UNKNOWN')

    def test_explicit_reject(self):
        def reject(frame,cache,**kwargs):
            cache.last_rule_results=[{'hard_reject':True}]
            return False,[],frame
        with patch.object(vc,'run_inference',side_effect=reject):
            self.assertEqual(self.capture().json['attempt']['verdict'],'NG')

    def test_required_sn_and_stale_camera(self):
        self.client.post('/api/edge/inspection',json={'action':'preferences','require_sn':True})
        self.assertEqual(self.capture('').status_code,400)
        self.ready=False
        self.assertEqual(self.capture().status_code,409)
        self.assertEqual(self.client.get('/api/edge/history').json['items'],[])

    def test_changed_revision_rejected(self):
        self.edge.active_revision=-1
        self.assertEqual(self.capture().status_code,409)
        self.assertIsNone(self.store.state()['active'])

    def test_full_storage_no_false_success(self):
        self.edge._storage_ok=lambda:False
        self.assertEqual(self.capture().status_code,409)
        self.assertIsNone(self.store.state()['active'])


if __name__=='__main__':
    unittest.main(verbosity=2)
