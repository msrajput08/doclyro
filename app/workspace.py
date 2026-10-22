"""Opt-in self-hosted account vault and signature-request service.

Stores user-selected documents on persistent disk, never the temporary processing
uploads. Authentication uses random bearer tokens stored as SHA-256 digests.
Signer links are long random, one-use bearer capabilities and do NOT verify identity.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import secrets
import smtplib
from email.message import EmailMessage
import shutil
import sqlite3
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import fitz
from fastapi import APIRouter, Body, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from .processor import op_sign, pdfopen, ProcessingError

DATA = Path(os.getenv('PDFCRAFT_DATA_DIR', str(Path(__file__).resolve().parents[1] / 'data')))
MAX_VAULT_BYTES = int(os.getenv('VAULT_TOTAL_MB', '300')) * 1024 * 1024
MAX_FILE_BYTES = int(os.getenv('VAULT_FILE_MB', '50')) * 1024 * 1024
SESSION_HOURS = 24
router = APIRouter(prefix='/api', tags=['accounts and signatures'])


def db():
    DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DATA / 'workspace.db'), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA busy_timeout=10000')
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY, email TEXT NOT NULL UNIQUE, salt TEXT NOT NULL,
        password_hash TEXT NOT NULL, created_at INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS password_resets (
        token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        expires_at INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS sessions (
        token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        expires_at INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS documents (
        id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        filename TEXT NOT NULL, size INTEGER NOT NULL, sha256 TEXT NOT NULL,
        created_at INTEGER NOT NULL);
    CREATE INDEX IF NOT EXISTS idx_doc_user ON documents(owner_id,created_at);
    CREATE TABLE IF NOT EXISTS sign_requests (
        id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE RESTRICT,
        recipient_name TEXT NOT NULL, recipient_email TEXT NOT NULL,
        token_hash TEXT NOT NULL UNIQUE, status TEXT NOT NULL,
        created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
        signed_at INTEGER, signature_text TEXT, original_sha256 TEXT NOT NULL,
        signed_sha256 TEXT, consent TEXT);
    CREATE TABLE IF NOT EXISTS rate_limits (key TEXT PRIMARY KEY, hits INTEGER NOT NULL, window_start INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS signature_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, request_id TEXT NOT NULL
        REFERENCES sign_requests(id) ON DELETE CASCADE,
        kind TEXT NOT NULL, timestamp INTEGER NOT NULL,
        details_json TEXT NOT NULL, previous_hash TEXT NOT NULL,
        event_hash TEXT NOT NULL);
    ''')
    return conn


def fail(status, message):
    raise HTTPException(status_code=status, detail=message)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode('utf8')).hexdigest()


def throttle(key: str, max_hits: int=12, seconds: int=900):
    """Shared SQLite request counter, backed by persistent storage across workers."""
    conn=db()
    try:
        now=int(time.time()); key=digest(key)
        with conn:
            entry=conn.execute('SELECT hits,window_start FROM rate_limits WHERE key=?',(key,)).fetchone()
            if not entry or now-entry['window_start']>=seconds:
                conn.execute('INSERT OR REPLACE INTO rate_limits VALUES (?,?,?)',(key,1,now))
            elif entry['hits']>=max_hits:
                fail(429,'Too many attempts. Try again later.')
            else:
                conn.execute('UPDATE rate_limits SET hits=hits+1 WHERE key=?',(key,))
    finally:conn.close()


def pwd_hash(password: str, salt: bytes) -> str:
    return hashlib.scrypt(password.encode('utf8'), salt=salt, n=2**14, r=8, p=1, dklen=32).hex()


def validate_email(email: str):
    email = email.strip().lower()
    if len(email) > 254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
        fail(422, 'Enter a valid email address.')
    return email


def safe_filename(name):
    return (re.sub(r'[^A-Za-z0-9_.() -]', '_', Path(str(name or 'document.pdf').replace('\\','/')).name)[:110] or 'document.pdf')


class Credentials(BaseModel):
    email: str=Field(max_length=254)
    password: str=Field(max_length=200)


def require_user(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith('Bearer '):
        fail(401, 'Sign in to use your document vault.')
    token = authorization.removeprefix('Bearer ').strip()
    if len(token) < 24:
        fail(401, 'Invalid session.')
    conn = db()
    try:
        user = conn.execute('''SELECT u.id,u.email,s.expires_at FROM sessions s
                    JOIN users u ON u.id=s.user_id WHERE s.token_hash=?''', (digest(token),)).fetchone()
        if not user or user['expires_at'] < int(time.time()):
            fail(401, 'Session expired. Please sign in again.')
        return {'id':user['id'], 'email':user['email'], 'token_hash':digest(token)}
    finally: conn.close()


def new_session(conn, userid):
    token = secrets.token_urlsafe(32)
    expires = int(time.time()) + SESSION_HOURS*3600
    conn.execute('INSERT INTO sessions VALUES (?,?,?)', (digest(token), userid, expires))
    conn.commit()
    return {'token':token, 'expires_at':expires}


@router.post('/auth/register')
def register(form: Credentials, request:Request):
    throttle('register:'+str(request.client.host if request.client else 'unknown'),max_hits=20,seconds=3600)
    email = validate_email(form.email)
    if not 12 <= len(form.password) <= 200:
        fail(422, 'Password must be at least 12 characters.')
    conn=db()
    try:
        if conn.execute('SELECT 1 FROM users WHERE email=?',(email,)).fetchone():
            fail(409, 'An account with this email already exists.')
        userid=uuid.uuid4().hex; salt=os.urandom(16)
        conn.execute('INSERT INTO users VALUES (?,?,?,?,?)',
                     (userid,email,salt.hex(),pwd_hash(form.password,salt),int(time.time())))
        conn.commit()
        return {'user':{'id':userid,'email':email}, **new_session(conn, userid)}
    finally:conn.close()


@router.post('/auth/login')
def login(form: Credentials, request:Request):
    throttle('login:'+form.email.strip().lower()+':'+str(request.client.host if request.client else 'unknown'),max_hits=20)
    # No distinction between unknown email and wrong password.
    email=validate_email(form.email)
    conn=db()
    try:
        row=conn.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
        if row:
            calculated=pwd_hash(form.password, bytes.fromhex(row['salt']))
            good=secrets.compare_digest(calculated,row['password_hash'])
        else:
            calculated=pwd_hash(form.password, b'0'*16)
            good=False
        if not good:
            fail(401, 'Invalid email or password.')
        return {'user':{'id':row['id'],'email':email}, **new_session(conn,row['id'])}
    finally:conn.close()


class PasswordResetRequest(BaseModel):
    email: str=Field(max_length=254)


class PasswordResetComplete(BaseModel):
    token: str=Field(min_length=32,max_length=200)
    password: str=Field(min_length=12,max_length=200)


def send_email(to: str, subject: str, message: str):
    """Optional authenticated SMTP. No email is silently queued without a server."""
    host=os.getenv('SMTP_HOST','').strip()
    sender=os.getenv('SMTP_FROM','').strip()
    if not host or not sender:
        raise RuntimeError('SMTP_HOST and SMTP_FROM must be configured.')
    port=int(os.getenv('SMTP_PORT','587'))
    mail=EmailMessage();mail['From']=sender;mail['To']=to;mail['Subject']=subject
    mail.set_content(message)
    if os.getenv('SMTP_SSL','false').lower()=='true':
        server=smtplib.SMTP_SSL(host,port,timeout=15)
    else:
        server=smtplib.SMTP(host,port,timeout=15)
    with server:
        if os.getenv('SMTP_STARTTLS','true').lower()=='true' and os.getenv('SMTP_SSL','false').lower()!='true':
            server.starttls()
        username=os.getenv('SMTP_USERNAME','')
        if username:server.login(username,os.getenv('SMTP_PASSWORD',''))
        server.send_message(mail)


@router.post('/auth/request-reset')
def request_reset(body:PasswordResetRequest,request:Request):
    throttle('reset:'+str(request.client.host if request.client else 'unknown'),max_hits=15,seconds=3600)
    if not os.getenv('SMTP_HOST') or not os.getenv('SMTP_FROM'):
        fail(503,'Email recovery is unavailable until SMTP is configured by the server administrator.')
    email=validate_email(body.email)
    conn=db()
    try:
        row=conn.execute('SELECT id FROM users WHERE email=?',(email,)).fetchone()
        if row:
            token=secrets.token_urlsafe(40)
            expiry=int(time.time())+1800
            with conn:
                conn.execute('DELETE FROM password_resets WHERE user_id=?',(row['id'],))
                conn.execute('INSERT INTO password_resets VALUES (?,?,?)',(digest(token),row['id'],expiry))
            base=os.getenv('PDFCRAFT_PUBLIC_URL','').rstrip('/') or str(request.base_url).rstrip('/')
            link=base+'/#reset/'+token
            try:send_email(email,'PDFCraft Studio password reset',
                'You requested a password reset. This link expires in 30 minutes and can only be used once:\n\n'+link+
                '\n\nIf you did not request this, ignore this email.')
            except Exception:
                import logging
                logging.exception('SMTP password reset delivery failed')
    finally:conn.close()
    return {'message':'If an account exists, a one-time recovery link has been sent.'}


@router.post('/auth/reset-password')
def reset_password(body:PasswordResetComplete):
    conn=db()
    try:
        row=conn.execute('SELECT user_id,expires_at FROM password_resets WHERE token_hash=?',
                         (digest(body.token),)).fetchone()
        if not row or row['expires_at']<int(time.time()):
            fail(422,'Reset link is invalid or expired.')
        salt=os.urandom(16)
        with conn:
            conn.execute('UPDATE users SET salt=?,password_hash=? WHERE id=?',
                         (salt.hex(),pwd_hash(body.password,salt),row['user_id']))
            conn.execute('DELETE FROM password_resets WHERE user_id=?',(row['user_id'],))
            conn.execute('DELETE FROM sessions WHERE user_id=?',(row['user_id'],))
        return {'ok':True,'message':'Password changed. All previous sessions have been signed out.'}
    finally:conn.close()


@router.get('/auth/me')
def me(user=Depends(require_user)):
    return {'id':user['id'],'email':user['email']}


@router.post('/auth/logout')
def logout(user=Depends(require_user)):
    conn=db()
    try:
        conn.execute('DELETE FROM sessions WHERE token_hash=?',(user['token_hash'],));conn.commit()
    finally:conn.close()
    return {'ok':True}


def vault_path(user_id, doc_id):
    # Both IDs are exclusively server-created UUID hex strings.
    return DATA/'vault'/user_id/(doc_id+'.pdf')


def document(conn, userid, docid):
    item=conn.execute('SELECT * FROM documents WHERE id=? AND owner_id=?',(docid,userid)).fetchone()
    if not item:fail(404,'Document not found.')
    return item


@router.get('/vault')
def list_documents(user=Depends(require_user)):
    conn=db()
    try:
        items=[dict(x) for x in conn.execute('''SELECT id,filename,size,sha256,created_at
                       FROM documents WHERE owner_id=? ORDER BY created_at DESC''',(user['id'],))]
        return {'documents':items,'used_bytes':sum(x['size'] for x in items), 'quota_bytes':MAX_VAULT_BYTES}
    finally:conn.close()


async def store_document(file, owner_id):
    temp=Path(tempfile.mkstemp(prefix='pdfcraft_vault_',suffix='.pdf')[1]);size=0
    try:
        with temp.open('wb') as out:
            while True:
                chunk=await file.read(1024*1024)
                if not chunk: break
                size += len(chunk)
                if size>MAX_FILE_BYTES:fail(413,'Vault file exceeds configured limit.')
                out.write(chunk)
        if not size:fail(422,'Empty PDF.')
        try:
            with fitz.open(str(temp)) as d:
                if not d.is_pdf or d.needs_pass or len(d)==0:
                    fail(422,'Upload a valid, unlocked PDF file.')
        except (fitz.FileDataError,fitz.FileNotFoundError):
            fail(422,'Invalid PDF file.')
        conn=db()
        try:
            used=conn.execute('SELECT COALESCE(SUM(size),0) FROM documents WHERE owner_id=?',(owner_id,)).fetchone()[0]
            if used+size>MAX_VAULT_BYTES:fail(413,'Document vault storage limit exceeded.')
            docid=uuid.uuid4().hex
            final=vault_path(owner_id,docid);final.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            sha=hashlib.sha256(temp.read_bytes()).hexdigest()
            shutil.move(str(temp),final)
            conn.execute('INSERT INTO documents VALUES (?,?,?,?,?,?)',
                         (docid,owner_id,safe_filename(file.filename),size,sha,int(time.time())))
            conn.commit()
            return {'id':docid,'filename':safe_filename(file.filename),'size':size,'sha256':sha}
        finally:conn.close()
    finally:temp.unlink(missing_ok=True)


@router.post('/vault',status_code=201)
async def upload_to_vault(file:UploadFile=File(...), user=Depends(require_user)):
    return await store_document(file,user['id'])


@router.get('/vault/{docid}')
def get_document(docid:str,user=Depends(require_user)):
    conn=db()
    try: item=document(conn,user['id'],docid)
    finally:conn.close()
    path=vault_path(user['id'],item['id'])
    if not path.is_file():fail(404,'Document contents unavailable.')
    return FileResponse(str(path),media_type='application/pdf',filename=item['filename'],headers={'Cache-Control':'no-store'})


@router.delete('/vault/{docid}')
def delete_document(docid:str,user=Depends(require_user)):
    conn=db()
    try:
        item=document(conn,user['id'],docid)
        waiting=conn.execute('''SELECT 1 FROM sign_requests WHERE owner_id=?
                                 AND document_id=? AND status='pending' LIMIT 1''',(user['id'],docid)).fetchone()
        if waiting:fail(409,'Cancel the pending signature requests before deleting this document.')
        # Historic sign requests reference source documents; do not delete them until requests removed.
        conn.execute('DELETE FROM signature_events WHERE request_id IN (SELECT id FROM sign_requests WHERE document_id=?)',(docid,))
        conn.execute('DELETE FROM sign_requests WHERE document_id=? AND owner_id=?',(docid,user['id']))
        conn.execute('DELETE FROM documents WHERE id=? AND owner_id=?',(docid,user['id']))
        conn.commit()
        vault_path(user['id'],docid).unlink(missing_ok=True)
        return {'ok':True}
    finally:conn.close()


def audit(conn, rid, kind, details):
    stamp=int(time.time())
    prev=conn.execute('SELECT event_hash FROM signature_events WHERE request_id=? ORDER BY id DESC LIMIT 1',(rid,)).fetchone()
    previous=prev['event_hash'] if prev else '0'*64
    payload=json.dumps({'request_id':rid,'kind':kind,'time':stamp,'details':details},sort_keys=True,separators=(',',':'))
    eventhash=digest(previous+payload)
    conn.execute('''INSERT INTO signature_events
                  (request_id,kind,timestamp,details_json,previous_hash,event_hash)
                  VALUES (?,?,?,?,?,?)''',(rid,kind,stamp,payload,previous,eventhash))


class SignatureRequest(BaseModel):
    document_id: str
    recipient_name: str=Field(min_length=1,max_length=120)
    recipient_email: str
    expiry_days: int=Field(default=7,ge=1,le=30)


@router.post('/sign-requests',status_code=201)
def create_signature_request(body: SignatureRequest, request: Request, user=Depends(require_user)):
    recipient_email=validate_email(body.recipient_email)
    conn=db()
    try:
        item=document(conn,user['id'],body.document_id)
        if not vault_path(user['id'],item['id']).exists():fail(404,'Stored PDF not found.')
        rid=uuid.uuid4().hex; token=secrets.token_urlsafe(40); now=int(time.time())
        conn.execute('''INSERT INTO sign_requests (id,owner_id,document_id,recipient_name,recipient_email,
                       token_hash,status,created_at,expires_at,original_sha256)
                       VALUES (?,?,?,?,?,?,?,?,?,?)''',
                     (rid,user['id'],item['id'],body.recipient_name.strip(),recipient_email,digest(token),'pending',now,now+body.expiry_days*86400,item['sha256']))
        audit(conn,rid,'request_created',{'document_sha256':item['sha256'],'recipient_email':recipient_email})
        conn.commit()
        base=os.getenv('PDFCRAFT_PUBLIC_URL','').rstrip('/') or str(request.base_url).rstrip('/')
        link=base+'/sign.html#'+token
        sent=False
        if os.getenv('SMTP_HOST') and os.getenv('SMTP_FROM'):
            try:
                send_email(recipient_email,'Signature requested — PDFCraft Studio',
                           f'{body.recipient_name.strip()},\n\nYou have been invited to review and electronically sign {item["filename"]}. '
                           f'Use this private link before it expires:\n\n{link}\n\nDo not forward this link.')
                sent=True
            except Exception:
                import logging
                logging.exception('SMTP signature invitation delivery failed')
        return {'id':rid,'status':'pending','sign_url':link,'email_sent':sent,
                'expires_at':now+body.expiry_days*86400,
                'notice':'Signer link proves possession of link, not the signer’s legal identity.'}
    finally:conn.close()


def signer_record(conn, token):
    if not re.fullmatch(r'[A-Za-z0-9_-]{40,150}',token):fail(404,'Signature request not found.')
    item=conn.execute('SELECT * FROM sign_requests WHERE token_hash=?',(digest(token),)).fetchone()
    if not item:fail(404,'Signature request not found.')
    if item['expires_at'] < int(time.time()):fail(410,'Signature request expired.')
    if item['status'] != 'pending':fail(409,'Signature request is not open.')
    return item


@router.get('/sign-public/{token}')
def public_signature_info(token:str):
    conn=db()
    try:
        item=signer_record(conn,token)
        docpath=vault_path(item['owner_id'],item['document_id'])
        with fitz.open(str(docpath)) as doc:
            return {'recipient_name':item['recipient_name'],'recipient_email':item['recipient_email'],
                    'pages':len(doc),'expires_at':item['expires_at'],
                    'original_sha256':item['original_sha256']}
    finally:conn.close()


@router.get('/sign-public/{token}/preview')
def public_signature_preview(token:str, page:int=1):
    conn=db()
    try:
        item=signer_record(conn,token)
        with fitz.open(str(vault_path(item['owner_id'],item['document_id']))) as doc:
            if not 1<=page<=len(doc):fail(422,'Invalid page number.')
            pix=doc[page-1].get_pixmap(matrix=fitz.Matrix(0.9,0.9),alpha=False)
            return Response(pix.tobytes('png'),media_type='image/png',headers={'Cache-Control':'no-store'})
    finally:conn.close()


class SignedConsent(BaseModel):
    signer_name: str=Field(min_length=2,max_length=120)
    consent: bool
    signature_image: str | None = None
    signature_text: str | None = None
    page: int=Field(default=1,ge=1)
    x: float=Field(default=72,ge=0)
    y: float=Field(default=0,ge=0)
    width: float=Field(default=220,ge=20,le=500)
    height: float=Field(default=80,ge=10,le=300)


@router.post('/sign-public/{token}/sign')
def public_sign(token:str,body:SignedConsent,request:Request):
    throttle('sign:'+token,max_hits=15)
    if not body.consent:fail(422,'Consent is required before signing.')
    # Signers are never instructed to enter passwords or government identity numbers.
    conn=db()
    try:
        row=signer_record(conn,token)
        rid=row['id'];source=vault_path(row['owner_id'],row['document_id'])
        if not source.exists():fail(404,'Original document unavailable.')
        folder=DATA/'signatures'/row['owner_id'];folder.mkdir(parents=True,exist_ok=True,mode=0o700)
        with tempfile.TemporaryDirectory(prefix='sign_',dir=folder) as tmp:
            opts={'text':(body.signature_text or body.signer_name),
                  'page':body.page,'x':body.x,'y':body.y,
                  'width':body.width,'height':body.height}
            if body.signature_image:opts['signature_image']=body.signature_image
            try:result=op_sign([source],opts,Path(tmp))
            except (ProcessingError,ValueError) as ex:fail(422,str(ex))
            temp_result=folder/(rid+'_'+uuid.uuid4().hex+'.tmp')
            shutil.copyfile(result,temp_result)
        target=folder/(rid+'.pdf')
        stamp=int(time.time()); contenthash=hashlib.sha256(temp_result.read_bytes()).hexdigest()
        # Atomic state transition prevents a second signer overwrite on concurrent requests.
        cur=conn.execute('''UPDATE sign_requests SET status='signed',signed_at=?,signature_text=?,signed_sha256=?,consent=?
                    WHERE id=? AND status='pending' AND expires_at>=?''',
                (stamp,body.signer_name,contenthash,'I agree to sign this document',rid,stamp))
        if cur.rowcount != 1:
            temp_result.unlink(missing_ok=True)
            fail(409,'This request has already been completed or expired.')
        os.replace(temp_result,target)
        audit(conn,rid,'signed',{'signer_name':body.signer_name,
                                'sha256':contenthash,
                                'original_sha256':row['original_sha256'],
                                'consent':True, 'verification':'link possession only'})
        conn.commit()
        return {'status':'signed','timestamp':stamp,'sha256':contenthash,
                'notice':'Visible electronic signature: identity and cryptographic certificate not verified.'}
    finally:conn.close()


@router.get('/sign-requests')
def list_sign_requests(user=Depends(require_user)):
    conn=db()
    try:
        requests=[dict(row) for row in conn.execute('''SELECT r.id,r.document_id,d.filename,r.recipient_name,
          r.recipient_email,r.status,r.created_at,r.expires_at,r.signed_at,r.signed_sha256
          FROM sign_requests r JOIN documents d ON d.id=r.document_id
          WHERE r.owner_id=? ORDER BY r.created_at DESC''',(user['id'],))]
        return {'requests':requests}
    finally:conn.close()


@router.post('/sign-requests/{rid}/cancel')
def cancel_signature_request(rid:str,user=Depends(require_user)):
    conn=db()
    try:
        row=conn.execute('SELECT * FROM sign_requests WHERE id=? AND owner_id=?',(rid,user['id'])).fetchone()
        if not row:fail(404,'Request not found.')
        if row['status']!='pending':fail(409,'Only pending requests can be cancelled.')
        conn.execute('UPDATE sign_requests SET status=? WHERE id=?',('cancelled',rid))
        audit(conn,rid,'cancelled',{'by':'requester'});conn.commit()
        return {'ok':True}
    finally:conn.close()


@router.get('/sign-requests/{rid}/download')
def download_signed(rid:str,user=Depends(require_user)):
    conn=db()
    try:
        row=conn.execute('SELECT * FROM sign_requests WHERE id=? AND owner_id=?',(rid,user['id'])).fetchone()
        if not row:fail(404,'Request not found.')
        if row['status']!='signed':fail(409,'Document is not signed yet.')
        original=conn.execute('SELECT filename FROM documents WHERE id=?',(row['document_id'],)).fetchone()
        filename=('signed_'+original['filename']) if original else 'signed.pdf'
        path=DATA/'signatures'/user['id']/(rid+'.pdf')
        if not path.exists():fail(404,'Signed file missing.')
        return FileResponse(str(path),filename=filename,media_type='application/pdf')
    finally:conn.close()


@router.get('/sign-requests/{rid}/audit')
def get_signature_audit(rid:str,user=Depends(require_user)):
    conn=db()
    try:
        row=conn.execute('SELECT * FROM sign_requests WHERE id=? AND owner_id=?',(rid,user['id'])).fetchone()
        if not row:fail(404,'Request not found.')
        history=[json.loads(x['details_json']) | {'previous_hash':x['previous_hash'],'event_hash':x['event_hash']} for x in
                 conn.execute('SELECT * FROM signature_events WHERE request_id=? ORDER BY id',(rid,))]
        previous='0'*64
        for event in history:
            body={key:event[key] for key in ('request_id','kind','time','details')}
            if event['previous_hash'] != previous or digest(previous+json.dumps(body,sort_keys=True,separators=(',',':'))) != event['event_hash']:
                fail(500,'Audit event integrity check failed.')
            previous=event['event_hash']
        return {'request_id':rid,'status':row['status'], 'recipient_email':row['recipient_email'],
                'source_sha256':row['original_sha256'],'signed_sha256':row['signed_sha256'],
                'events':history,'verified_chain':True,
                'disclaimer':'App-generated evidence, not an independently trusted digital signature or identity audit.'}
    finally:conn.close()
