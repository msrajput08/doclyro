# Doclyro consolidated test report

- `python -m pytest -q`: **81 passed, 5 subtests passed** (local environment).
- `python scripts/smoke_all_tools.py`: **41 passed, 0 failed, 1 skipped**. Translation skipped because no translation server was configured.
- Frontend `.js` scripts pass `node --check`.
- PDF output validity checked by smoke script (PyMuPDF opens generated PDFs).
- HTTP route integration covers binary downloads, PNG zip, text extraction, blank pages and flattening.
- Chromium navigation is blocked by this execution environment's administrator policy; no browser E2E pass is claimed.
- Real Render deployment, load, OAuth provider approval and independent security review not tested.
