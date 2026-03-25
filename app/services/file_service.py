"""
File Service — downloads Telegram files, stores them, and extracts text.

Storage layout (Ministry of Revenue compliant):
  uploads/
    {company_slug}/
      {YYYY}/
        {MM}/
          {YYYY-MM-DD}_tx{id}_{counterparty}.{ext}

Original files are NEVER deleted or overwritten.
"""
from __future__ import annotations

import logging
import re
import uuid
import zipfile
from datetime import date
from io import BytesIO
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.models.attachment import Attachment

logger = logging.getLogger(__name__)

BASE_UPLOAD_DIR = Path(settings.upload_dir)
BASE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
PDF_EXTENSIONS = {".pdf"}


# ── Storage path helpers ──────────────────────────────────────────────────────

def _company_upload_dir(company_slug: str, year: int, month: int) -> Path:
    """Returns (and creates) uploads/{slug}/{YYYY}/{MM}/"""
    path = BASE_UPLOAD_DIR / company_slug / str(year) / f"{month:02d}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _safe_name(text: str) -> str:
    """Strip characters unsafe for filenames."""
    return re.sub(r"[^\w\-]", "_", text or "unknown")[:30]


def _build_filename(
    ext: str,
    tx_date: Optional[date] = None,
    tx_id: Optional[int] = None,
    counterparty: Optional[str] = None,
) -> str:
    """
    Build a human-readable filename:
      2026-03-25_tx42_Ethio_Telecom.jpg
    Falls back to a UUID if no transaction info is available yet.
    """
    if tx_date and tx_id:
        cp = _safe_name(counterparty) if counterparty else "unknown"
        return f"{tx_date}_tx{tx_id}_{cp}{ext}"
    return f"{uuid.uuid4().hex}{ext}"


# ── Public API ────────────────────────────────────────────────────────────────

def store_file(
    db: Session,
    company_id: int,
    file_bytes: bytes,
    original_filename: str,
    telegram_file_id: Optional[str] = None,
    transaction_id: Optional[int] = None,
    company_slug: str = "default",
    tx_date: Optional[date] = None,
    counterparty: Optional[str] = None,
) -> Attachment:
    """
    Save file to disk under an organised path and create an Attachment record.
    Files are stored immediately on upload; renamed once linked to a transaction.
    """
    today = tx_date or date.today()
    ext = Path(original_filename).suffix.lower() or ".bin"
    upload_dir = _company_upload_dir(company_slug, today.year, today.month)
    filename = _build_filename(ext, tx_date, transaction_id, counterparty)
    stored_path = upload_dir / filename

    # Avoid overwriting if somehow same name exists
    if stored_path.exists():
        stored_path = upload_dir / f"{uuid.uuid4().hex[:8]}_{filename}"

    stored_path.write_bytes(file_bytes)
    logger.info("FileService: saved %s (%d bytes)", stored_path, len(file_bytes))

    attachment = Attachment(
        company_id=company_id,
        transaction_id=transaction_id,
        original_filename=original_filename,
        stored_path=str(stored_path),
        file_type=_classify_file(ext),
        file_size_bytes=len(file_bytes),
        telegram_file_id=telegram_file_id,
    )
    db.add(attachment)
    db.flush()
    return attachment


def rename_after_confirmation(
    attachment: Attachment,
    tx_id: int,
    tx_date: date,
    counterparty: Optional[str],
    company_slug: str,
) -> None:
    """
    Rename the stored file to include transaction ID and date after confirmation.
    Updates the attachment record in place (caller must flush/commit).
    """
    old_path = Path(attachment.stored_path)
    if not old_path.exists():
        return

    ext = old_path.suffix.lower()
    new_dir = _company_upload_dir(company_slug, tx_date.year, tx_date.month)
    new_name = _build_filename(ext, tx_date, tx_id, counterparty)
    new_path = new_dir / new_name

    if new_path.exists():
        new_path = new_dir / f"{uuid.uuid4().hex[:8]}_{new_name}"

    old_path.rename(new_path)
    attachment.stored_path = str(new_path)
    logger.info("FileService: renamed %s → %s", old_path.name, new_path.name)


def list_attachments_for_period(
    db: Session,
    company_id: int,
    year: int,
    month: Optional[int] = None,
) -> list[Attachment]:
    """Return all attachments for a given year (or year+month)."""
    from sqlalchemy import extract
    from app.models.transaction import Transaction

    q = (
        db.query(Attachment)
        .join(Transaction, Attachment.transaction_id == Transaction.id, isouter=True)
        .filter(Attachment.company_id == company_id)
    )
    if month:
        q = q.filter(
            extract("year", Transaction.transaction_date) == year,
            extract("month", Transaction.transaction_date) == month,
        )
    else:
        q = q.filter(extract("year", Transaction.transaction_date) == year)

    return q.order_by(Transaction.transaction_date).all()


def build_zip_for_period(
    db: Session,
    company_id: int,
    year: int,
    month: Optional[int] = None,
) -> tuple[bytes, str]:
    """
    Bundle all receipt files for a period into a ZIP archive.
    Returns (zip_bytes, suggested_filename).
    """
    attachments = list_attachments_for_period(db, company_id, year, month)

    period_label = f"{year}-{month:02d}" if month else str(year)
    zip_filename = f"helias_receipts_{period_label}.zip"

    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        added = 0
        for att in attachments:
            path = Path(att.stored_path)
            if path.exists():
                # Use the human-readable filename inside the ZIP
                arcname = path.name
                zf.write(path, arcname=arcname)
                added += 1
            else:
                logger.warning("FileService: missing file %s for attachment %d", path, att.id)

    if added == 0:
        return b"", zip_filename

    return buf.getvalue(), zip_filename


def extract_text_from_attachment(attachment: Attachment) -> str:
    path = Path(attachment.stored_path)
    if not path.exists():
        logger.warning("FileService: file not found: %s", path)
        return ""
    if path.suffix.lower() in PDF_EXTENSIONS:
        return _extract_pdf_text(path)
    return ""


def read_file_bytes(attachment: Attachment) -> bytes:
    path = Path(attachment.stored_path)
    return path.read_bytes() if path.exists() else b""


# ── Internal helpers ──────────────────────────────────────────────────────────

def _extract_pdf_text(path: Path) -> str:
    try:
        import PyPDF2
        with path.open("rb") as f:
            reader = PyPDF2.PdfReader(f)
            return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except Exception as exc:
        logger.error("FileService: PDF extraction failed: %s", exc)
        return ""


def _classify_file(ext: str) -> str:
    if ext in IMAGE_EXTENSIONS:
        return "image"
    if ext in PDF_EXTENSIONS:
        return "pdf"
    if ext in {".xlsx", ".xls", ".csv"}:
        return "excel"
    return "other"
