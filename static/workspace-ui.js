'use strict';
(() => {
  const $=sel=>document.querySelector(sel);
  const TOKEN_KEY='pdfcraft_session';
  let token=sessionStorage.getItem(TOKEN_KEY)||'';
  let vaultDocs=[];
  const showError=text=>{$('#workspaceError').hidden=!text;$('#workspaceError').textContent=text||''};
  const humanSize=n=>n<1048576?`${Math.round(n/1024)} KB`:`${(n/1048576).toFixed(1)} MB`;
  async function api(path,opts={}){
    const headers={...(opts.headers||{})};
    if(token)headers.Authorization=`Bearer ${token}`;
    if(opts.body&&!(opts.body instanceof FormData))headers['Content-Type']='application/json';
    const r=await fetch('/api'+path,{...opts,headers});
    if(!r.ok){const e=await r.json().catch(()=>({}));throw Error(e.detail||e.error||`HTTP ${r.status}`)}
    return opts.raw?r:r.json();
  }
  function open(){showError('');$('#workspaceOverlay').hidden=false;document.body.classList.add('modal-open');renderState()}
  function close(){$('#workspaceOverlay').hidden=true;document.body.classList.remove('modal-open')}
  async function renderState(){
    $('#workspaceGuest').hidden=!!token;$('#workspaceSigned').hidden=!token;
    if(!token)return;
    try{
      const [who,vault,signs]=await Promise.all([api('/auth/me'),api('/vault'),api('/sign-requests')]);
      $('#signedEmail').textContent=who.email;refreshCloud();
      vaultDocs=vault.documents;
      $('#vaultQuota').textContent=`${humanSize(vault.used_bytes)} of ${humanSize(vault.quota_bytes)} used`;
      renderDocs();renderSigns(signs.requests);
    }catch(e){if(/Session expired|sign in|Invalid session/i.test(e.message)){token='';sessionStorage.removeItem(TOKEN_KEY);renderState()}showError(e.message)}
  }
  function action(label,cb){const b=document.createElement('button');b.type='button';b.textContent=label;b.addEventListener('click',cb);return b}
  function renderDocs(){
    const list=$('#vaultDocs');list.replaceChildren();const select=$('#sigDocSelect');select.replaceChildren();
    if(!vaultDocs.length){list.textContent='No saved PDFs yet. Upload one to begin.';return}
    for(const d of vaultDocs){
      const row=document.createElement('div');row.className='workspace-file';
      const name=document.createElement('span');name.textContent=`${d.filename} · ${humanSize(d.size)}`;
      row.append(name,action('Download',async()=>{try{const r=await api('/vault/'+d.id,{raw:true});download(await r.blob(),d.filename)}catch(e){showError(e.message)}}),
        action('Edit',async()=>{try{const r=await api('/vault/'+d.id,{raw:true});const blob=await r.blob();close();window.location.hash='#tool/edit';setTimeout(()=>{const input=document.querySelector('#fileInput');if(input){const file=new File([blob],d.filename,{type:'application/pdf'});const dt=new DataTransfer();dt.items.add(file);input.files=dt.files;input.dispatchEvent(new Event('change'))}},80)}catch(e){showError(e.message)}}),
        action('Delete',async()=>{if(!confirm(`Delete ${d.filename} from vault?`))return;try{await api('/vault/'+d.id,{method:'DELETE'});renderState()}catch(e){showError(e.message)}}));
      row.append(action('To cloud',()=>exportToCloud(d.id)));
      list.append(row);
      const o=document.createElement('option');o.value=d.id;o.textContent=d.filename;select.append(o);
    }
  }
  async function refreshCloud(){
    const box=$('#cloudProviders');box.replaceChildren();
    try{
      const status=await api('/cloud');
      for(const [provider,info] of Object.entries(status.providers)){
        const row=document.createElement('div');row.className='workspace-file';
        const label=document.createElement('span');label.textContent=`${provider==='google'?'Google Drive':'Dropbox'} · ${info.connected?'Connected':info.configured?'Ready to connect':'Server setup required'}`;row.append(label);
        if(info.connected){
          row.append(action('Browse',()=>listCloud(provider)),action('Disconnect',async()=>{
            try{await api('/cloud/'+provider,{method:'DELETE'});refreshCloud()}catch(err){showError(err.message)}
          }));
        }else if(info.configured){row.append(action('Connect',async()=>{
          try{const d=await api('/cloud/'+provider+'/authorize',{method:'POST'});location.assign(d.authorization_url)}
          catch(err){showError(err.message)}
        }))}
        box.append(row);
      }
    }catch(e){box.textContent='Cloud connections unavailable: '+e.message}
  }
  async function listCloud(provider){
    const root=$('#cloudRemoteFiles');root.replaceChildren();root.hidden=false;
    try{
      const data=await api('/cloud/'+provider+'/files');
      const title=document.createElement('strong');title.textContent=`${provider==='google'?'Google Drive':'Dropbox'} · PDF files`;
      root.append(title);
      if(!data.files.length){root.append(document.createTextNode(' · No accessible PDFs'));return}
      for(const f of data.files){
        const row=document.createElement('div');row.className='workspace-file';
        const name=document.createElement('span');name.textContent=f.name;row.append(name,action('Import PDF',async()=>{
          try{await api('/cloud/'+provider+'/import',{method:'POST',body:JSON.stringify({file_id:f.id})});renderState();showError('')}
          catch(err){showError(err.message)}
        }));root.append(row);
      }
    }catch(err){showError(err.message)}
  }
  async function exportToCloud(docid){
    try{
      const state=await api('/cloud');
      const providers=Object.keys(state.providers).filter(x=>state.providers[x].connected);
      if(!providers.length){showError('Connect Google Drive or Dropbox to export PDFs.');return}
      const choice=providers.length===1?providers[0]:prompt('Export to google or dropbox?',providers[0]);
      if(!providers.includes(choice))return;
      await api('/cloud/'+choice+'/export/'+docid,{method:'POST'});
      showError('');alert('PDF exported to '+choice+'.');
    }catch(err){showError(err.message)}
  }
  function renderSigns(signs){const root=$('#signRequestsList');root.replaceChildren();
    if(!signs.length){root.textContent='No signature requests yet.';return}
    for(const r of signs){
      const row=document.createElement('div');row.className='workspace-file';
      const label=document.createElement('span');label.textContent=`${r.filename} → ${r.recipient_name} (${r.status})`;row.append(label);
      if(r.status==='signed')row.append(action('Signed PDF',async()=>{try{const response=await api('/sign-requests/'+r.id+'/download',{raw:true});download(await response.blob(),'signed_'+r.filename)}catch(e){showError(e.message)}}));
      row.append(action('Audit',async()=>{try{const record=await api('/sign-requests/'+r.id+'/audit');download(new Blob([JSON.stringify(record,null,2)],{type:'application/json'}),'audit_'+r.id+'.json')}catch(e){showError(e.message)}}));
      if(r.status==='pending')row.append(action('Cancel',async()=>{try{await api('/sign-requests/'+r.id+'/cancel',{method:'POST'});renderState()}catch(e){showError(e.message)}}));
      root.append(row);
    }
  }
  function download(blob,filename){const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=filename;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),10000)}
  async function authorize(register){showError('');const email=$('#accountEmail').value.trim();const password=$('#accountPassword').value;
    try{const data=await api(register?'/auth/register':'/auth/login',{method:'POST',body:JSON.stringify({email,password})});token=data.token;sessionStorage.setItem(TOKEN_KEY,token);$('#accountPassword').value='';renderState()}
    catch(e){showError(e.message)}
  }
  $('#openWorkspace').addEventListener('click',open);
  $('#closeWorkspace').addEventListener('click',close);
  $('#workspaceOverlay').addEventListener('click',e=>{if(e.target===$('#workspaceOverlay'))close()});
  $('#authForm').addEventListener('submit',e=>{e.preventDefault();authorize(false)});
  $('#registerSubmit').addEventListener('click',()=>authorize(true));
  $('#forgotPassword').addEventListener('click',async()=>{
    const email=$('#accountEmail').value.trim()||prompt('Enter your account email to receive a reset link:');
    if(!email)return;
    try{const result=await api('/auth/request-reset',{method:'POST',body:JSON.stringify({email})});showError(result.message)}
    catch(e){showError(e.message)}
  });
  $('#resetPasswordForm').addEventListener('submit',async e=>{
    e.preventDefault();const reset=location.hash.match(/^#reset\/([A-Za-z0-9_-]{32,150})$/);
    if(!reset)return showError('Password reset token missing.');
    try{await api('/auth/reset-password',{method:'POST',body:JSON.stringify({token:reset[1],password:$('#resetNewPassword').value})});
      location.hash='#workspace';$('#resetPasswordForm').hidden=true;$('#resetNewPassword').value='';
      showError('Password successfully updated. Sign in with your new password.')}
    catch(err){showError(err.message)}
  });
  if(location.hash.startsWith('#reset/')){setTimeout(()=>{open();$('#resetPasswordForm').hidden=false;showError('Set a new password for your account.')},100)}
  $('#logoutAccount').addEventListener('click',async()=>{try{await api('/auth/logout',{method:'POST'})}catch{}token='';sessionStorage.removeItem(TOKEN_KEY);renderState()});
  $('#vaultUpload').addEventListener('change',async e=>{const file=e.target.files?.[0];e.target.value='';if(!file)return;
    const form=new FormData();form.append('file',file,file.name);
    try{await api('/vault',{method:'POST',body:form});renderState()}catch(err){showError(err.message)}
  });
  $('#signatureRequestForm').addEventListener('submit',async e=>{e.preventDefault();showError('');
    try{const req=await api('/sign-requests',{method:'POST',body:JSON.stringify({document_id:$('#sigDocSelect').value,recipient_name:$('#sigRecipientName').value,recipient_email:$('#sigRecipientEmail').value})});
      $('#signingLinkValue').value=req.sign_url;$('#signingLink').hidden=false;renderState()}
    catch(err){showError(err.message)}
  });
  $('#copySigningLink').addEventListener('click',()=>navigator.clipboard.writeText($('#signingLinkValue').value).catch(()=>{$('#signingLinkValue').select();document.execCommand('copy')}));
  async function saveResult(){const result=window.PDFCraftLastResult;
    if(!result||!result.filename.toLowerCase().endsWith('.pdf'))return;
    if(!token){open();showError('Sign in or create an account to save this PDF.');return}
    const data=new FormData();data.append('file',result.blob,result.filename);
    try{await api('/vault',{method:'POST',body:data});open();renderState()}catch(e){open();showError(e.message)}
  }
  window.PDFCraftWorkspace={open,saveResult};
  if(location.hash.startsWith('#workspace')){setTimeout(open,100)}
})();
