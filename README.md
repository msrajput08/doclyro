# Doclyro — PDF & Document Toolkit

Doclyro is an original responsive PDF web application with **42 registered document operations**, a FastAPI backend, and a browser frontend. Source is packaged as one project without iterative-version folders.

## Start on a PC

1. Install Docker Desktop (Windows/Mac) or Docker Engine with Compose (Linux).
2. Extract the ZIP and open a terminal in its `Doclyro` folder.
3. Execute `docker compose up --build`.
4. Open **http://localhost:8000**. File conversions run locally on the **server** (they are not in-browser PDF operations).

On Windows you can alternatively double-click `START_WINDOWS.bat` after starting Docker Desktop.

## Free online hosting configuration

A Render Free Docker Blueprint is provided in `render.yaml`; deploy this repository as a **new** Render service, separate from other applications. The free host uses **guest-only temporary processing**, not persistent account/vault storage. Once deployed, Render assigns an `.onrender.com` HTTPS address. Availability, build success and adequate memory on its 512 MB plan are not guaranteed; heavy LibreOffice/OCR/AI jobs can fail or be slow.

Do **not** point a publicly accessible free-service instance to persistent mode. Render Free filesystem is ephemeral. For persistent features, an external durable database/object store and its access controls are mandatory.

## Included operations

Merge, split, compress, remove/extract/reorder pages, scan, repair, OCR, JPG→PDF, Word/PowerPoint/Excel→PDF, HTML→PDF, PDF→JPG/PNG/Word/PowerPoint/Excel/Text/Markdown/PDF-A, rotate, page numbers, watermark, crop, edit, forms, workflow, unlock, protect, visible signing, P12/PFX certificate signing and integrity checks, redaction, comparison, summary, translation, metadata removal, grayscale, flatten, blank page insertion.

Summary works in local extractive mode without AI credentials. Translation requires a separately configured LibreTranslate-compatible endpoint. Certificate signing requires the user's own P12/PFX. Complex Office/PDF roundtrips vary; PDF/A output lacks formal compliance certification; remote signing is not legally qualified signing.

## Quality checks on the consolidated source

- 81 Python tests and 5 subtests passed.
- A local direct smoke script exercised 41/42 operations successfully; translation is conditional on an external service and was skipped.
- JavaScript syntax passed.
- Python HTTP integration tests covered conversion and downloadable results.
- A full real Render deployment, public browser flow, independent security penetration audit, and cross-browser/performance testing are not completed or certified.

See `FINAL_RELEASE_NOTES.md`, `SECURITY.md`, `RENDER_FREE.md`, `TECHNICAL_REFERENCE.md`, and `PARITY_MATRIX.md` for configuration and real constraints. The project is **not independently verified as 100% parity with iLovePDF**; source operation count is not a completeness percentage.
