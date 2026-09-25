"""Reusable label library: edits update same-product rules; foreign products keep snapshots."""
import hashlib,json,math
import cv2
from flask import request,jsonify,send_from_directory

def version(row):
 return hashlib.sha256(json.dumps(dict(row),sort_keys=True,default=str).encode()).hexdigest()[:24]

def register(app,base,edge):
 @app.route('/api/products/<int:pid>/label-library/<int:rid>/image-test',methods=['POST'])
 def test_label_image(pid,rid):
  # Read-only diagnostics: no camera, SOP progression or inspection-history writes.
  body=request.get_json(silent=True) or {}
  encoded=body.get('image_b64') if isinstance(body,dict) else None
  if not isinstance(encoded,str) or not encoded or len(encoded)>28_000_000:
   return jsonify(error='請提供 20 MB 以下的測試圖片'),400
  try:frame=base.b64_to_cv2(encoded)
  except Exception:frame=None
  if frame is None:return jsonify(error='無法讀取圖片，請使用 PNG 或 JPEG'),400
  if frame.shape[0]*frame.shape[1]>25_000_000:return jsonify(error='圖片超過 2500 萬像素'),400
  db=base.get_db()
  try:
   row=db.execute('''SELECT r.*,COALESCE(g.thumb_b64,p.reference_img_b64) AS source_frame
     FROM regions r JOIN products p ON p.id=r.product_id
     LEFT JOIN capture_groups g ON g.id=r.capture_group_id
     WHERE r.product_id=? AND r.id=?''',(pid,rid)).fetchone()
   if row is None:return jsonify(error='找不到 Label'),404
   reg=dict(row)
  finally:db.close()
  source=base.b64_to_cv2(reg.get('source_frame') or '')
  if source is not None and source.shape[:2]!=frame.shape[:2]:
   return jsonify(error=f'測試圖片尺寸須與取樣畫面一致：{source.shape[1]}×{source.shape[0]}；目前為 {frame.shape[1]}×{frame.shape[0]}'),400
  tpl=base.b64_to_cv2(reg.get('template_b64') or '')
  if tpl is None:return jsonify(error='無法讀取樣板'),400
  reg['tpl_gray']=cv2.cvtColor(tpl,cv2.COLOR_BGR2GRAY)
  reg['th'],reg['tw']=reg['tpl_gray'].shape
  if edge._method()==cv2.TM_CCOEFF_NORMED and float(reg['tpl_gray'].std())<1e-6:
   return jsonify(error='樣板沒有明暗特徵，無法可靠比對；請重新標記包含邊緣或紋理的區域'),400
  gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
  result=base.vc._match_one_template(gray,*gray.shape,reg,edge._method())
  if result.get('match_loc'):
   x,y=result['match_loc'];w,h=result['match_size']
   cv2.rectangle(frame,(x,y),(x+w,y+h),(50,170,30) if result['pass'] else (40,40,220),2)
  return jsonify(result=result,image_b64=base.cv2_to_b64(frame),sample_hint=reg.get('sample_hint','OK'),
    search_margin=reg.get('search_margin',0),scope='single_label_only')
 @app.route('/template-studio')
 def template_studio_page():return send_from_directory('static','template_workspace.html')

 def references(db,rid):
  return [dict(x) for x in db.execute('SELECT DISTINCT i.product_id,i.name FROM inspection_items i JOIN inspection_item_templates t ON t.item_id=i.id WHERE t.source_region_id=? UNION SELECT r.product_id,r.name FROM inspection_rules r JOIN inspection_rule_items t ON t.rule_id=r.id WHERE t.region_id=?',(rid,rid))]

 @app.route('/api/products/<int:pid>/label-library',methods=['GET'])
 def label_library(pid):
  db=base.get_db()
  try:
   items=[]
   for row in db.execute("SELECT * FROM regions WHERE product_id=? AND COALESCE(template_b64,'')<>'' ORDER BY id",(pid,)):
    d=dict(row);d['version']=version(row);d['references']=references(db,row['id']);items.append(d)
   return jsonify(items=items)
  finally:db.close()

 @app.route('/api/products/<int:pid>/label-library/<int:rid>',methods=['PUT','DELETE'])
 def edit_label(pid,rid):
  data=request.get_json(silent=True) or {}
  if not isinstance(data,dict):return jsonify(error='Invalid JSON body'),400
  with edge.control_lock:
   db=base.get_db()
   try:
    db.execute('BEGIN IMMEDIATE')
    row=db.execute('SELECT * FROM regions WHERE id=? AND product_id=?',(rid,pid)).fetchone()
    if not row:return jsonify(error='找不到樣板'),404
    if data.get('version')!=version(row):return jsonify(error='樣板已被更新，請重新載入後再修改'),409
    refs=references(db,rid);affected={pid}
    active=edge.cfg.product_id in affected
    if active and (getattr(edge,'inspection_active',lambda:False)() or (edge.packaging and edge.packaging.cycle_id) or edge.status()['recording']):
     return jsonify(error='請先結束目前工件並停止錄影，再修改引用中的樣板'),409
    if request.method=='DELETE':
     from packaging_cycle import load_settings
     pack=load_settings(db,pid)
     if refs or rid in [pack.get(k) for k in ('vacant_region_id','ready_region_id','presence_region_id')]:return jsonify(error='樣板仍被規則或包裝條件引用，請先移除引用'),409
     db.execute('DELETE FROM regions WHERE id=?',(rid,))
    else:
     name=str(data.get('label','')).strip();threshold=float(data['threshold']);margin=int(data['search_margin'])
     if not name or len(name)>240 or not math.isfinite(threshold) or not 0<=threshold<=1 or margin!=float(data['search_margin']) or not 0<=margin<=10000:raise ValueError('名稱、門檻或位置容許值無效')
     hint=data.get('sample_hint','OK')
     if hint not in ('OK','NG','NEUTRAL'):raise ValueError('樣板類型無效')
     db.execute('UPDATE regions SET label=?,threshold=?,search_margin=?,sample_hint=? WHERE id=?',(name,threshold,margin,hint,rid))
     # Runtime rules store snapshots. Update those copies in this same transaction.
     db.execute('UPDATE inspection_item_templates SET sample_name=?,threshold=?,search_margin=? WHERE source_region_id=? AND item_id IN (SELECT id FROM inspection_items WHERE product_id=?)',(name,threshold,margin,rid,pid))
    db.commit();return jsonify(ok=True,affected_products=sorted(affected),references=refs)
   except (ValueError,TypeError,KeyError,OverflowError) as exc:return jsonify(error=str(exc)),400
   finally:db.close()

 @app.route('/api/products/<int:pid>/label-library/test',methods=['POST'])
 def test_library(pid):
  # Diagnostic only: never moves the production SOP or writes inspection history.
  with edge.control_lock:
   with edge.lock:
    if not edge.status()['frame_fresh'] or edge.latest_raw is None:return jsonify(error='相機尚未就緒'),409
    frame=edge.latest_raw.copy()
   product=base._load_product_dict(pid)
   if not product:return jsonify(error='找不到產品'),404
   frame=base._prepare_frame(frame,product)
   mgr=base.vc.CacheManager(base.DB_PATH,pid)
   if not mgr.initial_load():return jsonify(error='無法讀取樣板'),400
   gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
   results=[base.vc._match_one_template(gray,*gray.shape,r,edge._method()) for r in mgr.get().regions]
   return jsonify(results=results,image_b64=base.cv2_to_b64(frame),scope='labels_only',revision=str(mgr._version))
