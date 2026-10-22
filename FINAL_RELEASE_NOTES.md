# Doclyro — consolidated source release

The independent Doclyro web app includes 42 registered PDF/document operations, FastAPI backend, static interface, Docker configuration, and a Render Free guest-preview blueprint.

## Local launch

With Docker installed, run `docker compose up --build` in the extracted project folder and browse to `http://localhost:8000`. If using the guest-only setup, set `PDFCRAFT_EPHEMERAL_MODE=true` so vault/account routes are not exposed on disposable storage.

## Hosting

`render.yaml` supports a free Docker-hosted guest preview, with no purchased domain or card needed. Production user accounts and storage MUST be hosted with durable DB + object storage; Render Free's disk is not persistent. Runtime availability, memory fit, paid quota, and URL are not guaranteed.

## Scope and disclosure

42 tools are implemented in source. That does not mean complete commercial iLovePDF parity. PDF/A validation, provider OAuth onboarding, legal QES identity verification, document fidelity for complex Office sources, generative AI model availability, heavy CPU workloads, safe image/text redaction under all circumstances and production security certification require separate integration or evidence. Never advertise those as independently certified.

Do not publish a public site with promises of 'fully private local-only processing' because PDFs are uploaded to the server for processing. Successful jobs use temporary files which are deleted after the response completes.
