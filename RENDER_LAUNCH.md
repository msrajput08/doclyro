# Doclyro — Render Free deployment handoff

## Code prerequisites

- Connect a **separate** GitHub repository for Doclyro. Never deploy from another project's production branch.
- Commit all project files at repository root, including `Dockerfile`, `requirements.txt`, `app/`, `static/` and `render.yaml`.
- The project intentionally serves both frontend and API from the same Docker/FastAPI service.

## Render Free settings

- Service type: **Web Service**
- Runtime: **Docker**
- Plan: **Free** only
- Branch: `main`
- Dockerfile path: `./Dockerfile`
- Health check: `/api/health`
- Region: Singapore (nearest available for India) if offered
- Root directory: leave blank
- Environment variables:

```env
PDFCRAFT_EPHEMERAL_MODE=true
PDFCRAFT_CONCURRENT_JOBS=1
PDFCRAFT_REQUESTS_PER_10_MIN=12
MAX_UPLOAD_MB=10
MAX_JOB_MB=20
PDFCRAFT_ALLOW_REMOTE_URLS=false
WEB_CONCURRENCY=1
PYTHONUNBUFFERED=1
```

Don't add persistent account/vault routes on this free filesystem. Do not enable paid resources, disks or databases.

## After the deployment

- Wait for a successful build/live status and read the service's own URL. The `doclyro.onrender.com` hostname is not guaranteed in advance.
- Check `/api/health` and `/api/capabilities`; `ephemeral_mode` should be true and `tools` should be 42.
- Open the site and perform a small non-sensitive sample PDF conversion before inviting users.
- Free plan constraints: 512 MB RAM/0.1 CPU, 15-minute idle spin-down, ephemeral local files, shared monthly workspace free-hour and build/bandwidth quota.
- Existing external provider integrations and guaranteed large conversions cannot be declared ready without real-world checks.
