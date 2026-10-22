'use strict';
/* Interactive two-PDF comparison. All previews are temporary; nothing is saved. */
(() => {
 const root=document.getElementById('compareBuilder');
 if(!root)return;
 let files=[],page=1,total=1,current=null,view='overlay',loadId=0;
 const template=`
  <div class="compare-head"><div><strong>Interactive document comparison</strong><p>Inspect corresponding pages before downloading a difference report.</p></div></div>
  <div class="compare-nav">
    <button type="button" id="comparePrev" aria-label="Previous comparison page">← Previous</button>
    <strong id="comparePageLabel" aria-live="polite">Page 1</strong>
    <button type="button" id="compareNext" aria-label="Next comparison page">Next →</button>
  </div>
  <div class="compare-modes" role="group" aria-label="Comparison view">
    <button type="button" data-compare-view="overlay" aria-pressed="true">Overlay</button>
    <button type="button" data-compare-view="side" aria-pressed="false">Side by side</button>
    <button type="button" data-compare-view="highlight" aria-pressed="false">Highlight changes</button>
  </div>
  <label id="compareSliderLabel" class="compare-slider-label">Revised overlay opacity
    <input id="compareOpacity" type="range" min="0" max="100" step="1" value="50" aria-label="Opacity of revised PDF page"><output id="compareOpacityOut">50%</output>
  </label>
  <p id="compareStatus" role="status" class="compare-status">Select two PDFs to compare.</p>
  <div class="compare-viewbox" id="compareViewbox" hidden>
    <div class="compare-layered" id="compareOverlay"><img id="compareOld" alt="Original PDF page"><img id="compareNew" alt="Revised PDF page" class="compare-revised"></div>
    <div class="compare-side" id="compareSide" hidden><figure><figcaption>Original</figcaption><img id="compareSideOld" alt="Original PDF page"></figure><figure><figcaption>Revised</figcaption><img id="compareSideNew" alt="Revised PDF page"></figure></div>
    <img id="compareHighlighted" alt="PDF revision, with changed areas highlighted" hidden>
  </div>
  <p class="compare-note">Pixel percentage is an approximate rendering comparison; anti-aliasing and fonts can affect results. The downloaded PDF contains the page-by-page comparison.</p>`;
 root.innerHTML=template;
 const $=selector=>root.querySelector(selector);
 const status=$('#compareStatus'),viewbox=$('#compareViewbox');
 function paint(){
   if(!current)return;
   $('#compareOld').src=$('#compareSideOld').src=current.original;
   $('#compareNew').src=$('#compareSideNew').src=current.revised;
   $('#compareHighlighted').src=current.highlighted;
   $('#comparePageLabel').textContent=`Page ${page} / ${total}`;
   $('#comparePrev').disabled=page<=1;$('#compareNext').disabled=page>=total;
   const opacity=Number($('#compareOpacity').value);
   $('#compareNew').style.opacity=String(opacity/100);
   $('#compareOpacityOut').textContent=opacity+'%';
   $('#compareOverlay').hidden=view!=='overlay';
   $('#compareSide').hidden=view!=='side';
   $('#compareHighlighted').hidden=view!=='highlight';
   $('#compareSliderLabel').hidden=view!=='overlay';
   root.querySelectorAll('[data-compare-view]').forEach(btn=>btn.setAttribute('aria-pressed',String(view===btn.dataset.compareView)));
   status.textContent=`Rendered difference: ${current.changed_pixels_percent}% of page pixels. Text ${current.text_changed?'has changed':'is identical'}.`;
   viewbox.hidden=false;
 }
 async function load(){
   const id=++loadId;
   viewbox.hidden=true;
   if(files.length!==2){status.textContent='Choose exactly two PDFs. Preview is available after both uploads.';return;}
   if(!files.every(f=>/\.pdf$/i.test(f.name))){status.textContent='Please use two PDF files.';return;}
   status.textContent='Preparing comparison preview…';
   const form=new FormData();form.append('files',files[0],files[0].name);form.append('files',files[1],files[1].name);form.append('page',String(page));form.append('width','720');
   try{
     const response=await fetch('/api/compare-preview',{method:'POST',body:form});
     if(!response.ok){const detail=await response.json().catch(()=>({}));throw Error(detail.error||detail.detail||'Comparison preview unavailable.');}
     const result=await response.json();if(id!==loadId)return;
     current=result;total=result.total_pages;paint();
   }catch(err){if(id===loadId)status.textContent=err.message||'Unable to preview this PDF.';}
 }
 $('#comparePrev').onclick=()=>{if(page>1){page--;load()}};
 $('#compareNext').onclick=()=>{if(page<total){page++;load()}};
 root.querySelectorAll('[data-compare-view]').forEach(btn=>btn.onclick=()=>{view=btn.dataset.compareView;paint()});
 $('#compareOpacity').oninput=()=>paint();
 window.PDFCraftCompare={
  onOpen(slug){loadId++;files=[];page=total=1;current=null;view='overlay';$('#compareOpacity').value='50';root.hidden=slug!=='compare';viewbox.hidden=true;status.textContent='Choose exactly two PDFs to compare.'},
  onFiles(input){if(root.hidden)return;files=[...input];page=total=1;current=null;load()},
  onClose(){loadId++;files=[];current=null;root.hidden=true;viewbox.hidden=true;for(const img of root.querySelectorAll('img'))img.removeAttribute('src')}
 };
})();
