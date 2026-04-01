from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import String, Numeric, Date, Text, Boolean, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Transaction(Base, TimestampMixin):
    """
    Core financial record.  Raw input is always preserved.
    Status lifecycle: draft → confirmed | needs_clarification | rejected
    """
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    created_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"), nullable=True)
    counterparty_id: Mapped[Optional[int]] = mapped_column(ForeignKey("counterparties.id"), nullable=True)

    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    transaction_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)       # Gregorian
    transaction_date_et: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # Ethiopian "DD/MM/YYYY EC"
    entry_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    amount_base: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    exchange_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6), nullable=True)

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payment_method: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    reference_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_tax_relevant: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Cash Flow classification ──────────────────────────────────────────────
    # operating (default) | investing | financing
    activity_type: Mapped[str] = mapped_column(String(20), default="operating")

    # ── Ethiopian tax fields ──────────────────────────────────────────────────
    vat_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    withholding_tax: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    is_vat_inclusive: Mapped[bool] = mapped_column(Boolean, default=False)

    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(30), default="telegram")

    ai_confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4), nullable=True)
    ai_ambiguity_flags: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(30), default="draft")

    is_duplicate: Mapped[bool] = mapped_column(Boolean, default=False)
    duplicate_of_id: Mapped[Optional[int]] = mapped_column(ForeignKey("transactions.id"), nullable=True)

    company: Mapped["Company"] = relationship("Company", back_populates="transactions")
    created_by: Mapped[Optional["User"]] = relationship("User", back_populates="transactions")
    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="transactions")
    counterparty: Mapped[Optional["Counterparty"]] = relationship("Counterparty", back_populates="transactions")
    attachments: Mapped[List["Attachment"]] = relationship("Attachment", back_populates="transaction", lazy="select")
    audit_logs: Mapped[List["AuditLog"]] = relationship("AuditLog", back_populates="transaction", lazy="select")
    clarification_requests: Mapped[List["ClarificationRequest"]] = relationship(
        "ClarificationRequest", back_populates="transaction", lazy="select"
    )
    duplicate_of: Mapped[Optional["Transaction"]] = relationship(
        "Transaction", remote_side="Transaction.id", foreign_keys="Transaction.duplicate_of_id"
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction id={self.id} type={self.transaction_type!r} "
            f"amount={self.amount} {self.currency} status={self.status!r}>"
        )
