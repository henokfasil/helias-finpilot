from __future__ import annotations

from typing import List, Optional
from sqlalchemy import String, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class Counterparty(Base, TimestampMixin):
    __tablename__ = "counterparties"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="unknown")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    company: Mapped["Company"] = relationship("Company", back_populates="counterparties")
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="counterparty", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Counterparty id={self.id} name={self.name!r}>"
