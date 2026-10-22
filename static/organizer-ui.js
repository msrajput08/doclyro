/* Doclyro multi-file page organizer: all-page lazy thumbnails rendered locally.
   The backend performs the PDF transformation and validates page sequences. */
'use strict';
(() => {
  const root=document.getElementById('organizerBuilder');if(!root)return;
  root.innerHTML=`<div class="adv-heading"><strong>Visual page organizer</strong><span>View every page. Drag or use arrows to reorder; rotate, duplicate or remove pages before downloading.</span></div>
    <p id="organizerStatus" class="adv-status" role="status">Upload PDFs to see all pages.</p>
    <div class="wf-actions"><button id="organizerReset" type="button">Restore original pages</button><button id="organizerReverse" type="button">Reverse current order</button></div>
    <div id="organizerGrid" class="organizer-grid" aria-label="Pages in output order"></div>`;
  const status=document.getElementById('organizerStatus'), grid=document.getElementById('organizerGrid');
  let opened=false, generation=0, selected=[], records=[], busy=false, observer=null;
  let pending=[], active=0;
  const docs=new Map(), thumbnails=new Map(), objectUrls=new Set(), inflight=new Set();
  const fileIds=new WeakMap();let nextId=1;
  function identity(file){if(!fileIds.has(file))fileIds.set(file,nextId++);return fileIds.get(file);}
  function key(record){return `${identity(record.file)}:${record.page}`;}
  function cleanup(){
    generation++;pending=[];inflight.clear();if(observer){observer.disconnect();observer=null;}
    for(const url of objectUrls)URL.revokeObjectURL(url);objectUrls.clear();thumbnails.clear();
    for(const doc of docs.values())try{doc.destroy?.()}catch{}docs.clear();
  }
  function reset(){cleanup();selected=[];records=[];busy=false;grid.replaceChildren();}
  function onOpen(slug){opened=slug==='organize';root.hidden=!opened;reset();if(opened)status.textContent='Upload PDFs to see every page.';}
  function onClose(){opened=false;root.hidden=true;reset();}
  async function metadata(file){
    // PDF.js opens the file locally, so opening 300 pages costs zero API calls.
    if(window.DoclyroPDF){try{const doc=await window.DoclyroPDF.load(file);docs.set(file,doc);return {pages:doc.numPages};}catch{/* server metadata fallback */}}
    const form=new FormData();form.append('file',file,file.name);
    const res=await fetch('/api/inspect',{method:'POST',body:form});const data=await res.json();
    if(!res.ok)throw Error(data.error||data.detail||`Cannot inspect ${file.name}`);
    return data;
  }
  function control(text,label,click){const b=document.createElement('button');b.type='button';b.className='organizer-action';b.textContent=text;b.title=label;b.setAttribute('aria-label',label);b.onclick=click;return b;}
  function move(from,to){if(to<0||to>=records.length||from===to)return;const [item]=records.splice(from,1);records.splice(to,0,item);render();}
  function refreshImages(record,url){
    for(const [i,r] of records.entries())if(key(r)===key(record)){
      r.url=url;const card=grid.children[i];if(!card)continue;
      const image=card.querySelector('.organizer-thumb');if(!image)continue;
      image.replaceChildren();const img=document.createElement('img');img.alt=`Page ${r.page} preview`;img.loading='lazy';img.src=url;img.style.transform=`rotate(${r.rotate}deg)`;image.append(img);
    }
  }
  function render(){
    if(observer)observer.disconnect();
    const fragment=document.createDocumentFragment();
    status.textContent=busy?'Loading pages…':`${records.length} page${records.length===1?'':'s'} in output · ${selected.length} PDF${selected.length===1?'':'s'} · Scroll to see every page.`;
    records.forEach((record,i)=>{
      const card=document.createElement('article');card.className='organizer-card';card.draggable=true;card.dataset.index=String(i);
      card.setAttribute('aria-label',`Position ${i+1}: ${record.file.name}, page ${record.page}`);
      card.ondragstart=e=>{e.dataTransfer.effectAllowed='move';e.dataTransfer.setData('text/plain',String(i));card.classList.add('dragging')};
      card.ondragend=()=>card.classList.remove('dragging');
      card.ondragover=e=>{e.preventDefault();e.dataTransfer.dropEffect='move';card.classList.add('drop-target')};
      card.ondragleave=()=>card.classList.remove('drop-target');
      card.ondrop=e=>{e.preventDefault();card.classList.remove('drop-target');const from=Number(e.dataTransfer.getData('text/plain'));if(Number.isInteger(from))move(from,i)};
      const badge=document.createElement('span');badge.className='organizer-index';badge.textContent=String(i+1);
      const thumb=document.createElement('div');thumb.className='organizer-thumb';
      record.url=thumbnails.get(key(record))||null;
      if(record.url){const image=document.createElement('img');image.src=record.url;image.alt=`Page ${record.page} preview`;image.loading='lazy';image.style.transform=`rotate(${record.rotate}deg)`;thumb.append(image)}
      else thumb.textContent=`Page ${record.page}`;
      const info=document.createElement('small');info.textContent=`${record.file.name} · p${record.page}`;info.title=info.textContent;
      const actions=document.createElement('div');actions.className='organizer-controls';
      actions.append(control('←','Move page earlier',()=>move(i,i-1)),control('→','Move page later',()=>move(i,i+1)),
        control('↻','Rotate page 90 degrees',()=>{record.rotate=(record.rotate+90)%360;render()}),
        control('＋','Duplicate page',()=>{if(records.length>=800)return;records.splice(i+1,0,{...record});render()}),
        control('×','Remove page',()=>{records.splice(i,1);render()}));
      card.append(badge,thumb,info,actions);fragment.append(card);
    });
    grid.replaceChildren(fragment);
    const seq=generation;
    observer='IntersectionObserver' in window ? new IntersectionObserver(entries=>{
      entries.forEach(entry=>{if(!entry.isIntersecting)return;const i=Number(entry.target.dataset.index);const r=records[i];if(r&&!r.url)queue(r,seq);});
    },{root:grid,rootMargin:'260px'}) : null;
    if(observer){for(const card of grid.children)observer.observe(card)}
    else records.forEach(r=>{if(!r.url)queue(r,seq)});
  }
  function queue(record,seq){if(seq!==generation||thumbnails.has(key(record))||inflight.has(key(record))||pending.some(x=>key(x.record)===key(record)))return;
    pending.push({record,seq});pump();}
  async function drawThumbnail(record){
    const doc=docs.get(record.file);
    if(doc){const page=await doc.getPage(record.page),unit=page.getViewport({scale:1});
      const viewport=page.getViewport({scale:Math.min(1,145/Math.max(unit.width,1))});
      const canvas=document.createElement('canvas');canvas.width=Math.ceil(viewport.width);canvas.height=Math.ceil(viewport.height);
      await page.render({canvasContext:canvas.getContext('2d',{alpha:false}),viewport}).promise;
      const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',0.72));canvas.width=0;canvas.height=0;
      if(!blob)throw Error('Unable to preview page');return blob;}
    const form=new FormData();form.append('file',record.file,record.file.name);form.append('page',String(record.page));
    const res=await fetch('/api/thumbnail',{method:'POST',body:form});if(!res.ok)throw Error('Preview unavailable');return res.blob();
  }
  function pump(){while(active<2&&pending.length){const {record,seq}=pending.shift();if(seq!==generation)continue;
      active++;inflight.add(key(record));(async()=>{try{const blob=await drawThumbnail(record);if(seq!==generation)return;
        const url=URL.createObjectURL(blob);objectUrls.add(url);thumbnails.set(key(record),url);refreshImages(record,url);
      }catch{/* placeholders stay and the user can still organize via page numbers */}
      finally{inflight.delete(key(record));active--;pump();}})();
    }}
  async function onFiles(files){if(!opened)return;const next=Array.from(files||[]);
    if(next.length===selected.length&&next.every((f,i)=>f===selected[i]))return;
    // Reset eliminates dangling thumbnails for removed source PDFs.
    reset();selected=next;busy=Boolean(next.length);render();const seq=generation;
    const added=[];
    for(const file of next){try{const info=await metadata(file);if(seq!==generation)return;
      if(info.pages>800||added.length+info.pages>800)throw Error('Organizer supports up to 800 pages per operation.');
      for(let page=1;page<=info.pages;page++)added.push({file,page,rotate:0,url:null});
    }catch(err){if(seq===generation){status.textContent=err.message;busy=false;}return;}}
    if(seq!==generation)return;records=added;busy=false;render();
  }
  document.getElementById('organizerReset').onclick=()=>{const files=selected.slice();selected=[];onFiles(files);};
  document.getElementById('organizerReverse').onclick=()=>{records.reverse();render();};
  function options(slug){if(slug!=='organize')return {};
    if(busy)throw Error('PDF page list is still loading; try again in a moment.');
    if(!records.length)throw Error('Keep at least one page in your output PDF.');
    return {page_sequence:records.map(rec=>({file:selected.indexOf(rec.file),page:rec.page,rotate:rec.rotate}))};
  }
  window.PDFCraftOrganizer={onOpen,onClose,onFiles,options};
})();
