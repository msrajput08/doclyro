# Doclyro v6 — development build (not production release)

This source is the continued work on the PDFCraft Studio project, renamed **Doclyro**. The original v5 engine is retained; v6 introduces 2 additional tools (38 operation slugs total), Render Free preview configuration and safer handling of ephemeral file storage. See `RELEASE_STATUS.md` and `RENDER_FREE.md` first.

**Current state:** Not yet 100% feature complete or fully tested. Do not advertise full commercial iLovePDF parity, guarantee legal signature identity, or assume every large Office/OCR conversion runs on free hosting.

**Never use Render Free to store permanent user accounts, document vault contents or remote signature requests.** The included `render.yaml` enforces `PDFCRAFT_EPHEMERAL_MODE=true` for preview mode and hides those features; full self-hosted features exist in source for environments with genuinely durable storage.

Detailed v5 implementation documentation follows.

---

# PDFCraft Studio v5 — self-hosted PDF toolkit

**Current status: Expanded working source project. NOT 100% iLovePDF commercial/service-level parity.**

This is an independently authored app, not a copy of a competitor's proprietary source, logo, or brand. Existing v4 functionality is retained; v5 adds meaningful capabilities without replacing the project. Full end-to-end testing is explicitly **deferred until the feature-complete final build**, at the owner's request.

## Launch (Windows, Mac, Linux)

1. Install Docker Desktop (Windows/Mac) or Docker Engine + Compose (Linux).
2. Extract ZIP. Open a terminal in the extracted project directory.
3. Start: `docker compose up --build` (or double-click `START_WINDOWS.bat` on Windows).
4. Visit `http://localhost:8000`.

Ordinary PDF tools work without accounts or cloud providers. The self-hosted API docs are at `/docs`.

## New in v5

- **Actual detached CMS certificate-based PDF signing** using a signer-supplied PKCS#12 `.p12` or `.pfx` and its password. Select **Digital Certificate Sign**, upload PDF first and P12/PFX second. Output is a PDF with a genuine cryptographic CMS signature (SHA-256). Rejects adding signatures to already signed PDFs rather than accidentally invalidating them. Existing **Sign PDF** remains a separate visible handwritten-style annotation. **This is not a qualified e-signature or a verification of the signer's identity.**
- **Verify Digital Signatures** checks CMS byte integrity using OpenSSL, detects files with appended unsigned material, returns a downloadable PDF report, and exposes JSON inspection through `POST /api/signature-inspect`. **A basic chain check against the host system CA store is attempted; revocation, accredited trust lists, identity and legal status are NOT evaluated.** You must bring a valid signing certificate; no legitimate system can issue one on your behalf without verification.
- **Interactive PDF comparison** now includes side-by-side page viewing, page navigation, a revised-page opacity overlay slider, changed-pixel highlighting, and a visual/text change indicator. Downloadable comparison report remains available. Local preview endpoint: `POST /api/compare-preview`. Visual differences are approximate rendered pixel measurements, not a semantic or legal equivalence determination.
- **Authenticated protected-PDF to PDF/A conversion** now decrypts into the temporary job directory only with a correct password before invoking Ghostscript. Formal ISO PDF/A conformance needs independent veraPDF/other certified validator; Ghostscript export is not itself a certificate of compliance.
- **Optional local models**: `docker-compose.local-ai.yml` connects open source Ollama (OpenAI-compatible generative summarization) and LibreTranslate (best-effort PDF translation). This is an *optional*, resource-intensive, independently hosted setup; model download, multilingual quality, fonts and correct translations are not guaranteed. No third-party API key is needed for the supported local-model path.
- **Static readiness diagnostics**: `python scripts/readiness.py` prints missing deployment tools and credentials without leaking secrets or running end-to-end tests.

## All previous tools retained

36 tool operations in the UI and backend: Merge, Split, Compress, Remove Pages, Extract Pages, Organize, Scan, Repair, OCR, JPG→PDF, Word→PDF, PowerPoint→PDF, Excel→PDF, HTML→PDF, PDF→JPG, PDF→Word, PDF→PowerPoint, PDF→Excel, PDF→PDF/A, Rotate, Page Numbers, Watermark, Crop, Edit, Forms, Workflows, Unlock, Protect, Sign PDF (visible), **Digital Certificate Sign**, **Verify Digital Signatures**, Redact, Compare, Summarize, Translate and PDF→Markdown.

Available workflows include multi-PDF visual page ordering, visual redaction, form radio groups and checkboxes, image extraction, camera-scan perspective correction, optional password recovery, private user vault, consent-based signing links and conditional Drive/Dropbox OAuth. Not all operations have commercial-grade output fidelity; refer to `PARITY_MATRIX.md`.

## Optional local generative AI & translation

```bash
# Start app plus local Ollama and LibreTranslate containers
# Requires internet for container images and language/model downloads.
docker compose -f docker-compose.yml -f docker-compose.local-ai.yml up -d --build

# Pull the selected open-weight summarization model (model download may be large)
docker compose -f docker-compose.yml -f docker-compose.local-ai.yml exec ollama ollama pull qwen2.5:3b-instruct
```

Services are private on the Compose network; neither Ollama nor translation service exposes an external host port. Model accuracy and language support vary. On limited-memory machines, use a hosted AI/translation provider instead. For existing remote providers, set `AI_API_KEY`, `AI_MODEL`, optional `AI_API_BASE_URL`, and `LIBRETRANSLATE_URL` as appropriate. PDF text sent to external services leaves the server.

## Remote integrations — owner action eventually required

To complete real Google Drive/Dropbox access, the operator must register provider OAuth clients, supply client IDs/secrets as environment variables, approve the requested scopes, and register canonical production HTTPS callback URLs. SMTP delivery needs verified sender credentials. Production requires a domain, HTTPS, trusted storage/backup, privacy policy, abuse prevention and security review.

**For qualified/certified digital signing:** The new local CMS implementation signs using a certificate already belonging to the signer; it does not issue a trusted certificate or assert PKI trust. A separate identity-verified, licensed signing/trust service and legal review may be necessary for specific countries/use cases.

## Technical notes

- Upload processing is temporary; content is removed after the response. User-saved vault documents persist until deleted.
- Never send private PKCS#12 files or passphrases to public deployments that you do not trust or control. Keys are only used transiently in the processing job and are not saved in the vault by certificate-signing itself.
- The backend uses FastAPI + PyMuPDF/pypdf + Pillow/OpenCV + LibreOffice + Ghostscript + Tesseract + cryptography/OpenSSL. OpenSSL is explicitly installed in the Docker image.
- Existing accounts, vault and signing-request API remain as in v4. No automatic migration or destructive reset of user data is included.
- Full browser upload→processing→download, infrastructure load, public HTTPS and provider-approved consent testing are postponed until the full feature build, per user direction. This deliverable contains *focused module-level regression tests and JS syntax checks*, not final E2E certification.

### Run focused v5 module tests (not E2E)

```bash
python -m unittest discover -s tests -p 'test_v5_units.py' -q
for f in static/*.js; do node --check "$f"; done
python scripts/readiness.py
```

Existing v4 unit/API smoke scripts remain available for **final test phase**, but the full suite is deliberately not claimed as rerun on v5 yet.

See `HANDOFF_REQUIREMENTS.md`, `SECURITY.md`, `PARITY_MATRIX.md`, and `QA_REPORT.md` for implementation status and setup.
