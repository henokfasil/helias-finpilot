from __future__ import annotations

from typing import List, Optional
from sqlalchemy import String, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class Company(Base, TimestampMixin):
    """
    Tenant entity. Every piece of financial data belongs to a company.
    Designed for future multi-tenant SaaS expansion.
    """
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), default="ETB", nullable=False)
    country: Mapped[str] = mapped_column(String(100), default="Ethiopia", nullable=False)
    fiscal_year_start_month: Mapped[int] = mapped_column(default=7)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    users: Mapped[List["User"]] = relationship("User", back_populates="company", lazy="select")
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="company", lazy="select")
    categories: Mapped[List["Category"]] = relationship("Category", back_populates="company", lazy="select")
    counterparties: Mapped[List["Counterparty"]] = relationship("Counterparty", back_populates="company", lazy="select")
    reports: Mapped[List["Report"]] = relationship("Report", back_populates="company", lazy="select")
    account_snapshots: Mapped[List["AccountSnapshot"]] = relationship("AccountSnapshot", back_populates="company", lazy="select")

    def __repr__(self) -> str:
        return f"<Company id={self.id} name={self.name!r}>"
