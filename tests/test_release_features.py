"""Focused checks for final consolidated tools and HTTP download flow."""
import io
import zipfile
import fitz
from fastapi.testclient import TestClient
from app.main import app


def pdf():
    d=fitz.open()
    d.new_page().insert_text((50, 70), 'First page extracted text')
    d.new_page().insert_text((50, 70), 'Second page extracted text')
    out=d.tobytes();d.close()
    return out


def post(slug, opts=None):
    import json
    with TestClient(app) as client:
        return client.post('/api/process/'+slug,files={'files':('demo.pdf',pdf(),'application/pdf')},data={'options':json.dumps(opts or {})})


def test_text_export_selected():
    r=post('pdf-to-text',{'pages':'2'})
    assert r.status_code==200, r.text
    assert 'Second page extracted text' in r.text
    assert 'First page extracted text' not in r.text


def test_png_export_zip():
    r=post('pdf-to-png',{'dpi':80})
    assert r.status_code==200,r.text
    z=zipfile.ZipFile(io.BytesIO(r.content))
    assert z.namelist()==['page_0001.png','page_0002.png']
    assert z.read('page_0001.png').startswith(b'\x89PNG')


def test_blank_pages():
    r=post('insert-blank-pages',{'position':'after','after_page':1,'count':2})
    assert r.status_code==200,r.text
    with fitz.open(stream=r.content,filetype='pdf') as d:
        assert len(d)==4
        assert 'First page' in d[0].get_text()
        assert not d[1].get_text().strip()
        assert not d[2].get_text().strip()
        assert 'Second page' in d[3].get_text()


def test_flatten():
    r=post('flatten-pdf')
    assert r.status_code==200,r.text
    with fitz.open(stream=r.content,filetype='pdf') as d:assert len(d)==2


def test_invalid_pages_errors():
    r=post('pdf-to-png',{'pages':'100'})
    assert r.status_code==422


def test_frontend_backend_tool_count_match():
    from pathlib import Path
    import re
    s=(Path(__file__).parent.parent/'static'/'app.js').read_text()
    from app.processor import OPS
    names=re.findall(r"^\['([a-z-]+)',",s,re.M)
    assert len(names)==len(OPS)==42
    assert set(names)==set(OPS)
