from __future__ import annotations

from typing import Optional
from sqlalchemy import String, Text, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class AuditLog(Base, TimestampMixin):
    """Immutable audit trail. Records are never deleted or modified."""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    transaction_id: Mapped[Optional[int]] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    user_telegram_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    action: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[Optional[int]] = mapped_column(nullable=True)
    before_state: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    after_state: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    transaction: Mapped[Optional["Transaction"]] = relationship("Transaction", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action!r}>"
