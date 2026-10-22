"""End-to-end route tests with an isolated temporary account database."""
import hashlib
import io
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

import fitz
from fastapi.testclient import TestClient

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import workspace
from app.main import app


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.mkdtemp(prefix='vault_test_')
        self.previous=workspace.DATA;workspace.DATA=Path(self.temp)
        self.c=TestClient(app)
        d=fitz.open();d.new_page().insert_text((72,72),'Signature needed')
        self.pdf=d.tobytes();d.close()
        self.a=self.register('a@example.org');self.b=self.register('b@example.org')

    def tearDown(self):
        self.c.close();workspace.DATA=self.previous;shutil.rmtree(self.temp)

    def register(self,email):
        r=self.c.post('/api/auth/register',json={'email':email,'password':'valid$password123'})
        self.assertEqual(r.status_code,200,r.text[:400]);return r.json()['token']

    def auth(self,token):return {'Authorization':'Bearer '+token}

    def save(self,token,name='draft.pdf'):
        return self.c.post('/api/vault',headers=self.auth(token),files={'file':(name,self.pdf,'application/pdf')})

    def test_auth_login_logout(self):
        r=self.c.post('/api/auth/register',json={'email':'a@example.org','password':'some$password123'})
        self.assertEqual(r.status_code,409)
        self.assertEqual(self.c.post('/api/auth/login',json={'email':'a@example.org','password':'wrong'}).status_code,401)
        r=self.c.post('/api/auth/login',json={'email':'a@example.org','password':'valid$password123'})
        self.assertEqual(r.status_code,200)
        t=r.json()['token']
        self.assertEqual(self.c.get('/api/auth/me',headers=self.auth(t)).json()['email'],'a@example.org')
        self.assertEqual(self.c.post('/api/auth/logout',headers=self.auth(t)).status_code,200)
        self.assertEqual(self.c.get('/api/auth/me',headers=self.auth(t)).status_code,401)

    def test_vault_access_isolation_and_delete(self):
        r=self.save(self.a);self.assertEqual(r.status_code,201,r.text)
        id=r.json()['id']
        self.assertEqual(self.c.get('/api/vault/'+id,headers=self.auth(self.a)).content,self.pdf)
        self.assertEqual(self.c.get('/api/vault/'+id,headers=self.auth(self.b)).status_code,404)
        self.assertEqual(self.c.delete('/api/vault/'+id,headers=self.auth(self.b)).status_code,404)
        self.assertEqual(self.c.get('/api/vault',headers=self.auth(self.b)).json()['documents'],[])
        self.assertEqual(self.c.delete('/api/vault/'+id,headers=self.auth(self.a)).status_code,200)
        self.assertEqual(self.c.get('/api/vault/'+id,headers=self.auth(self.a)).status_code,404)

    def test_invalid_uploads_rejected(self):
        r=self.c.post('/api/vault',headers=self.auth(self.a),files={'file':('bad.pdf',b'not a pdf','application/pdf')})
        self.assertEqual(r.status_code,422)
        r=self.c.post('/api/vault',files={'file':('draft.pdf',self.pdf,'application/pdf')})
        self.assertEqual(r.status_code,401)

    def test_sign_request_workflow_and_audit(self):
        docid=self.save(self.a).json()['id']
        req=self.c.post('/api/sign-requests',headers=self.auth(self.a),json={
            'document_id':docid,'recipient_name':'Alex Smith','recipient_email':'alex@example.com'})
        self.assertEqual(req.status_code,201,req.text)
        rid=req.json()['id'];token=req.json()['sign_url'].split('#')[1]
        self.assertEqual(self.c.get('/api/sign-public/'+token).status_code,200)
        preview=self.c.get('/api/sign-public/'+token+'/preview?page=1')
        self.assertEqual(preview.headers['content-type'],'image/png')
        self.assertTrue(preview.content.startswith(b'\x89PNG'))
        self.assertEqual(self.c.get('/api/sign-public/'+token+'/preview?page=9').status_code,422)
        without_consent=self.c.post('/api/sign-public/'+token+'/sign',json={'signer_name':'Alex Smith','consent':False})
        self.assertEqual(without_consent.status_code,422)
        result=self.c.post('/api/sign-public/'+token+'/sign',json={'signer_name':'Alex Smith','consent':True})
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(self.c.post('/api/sign-public/'+token+'/sign',json={'signer_name':'Alex Smith','consent':True}).status_code,409)
        response=self.c.get('/api/sign-requests/'+rid+'/download',headers=self.auth(self.a))
        self.assertEqual(response.status_code,200)
        with fitz.open(stream=response.content,filetype='pdf') as pdf:
            self.assertIn('Alex Smith',pdf[0].get_text())
        audit=self.c.get('/api/sign-requests/'+rid+'/audit',headers=self.auth(self.a))
        self.assertEqual(audit.status_code,200,audit.text)
        self.assertTrue(audit.json()['verified_chain'])
        self.assertEqual(len(audit.json()['events']),2)
        self.assertEqual(self.c.get('/api/sign-requests/'+rid+'/download',headers=self.auth(self.b)).status_code,404)

    def test_cancel_pending(self):
        id=self.save(self.a).json()['id']
        req=self.c.post('/api/sign-requests',headers=self.auth(self.a),json={
            'document_id':id,'recipient_name':'Alex Smith','recipient_email':'alex@example.com'}).json()
        self.assertEqual(self.c.delete('/api/vault/'+id,headers=self.auth(self.a)).status_code,409)
        r=self.c.post('/api/sign-requests/'+req['id']+'/cancel',headers=self.auth(self.a))
        self.assertEqual(r.status_code,200)
        self.assertEqual(self.c.get('/api/sign-public/'+req['sign_url'].split('#')[1]).status_code,409)
        self.assertEqual(self.c.delete('/api/vault/'+id,headers=self.auth(self.a)).status_code,200)


if __name__=='__main__':unittest.main()
