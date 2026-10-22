/* Accessible multi-file PDF page organizer: drag, reorder, rotate, duplicate, remove.
   The server always performs the final PDF operation; thumbnails are previews only. */
'use strict';
(()=>{
 const root=document.getElementById('organizerBuilder');
 if(!root)return;
 let opened=false, generation=0, selected=[], records=[], busy=false;
 const MAX_PREVIEWS=100;
 const imageUrls=new Set();
 root.innerHTML=`<div class="adv-heading"><strong>Visual page organizer</strong>
   <span>Move pages between PDFs. Drag cards or use the arrows. Rotate, duplicate or remove individual pages, then click Organize PDF.</span></div>
   <p id="organizerStatus" class="adv-status" role="status">Upload PDFs to preview their pages.</p>
   <div class="wf-actions"><button id="organizerReset" type="button">Restore original pages</button>
   <button id="organizerReverse" type="button">Reverse current order</button></div>
   <div id="organizerGrid" class="organizer-grid" aria-label="Pages in output order"></div>`;
 const status=document.getElementById('organizerStatus');
 const grid=document.getElementById('organizerGrid');
 function cleanup(){for(const url of imageUrls)URL.revokeObjectURL(url);imageUrls.clear()}
 function onOpen(slug){opened=slug==='organize';root.hidden=!opened;reset();if(opened)status.textContent='Upload PDFs to organize their pages.'}
 function reset(){generation++;selected=[];records=[];busy=false;cleanup();grid.replaceChildren()}
 function onClose(){opened=false;root.hidden=true;reset()}
 async function metadata(file){const form=new FormData();form.append('file',file,file.name);
  const res=await fetch('/api/inspect',{method:'POST',body:form});const data=await res.json();
  if(!res.ok)throw Error(data.error||data.detail||`Cannot inspect ${file.name}`);
  return data;
 }
 function button(caption,aria,click){const b=document.createElement('button');b.type='button';b.className='organizer-action';b.textContent=caption;b.setAttribute('aria-label',aria);b.onclick=click;return b}
 function move(from,to){if(to<0||to>=records.length||from===to)return;
  const [item]=records.splice(from,1);records.splice(to,0,item);render()}
 function render(){grid.replaceChildren();
  status.textContent=busy?'Loading PDF pages…':`${records.length} page${records.length===1?'':'s'} in the output · ${selected.length} source PDF${selected.length===1?'':'s'}.`;
  records.forEach((record,i)=>{
   const card=document.createElement('article');card.className='organizer-card';card.draggable=true;
   card.setAttribute('aria-label',`Position ${i+1}: ${record.file.name}, page ${record.page}`);
   card.ondragstart=e=>{e.dataTransfer.effectAllowed='move';e.dataTransfer.setData('text/plain',String(i));card.classList.add('dragging')};
   card.ondragend=()=>card.classList.remove('dragging');
   card.ondragover=e=>{e.preventDefault();e.dataTransfer.dropEffect='move';card.classList.add('drop-target')};
   card.ondragleave=()=>card.classList.remove('drop-target');
   card.ondrop=e=>{e.preventDefault();card.classList.remove('drop-target');const start=Number(e.dataTransfer.getData('text/plain'));
       if(Number.isInteger(start))move(start,i)};
   const badge=document.createElement('span');badge.className='organizer-index';badge.textContent=`${i+1}`;
   const image=document.createElement('div');image.className='organizer-thumb';
   if(record.url){const preview=document.createElement('img');preview.src=record.url;preview.alt=`Page ${record.page} preview`;preview.style.transform=`rotate(${record.rotate}deg)`;image.append(preview)}
   else image.textContent='PDF';
   const details=document.createElement('small');details.textContent=`${record.file.name} · p${record.page}`;details.title=details.textContent;
   const controls=document.createElement('div');controls.className='organizer-controls';
   controls.append(button('←','Move earlier',()=>move(i,i-1)),button('→','Move later',()=>move(i,i+1)),
     button('↻','Rotate 90 degrees',()=>{record.rotate=(record.rotate+90)%360;render()}),
     button('＋','Duplicate page',()=>{if(records.length>=800)return;records.splice(i+1,0,{...record});render()}),
     button('×','Remove page',()=>{records.splice(i,1);render()}));
   card.append(badge,image,details,controls);grid.append(card)
  });
 }
 async function loadThumbnails(recordsToLoad,seq){let index=0;
  async function worker(){while(index<recordsToLoad.length){const record=recordsToLoad[index++];
    if(seq!==generation)return;
    try{const form=new FormData();form.append('file',record.file,record.file.name);form.append('page',String(record.page));
        const response=await fetch('/api/thumbnail',{method:'POST',body:form});
        if(!response.ok)continue;
        const blob=await response.blob();if(seq!==generation)return;
        record.url=URL.createObjectURL(blob);imageUrls.add(record.url);render();
    }catch{/* preview failures never modify requested output order */}
  }}
  await Promise.all(Array.from({length:Math.min(4,recordsToLoad.length)},worker));
 }
 async function onFiles(files){if(!opened)return;
  const next=Array.from(files||[]);
  if(next.length===selected.length&&next.every((file,i)=>file===selected[i]))return;
  const seq=++generation;
  const gone=records.filter(record=>!next.includes(record.file));
  for(const record of gone){if(record.url){URL.revokeObjectURL(record.url);imageUrls.delete(record.url)}}
  records=records.filter(record=>next.includes(record.file));
  const newcomers=next.filter(file=>!selected.includes(file));selected=next;busy=Boolean(newcomers.length);render();
  let added=[];
  for(const file of newcomers){
    try{const info=await metadata(file);if(seq!==generation)return;
      if(info.pages>800)throw Error('Individual PDFs are limited to 800 pages.');
      for(let page=1;page<=info.pages;page++)added.push({file,page,rotate:0,url:null});
      if(records.length+added.length>800)throw Error('Organizer limit: 800 output pages.');
    }catch(ex){if(seq!==generation)return;status.textContent=ex.message;busy=false;return}
  }
  if(seq!==generation)return;
  records.push(...added);busy=false;render();
  // A bounded thumbnail budget keeps the organizer responsive for long PDFs.
  loadThumbnails(added.slice(0,MAX_PREVIEWS),seq);
 }
 document.getElementById('organizerReset').onclick=()=>{
   const preserve=selected.slice();selected=[];records=[];cleanup();onFiles(preserve)
 };
 document.getElementById('organizerReverse').onclick=()=>{records.reverse();render()};
 function options(slug){if(slug!=='organize')return {};
   if(busy)throw Error('Page previews are still loading; retry when the organizer is ready.');
   if(!records.length)throw Error('Keep at least one page in the organizer.');
   return {page_sequence:records.map(rec=>({file:selected.indexOf(rec.file),page:rec.page,rotate:rec.rotate}))};
 }
 window.PDFCraftOrganizer={onOpen,onClose,onFiles,options};
})();
