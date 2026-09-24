let inspectionState={},inspectionBusy=false,inspectionToken=null,inspectionPending=null,historyOffset=0;
const verdictText={OK:'合格',NG:'不合格',UNKNOWN:'待確認 · 請調整後重拍'};
function renderInspection(s){
 inspectionState=s;const active=s.active,last=s.last;
 $('inspectionSN').disabled=!!active||inspectionBusy||!!inspectionPending;
 if(active)$('inspectionSN').value=active.sn;
 $('inspectionSN').placeholder=s.require_sn?'請掃描序號，再按拍照判定':'序號（選填）';
 $('inspectionRequireSN').checked=!!s.require_sn;$('inspectionRequireSN').disabled=!!active||inspectionBusy;
 $('inspectionCapture').disabled=inspectionBusy||!lastStatus.inference_ready;
 $('inspectionClose').hidden=!active;$('inspectionClose').disabled=inspectionBusy;
 $('inspectionCapture').textContent=inspectionBusy?'正在判定與保存…':active?'重新拍照判定':'拍照判定';
 $('inspectionVerdict').textContent=last?verdictText[last.verdict]:'準備好，即可拍照';
 $('inspectionVerdict').dataset.verdict=last?.verdict||'';
 $('inspectionHint').textContent=active?'目前產品已鎖定。重拍會保留每次紀錄；完成後按「結束此件」。':'單張判定會保存原圖與結果，不代表整套步驟已完成。';
 $('inspectionEvidence').hidden=!last;if(last)$('inspectionEvidence').src=A+'/history/'+encodeURIComponent(last.id)+'/result';
}
async function refreshInspection(){try{renderInspection(await req(A+'/inspection'))}catch(e){$('inspectionCapture').disabled=true;$('inspectionHint').textContent='無法讀取檢測狀態，請重新整理後再操作。'}}
async function inspectionAction(action){
 if(inspectionBusy)return;
 const requestedPreference=$('inspectionRequireSN').checked;
 inspectionBusy=true;renderInspection(inspectionState);
 try{
  let payload={action,sn:$('inspectionSN').value,cycle_id:inspectionState.active?.id,require_sn:requestedPreference};
  if(action==='capture'){inspectionToken=inspectionToken||crypto.randomUUID();payload=inspectionPending||{...payload,request_id:inspectionToken};inspectionPending=payload;}
  const response=await fetch(A+'/inspection',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:AbortSignal.timeout(30000)});
  const s=await response.json();
  if(!response.ok){inspectionToken=null;inspectionPending=null;throw Error(s.error||'檢測失敗');}
  inspectionToken=null;inspectionPending=null;if(action==='close')$('inspectionSN').value='';renderInspection(s);
  if(action==='capture')message('已保存檢測紀錄','ok');
 }catch(e){message(e.message,'err');await refreshInspection();}
 finally{inspectionBusy=false;renderInspection(inspectionState);}
}
async function loadHistory(reset=false){
 if(reset)historyOffset=0;
 try{const d=await req(A+'/history?offset='+historyOffset+'&q='+encodeURIComponent($('historySearch').value));
 $('historyBody').innerHTML=d.items.map(r=>`<tr><td>${esc(new Date(r.created*1000).toLocaleString())}</td><td><span ${r.sn?'data-i18n-skip':''}>${esc(r.sn||'未填序號')}</span><br><span class="subtle">產品 ${esc(r.product_id)}</span></td><td><span class="state ${r.verdict==='OK'?'good':r.verdict==='NG'?'bad':'warn'}">${esc(verdictText[r.verdict])}</span></td><td><a class="history-link" target="_blank" rel="noopener" href="${A}/history/${encodeURIComponent(r.id)}/raw">原圖</a> · <a class="history-link" target="_blank" rel="noopener" href="${A}/history/${encodeURIComponent(r.id)}/result">結果</a> · <a class="history-link" target="_blank" rel="noopener" href="${A}/history/${encodeURIComponent(r.id)}/metadata">明細</a></td></tr>`).join('')||'<tr><td colspan="4" class="history-empty">還沒有拍照判定紀錄。完成第一次檢測後會出現在這裡。</td></tr>';
 $('historyPrev').disabled=historyOffset===0;$('historyNext').disabled=!d.more;$('historyPage').textContent='第 '+(historyOffset/30+1)+' 頁';
 }catch(e){message(e.message,'err');}
}
document.addEventListener('DOMContentLoaded',()=>{
 refreshInspection();
 $('inspectionSN').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();inspectionAction('capture')}});
 // Status polling already determines camera readiness; this timer never creates inspections.
 setInterval(()=>{if(!inspectionBusy)$('inspectionCapture').disabled=!lastStatus.inference_ready},800);
});
