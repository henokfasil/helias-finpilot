from __future__ import annotations

from typing import Optional
from sqlalchemy import String, Text, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class Attachment(Base, TimestampMixin):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transaction_id: Mapped[Optional[int]] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)

    original_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    telegram_file_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extraction_method: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)

    transaction: Mapped[Optional["Transaction"]] = relationship("Transaction", back_populates="attachments")

    def __repr__(self) -> str:
        return f"<Attachment id={self.id} file={self.original_filename!r}>"
