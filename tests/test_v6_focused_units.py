"""Focused development units; intentionally no browser/HTTP E2E tests."""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import fitz
import pytest

from app.processor import OPS, ProcessingError, process


def sample_pdf(path):
    with fitz.open() as d:
        p=d.new_page(width=450,height=500)
        p.insert_text((60,60),'Hello Doclyro searchable')
        d.set_metadata({'title':'Personal title','author':'Personal author'})
        d.embfile_add('private-note.txt',b'Temporary attachment')
        d.save(str(path))


def test_tool_registry_has_two_new_operations():
    assert all(n in OPS for n in ('remove-metadata','grayscale'))
    assert len(OPS)==42


def test_metadata_cleanup_removes_properties_and_attachment(tmp_path):
    src=tmp_path/'in.pdf';sample_pdf(src)
    with fitz.open(str(src)) as original:
        assert original.metadata.get('title')=='Personal title'
        assert original.embfile_count()==1
    out=process('remove-metadata',[src],{},tmp_path)
    with fitz.open(str(out)) as result:
        assert result.embfile_count()==0
        assert result.metadata.get('title','')==''
        assert result.metadata.get('author','')==''
        assert 'Hello Doclyro' in result[0].get_text()


def test_grayscale_rasterizes_page_and_preserves_dimensions(tmp_path):
    src=tmp_path/'in.pdf';sample_pdf(src)
    out=process('grayscale',[src],{'dpi':100},tmp_path)
    with fitz.open(str(out)) as result:
        assert len(result)==1
        assert abs(result[0].rect.width-450)<0.01
        assert abs(result[0].rect.height-500)<0.01
        assert result[0].get_text().strip()==''
        assert len(result[0].get_images(full=True))==1


def test_grayscale_rejects_oversized_page(tmp_path):
    src=tmp_path/'in.pdf'
    with fitz.open() as d:
        d.new_page(width=8000,height=8000)
        d.save(str(src))
    with pytest.raises(ProcessingError,match='too large'):
        process('grayscale',[src],{'dpi':160},tmp_path)


def test_grayscale_only_accepts_pdfs(tmp_path):
    bad=tmp_path/'file.txt';bad.write_text('x')
    with pytest.raises(ProcessingError,match='PDF'):
        process('grayscale',[bad],{},tmp_path)


def test_ephemeral_routes_excluded_without_persistent_storage():
    script='''from app.main import app, capabilities
paths={getattr(r,'path','') for r in app.routes}
assert not capabilities()['persistent_accounts']
assert '/api/process/merge' not in paths
assert '/api/process/{slug}' in paths
assert '/api/auth/register' not in paths
assert '/api/vault' not in paths
assert '/api/cloud' not in paths
assert '/api/sign-requests' not in paths
assert '/api/capabilities' in paths
'''
    env={**os.environ,'PDFCRAFT_EPHEMERAL_MODE':'true'}
    result=subprocess.run([sys.executable,'-c',script],cwd=Path(__file__).parents[1],env=env, capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stderr


def test_persistent_mode_keeps_account_routes_in_self_hosted_build():
    script='''from app.main import app, capabilities
paths={getattr(r,'path','') for r in app.routes}
assert capabilities()['persistent_accounts']
assert '/api/auth/register' in paths
assert '/api/vault' in paths
assert '/api/cloud' in paths
'''
    env={**os.environ,'PDFCRAFT_EPHEMERAL_MODE':'false'}
    result=subprocess.run([sys.executable,'-c',script],cwd=Path(__file__).parents[1],env=env,capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stderr
