'use strict';
(()=>{
 const $=s=>document.querySelector(s);
 let stream=null,count=0;
 async function stop(){if(stream){stream.getTracks().forEach(t=>t.stop());stream=null}$('#cameraPreview').srcObject=null;$('#cameraPreview').hidden=true;$('#snapCamera').hidden=true;$('#stopCamera').hidden=true}
 async function start(){
  $('#cameraMessage').textContent='';
  try{
   if(!navigator.mediaDevices?.getUserMedia)throw Error('This browser cannot access a camera from this connection. Use HTTPS or choose photos instead.');
   stream=await navigator.mediaDevices.getUserMedia({audio:false,video:{facingMode:{ideal:'environment'},width:{ideal:1920},height:{ideal:1080}}});
   const video=$('#cameraPreview');video.srcObject=stream;await video.play();video.hidden=false;
   $('#snapCamera').hidden=false;$('#stopCamera').hidden=false;
  }catch(e){$('#cameraMessage').textContent=e.message||'Camera unavailable. You can upload images instead.';stop()}
 }
 function snapshot(){const video=$('#cameraPreview');if(!stream||!video.videoWidth)return;
  const canvas=document.createElement('canvas');canvas.width=video.videoWidth;canvas.height=video.videoHeight;
  canvas.getContext('2d').drawImage(video,0,0);
  canvas.toBlob(blob=>{if(!blob)return;count++;const name=`scan_page_${String(count).padStart(3,'0')}.jpg`;
    const file=new File([blob],name,{type:'image/jpeg'});window.PDFCraftAddFiles?.([file]);
    $('#cameraMessage').textContent=`Captured ${count} page${count===1?'':'s'}. Continue capturing or process your PDF.`;
  },'image/jpeg',.9);
 }
 $('#startCamera').addEventListener('click',start);$('#snapCamera').addEventListener('click',snapshot);$('#stopCamera').addEventListener('click',stop);
 $('#cameraPhoto').addEventListener('change',e=>{if(e.target.files?.length)window.PDFCraftAddFiles?.(e.target.files);e.target.value=''});
 window.PDFCraftCamera={onOpen(slug){$('#cameraSection').hidden=slug!=='scan';count=0},onClose(){stop();$('#cameraSection').hidden=true}};
})();
