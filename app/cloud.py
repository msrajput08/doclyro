"""Optional user-authorized Google Drive / Dropbox integration.

No cloud provider data is accessed until the site operator supplies OAuth app
credentials AND an individual user authorizes their own account.
Access/refresh tokens are encrypted at rest; imported files enter the opt-in
user vault. External API calls are bounded by timeouts and file quotas.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import secrets
import sqlite3
import time
from pathlib import Path
from urllib.parse import urlencode, quote

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from starlette.datastructures import UploadFile

from . import workspace as ws

router=APIRouter(prefix='/api/cloud',tags=['cloud integrations'])
GOOGLE_AUTH='https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN='https://oauth2.googleapis.com/token'
GOOGLE_SCOPE='https://www.googleapis.com/auth/drive.readonly https://www.googleapis.com/auth/drive.file'
DROPBOX_AUTH='https://www.dropbox.com/oauth2/authorize'
DROPBOX_TOKEN='https://api.dropboxapi.com/oauth2/token'
PROVIDERS=('google','dropbox')


def check_provider(p):
    if p not in PROVIDERS:ws.fail(404,'Unknown cloud provider.')
    cid,secret = config(p)
    if not cid:ws.fail(503,f'{p.title()} OAuth app is not configured on this server.')
    return cid,secret


def config(provider):
    prefix='GOOGLE' if provider=='google' else 'DROPBOX'
    return os.getenv(prefix+'_CLIENT_ID',''),os.getenv(prefix+'_CLIENT_SECRET','')


def initialize(conn):
    conn.executescript('''CREATE TABLE IF NOT EXISTS oauth_flows (
        state_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        provider TEXT NOT NULL, verifier TEXT NOT NULL, expires_at INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS cloud_tokens (
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        provider TEXT NOT NULL, token_cipher TEXT NOT NULL,
        PRIMARY KEY(user_id,provider));''')


def token_cipher():
    from cryptography.fernet import Fernet
    supplied=os.getenv('PDFCRAFT_ENCRYPTION_KEY','').strip()
    if supplied:return Fernet(supplied.encode())
    ws.DATA.mkdir(parents=True,exist_ok=True,mode=0o700)
    keyfile=ws.DATA/'storage.key'
    try:
        fd=os.open(keyfile,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        try:
            with os.fdopen(fd,'wb') as f:f.write(Fernet.generate_key())
        except Exception:
            keyfile.unlink(missing_ok=True);raise
    except FileExistsError:pass
    return Fernet(keyfile.read_bytes().strip())


def state_hash(raw):return hashlib.sha256(raw.encode()).hexdigest()


def redirect_url(request,provider):
    origin=os.getenv('PDFCRAFT_PUBLIC_URL','').strip().rstrip('/')
    if not origin:origin=str(request.base_url).rstrip('/')
    return origin+'/api/cloud/callback/'+provider


@router.get('')
def status(user=Depends(ws.require_user)):
    conn=ws.db()
    try:
        initialize(conn)
        active={row['provider'] for row in conn.execute('SELECT provider FROM cloud_tokens WHERE user_id=?',(user['id'],))}
        return {'providers':{p:{'connected':p in active,'configured':bool(config(p)[0])} for p in PROVIDERS}}
    finally:conn.close()


@router.post('/{provider}/authorize')
def authorize(provider:str,request:Request,user=Depends(ws.require_user)):
    cid,secret=check_provider(provider)
    state=secrets.token_urlsafe(40);verifier=secrets.token_urlsafe(65)
    challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b'=').decode()
    conn=ws.db()
    try:
        initialize(conn)
        conn.execute('INSERT INTO oauth_flows VALUES (?,?,?,?,?)',
                     (state_hash(state),user['id'],provider,verifier,int(time.time())+600))
        conn.commit()
    finally:conn.close()
    callback=redirect_url(request,provider)
    if provider=='google':
        params={'client_id':cid,'redirect_uri':callback,'response_type':'code','scope':GOOGLE_SCOPE,
                'access_type':'offline','prompt':'consent','state':state,'code_challenge':challenge,
                'code_challenge_method':'S256'}
        url=GOOGLE_AUTH+'?'+urlencode(params)
    else:
        params={'client_id':cid,'redirect_uri':callback,'response_type':'code',
                'token_access_type':'offline','state':state,'code_challenge':challenge,
                'code_challenge_method':'S256'}
        url=DROPBOX_AUTH+'?'+urlencode(params)
    return {'authorization_url':url}


@router.get('/callback/{provider}')
def callback(provider:str,request:Request,state:str='',code:str='',error:str=''):
    check_provider(provider)
    if error or not state or not code:
        return RedirectResponse('/#workspace?error=oauth_denied',status_code=303)
    conn=ws.db()
    try:
        initialize(conn)
        row=conn.execute('SELECT * FROM oauth_flows WHERE state_hash=? AND provider=?',
                         (state_hash(state),provider)).fetchone()
        if not row or row['expires_at'] < time.time():ws.fail(400,'OAuth state expired or invalid.')
        conn.execute('DELETE FROM oauth_flows WHERE state_hash=?',(state_hash(state),))
        conn.commit()
        cid,secret=check_provider(provider)
        payload={'code':code,'grant_type':'authorization_code','redirect_uri':redirect_url(request,provider),
                 'client_id':cid,'code_verifier':row['verifier']}
        if secret:payload['client_secret']=secret
        endpoint=GOOGLE_TOKEN if provider=='google' else DROPBOX_TOKEN
        try:
            result=httpx.post(endpoint,data=payload,timeout=30)
            result.raise_for_status();tokens=result.json()
        except (httpx.HTTPError,ValueError) as exc:ws.fail(502,'Provider token exchange failed: '+str(exc)[:150])
        if not tokens.get('access_token'):ws.fail(502,'Provider returned no access token.')
        encrypted=token_cipher().encrypt(json.dumps(tokens).encode()).decode()
        conn.execute('''INSERT INTO cloud_tokens (user_id,provider,token_cipher) VALUES(?,?,?)
             ON CONFLICT (user_id,provider) DO UPDATE SET token_cipher=excluded.token_cipher''',
             (row['user_id'],provider,encrypted))
        conn.commit()
        return RedirectResponse('/#workspace',status_code=303)
    finally:conn.close()


def get_tokens(conn,provider,userid):
    initialize(conn)
    row=conn.execute('SELECT token_cipher FROM cloud_tokens WHERE user_id=? AND provider=?',(userid,provider)).fetchone()
    if not row:ws.fail(409,'Connect this provider from your workspace first.')
    try:tokens=json.loads(token_cipher().decrypt(row['token_cipher'].encode()))
    except (InvalidToken,ValueError):ws.fail(500,'Cloud credentials cannot be decrypted (check encryption key).')
    return tokens


def client_credentials(conn,provider,userid):
    tokens=get_tokens(conn,provider,userid)
    # Access token refreshing is opportunistic: retries once on unauthorized response.
    return tokens


def refresh(provider,tokens,userid,conn):
    refresh_token=tokens.get('refresh_token')
    if not refresh_token:ws.fail(401,'Cloud access expired. Reconnect the provider.')
    cid,secret=check_provider(provider)
    payload={'refresh_token':refresh_token,'grant_type':'refresh_token','client_id':cid}
    if secret:payload['client_secret']=secret
    endpoint=GOOGLE_TOKEN if provider=='google' else DROPBOX_TOKEN
    try:
        r=httpx.post(endpoint,data=payload,timeout=25);r.raise_for_status();new=r.json()
    except httpx.HTTPError:ws.fail(502,'Unable to refresh cloud access.')
    tokens.update(new);tokens['refresh_token']=new.get('refresh_token') or refresh_token
    cipher=token_cipher().encrypt(json.dumps(tokens).encode()).decode()
    conn.execute('UPDATE cloud_tokens SET token_cipher=? WHERE user_id=? AND provider=?',
                 (cipher,userid,provider));conn.commit()
    return tokens


def request_provider(provider,userid,method,url,**kwargs):
    conn=ws.db()
    try:
        token=get_tokens(conn,provider,userid)
        original_headers=kwargs.pop('headers',{})
        for attempt in range(2):
            header={**original_headers,'Authorization':'Bearer '+token['access_token']}
            try:
                resp=httpx.request(method,url,headers=header,timeout=60,**kwargs)
            except httpx.HTTPError as exc:ws.fail(502,'Provider network request failed: '+str(exc)[:150])
            if resp.status_code==401 and not attempt:
                token=refresh(provider,token,userid,conn);continue
            if resp.status_code>=400:ws.fail(502,f'Provider error ({resp.status_code}): '+resp.text[:140])
            return resp
        ws.fail(502,'Provider rejected the access token.')
    finally:conn.close()


@router.get('/{provider}/files')
def list_remote(provider:str,user=Depends(ws.require_user)):
    check_provider(provider)
    if provider=='google':
        # Non-exportable Google Docs deliberately excluded; PDFs only.
        params={'q':"mimeType='application/pdf' and trashed=false",'fields':'nextPageToken,files(id,name,size,mimeType,webViewLink)',
                'pageSize':100,'orderBy':'modifiedTime desc'}
        response=request_provider(provider,user['id'],'GET','https://www.googleapis.com/drive/v3/files',params=params)
        docs=[{'id':a['id'],'name':a['name'],'size':int(a.get('size',0) or 0)} for a in response.json().get('files',[])]
    else:
        response=request_provider(provider,user['id'],'POST','https://api.dropboxapi.com/2/files/list_folder',json={
            'path':'','recursive':False,'limit':100})
        docs=[{'id':a['id'],'name':a['name'],'size':a.get('size',0)} for a in response.json().get('entries',[])
              if a.get('.tag')=='file' and a.get('name','').lower().endswith('.pdf')]
    return {'files':docs}


class RemoteFile(BaseModel):
    file_id:str=Field(min_length=2,max_length=1024)


@router.post('/{provider}/import')
async def import_remote(provider:str,body:RemoteFile,user=Depends(ws.require_user)):
    check_provider(provider)
    if provider=='google':
        url='https://www.googleapis.com/drive/v3/files/'+quote(body.file_id,safe='')
        meta=request_provider(provider,user['id'],'GET',url,params={'fields':'id,name,mimeType,size'}).json()
        if meta.get('mimeType')!='application/pdf':ws.fail(422,'Only PDF files can be imported.')
        if int(meta.get('size') or 0)>ws.MAX_FILE_BYTES:ws.fail(413,'Remote PDF is too large.')
        data=request_provider(provider,user['id'],'GET',url,params={'alt':'media'}).content
    else:
        if not body.file_id.startswith('id:'):ws.fail(422,'Expected a Dropbox file ID.')
        response=request_provider(provider,user['id'],'POST',
            'https://content.dropboxapi.com/2/files/download',
            headers={'Dropbox-API-Arg':json.dumps({'path':body.file_id})})
        data=response.content
        meta=json.loads(response.headers.get('Dropbox-API-Result','{}'))
    if len(data)>ws.MAX_FILE_BYTES:ws.fail(413,'Remote PDF exceeds the file-size limit.')
    filename=meta.get('name','imported.pdf')
    upload=UploadFile(filename=filename,file=io.BytesIO(data))
    return await ws.store_document(upload,user['id'])


@router.post('/{provider}/export/{docid}')
def export_remote(provider:str,docid:str,user=Depends(ws.require_user)):
    check_provider(provider)
    conn=ws.db()
    try:item=ws.document(conn,user['id'],docid)
    finally:conn.close()
    pdf=ws.vault_path(user['id'],item['id']).read_bytes()
    if provider=='google':
        boundary='pdfcraft_'+secrets.token_hex(9)
        metadata=json.dumps({'name':item['filename'],'mimeType':'application/pdf'}).encode()
        body=(f'--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n'.encode()+metadata+
              f'\r\n--{boundary}\r\nContent-Type: application/pdf\r\n\r\n'.encode()+pdf+f'\r\n--{boundary}--\r\n'.encode())
        result=request_provider(provider,user['id'],'POST','https://www.googleapis.com/upload/drive/v3/files',
            params={'uploadType':'multipart','fields':'id,name,webViewLink'},
            headers={'Content-Type':f'multipart/related; boundary={boundary}'},content=body).json()
    else:
        result=request_provider(provider,user['id'],'POST',
            'https://content.dropboxapi.com/2/files/upload',
            headers={'Content-Type':'application/octet-stream',
                     'Dropbox-API-Arg':json.dumps({'path':'/'+item['filename'],'mode':'add','autorename':True})},
            content=pdf).json()
    return {'provider':provider,'result':result}


@router.delete('/{provider}')
def disconnect(provider:str,user=Depends(ws.require_user)):
    check_provider(provider)
    conn=ws.db()
    try:
        initialize(conn)
        conn.execute('DELETE FROM cloud_tokens WHERE user_id=? AND provider=?',(user['id'],provider));conn.commit()
        return {'disconnected':True}
    finally:conn.close()
