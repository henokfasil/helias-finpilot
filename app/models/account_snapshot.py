"""
AccountSnapshot — manually-entered Balance Sheet items.

Used for assets, liabilities, and equity entries that cannot be
derived from income/expense transactions alone. Examples:
  - Owner's capital injection
  - Equipment purchased (fixed asset)
  - Bank loan received
  - Opening cash balance

These items complete the Balance Sheet alongside computed figures
(cash derived from transactions, VAT/WHT payables, retained earnings).
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Numeric, Date, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class AccountSnapshot(Base, TimestampMixin):
    __tablename__ = "account_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)

    account_name: Mapped[str] = mapped_column(String(150), nullable=False)
    # asset | liability | equity
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # Sub-type for grouping in Balance Sheet
    # asset:     current_asset | fixed_asset | other_asset
    # liability: current_liability | long_term_liability
    # equity:    capital | retained_earnings
    account_subtype: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)

    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="ETB")
    entry_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    company: Mapped["Company"] = relationship("Company", back_populates="account_snapshots")

    def __repr__(self) -> str:
        return (
            f"<AccountSnapshot id={self.id} name={self.account_name!r} "
            f"type={self.account_type!r} amount={self.amount} {self.currency}>"
        )
