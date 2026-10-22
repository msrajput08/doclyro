"""Local PAdES-compatible detached CMS PDF signatures.

Signing uses a user-supplied PKCS#12 private key bundle.  The cryptographic
signature proves byte integrity, NOT the identity/trustworthiness of a signer:
certificate issuance, path validation and legal qualified-signature services
are out of scope.  No credentials are saved outside the temporary job folder.
"""
from __future__ import annotations
import io
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.serialization import pkcs7, pkcs12
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject, BooleanObject, ByteStringObject, DictionaryObject,
    NameObject, NumberObject, TextStringObject,
)

# The placeholder makes the output's /ByteRange values stable while signing.
# 16 KiB is sufficient for typical certificate chains and short-lived PDFs.
RESERVED_SIGNATURE_BYTES = 16384
PLACEHOLDER_NUMBER = 9999999999
MAX_SIGNATURE_PDF_BYTES = 100 * 1024 * 1024

class SignatureError(ValueError):
    pass


def _pdf_writer_with_field(pdf_path: Path, field_name: str, reserved: int) -> bytes:
    try:
        writer = PdfWriter(clone_from=str(pdf_path))
        if not writer.pages:
            raise SignatureError('Document has no PDF pages.')
    except SignatureError:
        raise
    except Exception as e:
        raise SignatureError('Unable to load the PDF for signing: ' + str(e)[:160]) from e
    if writer.is_encrypted:
        raise SignatureError('Unlock the encrypted PDF first, then add a certificate signature.')

    # The contents is encoded as one hex string by pypdf.  Each /ByteRange
    # number is padded in-place, without changing any subsequent PDF offsets.
    sig = DictionaryObject({
        NameObject('/Type'): NameObject('/Sig'),
        NameObject('/Filter'): NameObject('/Adobe.PPKLite'),
        NameObject('/SubFilter'): NameObject('/adbe.pkcs7.detached'),
        NameObject('/ByteRange'): ArrayObject([NumberObject(PLACEHOLDER_NUMBER)] * 4),
        NameObject('/Contents'): ByteStringObject(b'\0' * reserved),
        NameObject('/M'): TextStringObject(__import__('datetime').datetime.now(__import__('datetime').timezone.utc).strftime("D:%Y%m%d%H%M%SZ")),
        NameObject('/Name'): TextStringObject(field_name),
    })
    sig_ref = writer._add_object(sig)
    page = writer.pages[0]
    widget = DictionaryObject({
        NameObject('/Type'): NameObject('/Annot'),
        NameObject('/Subtype'): NameObject('/Widget'),
        NameObject('/FT'): NameObject('/Sig'),
        NameObject('/T'): TextStringObject(field_name),
        NameObject('/Rect'): ArrayObject([NumberObject(0)] * 4),
        NameObject('/F'): NumberObject(4),
        NameObject('/V'): sig_ref,
        NameObject('/P'): page.indirect_reference,
    })
    widget_ref = writer._add_object(widget)
    if '/Annots' in page:
        existing = page['/Annots'].get_object()
        existing.append(widget_ref)
    else:
        page[NameObject('/Annots')] = ArrayObject([widget_ref])
    root = writer._root_object
    if '/AcroForm' in root:
        acro = root['/AcroForm'].get_object()
    else:
        acro = DictionaryObject()
        root[NameObject('/AcroForm')] = writer._add_object(acro)
    if '/Fields' not in acro:
        acro[NameObject('/Fields')] = ArrayObject()
    acro['/Fields'].get_object().append(widget_ref)
    acro[NameObject('/SigFlags')] = NumberObject(3)
    data = io.BytesIO()
    writer.write(data)
    return data.getvalue()


def _signature_placeholder(raw: bytes, reserved: int) -> tuple[int, int, tuple[int, int, int, int], tuple[int, int]]:
    # Exactly one placeholder is created by this function; reject ambiguity.
    hex_placeholder = b'0' * (reserved * 2)
    matches = list(re.finditer(rb'/Contents\s*<(' + hex_placeholder + rb')>', raw))
    if len(matches) != 1:
        raise SignatureError('Cannot locate the PDF signing placeholder.')
    match = matches[0]
    opening = match.start(1) - 1
    closing = match.end(1) + 1
    byte_range = (0, opening, closing, len(raw) - closing)
    pattern = re.compile(rb'/ByteRange\s*\[\s*9999999999\s+9999999999\s+9999999999\s+9999999999\s*\]')
    matches = list(pattern.finditer(raw))
    if len(matches) != 1:
        raise SignatureError('Cannot locate the PDF signing byte range.')
    br_match = matches[0]
    br_numbers = list(re.finditer(rb'9999999999', br_match.group(0)))
    if len(br_numbers) != 4:
        raise SignatureError('Unexpected PDF signing byte-range representation.')
    if max(byte_range) >= 10**10:
        raise SignatureError('PDF is too large for this signing operation.')
    return match.start(1), match.end(1), byte_range, tuple(br_match.start()+m.start() for m in br_numbers)


def sign_pdf(input_pdf: Path, p12_path: Path, password: str, output_pdf: Path, field_name: str = 'PDFCraftSignature') -> Path:
    if input_pdf.suffix.lower() != '.pdf' or p12_path.suffix.lower() not in ('.p12', '.pfx'):
        raise SignatureError('Upload a PDF followed by your PKCS#12 .p12/.pfx certificate bundle.')
    if not 0 < input_pdf.stat().st_size <= MAX_SIGNATURE_PDF_BYTES:
        raise SignatureError('The PDF is too large for certificate signing.')
    try:
        private_key, cert, other_certs = pkcs12.load_key_and_certificates(
            p12_path.read_bytes(), password.encode('utf-8') if password else None)
    except Exception as e:
        raise SignatureError('Could not open PKCS#12 bundle. Check certificate and passphrase.') from e
    if not private_key or not cert:
        raise SignatureError('The PKCS#12 bundle must contain a private key and a signing certificate.')
    clean_name = re.sub(r'[^\w -]', '', field_name or '').strip()[:50] or 'PDFCraftSignature'
    raw = bytearray(_pdf_writer_with_field(input_pdf, clean_name, RESERVED_SIGNATURE_BYTES))
    start, end, ranges, number_positions = _signature_placeholder(bytes(raw), RESERVED_SIGNATURE_BYTES)
    for offset, number in zip(number_positions, ranges):
        raw[offset:offset+10] = f'{number:>10d}'.encode('ascii')
    signed_bytes = bytes(raw[:ranges[1]] + raw[ranges[2]:])
    builder = pkcs7.PKCS7SignatureBuilder().set_data(signed_bytes).add_signer(cert, private_key, hashes.SHA256())
    for extra in other_certs or ():
        builder = builder.add_certificate(extra)
    cms = builder.sign(serialization.Encoding.DER, [pkcs7.PKCS7Options.DetachedSignature, pkcs7.PKCS7Options.Binary])
    if len(cms) > RESERVED_SIGNATURE_BYTES:
        raise SignatureError('Certificate chain is too large for the signature placeholder.')
    content = cms.hex().encode('ascii')
    raw[start:end] = content.ljust(end-start, b'0')
    output_pdf.write_bytes(raw)
    return output_pdf


def inspect_signatures(pdf_path: Path) -> list[dict]:
    """Verify PDF ByteRange cryptographic integrity. Does not assert CA trust."""
    try:
        reader = PdfReader(str(pdf_path), strict=False)
    except Exception as e:
        raise SignatureError('Cannot read this PDF: ' + str(e)[:160]) from e
    results: list[dict] = []
    fields = reader.get_fields() or {}
    raw = pdf_path.read_bytes()
    for name, field in fields.items():
        if str(field.get('/FT')) != '/Sig' or not field.get('/V'):
            continue
        sig = field['/V'].get_object()
        byte_range = sig.get('/ByteRange')
        contents = sig.get('/Contents')
        result = {'field': name, 'cryptographically_valid': False, 'covers_entire_file': False,
                  'trust_status': 'not_evaluated', 'certificate_subject': '',
                  'certificate_currently_valid': None,
                  'system_ca_chain_valid': None, 'message': ''}
        try:
            if not byte_range or len(byte_range) != 4 or not contents:
                raise SignatureError('Missing signature ByteRange or Contents.')
            a, b, c, d = map(int, byte_range)
            if a != 0 or min(b,c,d) < 0 or b >= c or c+d > len(raw):
                raise SignatureError('Malformed signature byte offsets.')
            result['covers_entire_file'] = (c+d == len(raw))
            cms = bytes(contents).rstrip(b'\0')
            from cryptography.hazmat.primitives.serialization.pkcs7 import load_der_pkcs7_certificates
            certificates = load_der_pkcs7_certificates(cms)
            if certificates:
                result['certificate_subject'] = certificates[0].subject.rfc4514_string()[:500]
                cert_obj = certificates[0]
                now = datetime.now(timezone.utc)
                # Cryptography's timezone-aware X.509 properties are available
                # in modern versions (dependency currently >=42).
                result['certificate_currently_valid'] = (
                    cert_obj.not_valid_before_utc <= now <= cert_obj.not_valid_after_utc)
            payload = raw[a:a+b] + raw[c:c+d]
            # OpenSSL validates CMS signature against the detached bytes while
            # deliberately not asserting an external trusted CA/root.
            with tempfile.TemporaryDirectory(prefix='pdfcraft_sigverify_') as td:
                p = Path(td)
                (p/'contents.p7s').write_bytes(cms)
                (p/'signed.bin').write_bytes(payload)
                cmd=['openssl','cms','-verify','-inform','DER','-binary','-noverify',
                     '-in',str(p/'contents.p7s'),'-content',str(p/'signed.bin'),
                     '-out',os.devnull]
                proc = subprocess.run(cmd, capture_output=True, timeout=20, check=False)
                result['cryptographically_valid'] = proc.returncode == 0
                if proc.returncode == 0:
                    # This additional check is only against the HOST SYSTEM CA
                    # store. It is not AATL/EUTL status, QES, identity proof,
                    # signed-at-time validation, or revocation validation.
                    chain_cmd=['openssl','cms','-verify','-inform','DER','-binary',
                               '-purpose','any','-in',str(p/'contents.p7s'),
                               '-content',str(p/'signed.bin'),'-out',os.devnull]
                    try:
                        chain_proc = subprocess.run(chain_cmd,capture_output=True,timeout=20,check=False)
                        result['system_ca_chain_valid'] = (chain_proc.returncode == 0)
                    except (subprocess.TimeoutExpired, OSError):
                        result['system_ca_chain_valid'] = None
                result['message'] = ('Cryptographic signature valid (certificate trust not checked).'
                                     if proc.returncode == 0 else 'Signature bytes do not verify: ' + proc.stderr.decode(errors='replace')[-180:])
        except Exception as e:
            result['message'] = 'Signature verification failed: ' + str(e)[:180]
        results.append(result)
    return results

