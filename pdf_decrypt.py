"""Module 1: PDF decryption.

Takes a password-protected bank/CC statement PDF and a list of candidate
passwords, tries each, and writes out a decrypted copy. Pure-Python
(pypdf), no hosted service, no third-party API — statement content never
leaves the machine.
"""
from pypdf import PdfReader, PdfWriter
from pypdf.errors import FileNotDecryptedError


class DecryptionError(Exception):
    pass


def decrypt_pdf(input_path: str, output_path: str, passwords: list[str]) -> str:
    """Decrypt input_path using the first matching password in passwords.

    Returns output_path on success. Raises DecryptionError if the file is
    encrypted and none of the passwords work.
    """
    reader = PdfReader(input_path)

    if not reader.is_encrypted:
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        with open(output_path, "wb") as f:
            writer.write(f)
        return output_path

    matched = False
    for pw in passwords:
        result = reader.decrypt(pw)
        # pypdf: 0 = failed, 1 = matched user password, 2 = matched owner password
        if result:
            matched = True
            break

    if not matched:
        raise DecryptionError(
            f"None of the {len(passwords)} candidate passwords unlocked {input_path}"
        )

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    with open(output_path, "wb") as f:
        writer.write(f)
    return output_path


def extract_text(pdf_path: str) -> str:
    """Extract raw text from a (decrypted) PDF, page-joined with form feeds."""
    reader = PdfReader(pdf_path)
    return "\f".join(page.extract_text() or "" for page in reader.pages)
