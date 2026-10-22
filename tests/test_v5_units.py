"""Focused module-level regression checks (NOT full HTTP/browser end-to-end QA)."""
from __future__ import annotations
import datetime
import tempfile
import unittest
from pathlib import Path

import fitz
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from app.compare_views import compare_page
from app.digital_signing import SignatureError, sign_pdf, inspect_signatures
from app.processor import ProcessingError, op_sign_certificate, op_verify_signatures


class CertificateSigningUnitTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory(prefix='pdfcraft_v5_unit_')
        self.wd = Path(self.dir.name)
        self.pdf = self.wd/'input.pdf'
        doc=fitz.open()
        doc.new_page().insert_text((90,90),'Original PDF for test signing')
        doc.save(self.pdf)
        doc.close()
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,'Test Signing Identity')])
        today=datetime.datetime.now(datetime.timezone.utc)
        certificate=(x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(private_key.public_key())
                     .serial_number(x509.random_serial_number()).not_valid_before(today-datetime.timedelta(days=1))
                     .not_valid_after(today+datetime.timedelta(days=30)).sign(private_key,hashes.SHA256()))
        self.p12=self.wd/'identity.p12'
        self.p12.write_bytes(pkcs12.serialize_key_and_certificates(
            b'test',private_key,certificate,None,serialization.BestAvailableEncryption(b'test-pass')))
    def tearDown(self):
        self.dir.cleanup()
    def test_genuine_cms_signature_and_inspection(self):
        output=sign_pdf(self.pdf,self.p12,'test-pass',self.wd/'signed.pdf')
        result=inspect_signatures(output)
        self.assertEqual(len(result),1)
        self.assertTrue(result[0]['cryptographically_valid'], result)
        self.assertTrue(result[0]['covers_entire_file'])
        self.assertIn('Test Signing Identity',result[0]['certificate_subject'])
        self.assertEqual(result[0]['trust_status'],'not_evaluated')
        self.assertTrue(result[0]['certificate_currently_valid'])
        self.assertFalse(result[0]['system_ca_chain_valid'])
        with fitz.open(output) as d:
            self.assertEqual(len(d),1)
            self.assertIn('Original PDF',d[0].get_text())
    def test_modified_signed_bytes_are_rejected(self):
        output=sign_pdf(self.pdf,self.p12,'test-pass',self.wd/'signed.pdf')
        raw=bytearray(output.read_bytes())
        spot=raw.index(b'Original PDF') if b'Original PDF' in raw else raw.index(b'/MediaBox')
        raw[spot]=ord('X')
        output.write_bytes(raw)
        result=inspect_signatures(output)
        self.assertEqual(len(result),1)
        self.assertFalse(result[0]['cryptographically_valid'])
    def test_wrong_password_rejected(self):
        with self.assertRaisesRegex(SignatureError,'passphrase'):
            sign_pdf(self.pdf,self.p12,'incorrect',self.wd/'wrong.pdf')
    def test_non_pdf_certificate_upload_order(self):
        with self.assertRaisesRegex(ProcessingError,'PDF first'):
            op_sign_certificate([self.p12,self.pdf],{},self.wd)
    def test_refuse_rewriting_existing_signed_pdf(self):
        signed=sign_pdf(self.pdf,self.p12,'test-pass',self.wd/'signed.pdf')
        with self.assertRaisesRegex(ProcessingError,'already signed'):
            op_sign_certificate([signed,self.p12],{'certificate_password':'test-pass'},self.wd)
    def test_signature_verification_report_pdf(self):
        signed=sign_pdf(self.pdf,self.p12,'test-pass',self.wd/'signed.pdf')
        report=op_verify_signatures([signed],{},self.wd)
        with fitz.open(report) as d:
            text=d[0].get_text()
            self.assertIn('Cryptographic bytes valid: YES',text)
            self.assertIn('NOT PERFORMED',text)
    def test_unsigned_append_flagged(self):
        # Appended bytes can retain a valid historical CMS signature, but are
        # not covered by the signed PDF byte ranges.
        output=sign_pdf(self.pdf,self.p12,'test-pass',self.wd/'signed.pdf')
        output.write_bytes(output.read_bytes()+b'\n% extra unsigned data\n')
        results=inspect_signatures(output)
        self.assertEqual(len(results),1)
        self.assertTrue(results[0]['cryptographically_valid'])
        self.assertFalse(results[0]['covers_entire_file'])

    def test_no_signatures_report(self):
        report=op_verify_signatures([self.pdf],{},self.wd)
        with fitz.open(report) as d:
            self.assertIn('No cryptographic signature',d[0].get_text())


class ComparePageUnitTests(unittest.TestCase):
    def setUp(self):
        self.dir=tempfile.TemporaryDirectory(prefix='pdfcraft_v5_compare_')
        self.wd=Path(self.dir.name)
        self.pdf1=self.wd/'original.pdf'
        self.pdf2=self.wd/'revised.pdf'
        for path, text in [(self.pdf1,'Same text'),(self.pdf2,'Changed text')]:
            d=fitz.open();d.new_page(width=400,height=500).insert_text((40,75),text)
            d.save(path);d.close()
    def tearDown(self):
        self.dir.cleanup()
    def test_detect_changed_text_and_pixmap(self):
        result=compare_page(self.pdf1,self.pdf2,1,target_width=500)
        self.assertEqual(result['total_pages'],1)
        self.assertTrue(result['text_changed'])
        self.assertGreater(result['changed_pixels_percent'],0)
        for key in ['original','revised','highlighted']:
            self.assertTrue(result[key].startswith('data:image/png;base64,'))
    def test_same_pdf_no_changes(self):
        result=compare_page(self.pdf1,self.pdf1,1)
        self.assertFalse(result['text_changed'])
        self.assertEqual(result['changed_pixels_percent'],0)
    def test_bad_page_number_rejected(self):
        with self.assertRaisesRegex(ValueError,'Page does not exist'):
            compare_page(self.pdf1,self.pdf2,2)
    def test_missing_second_page(self):
        d=fitz.open(self.pdf2)
        d.new_page().insert_text((30,40),'Second page added')
        d.save(self.wd/'revised2.pdf')
        d.close()
        out=compare_page(self.pdf1,self.wd/'revised2.pdf',2)
        self.assertFalse(out['original_page_exists'])
        self.assertTrue(out['revised_page_exists'])
        self.assertGreater(out['changed_pixels_percent'],0)


if __name__ == '__main__':
    unittest.main()
