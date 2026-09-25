"""QTI property controls adapted from tm_app, with explicit capability/readback reporting."""
import json
SPECS={
 'white_balance_mode':('white-balance-mode',0,10,0),
 'antibanding':('antibanding',0,3,3),
 'iso_mode':('iso-mode',0,8,0),
 'manual_iso_value':('manual-iso-value',100,3200,800),
 'exposure_compensation':('exposure-compensation',-12,12,0),
 'contrast':('contrast',1,10,5),
 'saturation':('saturation',0,10,5),
 'sharpness':('sharpness',0,6,2),
}
def normalize(mode,values):
 if mode not in ('safe','off','manual'):raise ValueError('相機控制模式無效')
 if isinstance(values,str):values=json.loads(values)
 if not isinstance(values,dict) or set(values)-set(SPECS):raise ValueError('不支援的相機控制項目')
 out={}
 for k,v in values.items():
  n=int(v);_,lo,hi,_=SPECS[k]
  if n!=float(v) or not lo<=n<=hi:raise ValueError('相機控制值超出範圍: '+k)
  out[k]=n
 return mode,out

def apply(source,mode,values):
 mode,values=normalize(mode,values);report={'mode':mode,'properties':{},'applied':{},'verified':False}
 for key,(prop,lo,hi,default) in SPECS.items():
  spec=source.find_property(prop)
  enums=getattr(getattr(spec,'enum_class',None),'__enum_values__',{}) if spec else {}
  report['properties'][key]={'supported':bool(spec),'min':max(lo,getattr(spec,'minimum',lo)) if spec else lo,'max':min(hi,getattr(spec,'maximum',hi)) if spec else hi,'default':default,'choices':[{'value':int(v),'label':getattr(e,'value_nick',str(v))} for v,e in enums.items()]}
  if spec:
   try:report['properties'][key]['current']=int(source.get_property(prop))
   except Exception:pass
 requested={} if mode=='off' else {'white_balance_mode':values.get('white_balance_mode',0)} if mode=='safe' else values
 for key,value in requested.items():
  spec=report['properties'][key]
  if not spec['supported']:
   if mode=='manual':raise RuntimeError('QTI 不支援相機控制: '+key)
   continue
  if not spec['min']<=value<=spec['max']:raise RuntimeError('QTI 相機控制值超出設備範圍: '+key)
  if spec['choices'] and value not in [x['value'] for x in spec['choices']]:raise RuntimeError('QTI 相機控制選項不支援: '+key)
  source.set_property(SPECS[key][0],value)
  actual=int(source.get_property(SPECS[key][0]))
  if actual!=value:raise RuntimeError('QTI 相機控制讀回不一致: '+key)
  report['applied'][key]=actual
  report['properties'][key]['current']=actual
 report['verified']=True
 return report
