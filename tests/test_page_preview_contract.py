from pathlib import Path


STATIC=Path(__file__).resolve().parents[1]/"static"

def test_page_preview_script_and_ui_are_linked():
    page=(STATIC/"index.html").read_text()
    assert 'id="pagePreview"' in page
    assert '/page-preview.js' in page
    assert 'id="organizerBuilder"' in page

def test_page_selection_is_applied_to_backend_options():
    js=(STATIC/"app.js").read_text()
    viewer=(STATIC/"page-preview.js").read_text()
    assert 'DoclyroPagePreview?.onFiles' in js
    assert 'DoclyroPagePreview?.options' in js
    assert "'remove-pages', 'extract-pages', 'rotate'" in viewer
    assert 'You must keep at least one page' in viewer

def test_organizer_uses_local_pdfjs_renderer():
    js=(STATIC/"organizer-ui.js").read_text()
    assert 'window.DoclyroPDF.load(file)' in js
    assert 'IntersectionObserver' in js
    assert 'page_sequence:' in js

def test_pdfjs_worker_matches_browser_script():
    root=STATIC.parent
    docker=(root/'Dockerfile').read_text()
    js=(STATIC/'page-preview.js').read_text()
    assert 'pdf.js/3.11.174/pdf.min.js' in docker
    assert 'pdf.js/3.11.174/pdf.worker.min.js' in docker
    assert "'/vendor/pdf.min.js'" in js
    assert "'/vendor/pdf.worker.min.js'" in js
