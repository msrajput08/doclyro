"""Regression tests for genuine advanced PDF content and document workflows."""
import base64
import io
import sys
import tempfile
import unittest
from pathlib import Path
import fitz
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.processor import process, ProcessingError
from app.advanced import detect_labeled_fields
from fastapi.testclient import TestClient
from app.main import app


class AdvancedTools(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.wd=Path(self.tmp.name)
        self.pdf=self.wd/'input.pdf'
        with fitz.open() as d:
            p=d.new_page();p.insert_text((50,80),'Name:                 hello SECRET 12345')
            d.new_page().insert_text((50,80),'Second page')
            d.save(str(self.pdf))

    def tearDown(self):self.tmp.cleanup()
    def go(self,slug,opts):return process(slug,[self.pdf],opts,self.wd)
    def image_data(self):
        img=Image.new('RGBA',(120,50),(0,0,0,0))
        for x in range(20,90):img.putpixel((x,25),(20,45,90,255))
        b=io.BytesIO();img.save(b,format='PNG')
        return 'data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()

    def test_editor_vector_shapes_and_freehand(self):
        o=self.go('edit',{'elements':[
            {'type':'text','page':1,'x':35,'y':120,'w':250,'h':80,'text':'Hello edited page','font_size':13},
            {'type':'rectangle','page':1,'x':30,'y':170,'w':120,'h':30},
            {'type':'ellipse','page':1,'x':160,'y':170,'w':100,'h':40},
            {'type':'highlight','page':1,'x':30,'y':210,'w':200,'h':25,'color':'#fff000'},
            {'type':'line','page':1,'x':30,'y':250,'x2':210,'y2':300},
            {'type':'freehand','page':2,'points':[[40,140],[45,145],[55,155],[70,160]]},
        ]})
        with fitz.open(o) as d:
            self.assertEqual(len(d),2)
            self.assertIn('Hello edited page',d[0].get_text())
            self.assertGreater(len(d[0].get_drawings()),2)
            self.assertGreater(len(d[1].get_drawings()),0)

    def test_editor_image_and_replacement(self):
        o=self.go('edit',{'elements':[
            {'type':'replace-text','page':1,'search':'hello','text':'changed','font_size':11},
            {'type':'image','page':1,'x':220,'y':100,'w':120,'h':60,'data':self.image_data()},
        ]})
        with fitz.open(o) as d:
            self.assertNotIn('hello',d[0].get_text())
            self.assertIn('changed',d[0].get_text())
            self.assertGreater(len(d[0].get_images()),0)

    def test_rectangle_redaction_actually_removes_text(self):
        o=self.go('redact',{'elements':[{'type':'redact','page':1,'x':175,'y':60,'w':280,'h':35}]})
        with fitz.open(o) as d:
            self.assertNotIn('SECRET',d[0].get_text())
            self.assertNotIn('12345',d[0].get_text())

    def test_form_bulk_field_types_and_fill(self):
        o=self.go('forms',{'mode':'bulk','elements':[
            {'type':'field-text','page':1,'name':'Person','x':70,'y':150,'w':130,'h':28},
            {'type':'field-multiline','page':1,'name':'Comments','x':70,'y':190,'w':180,'h':60},
            {'type':'field-checkbox','page':1,'name':'Agree','x':70,'y':270,'w':25,'h':25},
            {'type':'field-dropdown','page':1,'name':'Size','x':70,'y':310,'w':150,'h':28,'choices':'S,M,L'},
        ]})
        with fitz.open(o) as d:
            fs={f.field_name:f for f in d[0].widgets()}
            self.assertEqual(set(fs),{'Person','Comments','Agree','Size'})
            self.assertEqual(fs['Size'].choice_values,['S','M','L'])
        next_dir=self.wd/'filled';next_dir.mkdir();filled=process('forms',[o],{'mode':'fill-all','values':{'Person':'Testing'}},next_dir)
        with fitz.open(filled) as d:
            self.assertEqual(next(w.field_value for w in d[0].widgets() if w.field_name=='Person'),'Testing')

    def test_auto_fields(self):
        with fitz.open(self.pdf) as d:
            suggestions=detect_labeled_fields(d)
        self.assertTrue(suggestions)
        o=self.go('forms',{'mode':'detect'})
        with fitz.open(o) as d:self.assertGreaterEqual(len(list(d[0].widgets())),1)

    def test_drawn_signature(self):
        o=self.go('sign',{'signature_image':self.image_data(),'x':70,'y':200,'width':180,'height':70})
        with fitz.open(o) as d:self.assertGreater(len(d[0].get_images()),0)

    def test_workflow_chains_real_operations(self):
        o=self.go('workflow',{'steps':[
            {'tool':'rotate','options':{'angle':90}},
            {'tool':'watermark','options':{'text':'TESTING','opacity':1}},
            {'tool':'page-numbers','options':{'start':3}}
        ]})
        with fitz.open(o) as d:
            self.assertEqual(d[0].rotation,90)
            self.assertIn('TESTING',d[0].get_text())
            self.assertEqual(len(d),2)

    def test_workflow_rejects_unsupported(self):
        with self.assertRaises(ProcessingError):self.go('workflow',{'steps':[{'tool':'html-to-pdf','options':{}}]})

    def test_image_watermark(self):
        o=self.go('watermark',{'image_data':self.image_data(),'image_width':130,'opacity':0.4})
        with fitz.open(o) as d:
            self.assertGreater(len(d[0].get_images()),0)
            self.assertGreater(len(d[1].get_images()),0)

    def test_compare_text_mode(self):
        other=self.wd/'modified.pdf'
        with fitz.open() as d:
            d.new_page().insert_text((40,80),'New PDF revision')
            d.save(str(other))
        result=process('compare',[self.pdf,other],{'mode':'text'},self.wd)
        with fitz.open(result) as d:
            text=''.join(p.get_text() for p in d)
            self.assertIn('PDF Text Comparison Report',text)
            self.assertIn('New PDF revision',text)

    def test_invalid_image_data_rejected(self):
        with self.assertRaises(ProcessingError):self.go('edit',{'elements':[{'type':'image','page':1,'x':20,'y':20,'w':40,'h':40,'data':'javascript:bad'}]})

    def test_api_field_detection(self):
        client=TestClient(app)
        with self.pdf.open('rb') as f: r=client.post('/api/suggest-fields',files={'file':('document.pdf',f,'application/pdf')})
        self.assertEqual(r.status_code,200,r.text)
        self.assertGreaterEqual(len(r.json()['suggestions']),1)
        with self.pdf.open('rb') as f:r=client.post('/api/inspect',files={'file':('document.pdf',f,'application/pdf')})
        self.assertEqual(len(r.json()['page_sizes']),2)
        client.close()
