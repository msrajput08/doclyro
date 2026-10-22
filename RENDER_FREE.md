# Doclyro v6 — Render Free deployment profile (source only)

This is a **guest-only preview profile**, not a claim of production hosting or iLovePDF parity.

## Why this mode exists
Render Free provides ~512 MB RAM and 0.1 CPU, sleeps after 15 minutes idle, and loses local filesystem data when restarting or sleeping. Therefore this project sets `PDFCRAFT_EPHEMERAL_MODE=true`, which omits user registration, saved PDFs, OAuth connections and remote signer workflows. Files temporarily uploaded for processing are removed after the response, and guest downloads must be stored by the user. It would be misleading or unsafe to allow people to store irreplaceable documents on ephemeral storage.

## Current work and remaining limits
- Single Docker-backed FastAPI web service, 1 worker, 1 concurrently accepted processing job per process, maximum 10 MB per file / 20 MB per upload batch.
- Rate controls are in-memory, single worker, best effort. They are not distributed WAF protection.
- Docker retains LibreOffice, Ghostscript, OCR etc. For real Render Free's 512 MB quota and weak CPU, complex LibreOffice conversions, OCR, PDF/A or large files can still OOM, timeout, or fail. **The full feature set is not guaranteed to run on Free hosting**.
- Remote model inference, unlimited translations, guaranteed cold-start speed, high concurrency, permanent vault or cloud-linked account features are NOT included at zero cost.
- TLS is managed by Render; `doclyro.onrender.com` is a proposed hostname and is not reserved until the service is created.

## Deploy when ready (after user-requested feature-complete development)
1. Create a private GitHub repository (source must be committed to Git; ZIP alone cannot deploy through Render's connected Git workflow).
2. Render Dashboard > New > Web Service > select repository > choose Docker > Free, or use `render.yaml` Blueprint. Make sure actual service name and URL are confirmed; do not replace existing SkillLens service.
3. Verify `PDFCRAFT_EPHEMERAL_MODE=true` and no paid plans/disks/databases are selected. Do not enter OAuth/SMTP secrets in source or enable persistent vault on this service.
4. After feature implementation complete, do final E2E, usability, security, load, memory and resource validation. Review logs for crashes. Use realistic representative PDF documents.
5. Upgrade hosting and provide durable datastore/object storage before offering accounts, remote signing, and long-term document storage; Render Free Postgres expires after 30 days and is not suitable as a permanent vault.

Sources: https://render.com/docs/free ; https://render.com/docs/blueprint-spec ; https://render.com/docs/web-services
