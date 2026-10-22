import os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import fitz,httpx
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.processor import process,ProcessingError
class TranslationTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.wd=Path(self.tmp.name)
  self.file=self.wd/'original.pdf'
  with fitz.open() as doc:
   p=doc.new_page();p.insert_text((72,80),'Original text',fontsize=12)
   p.draw_rect(fitz.Rect(20,20,40,40),fill=(0,0,1))
   doc.save(str(self.file))
 def tearDown(self):self.tmp.cleanup()
 def test_translation_not_faked_when_not_configured(self):
  with patch.dict(os.environ,{'LIBRETRANSLATE_URL':''}):
   with self.assertRaises(ProcessingError):process('translate',[self.file],{},self.wd)
 def test_layout_translation_overwrites_searchable_original_and_preserves_graphic(self):
  request=httpx.Request('POST','https://fake-translator.example/translate')
  mock=httpx.Response(200,request=request,json={'translatedText':'Texto nuevo'})
  with patch.dict(os.environ,{'LIBRETRANSLATE_URL':'https://fake-translator.example/translate'}),patch('httpx.post',return_value=mock):
   result=process('translate',[self.file],{'mode':'layout','language':'es'},self.wd)
  with fitz.open(result) as doc:
   text='\n'.join(p.get_text() for p in doc)
   self.assertNotIn('Original text',text)
   self.assertIn('Texto nuevo',text)
   self.assertGreater(len(doc[0].get_drawings()),0)
if __name__=='__main__':unittest.main()
