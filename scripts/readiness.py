"""Static deployment readiness checklist; does NOT run end-to-end tests."""
import os
import shutil
from pathlib import Path

checks = [
    ('PDF rendering', True, 'PyMuPDF and Pillow are in requirements.txt'),
    ('Office conversion', bool(shutil.which('libreoffice')), 'LibreOffice is installed in Docker image'),
    ('OCR engine', bool(shutil.which('tesseract')), 'Tesseract + selected language packs in Docker image'),
    ('Ghostscript compression/PDF-A', bool(shutil.which('gs')), 'Ghostscript in Docker image'),
    ('CMS cryptographic verification', bool(shutil.which('openssl')), 'OpenSSL in Docker image'),
    ('Generative AI configured', bool(os.getenv('AI_API_KEY')), 'Use provider key or local-ai Compose + Ollama model pull'),
    ('Translation configured', bool(os.getenv('LIBRETRANSLATE_URL')), 'Use approved translation provider or local-ai Compose'),
    ('Google OAuth configured', bool(os.getenv('GOOGLE_CLIENT_ID')), 'Register and approve a Google OAuth client'),
    ('Dropbox OAuth configured', bool(os.getenv('DROPBOX_CLIENT_ID')), 'Register a Dropbox OAuth app'),
    ('SMTP configured', bool(os.getenv('SMTP_HOST') and os.getenv('SMTP_FROM')), 'Supply a verified SMTP sender for invitations/recovery'),
    ('Canonical public URL configured', bool(os.getenv('PDFCRAFT_PUBLIC_URL')), 'Requires real deployment host for live email/OAuth callbacks'),
]

print('PDFCraft Studio — configuration readiness (NO end-to-end testing)\n')
for name, ok, note in checks:
    print(f'{"READY" if ok else "SETUP" :5}  {name:36} {note}')
print('\nCryptographic PDF signing requires a signer-owned PKCS#12 certificate at time of use.')
print('External PKI trust, provider consent, HTTPS deployment and security audit require operator action.')
