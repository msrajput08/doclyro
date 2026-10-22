import io
import sys
import unittest
from pathlib import Path
import fitz
from fastapi.testclient import TestClient
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app

class APISmoke(unittest.TestCase):
    def setUp(self):
        self.client=TestClient(app)
        d=fitz.open();d.new_page().insert_text((72,72),'PDFCraft API');self.pdf=d.tobytes();d.close()
    def tearDown(self):self.client.close()
    def test_homepage(self):
        self.assertEqual(self.client.get('/').status_code,200)
        self.assertIn('Doclyro',self.client.get('/').text)
        self.assertEqual(self.client.get('/app.js').status_code,200)
        self.assertEqual(self.client.get('/style.css').status_code,200)
    def test_tools(self):
        d=self.client.get('/api/tools').json();self.assertEqual(d['total'],42)
    def test_merge_download(self):
        r=self.client.post('/api/process/merge',files=[('files',('1.pdf',self.pdf,'application/pdf')),('files',('2.pdf',self.pdf,'application/pdf'))],data={'options':'{}'})
        self.assertEqual(r.status_code,200,r.text[:500]);self.assertIn('attachment',r.headers['content-disposition'])
        with fitz.open('pdf',r.content) as d:self.assertEqual(len(d),2)
    def test_preview(self):
        r=self.client.post('/api/thumbnail',files={'file':('1.pdf',self.pdf,'application/pdf')})
        self.assertEqual(r.status_code,200);self.assertEqual(r.headers['content-type'],'image/png')
    def test_invalid_tool(self):
        r=self.client.post('/api/process/nonexistent',data={'options':'{}'})
        self.assertEqual(r.status_code,404)

if __name__=='__main__':unittest.main()
