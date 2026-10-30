"""Regression tests for the Word/PDF conversion quality safeguards."""
import sys
from types import SimpleNamespace

import fitz
import pytest
from docx import Document
from PIL import Image

import app.processor as processor
from app.processor import ProcessingError, process


class RecordingConverter:
    calls = []

    def __init__(self, pdf_file, password=None):
        self.call = {"source": str(pdf_file), "password": password}
        type(self).calls.append(self.call)

    def convert(self, output, **options):
        self.call["options"] = options
        doc = Document()
        doc.add_paragraph("Converted with layout reconstruction")
        doc.save(output)

    def close(self):
        self.call["closed"] = True


def install_converter(monkeypatch, converter=RecordingConverter):
    converter.calls.clear()
    monkeypatch.setitem(sys.modules, "pdf2docx", SimpleNamespace(Converter=converter))


def make_text_pdf(path):
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((72, 72), "This PDF has enough selectable text for layout conversion.")
        doc.save(str(path))


def make_scanned_pdf(path, image_path):
    Image.new("RGB", (240, 320), "white").save(image_path)
    with fitz.open() as doc:
        page = doc.new_page(width=240, height=320)
        page.insert_image(page.rect, filename=str(image_path))
        doc.save(str(path))


def test_pdf_to_word_uses_strict_layout_conversion_and_forwards_password(monkeypatch, tmp_path):
    source = tmp_path / "locked.pdf"
    with fitz.open() as doc:
        doc.new_page().insert_text((72, 72), "Selectable text in a password protected PDF.")
        doc.save(
            str(source),
            encryption=fitz.PDF_ENCRYPT_AES_256,
            owner_pw="owner-secret",
            user_pw="user-secret",
        )
    install_converter(monkeypatch)

    result = process("pdf-to-word", [source], {"password": "user-secret"}, tmp_path)

    assert result.is_file()
    call = RecordingConverter.calls[-1]
    assert call["password"] == "user-secret"
    assert call["options"]["raw_exceptions"] is True
    assert call["options"]["ignore_page_error"] is False
    assert call["options"]["delete_end_line_hyphen"] is True
    assert call["closed"] is True


def test_pdf_to_word_rejects_wrong_password_before_conversion(monkeypatch, tmp_path):
    source = tmp_path / "locked.pdf"
    with fitz.open() as doc:
        doc.new_page().insert_text((72, 72), "Selectable text in a password protected PDF.")
        doc.save(str(source), encryption=fitz.PDF_ENCRYPT_AES_256,
                 owner_pw="owner-secret", user_pw="user-secret")
    install_converter(monkeypatch)

    with pytest.raises(ProcessingError, match="password"):
        process("pdf-to-word", [source], {"password": "wrong"}, tmp_path)
    assert RecordingConverter.calls == []


def test_pdf_to_word_automatically_ocr_processes_scanned_only_pdf(monkeypatch, tmp_path):
    source = tmp_path / "scan.pdf"
    make_scanned_pdf(source, tmp_path / "scan.png")
    install_converter(monkeypatch)
    ocr_calls = {}

    def fake_ocr(files, options, workdir):
        ocr_calls["options"] = options
        searchable = workdir / "ocr_ready.pdf"
        make_text_pdf(searchable)
        return searchable

    monkeypatch.setattr(processor, "op_ocr", fake_ocr)
    result = process("pdf-to-word", [source], {"language": "eng+hin", "dpi": "240"}, tmp_path)

    assert result.is_file()
    assert ocr_calls["options"]["language"] == "eng+hin"
    assert ocr_calls["options"]["dpi"] == 240
    assert RecordingConverter.calls[-1]["source"].endswith("ocr_ready.pdf")
    assert RecordingConverter.calls[-1]["password"] is None


def test_pdf_to_word_warns_instead_of_silently_dropping_scanned_pages(tmp_path):
    source = tmp_path / "mixed.pdf"
    image_path = tmp_path / "scan.png"
    Image.new("RGB", (240, 320), "white").save(image_path)
    with fitz.open() as doc:
        doc.new_page().insert_text((72, 72), "This page contains selectable text.")
        scanned = doc.new_page(width=240, height=320)
        scanned.insert_image(scanned.rect, filename=str(image_path))
        doc.save(str(source))

    with pytest.raises(ProcessingError, match="mixes scanned pages"):
        process("pdf-to-word", [source], {}, tmp_path)


def test_pdf_to_word_does_not_fall_back_to_plain_text_after_layout_failure(monkeypatch, tmp_path):
    source = tmp_path / "source.pdf"
    make_text_pdf(source)

    class BrokenConverter(RecordingConverter):
        calls = []

        def convert(self, output, **options):
            raise RuntimeError("table layout parser failed")

    install_converter(monkeypatch, BrokenConverter)

    with pytest.raises(ProcessingError, match="No simplified replacement was generated"):
        process("pdf-to-word", [source], {}, tmp_path)
    assert not (tmp_path / "converted.docx").exists()


@pytest.mark.parametrize(
    "slug,extension,expected_filter",
    [
        ("word-to-pdf", ".docx", "writer_pdf_Export"),
        ("powerpoint-to-pdf", ".pptx", "impress_pdf_Export"),
        ("excel-to-pdf", ".xlsx", "calc_pdf_Export"),
    ],
)
def test_office_to_pdf_selects_the_matching_export_filter(
    monkeypatch, tmp_path, slug, extension, expected_filter
):
    source = tmp_path / ("source" + extension)
    source.write_bytes(b"test source")
    captured = {}

    def fake_convert(path, workdir, output_extension, export_filter):
        captured["source"] = path
        captured["filter"] = export_filter
        result = workdir / "office.pdf"
        result.write_bytes(b"%PDF-test")
        return result

    monkeypatch.setattr(processor, "libreoffice_convert", fake_convert)
    result = process(slug, [source], {}, tmp_path)

    assert result.is_file()
    assert captured["source"] == source
    assert captured["filter"] == expected_filter


def test_office_to_pdf_rejects_unsupported_extension(tmp_path):
    source = tmp_path / "notes.txt"
    source.write_text("not an Office document")
    with pytest.raises(ProcessingError, match="Unsupported Office format"):
        process("word-to-pdf", [source], {}, tmp_path)


def test_libreoffice_conversion_uses_isolated_profile_and_validates_pdf(monkeypatch, tmp_path):
    source = tmp_path / "source.docx"
    source.write_bytes(b"test source")
    captured = {}

    def fake_cli(args, timeout=180):
        captured["args"] = args
        captured["timeout"] = timeout
        with fitz.open() as doc:
            doc.new_page()
            doc.save(str(tmp_path / "source.pdf"))

    monkeypatch.setattr(processor, "cli", fake_cli)
    result = processor.libreoffice_convert(
        source, tmp_path, "pdf", "writer_pdf_Export"
    )

    assert result.is_file()
    assert "--headless" in captured["args"]
    assert "--convert-to" in captured["args"]
    assert "pdf:writer_pdf_Export" in captured["args"]
    assert any("UserInstallation=file://" in item for item in captured["args"])
    assert captured["timeout"] == 180
