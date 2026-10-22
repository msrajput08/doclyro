/* Doclyro visual page selection. PDF.js renders locally in the browser;
   the original File is uploaded only when Process is clicked. */
'use strict';
(() => {
  const host = document.getElementById('pagePreview');
  if (!host) return;
  const PDFJS_URL = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
  const WORKER_URL = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
  const selectable = new Set(['remove-pages', 'extract-pages', 'rotate']);
  let generation = 0, tool = '', file = null, pdf = null, task = null, observer = null;
  let chosen = new Set(), canvasJobs = 0, pending = [], displayed = new Map();
  let fileUrl = null, lightboxPage = 0, lightboxRender = null;
  const MAX_CANVASES = 30, WORKERS = 2;
  host.innerHTML = `<div class="page-preview-top"><div><strong>All PDF pages</strong><p id="pagePreviewStatus" role="status">Select a PDF to preview every page.</p></div><span id="pagePreviewCount" class="page-preview-count"></span></div>
    <div id="pagePreviewActions" class="page-preview-actions" hidden><span id="pageSelectedCount"></span><button type="button" id="pageSelectAll">Select all</button><button type="button" id="pageClearSelection">Clear selection</button><small>Use the checkbox to select pages; click a page to enlarge it.</small></div>
    <div id="pagePreviewGrid" class="page-preview-grid" aria-label="PDF pages"></div>
    <div class="page-preview-fallback" id="pagePreviewFallback" hidden><p>Thumbnail renderer unavailable. You can still inspect the PDF below and enter page numbers manually.</p><iframe id="pagePreviewFrame" title="Complete PDF document" loading="lazy"></iframe></div>
    <div id="pageLightbox" class="page-lightbox" hidden role="dialog" aria-modal="true" aria-label="Enlarged PDF page"><div class="page-lightbox-head"><strong id="pageLightboxTitle"></strong><div><button type="button" id="pageLightboxPrev" aria-label="Previous page">←</button><button type="button" id="pageLightboxNext" aria-label="Next page">→</button><button type="button" id="pageLightboxClose" aria-label="Close enlarged page">×</button></div></div><div class="page-lightbox-image"><canvas id="pageLightboxCanvas" role="img" aria-label="Enlarged PDF page"></canvas></div></div>`;
  const el = id => document.getElementById(id);
  const grid = el('pagePreviewGrid'), status = el('pagePreviewStatus');
  function hasSelection() { return selectable.has(tool); }
  function current(seq) { return seq === generation && !!file && !!tool; }
  function pagesField() { return document.getElementById('opt-pages'); }
  function compact(values) {
    const nums = [...values].sort((a,b) => a-b), blocks = [];
    for (let i = 0; i < nums.length;) { let j = i; while (j + 1 < nums.length && nums[j+1] === nums[j] + 1) j++;
      blocks.push(j > i + 1 ? `${nums[i]}-${nums[j]}` : j === i+1 ? `${nums[i]},${nums[j]}` : String(nums[i])); i = j+1; }
    return blocks.join(',');
  }
  function parsePages(input, max) {
    if (!input.trim()) return [];
    const found = new Set();
    for (const part of input.split(',')) {
      const match = part.trim().match(/^(\d+)\s*(?:-\s*(\d+))?$/);
      if (!match) return null;
      const a = Number(match[1]), b = match[2] ? Number(match[2]) : a;
      if (a < 1 || a > max || b < a || b > max) return null;
      for (let i=a;i<=b;i++) found.add(i);
    }
    return [...found];
  }
  function updateSelected(sync = true) {
    el('pageSelectedCount').textContent = `${chosen.size} of ${pdf?.numPages || 0} pages selected`;
    for (const [num, card] of displayed) {
      const active = chosen.has(num); card.classList.toggle('selected',active);
      const checkbox = card.querySelector('input[type="checkbox"]'); if (checkbox) checkbox.checked = active;
    }
    const field = pagesField();
    if (sync && field && pdf && hasSelection()) {
      field.value = tool === 'rotate' && chosen.size === pdf.numPages ? '' : compact(chosen);
      field.dispatchEvent(new Event('change', {bubbles:true}));
    }
  }
  function pick(num, active) { if (active) chosen.add(num); else chosen.delete(num); updateSelected(); }
  function unmountCanvas(card) { const canvas = card.querySelector('canvas'); if (!canvas || !canvas.width) return;
    canvas.width = 0; canvas.height = 0; card.dataset.drawn = ''; }
  function limitCanvases(skip) {
    const mounted = [...displayed.values()].filter(c=>c.querySelector('canvas')?.width);
    if (mounted.length <= MAX_CANVASES) return;
    mounted.filter(c=>c!==skip && !c.matches(':hover')).slice(0,mounted.length-MAX_CANVASES).forEach(unmountCanvas);
  }
  async function pump() {
    if (canvasJobs>=WORKERS || !pending.length) return;
    const entry = pending.shift(); const {card,num,seq} = entry;
    if (!current(seq) || !pdf || card.dataset.drawn || card.dataset.drawing) {pump();return;}
    card.dataset.drawing='yes'; canvasJobs++;
    try {
      const page = await pdf.getPage(num);
      if (!current(seq)) return;
      const viewport = page.getViewport({scale:1});
      const scale = Math.min(1.1, 150/Math.max(viewport.width,1));
      const view = page.getViewport({scale});
      const canvas = card.querySelector('canvas');
      canvas.width=Math.max(1,Math.ceil(view.width));canvas.height=Math.max(1,Math.ceil(view.height));
      await page.render({canvasContext:canvas.getContext('2d',{alpha:false}),viewport:view}).promise;
      if (current(seq)) {card.dataset.drawn='yes';limitCanvases(card);}
    } catch { card.querySelector('.page-thumb-placeholder').textContent='Preview unavailable'; }
    finally { delete card.dataset.drawing; canvasJobs--; pump(); }
  }
  function schedule(card, num, seq) {
    if (!current(seq) || card.dataset.drawn || card.dataset.drawing || pending.some(p=>p.card===card)) return;
    pending.push({card,num,seq}); pump();
  }
  function buildCards(seq) {
    grid.replaceChildren();displayed.clear(); pending=[];
    if (observer) observer.disconnect();
    observer = 'IntersectionObserver' in window ? new IntersectionObserver(entries => {
      for (const entry of entries) if (entry.isIntersecting) schedule(entry.target, Number(entry.target.dataset.page), seq);
    },{root:null,rootMargin:'350px 0px'}) : null;
    const fragment=document.createDocumentFragment();
    for (let num=1;num<=pdf.numPages;num++) {
      const card=document.createElement('article'); card.className='page-thumb-card';card.dataset.page=String(num);
      const preview=document.createElement('button'); preview.type='button';preview.className='page-thumb-open';preview.title=`Enlarge page ${num}`;preview.setAttribute('aria-label',`Enlarge page ${num}`);
      preview.innerHTML='<span class="page-thumb-placeholder">Loading…</span><canvas aria-hidden="true"></canvas>';
      preview.onclick=()=>openLightbox(num);
      const bottom=document.createElement('div');bottom.className='page-thumb-footer';
      const caption=document.createElement('span');caption.textContent=`Page ${num}`;bottom.append(caption);
      if (hasSelection()) {
        const label=document.createElement('label');label.className='page-thumb-select';
        const cb=document.createElement('input');cb.type='checkbox';cb.setAttribute('aria-label',`${tool==='remove-pages'?'Remove':tool==='extract-pages'?'Extract':'Rotate'} page ${num}`);
        cb.checked=chosen.has(num);cb.onchange=()=>pick(num,cb.checked);
        label.append(cb,document.createTextNode(' Select'));bottom.append(label);
      }
      card.append(preview,bottom); displayed.set(num,card);fragment.append(card);
    }
    grid.append(fragment);updateSelected(false);
    if (observer) for (const card of displayed.values()) observer.observe(card);
    else for (const [num,card] of displayed) schedule(card,num,seq);
  }
  let libraryLoading=null;
  function ensurePDFJS() {
    if (window.pdfjsLib) return Promise.resolve(window.pdfjsLib);
    if (libraryLoading) return libraryLoading;
    const loadScript=(src,worker)=>new Promise((resolve,reject)=>{
      const script=document.createElement('script');script.src=src;script.async=true;script.crossOrigin='anonymous';
      script.onload=()=>window.pdfjsLib ? resolve({lib:window.pdfjsLib,worker}):reject(Error('PDF renderer unavailable'));
      script.onerror=()=>reject(Error('Could not load '+src));document.head.append(script);
    });
    // Prefer same-origin vendored PDF.js (bundled into the Docker image).
    libraryLoading=loadScript('/vendor/pdf.min.js','/vendor/pdf.worker.min.js')
      .catch(()=>loadScript(PDFJS_URL,WORKER_URL))
      .then(({lib,worker})=>{lib.GlobalWorkerOptions.workerSrc=worker;return lib;})
      .catch(err=>{libraryLoading=null;throw err;});
    return libraryLoading;
  }
  async function loadDocument(f, seq) {
    const lib=await ensurePDFJS();
    if (!current(seq)) return null;
    const bytes=new Uint8Array(await f.arrayBuffer());
    if (!current(seq)) return null;
    const loading=lib.getDocument({data:bytes,enableXfa:false,isEvalSupported:false});task=loading;
    loading.onPassword=(update,reason)=>{
      if(!current(seq))return;
      const pw=window.prompt(reason===2?'Incorrect password. Enter the PDF password:':'Enter the password to preview this PDF:');
      if (pw!==null) {const field=document.getElementById('opt-password');if(field)field.value=pw;update(pw);}
      else loading.destroy();
    };
    return await loading.promise;
  }
  async function fallback(f,seq,message) {
    if(!current(seq))return;
    status.textContent=message+' The complete document is available in the browser viewer below.';
    grid.replaceChildren();el('pagePreviewFallback').hidden=false;
    fileUrl=URL.createObjectURL(f);el('pagePreviewFrame').src=fileUrl;
    try { const form=new FormData();form.append('file',f,f.name);
      const res=await fetch('/api/inspect',{method:'POST',body:form}); if(!res.ok||!current(seq))return;
      const meta=await res.json();el('pagePreviewCount').textContent=`${meta.pages} pages`;
      if(hasSelection()) { pdf={numPages:meta.pages};chosen=new Set(tool==='rotate'?Array.from({length:meta.pages},(_,i)=>i+1):[1]); buildNumericFallback(meta.pages); }
    }catch{/* iframe still lets users inspect pages */}
  }
  function buildNumericFallback(count) {
    grid.replaceChildren(); displayed.clear();
    const fragment=document.createDocumentFragment();
    for(let n=1;n<=count;n++) {const label=document.createElement('label');label.className='page-number-fallback';
      const input=document.createElement('input');input.type='checkbox';input.checked=chosen.has(n);
      input.onchange=()=>pick(n,input.checked);label.append(input,document.createTextNode(` Page ${n}`));
      const article=document.createElement('article');article.className='page-thumb-card';article.append(label);fragment.append(article);displayed.set(n,article);}
    grid.append(fragment);updateSelected(false);
  }
  function onOpen(slug) {reset();tool=slug||'';host.hidden=true;}
  function reset() {
    generation++;pending=[];if(observer){observer.disconnect();observer=null;}
    if(task){try{task.destroy()}catch{}task=null;}
    if(pdf){try{pdf.destroy?.()}catch{}pdf=null;}
    if(fileUrl){URL.revokeObjectURL(fileUrl);fileUrl=null;}
    file=null;chosen.clear();displayed.clear();grid.replaceChildren();
    el('pagePreviewFallback').hidden=true;el('pagePreviewFrame').removeAttribute('src');
    el('pageLightbox').hidden=true;el('pagePreviewCount').textContent='';
    host.hidden=true;
  }
  function onClose() {reset();tool='';}
  async function onFiles(files) {
    const f=(files||[]).find(item=>/\.pdf$/i.test(item.name));
    if(f===file)return;reset();
    if(!f||tool==='organize'||tool==='compare'||tool==='sign-certificate')return;
    file=f;host.hidden=false;el('pagePreviewActions').hidden=!hasSelection();
    status.textContent='Opening PDF in your browser…';const seq=generation;
    try{
      pdf=await loadDocument(f,seq);if(!current(seq)||!pdf)return;
      el('pagePreviewCount').textContent=`${pdf.numPages} pages`;
      status.textContent=`${f.name} · ${pdf.numPages} page${pdf.numPages===1?'':'s'} · Scroll to explore. Thumbnails render when visible.`;
      chosen=new Set(tool==='rotate'?Array.from({length:pdf.numPages},(_,i)=>i+1):hasSelection()?[1]:[]);
      buildCards(seq);
      const field=pagesField();if(field&&hasSelection()) {
        field.addEventListener('input',()=>{if(!pdf||!current(seq))return;const parsed=parsePages(field.value,pdf.numPages);
          if(parsed!==null){chosen=new Set(tool==='rotate'&&!field.value.trim()?Array.from({length:pdf.numPages},(_,i)=>i+1):parsed);updateSelected(false);}}, {signal:fieldAbort.signal});
      }
    }catch(error) {if(current(seq))await fallback(f,seq,error?.message||'Could not render thumbnails.');}
  }
  let fieldAbort=new AbortController();
  const oldReset=reset;
  reset=function(){fieldAbort.abort();fieldAbort=new AbortController();oldReset();};
  function options(slug){if(!hasSelection()||slug!==tool||!pdf)return {};
    const field=pagesField();
    if(field){const entered=parsePages(field.value,pdf.numPages);
      if(entered===null)throw Error(`Invalid page range. Use page numbers from 1 to ${pdf.numPages}, e.g. 1,3-5.`);
      chosen=new Set(tool==='rotate'&&!field.value.trim()?Array.from({length:pdf.numPages},(_,i)=>i+1):entered);
    }
    if(!chosen.size)throw Error('Select at least one page.');
    if(tool==='remove-pages'&&chosen.size===pdf.numPages)throw Error('You must keep at least one page. Deselect a page before removing.');
    return {pages:tool==='rotate'&&chosen.size===pdf.numPages?'':compact(chosen)};
  }
  async function openLightbox(num) {
    if(!pdf || !pdf.getPage)return;
    lightboxPage=num;el('pageLightbox').hidden=false;await drawLightbox();
  }
  async function drawLightbox() {
    const seq=generation,num=lightboxPage;
    if(!pdf || !current(seq))return;
    el('pageLightboxTitle').textContent=`Page ${num} of ${pdf.numPages}`;
    el('pageLightboxPrev').disabled=num<=1;el('pageLightboxNext').disabled=num>=pdf.numPages;
    if(lightboxRender) {try{lightboxRender.cancel()}catch{}lightboxRender=null;}
    try {const page=await pdf.getPage(num);if(!current(seq)||lightboxPage!==num)return;
      const c=el('pageLightboxCanvas');const viewport=page.getViewport({scale:1});
      const scale=Math.min(2.0,900/Math.max(viewport.width,1));const v=page.getViewport({scale});
      c.width=Math.ceil(v.width);c.height=Math.ceil(v.height);
      lightboxRender=page.render({canvasContext:c.getContext('2d',{alpha:false}),viewport:v});
      await lightboxRender.promise;
    }catch(e){if(e.name!=='RenderingCancelledException')status.textContent='Could not render enlarged page.';}
  }
  el('pageLightboxClose').onclick=()=>{el('pageLightbox').hidden=true;};
  el('pageLightboxPrev').onclick=()=>{if(lightboxPage>1){lightboxPage--;drawLightbox();}};
  el('pageLightboxNext').onclick=()=>{if(pdf&&lightboxPage<pdf.numPages){lightboxPage++;drawLightbox();}};
  el('pageSelectAll').onclick=()=>{if(pdf){chosen=new Set(Array.from({length:pdf.numPages},(_,i)=>i+1));updateSelected();}};
  el('pageClearSelection').onclick=()=>{chosen.clear();updateSelected();};
  document.addEventListener('keydown',e=>{if(el('pageLightbox').hidden)return;
    if(e.key==='Escape') {el('pageLightbox').hidden=true;e.stopPropagation();}
    else if(e.key==='ArrowLeft'){el('pageLightboxPrev').click();}else if(e.key==='ArrowRight'){el('pageLightboxNext').click();}
  },true);
  window.DoclyroPDF={ensurePDFJS,load:async f => {const lib=await ensurePDFJS();return lib.getDocument({data:new Uint8Array(await f.arrayBuffer()),isEvalSupported:false}).promise;}};
  window.DoclyroPagePreview={onOpen,onClose,onFiles,options};
})();
