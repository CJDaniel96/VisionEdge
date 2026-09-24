"""Exercise real SQLite transactions and copy isolation, without camera hardware."""
import tempfile,threading
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import server as base
from workspace_api import register

def main():
 with tempfile.TemporaryDirectory() as td:
  base.DB_PATH=str(Path(td)/'test.sqlite');base.init_db();base.init_stream_schema();base.vc.ensure_runtime_revision(base.DB_PATH)
  active=[False];edge=SimpleNamespace(control_lock=threading.RLock(),cfg=SimpleNamespace(product_id=0),packaging=None,inspection_active=lambda:active[0],status=lambda:dict(recording=False))
  register(base.app,base,edge);c=base.app.test_client()
  p=c.post('/api/products',json={'serial':'OWN'}).json['id'];q=c.post('/api/products',json={'serial':'COPY'}).json['id'];url=f'/api/products/{p}/workspace'
  frame=np.random.default_rng(33).integers(0,255,(80,120,3),dtype=np.uint8);image=base.cv2_to_b64(frame)
  initial=c.get(url).json
  regions=[dict(label=n,x=x,y=10,w=20,h=20,threshold=t,search_margin=8,sample_hint='OK',source_image_b64=image,capture_group_temp_key='frame1') for n,x,t in [('A',10,.8),('B',70,.91)]]
  body=dict(version=initial['version'],image_b64=image,regions=regions,new_capture_groups={'frame1':dict(label='original',thumb_b64=image)})
  res=c.put(url,json=body);assert res.status_code==200,res.json
  saved=c.get(url).json;assert len(saved['regions'])==2 and len(saved['captures'])==1 and saved['image_b64']==image
  assert all(r['capture_group_id']==saved['captures'][0]['id'] for r in saved['regions'])
  assert c.get(f'/api/products/{p}/sop-definition').json['steps']==[]
  rid=saved['regions'][0]['id']
  for pid in (p,q):
   d=c.post(f'/api/products/{pid}/sop-definition',json=dict(config={'enabled':False},steps=[dict(name='group',samples=[dict(source_region_id=rid,sample_role='OK')])]))
   assert d.status_code==200,d.json
  assert c.get(url).json['version']==saved['version'],'Saving flows must not create or modify source labels'
  foreign=c.get(f'/api/products/{q}/sop-definition').json
  body=dict(version=saved['version'],image_b64=base.cv2_to_b64(255-frame),regions=saved['regions'])
  body['regions'][0]['label']='A revised';body['regions'][0]['threshold']=0;body['regions'][0]['search_margin']=5
  edge.cfg.product_id=p;active[0]=True
  assert c.put(url,json=body).status_code==409
  active[0]=False
  res=c.put(url,json=body);assert res.status_code==200,res.json
  after=c.get(url).json
  assert [r['id'] for r in after['regions']]==[r['id'] for r in saved['regions']]
  assert after['regions'][0]['template_b64']==saved['regions'][0]['template_b64'],'Other displayed frame must not recrop stored label'
  assert after['captures'][0]['thumb_b64']==image
  assert c.get(f'/api/products/{p}/sop-definition').json['steps'][0]['samples'][0]['threshold']==0
  foreign_now=c.get(f'/api/products/{q}/sop-definition').json
  assert foreign_now['steps'][0]['samples'][0]['threshold']==.8
  # Saving another field in the importing flow must not silently reimport source changes.
  smp=foreign['steps'][0]['samples'][0]
  res=c.post(f'/api/products/{q}/sop-definition',json=dict(config={'enabled':False},steps=[dict(name='renamed group',samples=[dict(existing_sample_id=smp['id'],source_region_id=rid,sample_role='OK')])]))
  assert res.status_code==200,res.json
  assert c.get(f'/api/products/{q}/sop-definition').json['steps'][0]['samples'][0]['threshold']==.8
  # A deliberate new selection imports the new value.
  c.post(f'/api/products/{q}/sop-definition',json=dict(config={'enabled':False},steps=[dict(name='group',samples=[dict(source_region_id=rid,sample_role='OK')])]))
  assert c.get(f'/api/products/{q}/sop-definition').json['steps'][0]['samples'][0]['threshold']==0
  assert c.put(url,json=body).status_code==409,'Stale batch must fail'
  bad=dict(version=after['version'],regions=after['regions']);bad['regions'][1]['threshold']=float('nan')
  assert c.put(url,json=bad).status_code==400
  assert c.get(url).json['version']==after['version'],'Invalid batch must be atomic'
  assert c.put(url,json=dict(version=after['version'],regions=[],clear_reference=True)).status_code==409,'Own rule reference deletion must fail'
  c.post(f'/api/products/{p}/sop-definition',json=dict(config={'enabled':False},steps=[]))
  assert c.put(url,json=dict(version=after['version'],regions=[],clear_reference=True)).status_code==200
  assert not c.get(url).json['image_b64'],'Clear must remove reference image'
  assert c.get(url).json['captures']==[],'Orphan frames must be removed with final region'
  db=base.get_db()
  assert db.execute('SELECT t.template_b64 FROM inspection_item_templates t JOIN inspection_items i ON i.id=t.item_id WHERE i.product_id=?',(q,)).fetchone()[0],'Foreign snapshot must survive source deletion'
  db.close()
 print('WORKSPACE PASS: multi-label atomic save, persistent frames, stable IDs, independent thresholds, stale/active/delete guards, no recrop, own update, foreign copy isolation')

if __name__=='__main__':main()
