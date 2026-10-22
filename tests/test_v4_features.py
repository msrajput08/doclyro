"""Real PDF structure, image pipeline and auth recovery regression tests for v4."""
from __future__ import annotations
import io
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fitz
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient
from pypdf import PdfReader

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.processor import process, ProcessingError, perspective_scan
from app.main import app
from app import workspace


class FormCropScanTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.wd=Path(self.temp.name)
        with fitz.open() as d:
            d.new_page(width=600,height=800)
            d.new_page(width=300,height=400)
            self.pdf=self.wd/'original.pdf'
            d.save(self.pdf)
    def tearDown(self):self.temp.cleanup()

    def test_true_radio_group_with_existing_text_field_and_fill(self):
        result=process('forms',[self.pdf],{'mode':'bulk','elements':[
            {'type':'field-text','page':1,'name':'Person','x':70,'y':60,'w':150,'h':28},
            {'type':'field-radio-group','page':1,'name':'Choice','x':70,'y':150,'choices':'Yes,No,Maybe','value':'Maybe'},
        ]},self.wd)
        with fitz.open(result) as pdf:
            fields=list(pdf[0].widgets())
            radios=[w for w in fields if w.field_type_string=='RadioButton']
            self.assertEqual(len(radios),3)
            self.assertEqual({w.field_name for w in radios},{'Choice'})
            self.assertEqual([w.field_value for w in radios],['Off','Off','Maybe'])
            self.assertTrue(any(w.field_name=='Person' for w in fields))
        self.assertIn('Choice',PdfReader(result).get_fields())
        sub=self.wd/'fill';sub.mkdir()
        filled=process('forms',[result],{'mode':'fill-all','values':{'Choice':'Yes','Person':'Amy'}},sub)
        with fitz.open(filled) as pdf:
            w=list(pdf[0].widgets())
            self.assertEqual(next(x.field_value for x in w if x.field_name=='Person'),'Amy')
            self.assertEqual([x.field_value for x in w if x.field_type_string=='RadioButton'],['Yes','Off','Off'])

    def test_radio_group_invalid_choice(self):
        with self.assertRaises(ProcessingError):
            process('forms',[self.pdf],{'mode':'create','field':'Vote','field_type':'field-radio-group',
                'choices':'Red,Blue','value':'Green'},self.wd)

    def test_visual_crop_page_or_all(self):
        out=process('crop',[self.pdf],{'crop_rect':{'page':1,'x':60,'y':80,'w':480,'h':640},'apply':'page'},self.wd)
        with fitz.open(out) as d:
            self.assertEqual(tuple(round(x) for x in d[0].rect), (0,0,480,640))
            self.assertEqual(tuple(round(x) for x in d[1].rect), (0,0,300,400))
        sub=self.wd/'all';sub.mkdir()
        out=process('crop',[self.pdf],{'crop_rect':{'page':1,'x':60,'y':80,'w':480,'h':640},'apply':'all'},sub)
        with fitz.open(out) as d:self.assertEqual(tuple(round(x) for x in d[1].rect),(0,0,240,320))

    def test_visual_crop_invalid(self):
        with self.assertRaises(ProcessingError):
            process('crop',[self.pdf],{'crop_rect':{'page':1,'x':590,'y':80,'w':500,'h':600}},self.wd)

    def test_scan_perspective_detection_and_fallback(self):
        photo=Image.new('RGB',(400,500),'#282828');brush=ImageDraw.Draw(photo)
        brush.polygon([(55,40),(350,70),(345,454),(40,442)],fill='white')
        scanned,changed=perspective_scan(photo)
        self.assertTrue(changed)
        self.assertNotEqual(scanned.size,photo.size)
        blank=Image.new('RGB',(400,500),'white')
        _,changed=perspective_scan(blank)
        self.assertFalse(changed)
        filename=self.wd/'image.png';photo.save(filename)
        sub=self.wd/'scan';sub.mkdir()
        output=process('scan',[filename],{'perspective':'auto','enhance':'true'},sub)
        with fitz.open(output) as pdf:
            self.assertEqual(len(pdf),1)
            self.assertGreater(len(pdf[0].get_images()),0)

    def test_multi_pdf_visual_page_organization(self):
        second=self.wd/'second.pdf'
        with fitz.open() as doc:
            doc.new_page(width=455,height=700).insert_text((45,70),'Second document')
            doc.save(second)
        out=process('organize',[self.pdf,second],{'page_sequence':[
            {'file':1,'page':1,'rotate':90},
            {'file':0,'page':2,'rotate':0},
            {'file':1,'page':1,'rotate':180},
        ]},self.wd)
        with fitz.open(out) as pdf:
            self.assertEqual(len(pdf),3)
            self.assertIn('Second document',pdf[0].get_text())
            self.assertEqual(pdf[0].rotation,90)
            self.assertEqual(pdf[1].rotation,0)
            self.assertEqual(pdf[2].rotation,180)

    def test_visual_organizer_rejects_invalid_page(self):
        with self.assertRaises(ProcessingError):
            process('organize',[self.pdf],{'page_sequence':[{'file':0,'page':99}]},self.wd)


class AccountRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.previous=workspace.DATA
        workspace.DATA=Path(self.temp.name)
        self.client=TestClient(app)
        self.email='alice@example.com'
        self.password='long-secret-passphrase'
        response=self.client.post('/api/auth/register',json={'email':self.email,'password':self.password})
        self.assertEqual(response.status_code,200,response.text)
        self.token=response.json()['token']

    def tearDown(self):
        self.client.close();workspace.DATA=self.previous;self.temp.cleanup()

    def test_reset_mail_one_use_revokes_sessions(self):
        sent=[]
        with patch.dict(os.environ,{'SMTP_HOST':'smtp.example.com','SMTP_FROM':'noreply@example.com',
                                    'PDFCRAFT_PUBLIC_URL':'https://pdf.example.com'}):
            with patch.object(workspace,'send_email',side_effect=lambda *args:sent.append(args)):
                resp=self.client.post('/api/auth/request-reset',json={'email':self.email})
                self.assertEqual(resp.status_code,200,resp.text)
                missing=self.client.post('/api/auth/request-reset',json={'email':'nobody@example.com'})
                self.assertEqual(missing.status_code,200)
        self.assertEqual(len(sent),1)
        self.assertIn('https://pdf.example.com/#reset/',sent[0][2])
        token=re.search(r'#reset/([A-Za-z0-9_-]+)',sent[0][2]).group(1)
        new_password='entirely-new-password'
        done=self.client.post('/api/auth/reset-password',json={'token':token,'password':new_password})
        self.assertEqual(done.status_code,200,done.text)
        self.assertEqual(self.client.get('/api/auth/me',headers={'Authorization':'Bearer '+self.token}).status_code,401)
        self.assertEqual(self.client.post('/api/auth/login',json={'email':self.email,'password':self.password}).status_code,401)
        self.assertEqual(self.client.post('/api/auth/login',json={'email':self.email,'password':new_password}).status_code,200)
        self.assertEqual(self.client.post('/api/auth/reset-password',json={'token':token,'password':new_password}).status_code,422)

    def test_smtp_not_configured_explicit_failure(self):
        with patch.dict(os.environ,{'SMTP_HOST':'','SMTP_FROM':''}):
            r=self.client.post('/api/auth/request-reset',json={'email':self.email})
            self.assertEqual(r.status_code,503)
            self.assertIn('SMTP',r.json()['detail'])


if __name__=='__main__':unittest.main()

class SafeURLTests(unittest.TestCase):
    def test_url_feature_opt_in(self):
        import os
        from app.processor import fetch_public_html
        with tempfile.TemporaryDirectory() as wd:
            with patch.dict(os.environ,{'PDFCRAFT_ALLOW_REMOTE_URLS':'false'}):
                with self.assertRaises(ProcessingError):
                    fetch_public_html('https://example.com/',Path(wd))

    def test_blocks_private_or_unsafe_urls(self):
        from app.processor import fetch_public_html
        with tempfile.TemporaryDirectory() as wd:
            with patch.dict(os.environ,{'PDFCRAFT_ALLOW_REMOTE_URLS':'true'}):
                with self.assertRaises(ProcessingError):
                    fetch_public_html('http://example.com/',Path(wd))
                with self.assertRaises(ProcessingError):
                    fetch_public_html('https://localhost/',Path(wd))
                with patch('socket.getaddrinfo',return_value=[(0,0,0,'',('127.0.0.1',443))]):
                    with self.assertRaises(ProcessingError):
                        fetch_public_html('https://example.com/',Path(wd))

    def test_url_fetch_pins_public_ip_and_generates_pdf(self):
        from app.processor import fetch_public_html,op_html_to_pdf
        with tempfile.TemporaryDirectory() as wd:
            root=Path(wd)
            def curl_fake(args,timeout=40):
                self.assertIn('--noproxy',args)
                self.assertIn('--resolve',args)
                self.assertIn('example.com:443:93.184.215.14',args)
                root.joinpath('remote.html').write_text('<h1>Secure URL PDF</h1><p>Sample HTML</p>')
            with patch.dict(os.environ,{'PDFCRAFT_ALLOW_REMOTE_URLS':'true'}),\
                 patch('socket.getaddrinfo',return_value=[(0,0,0,'',('93.184.215.14',443))]),\
                 patch('app.processor.cli',side_effect=curl_fake):
                txt=fetch_public_html('https://example.com/',root)
                self.assertIn('Secure URL PDF',txt)
                result=op_html_to_pdf([],{ 'url':'https://example.com/'},root)
                with fitz.open(result) as pdf:self.assertIn('Secure URL PDF',pdf[0].get_text())

class EmbeddedImagesTests(unittest.TestCase):
    def test_original_embedded_images_extraction(self):
        import zipfile
        with tempfile.TemporaryDirectory() as temp:
            wd=Path(temp)
            img=Image.new('RGB',(60,80),'blue');buf=io.BytesIO();img.save(buf,format='JPEG')
            with fitz.open() as pdf:
                page=pdf.new_page()
                page.insert_image(fitz.Rect(20,20,120,150),stream=buf.getvalue())
                filename=wd/'doc.pdf';pdf.save(filename)
            out=process('pdf-to-jpg',[filename],{'mode':'images'},wd)
            self.assertEqual(out.suffix,'.zip')
            with zipfile.ZipFile(out) as z:
                self.assertEqual(len(z.namelist()),1)
                name=z.namelist()[0]
                self.assertEqual(Image.open(io.BytesIO(z.read(name))).size,(60,80))

class RedactionPrivacyTests(unittest.TestCase):
    def test_redaction_scrubs_meta_and_attached_original(self):
        with tempfile.TemporaryDirectory() as t:
            wd=Path(t);f=wd/'secret.pdf'
            with fitz.open() as d:
                page=d.new_page()
                page.insert_text((50,80),'Secret token: TOPSECRET')
                d.set_metadata({'title':'TOPSECRET metadata'})
                d.embfile_add('original.txt',b'TOPSECRET in attachment',filename='original.txt')
                page.add_text_annot((50,120),'TOPSECRET comment')
                d.save(f)
            out=process('redact',[f],{'text':'TOPSECRET'},wd)
            with fitz.open(out) as d:
                self.assertNotIn('TOPSECRET',d[0].get_text())
                self.assertEqual(d.embfile_count(),0)
                self.assertNotIn('TOPSECRET',str(d.metadata))
                self.assertFalse(list(d[0].annots() or []))
