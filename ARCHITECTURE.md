# Doclyro architecture

## Overview

Doclyro is a single-service application: a FastAPI backend serves the browser interface and exposes document-processing APIs. The browser frontend is plain HTML, CSS, and JavaScript; PDF page previews are rendered in the browser with PDF.js. Actual conversion and manipulation requests are uploaded to the FastAPI server and processed there.

## Main components

- `app/main.py`: FastAPI application, processing endpoints, upload limits, temporary job directories, response cleanup, health/capability endpoints, and ephemeral-mode route selection.
- `app/processor.py`: operation registry (`OPS`) and PDF/document processing functions.
- `app/advanced.py`: advanced PDF form and field helpers.
- `app/compare_views.py`: page comparison preview generation.
- `app/digital_signing.py`: CMS certificate signing and signature inspection helpers.
- `app/workspace.py`: optional self-hosted accounts, sessions, private PDF vault, and consent-based signing request storage.
- `app/cloud.py`: optional Google Drive and Dropbox OAuth integrations.
- `static/`: browser UI and client-side modules.
- `tests/`: Python regression, API, conversion, workspace, and focused feature tests.

## Request lifecycle

1. Browser selects files and options.
2. The frontend sends multipart requests to `POST /api/process/{slug}`.
3. FastAPI validates the operation, options size, file count, per-file size, and aggregate job size.
4. A bounded processing semaphore limits concurrent jobs.
5. Files are written to a unique temporary job directory and passed to the operation registry.
6. The result is streamed as a download; the temporary directory is removed by response background cleanup. Error paths also remove the temporary directory.
7. Health and capabilities endpoints describe the current server configuration.

This is server-side processing, not browser-only or local-only conversion. Do not upload confidential documents to a server you do not control.

## Persistent workspace vs guest mode

- Self-hosted persistent mode includes the workspace and cloud routers. SQLite metadata and vault documents are stored under `PDFCRAFT_DATA_DIR` (default `./data`).
- Guest/ephemeral mode excludes account, vault, cloud, and remote-signing routes. It is intended for disposable preview hosting where the filesystem may be reset.
- Do not enable persistent accounts or vault storage on an ephemeral filesystem.
- Keep `data/`, `.env`, OAuth credentials, encryption keys, session tokens, and private signing certificates out of Git.

## Deployment profiles

- `docker-compose.yml`: local self-hosted app with a persistent data volume.
- `docker-compose.local-ai.yml`: optional private-network local AI/translation services.
- `Dockerfile`: Python runtime plus native conversion/OCR tools and a non-root runtime user.
- `render.yaml`: guest-only ephemeral preview profile; deployment is not part of this open-source foundation work.

## Compatibility principles

Preserve operation slugs, API contracts, existing UI workflows, and the persistent/ephemeral security boundary. Add focused regression coverage when changing these contracts. See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).
