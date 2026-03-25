from __future__ import annotations

from typing import Optional
from sqlalchemy import String, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    report_type: Mapped[str] = mapped_column(String(30), nullable=False)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    generated_by_telegram_id: Mapped[Optional[int]] = mapped_column(nullable=True)

    company: Mapped["Company"] = relationship("Company", back_populates="reports")

    def __repr__(self) -> str:
        return f"<Report id={self.id} type={self.report_type!r} year={self.period_year}>"
