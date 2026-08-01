import os
from pypdf import PdfWriter
from pdf_decrypt import decrypt_pdf, extract_text, DecryptionError


def _make_encrypted_pdf(path, password):
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.encrypt(password)
    with open(path, "wb") as f:
        writer.write(f)


def test_decrypt_with_correct_password(tmp_path):
    enc = tmp_path / "enc.pdf"
    dec = tmp_path / "dec.pdf"
    _make_encrypted_pdf(enc, "rightpw")

    result = decrypt_pdf(str(enc), str(dec), ["wrongpw", "rightpw"])

    assert result == str(dec)
    assert os.path.exists(dec)


def test_decrypt_fails_with_no_matching_password(tmp_path):
    enc = tmp_path / "enc.pdf"
    dec = tmp_path / "dec.pdf"
    _make_encrypted_pdf(enc, "rightpw")

    try:
        decrypt_pdf(str(enc), str(dec), ["wrongpw1", "wrongpw2"])
        assert False, "expected DecryptionError"
    except DecryptionError:
        pass


def test_decrypt_passthrough_for_unencrypted_pdf(tmp_path):
    src = tmp_path / "plain.pdf"
    dec = tmp_path / "dec.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    with open(src, "wb") as f:
        writer.write(f)

    result = decrypt_pdf(str(src), str(dec), ["irrelevant"])

    assert result == str(dec)
    assert os.path.exists(dec)
