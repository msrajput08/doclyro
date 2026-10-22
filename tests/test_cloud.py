"""Tests OAuth state validation and token encryption without provider access."""
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs,urlparse
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.main import app
from app import workspace as ws

class CloudTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.mkdtemp(prefix='cloudtest_')
        self.original=ws.DATA;ws.DATA=Path(self.tmp)
        self.client=TestClient(app)
        result=self.client.post('/api/auth/register',json={'email':'cloud@example.com','password':'passphrase-secure-123'})
        self.headers={'Authorization':'Bearer '+result.json()['token']}
    def tearDown(self):
        self.client.close();ws.DATA=self.original;shutil.rmtree(self.tmp)
    def test_nonconfigured_connect_returns_message(self):
        with patch.dict(os.environ,{'GOOGLE_CLIENT_ID':'','DROPBOX_CLIENT_ID':''}):
            status=self.client.get('/api/cloud',headers=self.headers)
            self.assertEqual(status.status_code,200)
            self.assertFalse(status.json()['providers']['google']['configured'])
            result=self.client.post('/api/cloud/google/authorize',headers=self.headers)
            self.assertEqual(result.status_code,503)
    def test_google_oauth_state_encrypted_and_disconnect(self):
        with patch.dict(os.environ,{'GOOGLE_CLIENT_ID':'test-client','GOOGLE_CLIENT_SECRET':'test-secret'}):
            result=self.client.post('/api/cloud/google/authorize',headers=self.headers)
            self.assertEqual(result.status_code,200)
            u=urlparse(result.json()['authorization_url']);params=parse_qs(u.query)
            self.assertEqual(params['client_id'],['test-client'])
            self.assertIn('code_challenge',params)
            state=params['state'][0]
            self.assertEqual(self.client.get('/api/cloud/callback/google',params={'state':'bad','code':'ok'}).status_code,400)
            request=httpx.Request('POST','https://oauth2.googleapis.com/token')
            response=httpx.Response(200,request=request,json={'access_token':'secret-access-token','refresh_token':'secret-refresh-token','expires_in':3600})
            with patch('app.cloud.httpx.post',return_value=response):
                cb=self.client.get('/api/cloud/callback/google',params={'state':state,'code':'test-code'},follow_redirects=False)
            self.assertEqual(cb.status_code,303)
            self.assertEqual(cb.headers['location'],'/#workspace')
            conn=ws.db()
            try:
                cipher=conn.execute('SELECT token_cipher FROM cloud_tokens').fetchone()['token_cipher']
            finally:conn.close()
            self.assertNotIn('secret-access-token',cipher)
            self.assertTrue(self.client.get('/api/cloud',headers=self.headers).json()['providers']['google']['connected'])
            self.assertEqual(self.client.get('/api/cloud/callback/google',params={'state':state,'code':'test-code'}).status_code,400)
            self.assertEqual(self.client.delete('/api/cloud/google',headers=self.headers).status_code,200)
            self.assertFalse(self.client.get('/api/cloud',headers=self.headers).json()['providers']['google']['connected'])

if __name__=='__main__':unittest.main()
