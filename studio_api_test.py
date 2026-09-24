"""Library integration tests use a temporary database and synthetic camera frame."""
import tempfile,threading,time
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import server as base
from edge_runtime import EdgeConfig
from studio_api import register
import qti_controls as qti

def main():
 with tempfile.TemporaryDirectory() as td:
  base.DB_PATH=str(Path(td)/'test.sqlite');base.init_db();base.init_stream_schema();base.vc.ensure_runtime_revision(base.DB_PATH)
  frame=np.random.default_rng(8).integers(0,255,(120,200,3),dtype=np.uint8)
  active=[False]
  edge=SimpleNamespace(control_lock=threading.RLock(),lock=threading.RLock(),cfg=SimpleNamespace(product_id=0),packaging=None,latest_raw=frame,inspection_active=lambda:active[0],status=lambda:dict(recording=False,frame_fresh=True),_method=lambda:base.cv2.TM_CCOEFF_NORMED)
  register(base.app,base,edge);c=base.app.test_client()
  p=c.post('/api/products',json={'serial':'LIBRARY'}).json['id']
  p2=c.post('/api/products',json={'serial':'REFERENCING'}).json['id']
  row=c.post(f'/api/products/{p}/regions/append',json=dict(label='A',x=30,y=20,w=40,h=30,threshold=.8,search_margin=5,source_image_b64=base.cv2_to_b64(frame))).json['region']
  rid=row['id'];url=f'/api/products/{p}/label-library'
  assert c.get(f'/api/products/{p}/sop-definition').json['steps']==[], 'Saving label must not create SOP'
  definition=dict(config={'enabled':False},steps=[dict(name='Group',samples=[dict(source_region_id=rid,sample_role='OK')])])
  res=c.post(f'/api/products/{p2}/sop-definition',json=definition);assert res.status_code==200,res.json
  old=c.get(url).json['items'][0];assert old['references'][0]['product_id']==p2
  body=dict(version=old['version'],label='New A',threshold=0,search_margin=12,sample_hint='NG')
  edge.cfg.product_id=p;active[0]=True
  assert c.put(f'{url}/{rid}',json=body).status_code==409
  active[0]=False
  assert c.put(f'{url}/{rid}',json={**body,'search_margin':1.5}).status_code==400
  assert c.put(f'{url}/{rid}',json={**body,'threshold':float('nan')}).status_code==400
  assert c.put(f'{url}/{rid}',json=body).status_code==200
  assert c.put(f'{url}/{rid}',json=body).status_code==409,'Stale update must not overwrite'
  new=c.get(url).json['items'][0];assert new['version']!=old['version'] and new['label']=='New A'
  sample=c.get(f'/api/products/{p2}/sop-definition').json['steps'][0]['samples'][0]
  assert sample['sample_name']!='New A' and sample['threshold']==.8 and sample['search_margin']==5,sample
  assert sample['sample_role']=='OK','Library hint must not silently invert existing rule'
  assert c.delete(f'{url}/{rid}',json={'version':new['version']}).status_code==409
  res=c.post(url+'/test',json={});assert res.status_code==200,res.json
  assert res.json['scope']=='labels_only' and res.json['results'][0]['pass'],res.json
  assert c.post(f'/api/products/{p2}/sop-definition',json=dict(config={'enabled':False},steps=[])).status_code==200
  assert c.delete(f'{url}/{rid}',json={'version':new['version']}).status_code==200
  assert c.get(url).json['items']==[]
  cfg=EdgeConfig();cfg.update(dict(camera_controls_mode='manual',camera_control_values={'contrast':7}));path=Path(td)/'edge.ini';cfg.save(path)
  assert EdgeConfig.load(path).camera_control_values=='{"contrast": 7}'
 class Source:
  def __init__(self):self.values={};self.bad=False
  def find_property(self,name):return None if name=='sharpness' else SimpleNamespace(minimum=-100,maximum=4000)
  def set_property(self,name,value):self.values[name]=value
  def get_property(self,name):return -9 if self.bad else self.values[name]
 source=Source();report=qti.apply(source,'safe',{'contrast':7});assert source.values=={'white-balance-mode':0} and report['verified']
 source=Source();qti.apply(source,'off',{});assert not source.values
 qti.apply(source,'manual',{'contrast':7});assert source.values['contrast']==7
 for mode,values in [('manual',{'sharpness':2}),('manual',{'contrast':30}),('manual',{'focus':1}),('manual',{'contrast':2.5})]:
  try:qti.apply(source,mode,values)
  except (ValueError,RuntimeError):pass
  else:raise AssertionError((mode,values))
 source.bad=True
 try:qti.apply(source,'manual',{'contrast':7})
 except RuntimeError:pass
 else:raise AssertionError('Readback mismatch must fail')
 print('STUDIO_API PASS: independent library, foreign copy isolation, stale/active guards, label test, delete references, QTI validation/readback/config roundtrip')

if __name__=='__main__':main()
