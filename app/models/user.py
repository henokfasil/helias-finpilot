from __future__ import annotations

from typing import List, Optional
from sqlalchemy import String, Boolean, BigInteger, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    telegram_username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="admin")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    company: Mapped["Company"] = relationship("Company", back_populates="users")
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="created_by", lazy="select")

    def __repr__(self) -> str:
        return f"<User id={self.id} telegram_id={self.telegram_id}>"
