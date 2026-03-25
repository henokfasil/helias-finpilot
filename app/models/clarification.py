from __future__ import annotations

from typing import Optional
from sqlalchemy import String, Text, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class ClarificationRequest(Base, TimestampMixin):
    __tablename__ = "clarification_requests"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transaction_id: Mapped[Optional[int]] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    telegram_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")

    transaction: Mapped[Optional["Transaction"]] = relationship(
        "Transaction", back_populates="clarification_requests"
    )

    def __repr__(self) -> str:
        return f"<ClarificationRequest id={self.id} field={self.field_name!r}>"
