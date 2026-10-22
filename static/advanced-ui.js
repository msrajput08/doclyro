/* PDFCraft Studio: PDF page editing, hand-drawn signatures & configurable workflows.
   All edits are serialized as declarative commands and applied on the server. */
'use strict';
(()=>{
 const el=id=>document.getElementById(id);
 const visual=el('visualEditor'),work=el('workflowBuilder'),sig=el('signatureBuilder'),watermark=el('watermarkBuilder');
 const E={file:null,meta:null,page:1,elements:[],mode:'text',image:null,url:null,seq:0,draw:null,signature:false,workflow:[],watermarkImage:null};
 const editable=['edit','forms','redact','crop'];
 const actions=[['text','Text'],['replace-text','Replace text'],['rectangle','Rectangle'],['ellipse','Ellipse'],['line','Line'],['highlight','Highlight'],['freehand','Freehand'],['image','Image / logo'],['sticky-note','Sticky note'],['link','HTTPS link'],['redact','Redact region'],['crop-region','Crop rectangle'],['field-text','Text field'],['field-multiline','Multiline field'],['field-checkbox','Checkbox'],['field-dropdown','Dropdown'],['field-listbox','List box'],['field-radio-group','Radio group']];
 const defFor={rotate:{angle:90},watermark:{text:'DRAFT',opacity:.25},'page-numbers':{start:1,position:'bottom'},crop:{left:10,right:10,top:10,bottom:10},compress:{quality:'ebook'},protect:{new_password:''},redact:{text:'CONFIDENTIAL'},ocr:{language:'eng',dpi:170},'remove-pages':{pages:'2'},'extract-pages':{pages:'1'},organize:{pages:''},sign:{text:'Signed'},repair:{}};
 const html=`<div class="adv-heading"><strong>Visual PDF editor</strong><span>Draw over a page to place objects. Changes are applied to your downloaded PDF.</span></div>
 <div class="adv-controls"><label>Tool<select id="drawMode"></select></label><label>Text / field name<input id="drawText" value="New text" maxlength="150"/></label><label>Find (replace)<input id="drawSearch" value="" placeholder="Exact text"/></label><label>Color<input type="color" id="drawColor" value="#28374a"/></label><label>Size<input type="number" id="drawFont" value="16" min="5" max="96"/></label><label>Dropdown items<input id="drawChoices" value="Yes,No"/></label><label>Image<input id="drawUpload" type="file" accept="image/png,image/jpeg,image/webp"/></label></div>
 <div class="adv-pager"><button type="button" id="drawPrevious">← Previous</button><span id="drawPageText">Page 1</span><button type="button" id="drawNext">Next →</button><button type="button" id="drawUndo">Undo</button><button type="button" id="drawClear">Clear page</button><button type="button" id="autoFields">Suggest form fields</button></div>
 <div class="adv-stage"><div class="adv-canvasbox" id="drawPageBox"><img id="drawPageImage" alt="PDF page for editing"/><canvas id="drawCanvas" aria-label="PDF editing canvas"></canvas></div></div>
 <p class="adv-status" id="drawStatus">Upload a PDF to begin.</p><div id="drawItems" class="adv-items"></div>`;
 visual.innerHTML=html;
 for(const [slug,name] of actions){const o=document.createElement('option');o.value=slug;o.textContent=name;el('drawMode').append(o)}
 const cvs=el('drawCanvas'),ctx=cvs.getContext('2d');
 const pageSize=()=>E.meta?.page_sizes?.[E.page-1]||{width:595,height:842};
 const point=(event)=>{const r=cvs.getBoundingClientRect(),p=pageSize();return {x:Math.max(0,Math.min(p.width,(event.clientX-r.left)/r.width*p.width)), y:Math.max(0,Math.min(p.height,(event.clientY-r.top)/r.height*p.height))}};
 const scalePoint=(x,y)=>{const p=pageSize();return [x/p.width*cvs.width,y/p.height*cvs.height]};
 const niceRect=(a,b)=>({x:Math.min(a.x,b.x),y:Math.min(a.y,b.y),w:Math.abs(b.x-a.x),h:Math.abs(b.y-a.y)});
 function paint(item){const same=item.page===E.page;if(!same)return;const co=item.color||'#28374a';ctx.strokeStyle=co;ctx.fillStyle=co;ctx.lineWidth=Math.max(1, (item.thickness||2)*cvs.width/pageSize().width);const [x,y]=scalePoint(item.x||0,item.y||0);const [w,h]=scalePoint(item.w||0,item.h||0);ctx.save();
  if(['rectangle','redact','crop-region','highlight','ellipse','image','field-text','field-multiline','field-checkbox','field-dropdown','field-listbox','field-radio-group','link'].includes(item.type)){
    if(item.type==='redact'){ctx.fillStyle='#000';ctx.fillRect(x,y,w,h)}else if(item.type==='crop-region'){ctx.strokeStyle='#e03147';ctx.lineWidth=3;ctx.strokeRect(x,y,w,h)}
    else if(item.type==='highlight'){ctx.globalAlpha=.25;ctx.fillRect(x,y,w,h)}
    else if(item.type==='ellipse'){ctx.beginPath();ctx.ellipse(x+w/2,y+h/2,Math.max(1,w/2),Math.max(1,h/2),0,0,2*Math.PI);ctx.stroke()}
    else {ctx.strokeRect(x,y,w,h); if(item.type.startsWith('field-')||item.type==='image'){ctx.font='11px sans-serif';ctx.fillText(item.name||item.type,x+3,y+14)}}
  } else if(item.type==='line'){let [xx,yy]=scalePoint(item.x2,item.y2);ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(xx,yy);ctx.stroke()}
  else if(item.type==='freehand'){if(item.points?.length>1){ctx.beginPath();item.points.forEach(([px,py],j)=>{let [xx,yy]=scalePoint(px,py);j?ctx.lineTo(xx,yy):ctx.moveTo(xx,yy)});ctx.stroke()}}
  else if(item.type==='text'){ctx.font=`${Math.max(8,item.font_size||16)*cvs.width/pageSize().width}px Arial`;ctx.fillText(item.text||'',x,y+18)}
  else if(item.type==='replace-text'){ctx.font='12px Arial';ctx.fillText(`Replace: ${item.search}`,x,y+8)}
  else if(item.type==='sticky-note'){ctx.font='18px Arial';ctx.fillText('📝',x,y+8)}
  ctx.restore();}
 function renderOverlay(temp){ctx.clearRect(0,0,cvs.width,cvs.height);for(const item of E.elements)paint(item);if(temp)paint(temp);el('drawStatus').textContent=`${E.elements.length} element(s) queued across pages · page ${E.page} of ${E.meta?.pages||1}. Draw on the page; click Process when ready.`;renderItemList()}
 function renderItemList(){const list=el('drawItems');list.replaceChildren();E.elements.forEach((item,i)=>{const button=document.createElement('button');button.type='button';button.className='adv-chip';button.textContent=`${item.type} · p${item.page} ×`;button.title='Remove this element';button.onclick=()=>{E.elements.splice(i,1);renderOverlay()};list.append(button)})}
 function syncCanvas(){const img=el('drawPageImage');if(!img.naturalWidth)return;const r=img.getBoundingClientRect();cvs.width=Math.max(1,Math.round(r.width));cvs.height=Math.max(1,Math.round(r.height));cvs.style.width=r.width+'px';cvs.style.height=r.height+'px';renderOverlay()}
 let updateId=0;
 async function drawPage(){if(!E.file||!E.meta)return;const request=++updateId;const fd=new FormData();fd.append('file',E.file,E.file.name);fd.append('page',String(E.page));
  el('drawPageText').textContent=`Page ${E.page} / ${E.meta.pages}`;el('drawPrevious').disabled=E.page<=1;el('drawNext').disabled=E.page>=E.meta.pages;
  try{const result=await fetch('/api/thumbnail',{method:'POST',body:fd});if(!result.ok)throw Error('Cannot display this PDF page.');const blob=await result.blob();if(request!==updateId)return;const url=URL.createObjectURL(blob);if(E.url)URL.revokeObjectURL(E.url);E.url=url;const img=el('drawPageImage');img.onload=syncCanvas;img.src=url}catch(ex){el('drawStatus').textContent=ex.message}
 }
 function reset(){updateId++;E.file=null;E.meta=null;E.page=1;E.elements=[];E.mode='text';E.image=null;E.draw=null;E.signature=false;E.workflow=[];E.watermarkImage=null;el('drawStatus').textContent='Upload a PDF to begin.';if(E.url)URL.revokeObjectURL(E.url);E.url=null;el('drawPageImage').removeAttribute('src');ctx.clearRect(0,0,cvs.width,cvs.height);el('drawItems').replaceChildren()}
 el('drawMode').onchange=()=>E.mode=el('drawMode').value;
 el('drawPrevious').onclick=()=>{if(E.page>1){E.page--;drawPage()}};
 el('drawNext').onclick=()=>{if(E.meta&&E.page<E.meta.pages){E.page++;drawPage()}};
 el('drawUndo').onclick=()=>{E.elements.pop();renderOverlay()};
 el('drawClear').onclick=()=>{E.elements=E.elements.filter(v=>v.page!==E.page);renderOverlay()};
 el('drawUpload').onchange=async e=>{const file=e.target.files[0];if(!file)return;if(file.size>4e6){el('drawStatus').textContent='Image maximum size: 4 MB.';return}const reader=new FileReader();reader.onload=()=>{E.image=reader.result;E.mode='image';el('drawMode').value='image';el('drawStatus').textContent='Image ready. Drag a rectangle to place it.'};reader.readAsDataURL(file)};
 cvs.addEventListener('pointerdown',event=>{if(!E.file||!E.meta)return;event.preventDefault();cvs.setPointerCapture(event.pointerId);const p=point(event);E.draw={start:p,points:[[p.x,p.y]],current:p}});
 cvs.addEventListener('pointermove',event=>{if(!E.draw)return;const p=point(event);E.draw.current=p;if(E.mode==='freehand')E.draw.points.push([p.x,p.y]);const a=E.draw.start,rect=niceRect(a,p);renderOverlay({type:E.mode,page:E.page,color:el('drawColor').value,thickness:2,...rect,x2:p.x,y2:p.y,points:E.draw.points})});
 cvs.addEventListener('pointerup',event=>{if(!E.draw)return;const d=E.draw;E.draw=null;const end=point(event), rect=niceRect(d.start,end),mode=E.mode;
  const base={page:E.page,type:mode,color:el('drawColor').value,font_size:Number(el('drawFont').value)||16,thickness:2,...rect};
  if(mode==='text'||mode==='replace-text'||mode==='sticky-note'||mode==='link'){
    base.x=d.start.x;base.y=d.start.y;base.w=240;base.h=70;
    base.text=el('drawText').value;
    if(mode==='replace-text'){base.search=el('drawSearch').value;if(!base.search.trim()){el('drawStatus').textContent='Fill Find text first.';return}}
    else if(mode==='link'){base.url=base.text;base.w=240;base.h=32;if(!base.url.startsWith('https://')){el('drawStatus').textContent='Enter a full HTTPS link in the text box.';return}}
    else if(!base.text.trim()){el('drawStatus').textContent='Type something first.';return}
  }else if(mode==='line'){base.x=d.start.x;base.y=d.start.y;base.x2=end.x;base.y2=end.y}
  else if(mode==='freehand'){base.points=d.points; if(base.points.length<2)return}
  else{
    if(base.w<6)base.w=mode==='field-checkbox'?21:mode.startsWith('field-')?190:120;
    if(base.h<6)base.h=mode==='field-checkbox'?21:mode.startsWith('field-')?27:60;
    if(mode==='image'){if(!E.image){el('drawStatus').textContent='Choose an image first.';return}base.data=E.image}
    if(mode.startsWith('field-')){base.name=el('drawText').value||'Field';base.choices=el('drawChoices').value;base.value=(el('drawChoices').value.split(',')[0]||'Yes').trim()}
  }
  if(mode==='crop-region')E.elements=[];E.elements.push(base);renderOverlay()});
 cvs.addEventListener('pointercancel',()=>{E.draw=null;renderOverlay()});
 window.addEventListener('resize',syncCanvas);
 el('autoFields').onclick=async()=>{if(!E.file)return;const fd=new FormData();fd.append('file',E.file,E.file.name);try{const r=await fetch('/api/suggest-fields',{method:'POST',body:fd});const o=await r.json();if(!r.ok)throw Error(o.error||o.detail);E.elements.push(...o.suggestions.slice(0,60));renderOverlay();el('drawStatus').textContent=`Added ${o.suggestions.length} heuristic suggestions. Review placement and delete unsuitable ones.`}catch(e){el('drawStatus').textContent=e.message}};
 const presets=[['Quick optimize',[{tool:'compress',options:{quality:'ebook'}}]],['Stamp & number',[{tool:'watermark',options:{text:'DRAFT'}},{tool:'page-numbers',options:{start:1}}]],['Rotate + protect',[{tool:'rotate',options:{angle:90}},{tool:'protect',options:{new_password:''}}]],['OCR + compress',[{tool:'ocr',options:{language:'eng'}},{tool:'compress',options:{quality:'ebook'}}]]];
 work.innerHTML=`<div class="adv-heading"><strong>Batch processing workflow</strong><span>Run up to 12 PDF processing steps in sequence, and reuse your saved pipeline.</span></div><div class="wf-actions"><label>Template<select id="wfPreset"></select></label><button type="button" id="wfLoadPreset">Load template</button><label>Operation<select id="wfStepTool"></select></label><button type="button" id="wfAdd">+ Add step</button><button type="button" id="wfSave">Save workflow</button><label class="file-button">Load JSON<input id="wfImport" type="file" accept="application/json,.json" hidden></label></div><div id="wfRows"></div><p class="adv-status">Steps run sequentially; changes from one step become input to the next. No files are retained after download.</p>`;
 for(const [name] of presets){const op=document.createElement('option');op.textContent=name;op.value=name;el('wfPreset').append(op)}
 for(const tool of ['compress','rotate','watermark','page-numbers','crop','repair','ocr','remove-pages','extract-pages','organize','redact','protect','sign']){const o=document.createElement('option');o.value=tool;o.textContent=tool.replaceAll('-',' ');el('wfStepTool').append(o)}
 function renderWorkflow(){const root=el('wfRows');root.replaceChildren();E.workflow.forEach((step,i)=>{
   const card=document.createElement('div');card.className='wf-row';const head=document.createElement('div');head.className='wf-row-head';const title=document.createElement('strong');title.textContent=`${i+1}. ${step.tool.replaceAll('-',' ')}`;const up=document.createElement('button');up.type='button';up.textContent='↑';up.title='Move step earlier';up.onclick=()=>{if(i>0){[E.workflow[i-1],E.workflow[i]]=[E.workflow[i],E.workflow[i-1]];renderWorkflow()}};
   const down=document.createElement('button');down.type='button';down.textContent='↓';down.title='Move step later';down.onclick=()=>{if(i+1<E.workflow.length){[E.workflow[i+1],E.workflow[i]]=[E.workflow[i],E.workflow[i+1]];renderWorkflow()}};
   const del=document.createElement('button');del.type='button';del.textContent='Remove';del.onclick=()=>{E.workflow.splice(i,1);renderWorkflow()};head.append(title,up,down,del);
   const label=document.createElement('label');label.textContent='Settings (JSON)';const ta=document.createElement('textarea');ta.value=JSON.stringify(step.options,null,2);ta.oninput=()=>{try{const v=JSON.parse(ta.value);if(v===null||Array.isArray(v)||typeof v!=='object')throw Error();step.options=v;ta.classList.remove('invalid')}catch{ta.classList.add('invalid')}};
   card.append(head,label,ta);root.append(card)})}
 el('wfLoadPreset').onclick=()=>{E.workflow=JSON.parse(JSON.stringify(presets.find(p=>p[0]===el('wfPreset').value)?.[1]||[]));renderWorkflow()};
 el('wfAdd').onclick=()=>{if(E.workflow.length>=12)return;const tool=el('wfStepTool').value;E.workflow.push({tool,options:{...(defFor[tool]||{})}});renderWorkflow()};
 el('wfSave').onclick=()=>{if(!E.workflow.length)return;const blob=new Blob([JSON.stringify(E.workflow,null,2)],{type:'application/json'});const u=URL.createObjectURL(blob);const a=document.createElement('a');a.download='pdfcraft_workflow.json';a.href=u;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)};
 el('wfImport').onchange=async e=>{const f=e.target.files[0];if(!f)return;try{const steps=JSON.parse(await f.text());if(!Array.isArray(steps)||steps.length>12||steps.some(s=>!defFor[s.tool]||typeof s.options!=='object'))throw Error('Invalid workflow file.');E.workflow=steps;renderWorkflow()}catch(ex){alert('Cannot load workflow: '+ex.message)}};
 sig.innerHTML=`<div class="adv-heading"><strong>Draw your signature</strong><span>Use a mouse, stylus or finger. The drawing will be stamped on the PDF page.</span></div><canvas id="signPad" width="680" height="180" aria-label="Handwritten signature drawing area"></canvas><div class="wf-actions"><button id="clearSign" type="button">Clear drawing</button><span>Use page, X, Y, width and height options to position the signature.</span></div>`;
 const pad=el('signPad'),g=pad.getContext('2d');g.strokeStyle='#172b4e';g.lineWidth=3;g.lineCap='round';g.lineJoin='round';let drawing=false;
 const position=(e)=>{const r=pad.getBoundingClientRect();return [(e.clientX-r.left)/r.width*pad.width,(e.clientY-r.top)/r.height*pad.height]};
 pad.onpointerdown=e=>{drawing=true;E.signature=true;pad.setPointerCapture(e.pointerId);const [x,y]=position(e);g.beginPath();g.moveTo(x,y);g.lineTo(x+.2,y+.2);g.stroke()};pad.onpointermove=e=>{if(!drawing)return;let [x,y]=position(e);g.lineTo(x,y);g.stroke()};pad.onpointerup=()=>drawing=false;pad.onpointercancel=()=>drawing=false;
 el('clearSign').onclick=()=>{g.clearRect(0,0,pad.width,pad.height);E.signature=false};
 watermark.innerHTML=`<div class="adv-heading"><strong>Image watermark</strong><span>Optionally upload a PNG, JPEG or WebP logo. When present, the image replaces the text watermark. Opacity and position are controlled by tool options below.</span></div><input id="watermarkUpload" type="file" accept="image/png,image/jpeg,image/webp"><span class="adv-status" id="watermarkStatus">No image selected — text watermark will be used.</span>`;
 el('watermarkUpload').onchange=e=>{const f=e.target.files[0];if(!f)return;if(f.size>4_000_000){el('watermarkStatus').textContent='Maximum image size 4 MB.';return}const r=new FileReader();r.onload=()=>{E.watermarkImage=r.result;el('watermarkStatus').textContent='Image ready: '+f.name};r.readAsDataURL(f)};
 function open(slug){reset();visual.hidden=!editable.includes(slug);work.hidden=slug!=='workflow';sig.hidden=slug!=='sign';watermark.hidden=slug!=='watermark';el('autoFields').hidden=slug!=='forms';if(slug==='forms'){E.mode='field-text';el('drawMode').value='field-text';el('drawText').value='Full Name'}else if(slug==='redact'){E.mode='redact';el('drawMode').value='redact'}else if(slug==='crop'){E.mode='crop-region';el('drawMode').value='crop-region'}else{el('drawMode').value='text';el('drawText').value='New text'}el('clearSign').click();if(slug==='workflow')el('wfLoadPreset').click()}
 async function files(f){
  if(!f||!/\.pdf$/i.test(f.name))return;
  if(E.file&&E.file!==f){E.elements=[];E.page=1;renderOverlay()}
  E.file=f;const sequence=++E.seq;const fd=new FormData();fd.append('file',f,f.name);
  try{const r=await fetch('/api/inspect',{method:'POST',body:fd});const meta=await r.json();if(sequence!==E.seq||E.file!==f)return;if(!r.ok)throw Error(meta.error||meta.detail||'Preview failed');E.meta=meta;E.page=1;drawPage()}catch(ex){el('drawStatus').textContent=ex.message}}
 function options(slug){if(slug==='edit'&&E.elements.length)return {elements:E.elements};
   if(slug==='redact'&&E.elements.length)return {elements:E.elements.filter(x=>x.type==='redact')};
   if(slug==='crop'&&E.elements.some(x=>x.type==='crop-region'))return {crop_rect:E.elements.filter(x=>x.type==='crop-region').at(-1)};
   if(slug==='forms'&&E.elements.some(x=>x.type.startsWith('field-')))return {mode:'bulk',elements:E.elements.filter(x=>x.type.startsWith('field-'))};
   if(slug==='sign'&&E.signature)return {signature_image:pad.toDataURL('image/png')};
   if(slug==='watermark'&&E.watermarkImage)return {image_data:E.watermarkImage};
   if(slug==='workflow'){const bad=[...document.querySelectorAll('#wfRows textarea.invalid')];if(bad.length)throw Error('Correct invalid workflow JSON first.');return {steps:E.workflow}}
   return {};
 }
 window.PDFCraftAdvanced={onOpen:open,onClose:reset,onFiles:files,options};
})();
