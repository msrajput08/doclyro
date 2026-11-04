# Third-party software and license inventory

Doclyro combines Python packages, operating-system packages, fonts, and browser-side libraries. This inventory is an audit starting point, not a claim that all dependencies share Doclyro's MIT license. Each component remains under its own license and notice requirements.

## Browser-side PDF rendering

- **PDF.js 3.11.174** — the Docker build downloads `pdf.min.js` and `pdf.worker.min.js` from cdnjs at image-build time. Mozilla PDF.js is distributed under Apache License 2.0. Preserve its license and required notices when distributing images or vendored copies. Verify the exact upstream release and include the corresponding license/notice in redistributed bundles.


## Important copyleft dependency: PyMuPDF

- **PyMuPDF** — the package metadata and Artifex licensing documentation identify the open-source route as GNU AGPL v3, with a separate commercial license option. This is a material licensing constraint: combining and distributing or operating the current application with the AGPL build may trigger AGPL obligations for the combined application, including source availability to network users under the AGPL's terms. The repository's existing MIT license does not override PyMuPDF's license.
- The project must choose one of these paths before claiming a clear, consistent project-wide license: (1) adopt AGPL-3.0 for the combined project after confirming all contributors' rights and preserving existing notices; (2) obtain an appropriate Artifex commercial license; or (3) replace PyMuPDF with a suitably licensed alternative and validate that all current PDF workflows remain equivalent.
- Do not merge or publish a blanket MIT licensing claim until this decision is resolved. See the official [PyMuPDF licensing page](https://pymupdf.io/licensing) and [PyMuPDF documentation](https://pymupdf.readthedocs.io/en/latest/about.html).

## Python runtime dependencies

The current `requirements.txt` declares FastAPI, Uvicorn, python-multipart, PyMuPDF, Pillow, python-docx, python-pptx, openpyxl, ReportLab, pdfplumber, WeasyPrint, pytesseract, httpx, pdf2docx, cryptography, pypdf, and opencv-python-headless. Transitive packages are also installed.

Do not assume a single license applies to this list. Verify license metadata and bundled notices for the exact resolved versions, including transitive packages. **PyMuPDF/Artifex licensing deserves particular attention** for the intended distribution and use model.

## Operating-system packages and fonts

The Docker image installs LibreOffice components, Ghostscript, Tesseract and language data, OpenSSL, Pango, GDK Pixbuf, fontconfig, DejaVu, Liberation, Carlito, Caladea, Noto fonts, and ICC profiles. Their licenses and attribution requirements are separate from Doclyro's license. Consult package metadata and upstream notices for the exact base-image distribution versions.

## Samples and project assets

- Review `samples/try_me.pdf` for authorship, redistribution permission, and personal or identifying metadata before using it in public demos.
- Review logos, icons, fonts, screenshots, and other assets for ownership and license compatibility.
- `static/google3d4d24a07fe849ba.html` appears to be a Google site-verification file. Confirm the repository owner intends to publish it and that it does not expose an unwanted site-verification capability.

## Maintainer checklist

- [ ] Confirm every source file is authored by the project owner or contributed under compatible terms.
- [ ] Confirm the existing MIT copyright holder wording accurately reflects all rights holders.
- [ ] Review every direct and transitive Python dependency license for selected versions.
- [ ] Preserve third-party license files and notices in source distributions and container images.
- [ ] Verify fonts, Tesseract language data, ICC profiles, and native package notices.
- [ ] Confirm sample PDF and verification-token file are appropriate for public distribution.
- [ ] Re-run this audit when dependencies or base images change.

If ownership or permission cannot be established, do not silently relicense the material as MIT. Replace it with a clearly licensed alternative or obtain permission first.
