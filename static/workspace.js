// The old single-workspace editor keeps ownership of drawing, frames and selection.
let workspaceVersion='',workspaceBaseline='',workspaceBusy=false,workspaceLeaving=false;
let qtiReport=null,qtiSavedValues={},cameraBaseline='';
const asImage=s=>!s?'':s.startsWith('data:')?s:'data:image/jpeg;base64,'+s;
async function studioRequest(url,options={}){const r=await fetch(url,{cache:'no-store',...options,headers:{'Content-Type':'application/json',...options.headers}});const d=await r.json();if(!r.ok||d.ok===false||d.success===false)throw Error(d.error||'操作失敗');return d;}
function toast(message){setStatus(message)}
function workspacePayload(){
 const new_capture_groups={};
 const regions=S.regions.map(r=>{
  const out={id:r.id,label:r.label,x:r.x,y:r.y,w:r.w,h:r.h,threshold:r.threshold,search_margin:r.search_margin??0,sample_hint:cleanSampleHint(r.sample_hint)};
  if(r._srcB64)out.source_image_b64=r._srcB64;
  if(typeof r._captureId==='string'&&r._captureId.startsWith('cap_')){
   out.capture_group_temp_key=r._captureId;const c=S.captures.find(c=>c.id===r._captureId);
   if(c)new_capture_groups[c.id]={label:c.ts,thumb_b64:c.b64};
  }else if(r._captureId)out.capture_group_id=r._captureId;
  return out;
 });
 return {regions,new_capture_groups,clear_reference:!!S.clearTemplate};
}
function workspacePending(){return S.editMode&&JSON.stringify(workspacePayload())!==workspaceBaseline;}
function workspaceDirtyUI(){
 document.getElementById('modeLabel').textContent=S.editMode?(workspacePending()?'編輯中 · 尚未儲存':'編輯模式'):'瀏覽模式';
 for(const id of ['workspaceTestBtn','workspaceApplyBtn','imageTestBtn'])document.getElementById(id).disabled=S.editMode||!S.selectedPid;
}
function workspaceLock(b){workspaceBusy=b;document.getElementById('app').inert=b;document.querySelectorAll('#cameraDialog button,#cameraDialog select,#cameraDialog input').forEach(e=>{if(b){e.dataset.wasDisabled=String(e.disabled);e.disabled=true}else{e.disabled=e.dataset.wasDisabled==='true'}})}
async function workspaceInit(){
 try{await loadProducts();const pid=Number(new URLSearchParams(location.search).get('product_id'));const p=S.products.find(p=>p.id===pid)||S.products[0];if(p)await selectProduct(p);else applyEditModeUI();}
 catch(e){toast(e.message)}
 document.getElementById('regionBody').addEventListener('input',workspaceDirtyUI);
}
fetchRegions=async function(pid){
 const d=await studioRequest(`/api/products/${pid}/workspace`);workspaceVersion=d.version;
 S.clearTemplate=false;
 S.regions=d.regions.map(r=>({...r,_captureId:r.capture_group_id||null,_thumbB64:asImage(r.template_b64),_sel:false}));
 S.captures=d.captures.map(g=>({id:g.id,b64:asImage(g.thumb_b64),ts:g.label||String(g.id)}));
 S.activeCaptureId=null;S.activeCaptureB64=null;S.srcB64=asImage(d.image_b64);
 if(S.captures.length){const c=S.captures[0];S.activeCaptureId=c.id;S.activeCaptureB64=c.b64;S.srcB64=c.b64;}
 if(S.srcB64)await displayImg(S.srcB64);
 workspaceBaseline=JSON.stringify(workspacePayload());renderCaptureStrip();renderTable();drawOverlay();workspaceDirtyUI();
};
selectProduct=async function(p){
 if(workspaceBusy||p.id===S.selectedPid)return;
 if(workspacePending()&&!await workspaceConfirm('尚有未儲存的修改，確定離開？'))return;
 workspaceLock(true);
 try{resetAll();S.selectedPid=p.id;S.editMode=false;await fetchRegions(p.id);renderProductList();applyEditModeUI();setStatus(p.serial);}
 catch(e){S.selectedPid=null;toast(e.message)}finally{workspaceLock(false)}
};
toggleEditMode=async function(){
 if(workspaceBusy)return;
 if(!S.selectedPid){toast('請先建立或選擇產品');return;}
 if(S.editMode){await cancelEdit();return;}
 workspaceLock(true);try{await fetchRegions(S.selectedPid);S.editMode=true;workspaceBaseline=JSON.stringify(workspacePayload());applyEditModeUI();}catch(e){toast(e.message)}finally{workspaceLock(false)}
};
cancelEdit=async function(){
 if(workspacePending()&&!await workspaceConfirm('放棄尚未儲存的修改並重新載入？'))return;
 workspaceLock(true);try{const pid=S.selectedPid;resetAll();S.editMode=false;await fetchRegions(pid);applyEditModeUI();toast('已取消修改');}catch(e){toast(e.message)}finally{workspaceLock(false)}
};
const legacyApplyEdit=applyEditModeUI;
applyEditModeUI=function(){legacyApplyEdit();document.getElementById('editModeBtn').textContent=S.editMode?'結束編輯':'編輯';renderCaptureStrip();DC.style.pointerEvents='auto';workspaceDirtyUI();labelControls()};
const legacyTable=renderTable;
renderTable=function(){legacyTable();workspaceDirtyUI()};
saveRegions=async function(){
 if(workspaceBusy||!S.editMode||!S.selectedPid)return;
 const payload=workspacePayload();
 if(payload.regions.some(r=>!r.label.trim()||!Number.isFinite(r.threshold)||r.threshold<0||r.threshold>1||!Number.isInteger(r.search_margin)||r.search_margin<0||r.search_margin>10000)){toast('名稱、門檻或位置容許值無效');return;}
 workspaceLock(true);
 try{
  await studioRequest(`/api/products/${S.selectedPid}/workspace`,{method:'PUT',body:JSON.stringify({...payload,image_b64:S.srcB64,version:workspaceVersion})});
  S.editMode=false;await fetchRegions(S.selectedPid);await loadProducts();applyEditModeUI();toast(payload.clear_reference?'樣板已清除，產品與流程已保留':'樣板已儲存，請試跑並套用');
 }catch(e){toast(e.message)}finally{workspaceLock(false)}
};
async function workspaceNavigate(path){if(workspaceBusy)return;if(workspacePending()&&!await workspaceConfirm('尚有未儲存的修改，確定離開？'))return;workspaceLeaving=true;location.href=path+'?product_id='+(S.selectedPid||0)}
const legacyAdd=openAddProduct;
openAddProduct=async function(){if(workspacePending()&&!await workspaceConfirm('尚有未儲存的修改，確定離開？'))return;legacyAdd()};
async function workspaceCapture(){
 if(workspaceBusy||!S.selectedPid||!S.editMode)return;
 workspaceLock(true);try{
  const d=await studioRequest(`/api/edge/template-frame?product_id=${S.selectedPid}`);
  _stopLabelUiLoop();_stopServerLabelPlay();clearTimeout(S.lblFallbackTimer);S.lblFallbackFile=null;
  LV.pause();S.lblVideoReady=false;S.lblServerMode=false;showVideoBar(false);_showMovingLabelVideo(false);
  _clearActivePin();S.srcB64=d.image_b64;await displayImg(d.image_b64);pinCurrentFrame();document.getElementById('backToLiveBtn').style.display='none';
  toast('相機畫面已固定，可以框選樣板');
 }catch(e){toast(e.message)}finally{workspaceLock(false)}
}
async function workspaceTest(){
 if(workspaceBusy||S.editMode||!S.selectedPid)return;
 workspaceLock(true);try{
  const d=await studioRequest(`/api/products/${S.selectedPid}/label-library/test`,{method:'POST',body:'{}'});
  document.getElementById('labelTestResults').innerHTML='<table><thead><tr><th>Label</th><th>分數</th><th>門檻</th><th>樣板符合</th></tr></thead><tbody>'+d.results.map(x=>`<tr><td data-i18n-skip>${esc(x.label)}</td><td>${x.score??'—'}</td><td>${x.threshold}</td><td>${x.error?esc(x.error):x.pass?'✓':'—'}</td></tr>`).join('')+'</tbody></table>';
  document.getElementById('testDialog').showModal();
 }catch(e){toast(e.message)}finally{workspaceLock(false)}
}
async function workspaceApply(){
 if(workspaceBusy||S.editMode||!S.selectedPid)return;workspaceLock(true);
 try{
  const d=await studioRequest(`/api/products/${S.selectedPid}/sop-definition`);
  if(!(d.steps||[]).length){
   const rows=S.regions.filter(r=>cleanSampleHint(r.sample_hint)!=='NEUTRAL');
   if(!rows.some(r=>cleanSampleHint(r.sample_hint)==='OK'))throw Error('直接檢查至少需要一個 OK Label');
   if(!await workspaceConfirm('建立基本檢查：全部 OK Label 都必須符合，任一 NG 符合則否決；不啟用 SOP。確定套用？'))return;
   await studioRequest(`/api/products/${S.selectedPid}/sop-definition`,{method:'POST',body:JSON.stringify({config:{enabled:false},packaging:{enabled:false},final_logic_mode:'ALL',steps:[{name:'基本檢查',enabled:true,required:true,logic_mode:'ALL',samples:rows.map(r=>({source_region_id:r.id,sample_role:cleanSampleHint(r.sample_hint),sample_name:r.label}))}]})});
  }else if(!await workspaceConfirm('將套用既有規則／流程。新增 Label 不會自動加入既有規則，請先確認引用。繼續？'))return;
  await studioRequest('/api/edge/apply',{method:'POST',body:JSON.stringify({product_id:S.selectedPid})});toast('設定已套用，請回即時檢測確認');
 }catch(e){toast(e.message)}finally{workspaceLock(false)}
}
function cameraForm(){return JSON.stringify([document.getElementById('qtiMode').value,...[...document.querySelectorAll('[data-qti]')].map(e=>e.value)])}
async function workspaceCameraOpen(){if(workspaceBusy)return;document.getElementById('cameraDialog').showModal();await cameraRefresh();}
async function workspaceCameraClose(){if(cameraBaseline&&cameraForm()!==cameraBaseline&&!await workspaceConfirm('放棄尚未儲存的相機設定？'))return;document.getElementById('studioLive').removeAttribute('src');document.getElementById('cameraDialog').close();}
function cameraMode(){const m=document.getElementById('qtiMode').value;document.querySelectorAll('[data-qti]').forEach(e=>e.disabled=!qtiReport?.properties?.[e.dataset.qti]?.supported||m==='off'||(m==='safe'&&e.dataset.qti!=='white_balance_mode'));}
async function cameraRefresh(){
 try{
  const [c,s]=await Promise.all([studioRequest('/api/edge/config'),studioRequest('/api/edge/status')]);const cfg=c.config||c;
  document.getElementById('qtiMode').value=cfg.camera_controls_mode||'safe';qtiReport=s.backend_status?.camera_controls;qtiSavedValues=JSON.parse(cfg.camera_control_values||'{}');
  document.querySelectorAll('[data-qti]').forEach(original=>{let e=original;const k=e.dataset.qti,p=qtiReport?.properties?.[k];
   if(p?.choices?.length&&e.tagName!=='SELECT'){e=document.createElement('select');e.dataset.qti=k;e.dataset.default=original.dataset.default;original.replaceWith(e);}
   if(e.tagName==='SELECT')e.innerHTML=(p?.choices||[]).map(c=>`<option value="${c.value}" data-i18n-skip>${esc(c.label)}</option>`).join('');
   e.value=qtiSavedValues[k]??p?.current??p?.default??e.dataset.default;if(p){e.min=p.min;e.max=p.max;}
   e.parentElement.querySelector('small').textContent=p?.supported?'設備支援':'尚未確認設備支援';
  });cameraMode();cameraBaseline=cameraForm();
  document.getElementById('qtiState').textContent=s.error||(!s.running?'相機未啟動':s.backend!=='qti'?'目前不是 QTI 相機':qtiReport?.verified?'QTI 設定已讀回，請確認實際影像':'等待設備確認');
  document.getElementById('qtiApplied').textContent=qtiReport?.mode==='safe'?'目前只套用白平衡':'取像與正式檢測共用相機設定';
 }catch(e){document.getElementById('qtiState').textContent=e.message}
}
async function cameraStart(){
 if(workspaceBusy)return;workspaceLock(true);try{await studioRequest('/api/edge/start',{method:'POST'});document.getElementById('studioLive').src='/api/edge/live.mjpg?mode=raw';document.getElementById('studioLive').hidden=false;
  for(let i=0;i<12;i++){const s=await studioRequest('/api/edge/status');if(s.error)throw Error(s.error);if(s.frame_fresh)break;await new Promise(r=>setTimeout(r,500));}
 }catch(e){document.getElementById('qtiState').textContent=e.message}finally{workspaceLock(false);await cameraRefresh()}
}
async function cameraApply(){
 if(workspaceBusy)return;if(workspacePending()){alert('請先儲存或取消樣板編輯，再變更相機');return;}
 const values={...qtiSavedValues};document.querySelectorAll('[data-qti]').forEach(e=>{if(!e.disabled)values[e.dataset.qti]=Number(e.value)});
 workspaceLock(true);try{
  await studioRequest('/api/edge/config',{method:'PUT',body:JSON.stringify({restart:true,camera_controls_mode:document.getElementById('qtiMode').value,camera_control_values:values})});
  cameraBaseline=cameraForm();toast('相機設定已儲存，請重新擷取並驗證樣板');
 }catch(e){document.getElementById('qtiState').textContent=e.message;workspaceLock(false);return;}
 workspaceLock(false);await cameraStart();
}
window.addEventListener('beforeunload',e=>{if(workspacePending()&&!workspaceLeaving){e.preventDefault();e.returnValue='';}});
document.getElementById('cameraDialog').addEventListener('cancel',e=>{e.preventDefault();workspaceCameraClose()});

function workspaceExpand(){document.body.classList.toggle('expanded-label');document.getElementById('workspaceExpand').textContent=document.body.classList.contains('expanded-label')?'收回標記':'展開標記';if(labelImage)labelRender()}
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&document.body.classList.contains('expanded-label'))workspaceExpand()});
const originalPin=pinCurrentFrame;pinCurrentFrame=function(){S.clearTemplate=false;originalPin();if(labelImage&&labelScale===null)labelRender()};

async function workspaceClearTemplates(){
 if(workspaceBusy||!S.editMode)return;
 if(!await workspaceConfirm('清除這個產品的全部樣板、Label 與取樣畫面？按「儲存樣板」才會生效；取消編輯可以還原。產品與流程會保留，仍被引用的 Label 會阻止儲存。'))return;
 resetAll();S.clearTemplate=true;renderTable();labelControls();workspaceDirtyUI();
 toast('樣板已暫時清除；請儲存或取消修改');
}


// App-owned confirmation stays visible even when the editor is temporarily locked.
function workspaceConfirm(message){return new Promise(resolve=>{
 const d=document.createElement('dialog');d.className='workspace-confirm';
 const p=document.createElement('p');p.textContent=message;d.appendChild(p);
 const no=document.createElement('button'),yes=document.createElement('button');
 no.className='btn';yes.className='btn primary';no.textContent='取消';yes.textContent='確認';
 const done=value=>{d.close();d.remove();resolve(value)};
 no.onclick=()=>done(false);yes.onclick=()=>done(true);d.oncancel=e=>{e.preventDefault();done(false)};
 d.append(no,yes);document.body.appendChild(d);d.showModal();no.focus();
})}
