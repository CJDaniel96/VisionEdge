const el=id=>document.getElementById(id),camFields=[['white_balance_mode','白平衡模式'],['exposure_compensation','亮度（曝光補償）'],['iso_mode','ISO 模式'],['manual_iso_value','手動 ISO'],['antibanding','抗閃爍模式'],['contrast','對比'],['saturation','飽和度'],['sharpness','銳利度']];
let cameraState={},capabilities={},savedValues={},initialValues={},baseline='',busy=false,leaving=false;
const form=()=>JSON.stringify([el('mode').value,...camFields.map(([k])=>el(k)?.value)]);
const dirty=()=>!!baseline&&form()!==baseline;
const say=m=>el('notice').textContent=m;
async function request(url,options={}){const r=await fetch(url,{cache:'no-store',...options,headers:{'Content-Type':'application/json'},signal:AbortSignal.timeout(20000)});const d=await r.json();if(!r.ok||d.success===false||d.ok===false)throw Object.assign(Error(d.error||'操作失敗'),{configSaved:!!d.config_saved});return d}
function ask(message){return new Promise(resolve=>{const d=document.createElement('dialog'),p=document.createElement('p');p.textContent=message;d.appendChild(p);for(const [label,ok] of [['取消',false],['確認',true]]){const b=document.createElement('button');b.textContent=label;b.onclick=()=>{d.close();d.remove();resolve(ok)};d.appendChild(b)}d.oncancel=e=>{e.preventDefault();d.close();d.remove();resolve(false)};document.body.appendChild(d);d.showModal()})}
function renderEnabled(){for(const [k] of camFields){const e=el(k);if(e)e.disabled=busy||!capabilities[k]?.supported||capabilities[k]?.current===undefined||el('mode').value==='off'||(el('mode').value==='safe'&&k!=='white_balance_mode')}
 el('mode').disabled=busy;el('start').disabled=busy;el('refresh').disabled=busy;el('discard').disabled=busy||!dirty();el('apply').disabled=busy||!dirty()||!cameraState.frame_fresh||cameraState.backend!=='qti'||!!cameraState.recording;
}
async function loadCamera(){
 const [c,s]=await Promise.all([request('/api/edge/config'),request('/api/edge/status')]);cameraState=s;const cfg=c.config||c;
 savedValues=typeof cfg.camera_control_values==='string'?JSON.parse(cfg.camera_control_values||'{}'):(cfg.camera_control_values||{});capabilities=s.backend_status?.camera_controls?.properties||{};el('mode').value=cfg.camera_controls_mode||'safe';
 el('basic').replaceChildren();el('advanced').replaceChildren();initialValues={};
 camFields.forEach(([k,title],i)=>{const p=capabilities[k],label=document.createElement('label'),text=document.createElement('span');text.textContent=title;label.appendChild(text);const e=document.createElement(p?.choices?.length?'select':'input');e.id=k;
  if(p?.choices?.length)for(const c of p.choices){const o=document.createElement('option');o.value=c.value;o.textContent=c.label;o.dataset.i18nSkip='';e.appendChild(o)}else{e.type='number';e.step='1';if(p){e.min=p.min;e.max=p.max}}
  e.value=savedValues[k]??p?.current??'';initialValues[k]=e.value;e.oninput=renderEnabled;label.appendChild(e);const hint=document.createElement('small');hint.textContent=!p?'尚未取得設備能力':!p.supported?'設備未提供此控制':p.current===undefined?'無法讀回，暫不允許修改':'設備讀回';label.appendChild(hint);
  if(p?.current!==undefined){const n=document.createElement('small');n.dataset.i18nSkip='';n.textContent=String(p.current)+(p.min!==undefined?` (${p.min} ~ ${p.max})`:'');label.appendChild(n)}el(i<5?'basic':'advanced').appendChild(label);
 });baseline=form();renderEnabled();el('device').textContent=s.backend||'—';
 if(s.frame_fresh){el('preview').src='/api/edge/live.mjpg?mode=raw';el('preview').hidden=false}else{el('preview').hidden=true;el('preview').removeAttribute('src')}
 say(s.error||(!s.running?'相機未啟動':s.backend!=='qti'?'目前不是 QTI 相機':s.frame_fresh?'相機就緒，請確認實際影像':'等待設備確認'));
}
async function refreshCamera(){if(busy)return;if(dirty()&&!await ask('重新讀取會放棄尚未儲存的修改，確定繼續？'))return;busy=true;renderEnabled();try{await loadCamera()}catch(e){say(e.message)}finally{busy=false;renderEnabled()}}
async function discardCamera(){await refreshCamera()}
async function waitReady(){for(let i=0;i<20;i++){const s=await request('/api/edge/status');if(s.error)throw Error(s.error);if(s.frame_fresh)return;await new Promise(r=>setTimeout(r,500))}throw Error('相機尚未就緒，請查看設備狀態')}
async function startPreview(){if(busy)return;if(dirty()&&!await ask('啟動預覽會重新讀取並放棄尚未儲存的修改，確定繼續？'))return;busy=true;renderEnabled();try{await request('/api/edge/start',{method:'POST'});await waitReady();await loadCamera()}catch(e){say(e.message)}finally{busy=false;renderEnabled()}}
async function applyCamera(){if(busy||el('apply').disabled)return;const values={...savedValues};for(const [k] of camFields){const e=el(k);if(!e.disabled&&e.value!==initialValues[k]){if(!e.value||!e.checkValidity()){e.reportValidity();return}values[k]=Number(e.value)}}
 if(!await ask('套用相機設定會中斷取像並重新啟動相機，確定繼續？'))return;
 busy=true;renderEnabled();let stored=false;try{await request('/api/edge/config',{method:'PUT',body:JSON.stringify({restart:true,camera_controls_mode:el('mode').value,camera_control_values:values})});stored=true;baseline=form();await waitReady();await loadCamera();say('設定已儲存，相機已恢復取像；請確認預覽並重新驗證樣板')}catch(e){say((stored||e.configSaved?'設定已儲存，但相機尚未恢復：':'套用失敗：')+e.message)}finally{busy=false;renderEnabled()}}
async function leaveCamera(path){if(busy)return;if(dirty()&&!await ask('尚有未儲存的修改，確定離開？'))return;leaving=true;location.href=path+'?product_id='+(new URLSearchParams(location.search).get('product_id')||cameraState.product_id||0)}
window.addEventListener('beforeunload',e=>{if((dirty()||busy)&&!leaving){e.preventDefault();e.returnValue=''}});
refreshCamera();
