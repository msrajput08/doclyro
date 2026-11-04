# Contributing to Doclyro

Thanks for considering a contribution. Doclyro is an independent PDF and document toolkit. Contributions should improve reliability, accessibility, security, documentation, or supported workflows without weakening existing behavior.

## Before you start

1. Read [README.md](README.md), [SECURITY.md](SECURITY.md), and [PARITY_MATRIX.md](PARITY_MATRIX.md).
2. Search existing issues and pull requests before opening a new one.
3. For substantial changes, open an issue first so the intended behavior and compatibility impact can be discussed.
4. Never include real personal documents, credentials, access tokens, private keys, or customer data in issues, tests, screenshots, or commits.

## Development setup

The supported packaged environment is Docker Compose:

```bash
docker compose up --build
```

Then open http://localhost:8000. The FastAPI API documentation is available at /docs while the app is running.

For Python development, use Python 3.11 and install the dependencies:

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
pip install pytest
```

Some operations additionally require system tools such as LibreOffice, Ghostscript, Tesseract, and OpenSSL. See the Dockerfile for the reference package list.

## Change requirements

- Keep existing API routes, operation slugs, request/response shapes, and user-visible workflows backward-compatible unless a breaking change is explicitly approved and documented.
- Add focused regression tests for bug fixes and new behavior.
- Keep file handling bounded; validate user input and avoid unsafe temporary-file or path handling.
- Do not log document contents, passwords, tokens, or authorization headers.
- Preserve the existing privacy and ephemeral-hosting safeguards.
- Update user-facing docs and the parity/limitation notes when behavior changes.
- Do not claim PDF/A certification, legal signature status, security certification, or commercial parity without independent evidence.
- Keep changes focused. Avoid unrelated formatting or broad refactors in feature-preservation patches.

## Checks

Run the checks relevant to your change:

```bash
python -m pytest -q
for f in static/*.js; do node --check "$f"; done
python scripts/readiness.py
```

The full browser/infrastructure end-to-end test phase is intentionally reserved until the feature set is complete. Focused unit and regression tests are welcome during development; describe exactly what you ran and what remains unverified.

## Pull requests

- Use the pull request template.
- Explain the problem, user-visible behavior, and compatibility impact.
- List tests run and tests not run.
- Include before/after screenshots for UI changes, using synthetic documents only.
- Link related issues and update documentation.
- Keep one logical change per pull request where practical.

By participating, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).

## Security issues

Do not report exploitable vulnerabilities in public issues. Follow the private reporting guidance in [SECURITY.md](SECURITY.md).
