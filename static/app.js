'use strict';
const iconPaths={
  merge:'M6 3h9l4 4v11H6z M13 3v5h6 M3 10v11h12 M9 16h5',
  split:'M6 3h9l4 4v14H6z M14 3v5h5 M3 13h19 M11 10v7',
  compress:'M12 2v7 M8 5l4 4 4-4 M12 22v-7 M8 19l4-4 4 4 M2 12h7 M5 8l4 4-4 4 M22 12h-7 M19 8l-4 4 4 4',
  pages:'M5 3h12v15H5z M9 7h4 M9 11h5 M8 21h12V7 M15 3l4 4',
  remove:'M4 3h15v18H4z M8 10l7 7 M15 10l-7 7',
  organize:'M4 4h7v7H4z M14 4h7v7h-7z M4 14h7v7H4z M14 14h7v7h-7z',
  scan:'M7 3H4v5 M17 3h3v5 M4 16v5h4 M20 16v5h-4 M7 9h10v6H7z',
  repair:'M5 4h13v16H5z M9 10l2 3 5-5 M15 4v4h3',
  ocr:'M3 8V4h4 M17 4h4v4 M3 16v4h4 M17 20h4v-4 M7 12h10 M9 9v6 M15 9v6',
  image:'M4 3h16v18H4z M7 15l4-4 3 3 3-5 3 5 M8 7h.01',
  word:'M5 2h11l4 4v16H5z M16 2v5h4 M8 11l2 7 2-4 2 4 2-7',
  ppt:'M5 2h11l4 4v16H5z M16 2v5h4 M9 17v-6h3a2 2 0 010 4H9',
  excel:'M5 2h11l4 4v16H5z M16 2v5h4 M8 11l7 7 M15 11l-7 7',
  html:'M4 4h16v16H4z M9 9l-3 3 3 3 M15 9l3 3-3 3 M14 8l-4 8',
  archive:'M5 4h14v16H5z M4 8h16 M10 12h4',
  rotate:'M3 10a9 9 0 1 1 2 8 M3 3v7h7 M12 8v5l4 2',
  number:'M5 3h14v18H5z M9 7h6 M9 13h2m3 0h2 M9 17h7',
  watermark:'M4 3h16v18H4z M8 8l4 9 4-9 M4 16l16-8',
  crop:'M8 2v16h14 M2 8h16V2 M8 18v4 M18 8h4',
  edit:'M5 4h12v16H5z M9 9h5 M9 13h4 M14 18l6-6 2 2-6 6-4 1z',
  forms:'M5 3h14v18H5z M9 9h7 M9 13h7 M9 17h4 M7 9h.01',
  unlock:'M5 11V8a6 6 0 0 1 11-3 M4 11h16v10H4z M12 15v3',
  protect:'M4 10h16v11H4z M7 10V7a5 5 0 0 1 10 0v3 M12 14v3',
  sign:'M4 20c4-8 4 0 8-7s4 3 8-8 M4 22h16',
  redact:'M5 3h14v18H5z M8 9h8 M8 13h8 M8 17h8 M8 10l8 8',
  compare:'M3 3h8v18H3z M13 3h8v18h-8z M6 9h2 M16 9h2 M16 15h2',
  ai:'M12 2l2 7 7 3-7 2-2 8-3-8-7-2 7-3z M19 2v4 M17 4h4',
  translate:'M3 5h12 M9 2v3 M6 9l6 6 M12 7c-1 4-4 7-8 9 M15 11l4 10 M14 17h7',
  markdown:'M3 6h18v12H3z M7 15V9l3 3 3-3v6 M16 9v6 M14 13l2 2 2-2',
};
function svg(which){return `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${iconPaths[which]||iconPaths.pages}"/></svg>`}
const TOOLS=[
['merge','Merge PDF','Combine multiple PDF files in the order you want.','Organize PDF','merge','red'],
['split','Split PDF','Separate pages into individual or grouped PDF files.','Organize PDF','split','orange'],
['compress','Compress PDF','Reduce PDF file size while preserving useful quality.','Optimize PDF','compress','green'],
['pdf-to-word','PDF to Word','Convert a PDF into an editable Word document.','Convert PDF','word','blue'],
['pdf-to-powerpoint','PDF to PowerPoint','Turn pages into a PowerPoint presentation.','Convert PDF','ppt','orange'],
['pdf-to-excel','PDF to Excel','Extract spreadsheet tables and data from PDF pages.','Convert PDF','excel','green'],
['word-to-pdf','Word to PDF','Convert Microsoft Word documents to PDF.','Convert PDF','word','blue'],
['powerpoint-to-pdf','PowerPoint to PDF','Convert slide presentations to PDF format.','Convert PDF','ppt','orange'],
['excel-to-pdf','Excel to PDF','Export your Excel spreadsheet to a PDF.','Convert PDF','excel','green'],
['edit','Edit PDF','Add text, shapes, images, freehand drawings and replace text in your PDF.','Edit PDF','edit','violet'],
['pdf-to-jpg','PDF to JPG','Render PDF pages to JPG or extract original embedded images.','Convert PDF','image','yellow'],
['jpg-to-pdf','JPG to PDF','Combine images and scans into a PDF document.','Convert PDF','image','pink'],
['sign','Sign PDF','Place a visible handwritten-style signature on a page.','PDF Security','sign','blue'],
['sign-certificate','Digital Certificate Sign','Cryptographically sign a PDF using your own P12/PFX certificate.','PDF Security','sign','violet'],
['verify-signatures','Verify Digital Signatures','Check PDF CMS signatures for byte integrity; CA trust is not verified.','PDF Security','protect','green'],
['watermark','Watermark','Stamp transparent text or image logos across PDF pages.','Edit PDF','watermark','violet'],
['rotate','Rotate PDF','Rotate all pages or selected pages in a PDF.','Edit PDF','rotate','blue'],
['html-to-pdf','HTML to PDF','Convert uploaded or pasted HTML content to PDF.','Convert PDF','html','green'],
['unlock','Unlock PDF','Remove an existing PDF password with authorization.','PDF Security','unlock','orange'],
['protect','Protect PDF','Encrypt your PDF securely with a password.','PDF Security','protect','red'],
['organize','Organize PDF','Visually combine, reorder, rotate, duplicate or remove pages across PDFs.','Organize PDF','organize','violet'],
['pdf-to-pdfa','PDF to PDF/A','Convert standard PDF to archival PDF/A output.','Convert PDF','archive','blue'],
['repair','Repair PDF','Rebuild PDFs with recoverable structural issues.','Optimize PDF','repair','green'],
['page-numbers','Page Numbers','Add numbered labels to every PDF page.','Edit PDF','number','red'],
['scan','Scan to PDF','Create a PDF from camera images or document photos.','Organize PDF','scan','blue'],
['ocr','OCR PDF','Make scanned pages searchable with text recognition.','Optimize PDF','ocr','violet'],
['compare','Compare PDF','Compare two PDFs and highlight pixel differences.','PDF Security','compare','blue'],
['redact','Redact PDF','Permanently remove occurrences of specific text.','PDF Security','redact','red'],
['crop','Crop PDF','Trim page boundaries using precise margins.','Edit PDF','crop','orange'],
['forms','PDF Forms','Create text, checkbox, dropdown and multiline interactive PDF fields.','Edit PDF','forms','violet'],
['workflow','PDF Workflows','Chain several tools and run them automatically in one click.','Organize PDF','organize','cyan'],
['summarize','Smart Summary','Generate a smart extractive or configured AI summary from PDF text.','PDF Intelligence','ai','pink'],
['translate','Translate PDF','Translate PDF text with layout-preserving mode through your configured service.','PDF Intelligence','translate','cyan'],
['pdf-to-markdown','PDF to Markdown','Turn PDF text into Markdown for easier reuse.','PDF Intelligence','markdown','blue'],
['pdf-to-text','PDF to Text','Extract selectable PDF text into a UTF-8 text file.','Convert PDF','markdown','green'],
['pdf-to-png','PDF to PNG','Export selected PDF pages as PNG images.','Convert PDF','image','blue'],
['flatten-pdf','Flatten PDF','Turn form fields and annotations into static page content.','Edit PDF','forms','violet'],
['insert-blank-pages','Insert Blank Pages','Insert up to 20 blank pages at the beginning, end or after a page.','Organize PDF','pages','orange'],
['remove-metadata','Remove PDF Metadata','Clear standard PDF properties, XMP and embedded attachments; does not erase hidden page content.','PDF Security','protect','green'],
['grayscale','Grayscale PDF','Convert every page to grayscale by rasterizing; text and form interactivity are not preserved.','Optimize PDF','image','blue'],
['remove-pages','Remove Pages','Delete specified pages from your PDF file.','Organize PDF','remove','red'],
['extract-pages','Extract Pages','Choose exactly the pages you want to keep.','Organize PDF','pages','green'],
];
const bySlug=Object.fromEntries(TOOLS.map(t=>[t[0],t]));
const TABS=['All','Organize PDF','Optimize PDF','Convert PDF','Edit PDF','PDF Security','PDF Intelligence'];
// Descriptor array fields: [name, label, input type, default, details], type can be text, number, password, textarea or select:option|label,...
const OPTS={
'merge':[['password','Password for encrypted inputs (optional)','password','']],
'split':[['mode','Split mode','select:each|One PDF per page,chunks|Every N pages,ranges|Custom page ranges','each'],['chunk_size','Pages per group (chunks mode)','number','2'],['ranges','Custom ranges (separate groups with semicolons)','text','1-2;3-4','Example: 1-3;4-6']],
'compress':[['quality','Compression preset','select:screen|Strong compression,ebook|Recommended,printer|Higher quality,prepress|Maximum quality','ebook'],['password','PDF password (if needed)','password','']],
'remove-pages':[['pages','Pages to remove','text','1','Example: 1,3,5-7']],
'extract-pages':[['pages','Pages to extract','text','1','Example: 2,4-8']],
'organize':[['pages','New page sequence','text','','Use 4,1,2,2 to reorder and duplicate pages. Leave empty to keep order.']],
'ocr':[['language','OCR language code','text','eng','Requires installed Tesseract language pack.'],['dpi','Resolution (DPI)','number','170']],
'jpg-to-pdf':[['margin','Margin in points','number','12']],
'scan':[['margin','Margin in points','number','12'],['enhance','Improve scanned contrast','select:true|Auto enhance,false|Original','true'],['grayscale','Image color','select:false|Color,true|Black & white','false'],['perspective','Fix camera perspective','select:auto|Auto detect page,false|Do not crop photo','auto']],
'pdf-to-jpg':[['mode','Image output','select:pages|Render each PDF page,images|Extract original embedded images','pages'],['dpi','Render resolution (DPI)','number','140']],
'pdf-to-powerpoint':[['editable','PowerPoint text mode','select:true|Editable text (best effort),false|Pixel-faithful snapshot','true']],
'pdf-to-word':[['password','PDF password (if needed)','password','']],
'pdf-to-pdfa':[['password','PDF password (if needed)','password','']],
'rotate':[['angle','Rotation','select:90|90° right,180|180°,270|90° left,-90|-90°','90'],['pages','Pages to rotate (blank = all)','text','','Example: 1,3-5']],
'page-numbers':[['position','Position','select:bottom|Bottom center,top|Top center','bottom'],['start','Starting number','number','1'],['font_size','Font size','number','12']],
'watermark':[['text','Watermark text','text','CONFIDENTIAL'],['position','Position','select:center|Center,top|Top center,bottom|Bottom center','center'],['font_size','Font size','number','32'],['opacity','Opacity (0.05–1)','number','0.25'],['image_width','Image watermark width (pt)','number','160']],
'crop':[['left','Left margin (pt)','number','20'],['right','Right margin (pt)','number','20'],['top','Top margin (pt)','number','20'],['bottom','Bottom margin (pt)','number','20'],['apply','Visual crop applies to','select:all|All pages,page|Selected page','all']],
'edit':[['text','Text to insert','text','New annotation'],['page','Page number','number','1'],['x','X position in points','number','60'],['y','Y position in points','number','80'],['font_size','Font size','number','18']],
'forms':[['mode','Action','select:create|Create single field,fill|Fill existing field,fill-all|Fill multiple fields,detect|Detect labelled blanks,bulk|Use visual field creator','create'],['field_type','Single field type','select:field-text|Text,field-multiline|Multiline,field-checkbox|Checkbox,field-dropdown|Dropdown,field-listbox|List box,field-radio-group|Radio group','field-text'],['field','Field name','text','Full Name'],['value','Value (fill mode)','text',''],['values','Fill multiple fields (JSON mapping)','textarea','{}'],['choices','Dropdown options, comma separated','text','Yes,No'],['page','Page number (create mode)','number','1'],['x','X position','number','72'],['y','Y position','number','130'],['flatten','Flatten form after filling?','select:false|Keep editable,true|Flatten to static','false']],
'unlock':[['password','Current password','password','']],
'protect':[['new_password','New PDF password','password','']],
'sign-certificate':[['certificate_password','Certificate bundle passphrase','password',''],['signature_field','Unique signature field name','text','PDFCraftSignature']],
'verify-signatures':[],
'sign':[['text','Name or signature','text','Signed'],['page','Page number','number','1'],['x','X position in points','number','68'],['y','Y position in points (0 uses default)','number','0'],['width','Drawn signature width (pt)','number','220'],['height','Drawn signature height (pt)','number','80']],
'redact':[['text','Text to permanently remove (or draw black rectangles)','text',''],['sanitize','Remove metadata, attachments, comments and links','select:true|Yes (recommended),false|Keep','true']],
'compare':[['mode','Compare by','select:visual|Visual pixel comparison,text|Text change report','visual']],
'summarize':[['mode','Summary mode','select:auto|Use AI if configured,extractive|Local extractive,generative|Require AI service','auto'],['sentences','Maximum extractive sentences','number','7']],
'workflow':[['steps','Workflow steps (JSON; visual builder below)','textarea','[]','Up to 12 PDF processing steps.'],['password','PDF password if needed','password','']],
'translate':[['mode','PDF layout','select:layout|Retain page graphics (best effort),reflow|Reflow translated text','layout'],['language','Target language','select:es|Spanish,fr|French,de|German,hi|Hindi,it|Italian,pt|Portuguese,ja|Japanese,ar|Arabic','es']],
'grayscale':[['dpi','Grayscale rendering DPI (72–160)','number','110','Raster output loses selectable text, active links and form fields.']],
'pdf-to-text':[['pages','Pages (blank means all)','text','','Example 1,3-5'],['password','PDF password (if needed)','password','']],
'pdf-to-png':[['pages','Pages (blank means all)','text','','Example 1,3-5'],['dpi','Image quality (DPI)','number','120'],['password','PDF password (if needed)','password','']],
'flatten-pdf':[['password','PDF password (if needed)','password','']],
'insert-blank-pages':[['position','Insert at','select:start|Beginning,end|End,after|After a selected page','end'],['after_page','Page number when position is After','number','1'],['count','How many blank pages (1-20)','number','1'],['password','PDF password (if needed)','password','']],
'remove-metadata':[['password','PDF password (if needed)','password','']],
'html-to-pdf':[['url','Public webpage HTTPS URL (optional)','text','','Requires server opt-in; remote stylesheets and images are blocked.'],['html','HTML source (if no file/URL)','textarea','','Paste HTML or upload an .html file. External resources are blocked.']],
};
const EXTRA_HINT={
 'pdf-to-jpg':'Extract original embedded images without rerendering, or export each page as a JPG.','pdf-to-powerpoint':'Creates editable PowerPoint text boxes over a rasterized background (other artwork is not editable). Use Snapshot for pixel-faithful slides.',
 'pdf-to-word':'The best available layout conversion is used, with a text-recovery fallback for difficult PDFs.',
 'pdf-to-excel':'Works best on PDFs that contain real tables. Scanned documents may need OCR first.',
 'compress':'Already compressed PDFs may not shrink further.',
 'sign':'Adds a visible signature annotation. This is not a cryptographic digital signature or a remote signing service.',
 'sign-certificate':'Upload the PDF first, then your .p12/.pfx bundle. A real detached CMS signature is added. Only use a certificate you own; trust status is NOT evaluated. Existing signatures are protected from accidental invalidation.',
 'verify-signatures':"Checks the PDF's detached CMS integrity and reports if it covers the complete current file. Does not establish certificate trust or legal identity.",
 'pdf-to-pdfa':'Requires Ghostscript and ICC profiles. Verify formal archive compliance with a PDF/A validator.',
 'summarize':'Generative mode requires your own AI_API_KEY and AI_MODEL. Without it, Auto uses local extractive summarization, clearly labelled.',
 'translate':'Requires your own trusted LibreTranslate-compatible server. Layout mode retains PDF artwork and places translated text in original regions; long passages may go to an appendix.',
 'redact':'Redacts matched selectable text (and image pixels intersecting it). For scanned documents run OCR first.',
 'compare':'Choose a visual page-by-page difference PDF or a textual unified diff report.',
 'forms':'Supports text, multiline, checkbox, dropdown, listbox and true radio-button groups. Review automatically suggested fields before use.',
 'ocr':'OCR creates searchable scanned pages, subject to the accuracy of Tesseract.',
 'grayscale':'Grayscale rasterization makes text non-searchable and discards interactive PDF elements.',
 'flatten-pdf':'Makes annotations and form appearances static. This is not a legal/cryptographic signature flattening method.',
 'pdf-to-text':'Only selectable text is extracted. For scans, run OCR first.',
 'remove-metadata':'Removes PDF metadata, XMP and embedded files. Does not remove text, revisions in other files, or screen-visible content.'
};
const state={tab:'All',query:'',tool:null,files:[],busy:false,downloadUrl:null,previewUrl:null,controller:null,maxUploadMB:50,maxJobMB:120,ephemeral:false};
const $=s=>document.querySelector(s);
const grid=$('#toolGrid'), filters=$('#filters'), input=$('#searchInput');
function makeCard(t){const b=document.createElement('button');b.className='tool-card';b.dataset.slug=t[0];b.setAttribute('aria-label','Open '+t[1]);b.innerHTML=`<div class="card-icon tone-${t[5]}">${svg(t[4])}</div><span class="card-arrow">↗</span><h3>${t[1]}</h3><p>${t[2]}</p>`;b.addEventListener('click',()=>openTool(t[0]));return b}
function render(){filters.replaceChildren();TABS.forEach(tab=>{const n=tab==='All'?TOOLS.length:TOOLS.filter(t=>t[3]===tab).length;const b=document.createElement('button');b.className='filter'+(tab===state.tab?' active':'');b.innerHTML=`${tab} <span class="filter-count">${n}</span>`;b.setAttribute('aria-pressed',String(tab===state.tab));b.onclick=()=>{state.tab=tab;render()};filters.append(b)});
grid.replaceChildren();const matches=TOOLS.filter(t=>(state.tab==='All'||t[3]===state.tab)&&[t[1],t[2],t[3]].join(' ').toLowerCase().includes(state.query.toLowerCase()));matches.forEach(t=>grid.append(makeCard(t)));$('#emptyState').hidden=matches.length>0}
input.addEventListener('input',e=>{state.query=e.target.value.trim();render()});
function alertToast(msg){const t=$('#toast');t.textContent=msg;t.classList.add('show');clearTimeout(window.toastTimer);window.toastTimer=setTimeout(()=>t.classList.remove('show'),3300)}
function openTool(slug){if(!bySlug[slug])return;const t=bySlug[slug];state.tool=t;state.files=[];state.busy=false;window.PDFCraftLastResult=null;$('#filePreview').hidden=true;$('#modalBackdrop').hidden=false;document.body.classList.add('modal-open');$('#modalIcon').className=`modal-tool-icon tone-${t[5]}`;$('#modalIcon').innerHTML=svg(t[4]);$('#toolTitle').textContent=t[1];$('#toolDescription').textContent=t[2];$('#resultPanel').hidden=true;$('#errorBox').hidden=true;$('#fileSection').hidden=true;$('#dropzone').hidden=false;$('#optionsPanel').hidden=false;$('.modal-footer').hidden=false;$('#processButton').disabled=false;$('#processLabel').textContent=t[1]==='Merge PDF'?'Merge PDF':t[1];$('#fileInput').value='';
const images=['jpg-to-pdf','scan'],html=slug==='html-to-pdf';const accepts=images.includes(slug)?'image/jpeg,image/png,image/webp,image/bmp,image/tiff':slug==='word-to-pdf'?'.doc,.docx':slug==='powerpoint-to-pdf'?'.ppt,.pptx':slug==='excel-to-pdf'?'.xls,.xlsx':slug==='sign-certificate'?'.pdf,.p12,.pfx':html?'.html,.htm,text/html':'.pdf,application/pdf';
$('#fileInput').accept=accepts;$('#fileInput').multiple=['merge','jpg-to-pdf','scan','compare','organize','sign-certificate'].includes(slug);$('#fileHint').textContent=slug==='sign-certificate'?`PDF + PKCS#12 bundle · upload in that order · ${state.maxUploadMB} MB/file`:html?'Optional HTML file · or paste code below':images.includes(slug)?`JPG, PNG, WebP · up to ${state.maxUploadMB} MB each`:slug.endsWith('-to-pdf')&&slug!=='jpg-to-pdf'?`Office documents · up to ${state.maxUploadMB} MB each`:`PDF files · up to ${state.maxUploadMB} MB each`;
createOptions(slug);renderFiles();window.PDFCraftAdvanced?.onOpen?.(slug);window.PDFCraftOrganizer?.onOpen?.(slug);window.PDFCraftCompare?.onOpen?.(slug);window.PDFCraftCamera?.onOpen?.(slug);history.replaceState({},'',`#tool/${slug}`);$('#closeModal').focus();}
function closeTool(){window.PDFCraftCamera?.onClose?.();window.PDFCraftAdvanced?.onClose?.();window.PDFCraftOrganizer?.onClose?.();window.PDFCraftCompare?.onClose?.();if(state.busy&&state.controller)state.controller.abort();state.busy=false;if(state.downloadUrl)URL.revokeObjectURL(state.downloadUrl);state.downloadUrl=null;if(state.previewUrl)URL.revokeObjectURL(state.previewUrl);state.previewUrl=null;$('#modalBackdrop').hidden=true;document.body.classList.remove('modal-open');state.tool=null;history.replaceState({},'','#tools')}
$('#closeModal').onclick=closeTool;$('#modalBackdrop').addEventListener('click',e=>{if(e.target===$('#modalBackdrop'))closeTool()});document.addEventListener('keydown',e=>{if(e.key==='Escape'&&state.tool){closeTool();return}if(e.key==='/'&&!state.tool&&!['INPUT','TEXTAREA'].includes(document.activeElement.tagName)){e.preventDefault();input.focus()}});
function createOptions(slug){const root=$('#optionsFields');root.replaceChildren();const defs=OPTS[slug]||[];if(!defs.length){const p=document.createElement('p');p.className='option-noopts';p.textContent='No additional settings required. Upload your file and start processing.';root.append(p)}defs.forEach(([name,title,type,value,help])=>{const box=document.createElement('div');box.className='option-field'+(type==='textarea'||name==='html'||name==='ranges'?' full':'');const label=document.createElement('label');label.textContent=title;label.htmlFor=`opt-${name}`;box.append(label);let field;if(type.startsWith('select:')){field=document.createElement('select');type.slice(7).split(',').forEach(pair=>{let [val,...parts]=pair.split('|');const opt=document.createElement('option');opt.value=val;opt.textContent=parts.join('|')||val;field.append(opt)})}else if(type==='textarea'){field=document.createElement('textarea')}else{field=document.createElement('input');field.type=type==='number'?'number':type==='password'?'password':'text';if(type==='number')field.step='any'}field.id=`opt-${name}`;field.name=name;field.value=value;box.append(field);if(help){const sm=document.createElement('small');sm.textContent=help;box.append(sm)}root.append(box)});if(EXTRA_HINT[slug]){const help=document.createElement('div');help.className='option-help';help.textContent=EXTRA_HINT[slug];root.append(help)}}
function filesize(n){return n<1024?`${n} B`:n<1048576?`${(n/1024).toFixed(1)} KB`:`${(n/1048576).toFixed(2)} MB`}
function renderFiles(){const root=$('#fileList');root.replaceChildren();const present=state.files.length>0;$('#fileSection').hidden=!present;$('#dropzone').hidden=present;$('#fileCount').textContent=state.files.length;state.files.forEach((f,i)=>{const row=document.createElement('div');row.className='file-item';const badge=document.createElement('div');badge.className='file-ico';badge.textContent=(f.name.split('.').pop()||'FILE').slice(0,4).toUpperCase();const detail=document.createElement('div');detail.className='file-detail';const title=document.createElement('div');title.className='file-name';title.textContent=f.name;const size=document.createElement('div');size.className='file-size';size.textContent=filesize(f.size);detail.append(title,size);const actions=document.createElement('div');actions.className='file-actions';[['↑','Move up',()=>{if(i===0)return;[state.files[i-1],state.files[i]]=[state.files[i],state.files[i-1]];renderFiles()}],['↓','Move down',()=>{if(i===state.files.length-1)return;[state.files[i+1],state.files[i]]=[state.files[i],state.files[i+1]];renderFiles()}],['×','Remove',()=>{state.files.splice(i,1);renderFiles();updatePreview()}]].forEach(([glyph,label,fn])=>{const b=document.createElement('button');b.textContent=glyph;b.title=label;b.setAttribute('aria-label',label+' '+f.name);b.onclick=()=>{fn();if(state.tool?.[0]==='organize')window.PDFCraftOrganizer?.onFiles?.(state.files);if(state.tool?.[0]==='compare')window.PDFCraftCompare?.onFiles?.(state.files)};actions.append(b)});row.append(badge,detail,actions);root.append(row)})}
function addFiles(selected){if(!state.tool||!selected?.length)return;const slug=state.tool[0],multi=['merge','jpg-to-pdf','scan','compare','organize','sign-certificate'].includes(slug);const incoming=Array.from(selected).filter(f=>f.size>0);if(!incoming.length){alertToast('Please choose a non-empty file.');return}if(incoming.some(f=>f.size>state.maxUploadMB*1048576)){showError(`Each file must be smaller than ${state.maxUploadMB} MB.`);return}const allowed=slug==='sign-certificate'?/\.(pdf|p12|pfx)$/i:slug==='jpg-to-pdf'||slug==='scan'?/\.(jpe?g|png|webp|bmp|tiff?)$/i:slug==='html-to-pdf'?/\.html?$/i:slug==='word-to-pdf'?/\.docx?$/i:slug==='powerpoint-to-pdf'?/\.pptx?$/i:slug==='excel-to-pdf'?/\.xlsx?$/i:/\.pdf$/i;if(incoming.some(f=>!allowed.test(f.name))){showError('Please choose files matching this tool’s accepted format.');return}state.files=multi?[...state.files,...incoming].slice(0,25):[incoming[0]];if(state.files.reduce((n,f)=>n+f.size,0)>state.maxJobMB*1048576){showError(`Total upload must not exceed ${state.maxJobMB} MB.`);state.files=[];return}if(slug==='sign-certificate'&&state.files.length>2){state.files=state.files.slice(0,2);}$('#errorBox').hidden=true;renderFiles();updatePreview();window.PDFCraftAdvanced?.onFiles?.(state.files[0]);window.PDFCraftOrganizer?.onFiles?.(state.files);window.PDFCraftCompare?.onFiles?.(state.files)}
window.PDFCraftAddFiles=addFiles;const dz=$('#dropzone'),fi=$('#fileInput');dz.onclick=()=>fi.click();dz.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();fi.click()}};$('#browseBtn').onclick=e=>{e.stopPropagation();fi.click()};$('#addMore').onclick=()=>fi.click();fi.onchange=e=>{addFiles(e.target.files);e.target.value=''};dz.ondragover=e=>{e.preventDefault();dz.classList.add('over')};dz.ondragleave=()=>dz.classList.remove('over');dz.ondrop=e=>{e.preventDefault();dz.classList.remove('over');addFiles(e.dataTransfer.files)};
async function updatePreview(){
  $('#filePreview').hidden=true;
  const file=state.files[0];if(!file||!/\.pdf$/i.test(file.name))return;
  const requestedTool=state.tool?.[0];const fd=new FormData();fd.append('file',file,file.name);
  try{
    const meta=await fetch('/api/inspect',{method:'POST',body:fd});if(!meta.ok)return;
    const info=await meta.json();if(!state.tool||state.tool[0]!==requestedTool||state.files[0]!==file)return;
    $('#previewMeta').textContent=`${info.pages} page${info.pages===1?'':'s'} · ${filesize(info.size_bytes)}`;
    const res=await fetch('/api/thumbnail',{method:'POST',body:fd});if(!res.ok)return;
    const data=await res.blob();if(!state.tool||state.tool[0]!==requestedTool||state.files[0]!==file)return;
    if(state.previewUrl)URL.revokeObjectURL(state.previewUrl);
    state.previewUrl=URL.createObjectURL(data);$('#previewImage').src=state.previewUrl;$('#filePreview').hidden=false;
  }catch{ /* An encrypted or damaged PDF simply has no preview. */ }
}
function showError(s){const box=$('#errorBox');box.textContent=s;box.hidden=false;box.scrollIntoView({block:'nearest',behavior:'smooth'})}
async function processTool(){if(state.busy||!state.tool)return;const slug=state.tool[0];if(!state.files.length&&slug!=='html-to-pdf'){showError('Choose a document to process first.');return}if(slug==='merge'&&state.files.length<2){showError('Merge needs at least two PDF files.');return}if(slug==='compare'&&state.files.length!==2){showError('Compare needs exactly two PDF files.');return}if(slug==='sign-certificate'&&(state.files.length!==2||!/\.pdf$/i.test(state.files[0].name)||!/\.(p12|pfx)$/i.test(state.files[1].name))){showError('Upload a PDF first and a .p12 or .pfx certificate bundle second.');return}let opts={};$('#optionsFields').querySelectorAll('input,select,textarea').forEach(el=>{opts[el.name]=el.value});try{Object.assign(opts,window.PDFCraftAdvanced?.options?.(slug)||{},window.PDFCraftOrganizer?.options?.(slug)||{})}catch(err){showError(err.message);return}if(slug==='html-to-pdf'&&!state.files.length&&!opts.html?.trim()&&!opts.url?.trim()){showError('Paste HTML, provide an allowed URL, or choose an HTML file.');return}
state.busy=true;state.controller=new AbortController();$('#processButton').disabled=true;$('#processLabel').textContent='Processing…';$('#errorBox').hidden=true;const form=new FormData();state.files.forEach(f=>form.append('files',f,f.name));form.append('options',JSON.stringify(opts));
try{const response=await fetch('/api/process/'+slug,{method:'POST',body:form,signal:state.controller.signal});if(!response.ok){let detail=await response.json().catch(()=>({}));throw new Error(detail.error||detail.detail||`Server error ${response.status}`)}const blob=await response.blob();if(!blob.size)throw Error('The resulting download is empty.');if(state.downloadUrl)URL.revokeObjectURL(state.downloadUrl);state.downloadUrl=URL.createObjectURL(blob);state.resultBlob=blob;const hdr=response.headers.get('content-disposition')||'';let filename='processed_file.pdf';const m=hdr.match(/filename\*=utf-8''([^;]+)/i)||hdr.match(/filename="?([^";]+)"?/i);if(m)try{filename=decodeURIComponent(m[1])}catch{filename=m[1]};const link=$('#downloadButton');link.href=state.downloadUrl;link.download=filename;$('#resultFilename').textContent=`${filename} · ${filesize(blob.size)}`;window.PDFCraftLastResult={blob,filename};$('#saveResult').hidden=!filename.toLowerCase().endsWith('.pdf');$('#resultPanel').hidden=false;$('#dropzone').hidden=true;$('#fileSection').hidden=true;$('#optionsPanel').hidden=true;$('#filePreview').hidden=true;$('#visualEditor').hidden=true;$('#workflowBuilder').hidden=true;$('#organizerBuilder').hidden=true;$('#compareBuilder').hidden=true;$('#signatureBuilder').hidden=true;$('#watermarkBuilder').hidden=true;$('.modal-footer').hidden=true;$('#resultPanel').scrollIntoView({block:'nearest',behavior:'smooth'});link.click();alertToast('Processed successfully. Your download is ready.');}catch(err){if(err.name!=='AbortError')showError(err.message||'Processing failed.');}finally{state.busy=false;state.controller=null;$('#processButton').disabled=false;$('#processLabel').textContent=state.tool?state.tool[1]:'Process PDF'}}
$('#saveResult').onclick=()=>window.PDFCraftWorkspace?.saveResult?.();$('#processButton').onclick=processTool;$('#startAgain').onclick=()=>{if(!state.tool)return;const slug=state.tool[0];$('.modal-footer').hidden=false;openTool(slug)};
function updateHash(){const m=location.hash.match(/^#tool\/([a-z-]+)$/);if(m&&bySlug[m[1]])openTool(m[1])}
$('#convertButton').onclick=e=>openMenu('Convert PDF',e.currentTarget);$('#organizeButton').onclick=e=>openMenu('Organize PDF',e.currentTarget);$('#menuButton').onclick=e=>openMenu('All',e.currentTarget);
function openMenu(category,trigger){const menu=$('#navDropdown');if(!menu.hidden&&menu.dataset.category===category){menu.hidden=true;return}menu.dataset.category=category;menu.replaceChildren();TOOLS.filter(t=>category==='All'||t[3]===category).slice(0,category==='All'?10:30).forEach(t=>{const btn=document.createElement('button');btn.textContent=t[1];btn.onclick=()=>{menu.hidden=true;openTool(t[0])};menu.append(btn)});menu.hidden=false;trigger.setAttribute('aria-expanded','true')}
document.addEventListener('click',e=>{if(!e.target.closest('.dropdown-menu,.nav-dropdown,.mobile-menu'))$('#navDropdown').hidden=true});
window.addEventListener('hashchange',updateHash);render();updateHash();

// Hosting capability gate: never offer permanent vault features on ephemeral free hosts.
fetch('/api/capabilities',{cache:'no-store'}).then(r=>r.ok?r.json():null).then(data=>{
  if(!data)return;
  const open=document.querySelector('#openWorkspace');
  const save=document.querySelector('#saveResult');
  state.ephemeral=!!data.ephemeral_mode;
  state.maxUploadMB=data.max_upload_mb||50;
  state.maxJobMB=data.max_job_mb||120;
  if(!data.persistent_accounts){
    if(open)open.hidden=true;
    if(save)save.hidden=true;
    const notice=document.querySelector('#hostingNotice');
    if(notice){notice.textContent='Free preview mode: process files without signing in. Save each download to your device; permanent document vault, account storage and remote signature requests are not available on this host.';notice.hidden=false;}
    document.body.dataset.ephemeral='true';
  }
  const hint=document.querySelector('#fileHint');
  if(hint&&data.max_upload_mb)hint.textContent=`Documents · up to ${data.max_upload_mb} MB each`;
}).catch(()=>{});
