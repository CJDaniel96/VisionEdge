let imageTestBusy=false;
function openImageTest(){
 if(S.editMode||workspaceBusy||imageTestBusy)return;
 if(!S.regions.length){toast('請先儲存至少一個 Label');return;}
 document.getElementById('imageTestResults').replaceChildren();document.getElementById('imageTestStatus').textContent='';document.getElementById('imageTestPreview').hidden=true;
 const select=document.getElementById('imageTestLabel');select.replaceChildren();
 for(const r of S.regions){const o=document.createElement('option');o.value=r.id;o.textContent=r.label+' · '+r.threshold+' · margin '+(r.search_margin||0);o.selected=!!r._sel;select.appendChild(o)}
 document.getElementById('imageTestDialog').showModal();
}
function readTestImage(file){return new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.onerror=()=>reject(Error('無法讀取圖片'));r.readAsDataURL(file)})}
async function runImageTests(files){
 if(imageTestBusy)return;
 const list=Array.from(files),input=document.getElementById('imageTestFiles'),select=document.getElementById('imageTestLabel');input.value='';
 if(!list.length)return;
 if(list.length>20){document.getElementById('imageTestStatus').textContent='一次最多選擇 20 張圖片';return;}
 const pid=S.selectedPid,rid=Number(select.value),label=select.selectedOptions[0]?.textContent||'';
 const root=document.getElementById('imageTestResults'),status=document.getElementById('imageTestStatus'),preview=document.getElementById('imageTestPreview');
 root.replaceChildren();preview.hidden=true;preview.removeAttribute('src');imageTestBusy=true;select.disabled=input.disabled=true;
 try{
  for(let i=0;i<list.length;i++){
   const file=list[i];status.textContent=`${i+1} / ${list.length}`;
   const row=document.createElement('div');row.style.cssText='padding:10px 0;border-bottom:1px solid #dfe2e7';
   const name=document.createElement('div');name.dataset.i18nSkip='';name.textContent=file.name+' — '+label;row.appendChild(name);root.appendChild(row);
   try{
    if(file.size>20*1024*1024)throw Error('圖片超過 20 MB');
    const data=await studioRequest(`/api/products/${pid}/label-library/${rid}/image-test`,{method:'POST',body:JSON.stringify({image_b64:await readTestImage(file)}),signal:AbortSignal.timeout(30000)});
    const r=data.result, verdict=document.createElement('strong');verdict.textContent=r.error?'無法判定':r.pass?'符合':'不符合';row.appendChild(verdict);
    const detail=document.createElement('div');detail.dataset.i18nSkip='';detail.textContent=r.error||`score ${r.score} / threshold ${r.threshold} · margin ${data.search_margin} · X,Y ${r.match_loc?.join(', ')||'—'}`;row.appendChild(detail);
    if(data.sample_hint==='NG'&&r.pass){const warning=document.createElement('div');warning.textContent='NG Label 符合：找到異常';row.appendChild(warning)}
    const view=document.createElement('button');view.className='btn';view.textContent='查看比對位置';view.onclick=()=>{preview.src=asImage(data.image_b64);preview.hidden=false};row.appendChild(view);
    if(i===0)view.onclick();
   }catch(e){const error=document.createElement('div');error.textContent=e.message;row.appendChild(error)}
  }
  status.textContent='圖片驗證完成';
 }finally{imageTestBusy=false;select.disabled=input.disabled=false}
}
