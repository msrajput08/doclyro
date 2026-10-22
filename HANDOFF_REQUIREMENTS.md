# Operator handoff — only when required for real external/production features

Continue implementing all self-contained project code before scheduling final E2E tests. The following cannot be supplied by generated source code alone and eventually need site-owner action:

1. **Google Drive** — create OAuth 2.0 app, approve required user scopes, supply `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and public `PDFCRAFT_PUBLIC_URL`, register `/api/cloud/callback/google`.
2. **Dropbox** — create Dropbox OAuth app, supply `DROPBOX_CLIENT_ID`, `DROPBOX_CLIENT_SECRET`, and register `/api/cloud/callback/dropbox`.
3. **Email** — choose/verify SMTP provider, supply `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, `SMTP_USERNAME`, `SMTP_PASSWORD`, TLS config, and publish a working canonical URL.
4. **AI** — optionally choose a hosted model/key or enable included local-model Compose profile and obtain container/model downloads. The local model route avoids the need for a paid API key but requires available CPU/RAM, storage and network for model provisioning.
5. **Translation** — optionally use included local LibreTranslate service or choose a trusted external server. Model support and layout fidelity must be judged against representative real documents after implementation.
6. **Qualified signatures** — if legally certified/identity-verified signing is required, contract with an accredited trust-service/signing provider, provide approved credentials, and determine country-specific standards. A user-supplied P12 creates a cryptographic signature but does not alone confer legal QES status.
7. **Public production launch** — specify domain, hosting account/platform, HTTPS, backup/retention/privacy requirements, operational monitoring and budget. Formal PDF/A validation tools and signing trust stores can be installed as part of that environment.

**Do not share passwords, private keys, API tokens, or P12 certificate bundles in chat or source code.** Configure them directly in your own secrets manager or server environment when integration time arrives.

Status: The project is not yet 100% parity. Full end-to-end testing remains deferred to the final phase, as requested.
