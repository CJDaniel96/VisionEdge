"""Rule group API round trip and actual inference semantics, isolated database."""
import tempfile
from pathlib import Path
import numpy as np
import server as base
import vision_core as vc

def main():
    old=base.DB_PATH
    with tempfile.TemporaryDirectory() as td:
        try:
            base.DB_PATH=str(Path(td)/'test.sqlite')
            base.init_db();base.init_stream_schema();vc.ensure_runtime_revision(base.DB_PATH)
            c=base.app.test_client()
            pid=c.post('/api/products',json={'serial':'RULE-TEST'}).json['id']
            frame=np.random.default_rng(17).integers(0,255,(100,140,3),dtype=np.uint8)
            ids=[]
            for label,img in [('A',frame),('B',255-frame)]:
                response=c.post(f'/api/products/{pid}/regions/append',json={
                    'label':label,'x':0,'y':0,'w':140,'h':100,'threshold':.9,
                    'source_image_b64':base.cv2_to_b64(img)})
                assert response.status_code==200,response.json
                ids.append(response.json['region']['id'])
            steps=[{'name':name,'enabled':True,'logic_mode':'ANY','samples':[
                {'source_region_id':rid,'sample_role':'OK'}]} for name,rid in zip(['A','B'],ids)]
            url=f'/api/products/{pid}/sop-definition'
            def save(mode=None):
                payload={'config':{'enabled':True},'steps':steps}
                if mode is not None:payload['final_logic_mode']=mode
                return c.post(url,json=payload)
            def infer():
                mgr=vc.CacheManager(base.DB_PATH,pid);assert mgr.initial_load()
                return vc.run_inference(frame,mgr.get(),draw_vis=False)[0]
            assert save('ANY').status_code==200
            assert c.get(url).json['final_logic_mode']=='ANY'
            assert c.get(f'/api/products/{pid}/rule-groups').json['final_logic_mode']=='ANY'
            assert infer() is True,'A passes, B fails: ANY should pass'
            assert save().status_code==200
            assert c.get(url).json['final_logic_mode']=='ANY','omitting mode must preserve ANY'
            assert save('invalid').status_code==400
            assert c.get(url).json['final_logic_mode']=='ANY','invalid save must not mutate state'
            assert save('ALL').status_code==200
            assert infer() is False,'ALL requires both groups'
            steps[1]['samples'].append({'source_region_id':ids[0],'sample_role':'NG'})
            assert save('ANY').status_code==200
            assert infer() is False,'NG in another enabled group overrides ANY'
            steps[1]['enabled']=False
            assert save('ANY').status_code==200
            assert infer() is True,'disabled group must not reject'
            print('RULE_GROUP_ROUNDTRIP PASS: ANY/ALL, preserve omitted mode, invalid rollback, NG override, disabled group')
        finally:base.DB_PATH=old

if __name__=='__main__':main()
