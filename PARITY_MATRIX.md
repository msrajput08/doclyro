# Doclyro v6 additions (22 October 2026)

All v5 limitations below still apply.

| v6 capability | Honest outcome |
|---|---|
| Remove metadata | Clears PDF standard metadata, optional XMP and embedded attachments; **not** forensic sanitization or hidden-content redaction. |
| Grayscale | Rasterizes PDF pages in monochrome; searchable text, links and interactive fields are not retained. |
| Render Free hosting | Guest-only preview profile with 10 MB/file, 20 MB/job, limited concurrent processing; not permanent storage or high-volume production. |
| Security/operational work | Free-host vault/cloud/signing endpoints disabled; concurrency and basic per-client request limits; resource constraints remain significant. |

**38 tool slugs is not 100% parity with any commercial platform.**

---

# PDFCraft Studio v5 baseline — feature/parity matrix (20 October 2026)

| Feature family | Implemented source behavior | Full commercial parity? |
|---|---|---|
| Basic manipulation | Merge, split, reorder, remove/extract, rotate, compress, repair, crop, pages/numbers/watermarks | Most local flows implemented, complex cases vary |
| Visual editor | Text, images, shapes, links, freehand strokes, redaction region, form fields | No pixel-perfect commercial editor/advanced typesetting guarantee |
| Office conversions | Word, PowerPoint, Excel ⇄ PDF with LibreOffice and extraction heuristics | Complex editable round-trip layout fidelity not guaranteed |
| Scanning/OCR | Tesseract searchable layers, camera capture, perspective fix, image output | Handwriting and multilingual corpus quality not established |
| PDF/A | Ghostscript PDF/A conversion, including authorized protected input | Formal ISO compliance validator not yet integrated/verified |
| Comparison | Difference-report download **plus new interactive overlay, side-by-side and marked changes UI** | Rendering-based; no semantic equivalence guarantee |
| PDF forms | Text, multiline, checkbox, radio, dropdown/list, fill/flatten | Complex XFA/Javascript and advanced field appearance vary |
| Visual eSign | Visible signatures and link-based remote consent | No independent legal identity/qualified signing |
| **Cryptographic digital signatures (new)** | Sign detached CMS with supplied P12/PFX, SHA256; verify CMS bytes and unsigned appended changes; basic host-system CA-chain check | Full trust-list/revocation validation and regulated QES still unavailable |
| AI summarization | Local extractive + configurable generative service, optional self-hosted Ollama compose | Accuracy and external/locally downloaded model quality not verified |
| PDF translation | Configurable LibreTranslate, optional local compose service, best-effort overlay/reflow | No guaranteed multilingual/font/layout matching |
| Google/Dropbox | OAuth API code, credential encryption, user scopes, import/export | Real provider registration, consent approval and live verification needed |
| Private vault/accounts | Login/session isolation, vault, optional SMTP recovery | MFA/email verification, audited enterprise controls and compliance outstanding |
| Public operations | Docker, non-root execution, security headers, size caps | Production hardening, scale, abuse controls and final E2E are pending |

**36 v5 local/UI operations** is a tool count, **not** a percent-complete claim. Existing v4 parity matrix provided the per-tool original baseline. This update adds P12 signing/verification and browser comparison capability. Proprietary service/infrastructure differences cannot be erased by counting tools or unit tests. **100% not achieved.**
