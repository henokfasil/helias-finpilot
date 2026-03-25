from __future__ import annotations

from typing import List, Optional
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)  # income | expense | transfer
    parent_id: Mapped[Optional[int]] = mapped_column(ForeignKey("categories.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    company: Mapped["Company"] = relationship("Company", back_populates="categories")
    transactions: Mapped[List["Transaction"]] = relationship("Transaction", back_populates="category", lazy="select")
    subcategories: Mapped[List["Category"]] = relationship(
        "Category", back_populates="parent", lazy="select"
    )
    parent: Mapped[Optional["Category"]] = relationship(
        "Category", back_populates="subcategories", remote_side="Category.id"
    )

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name!r} type={self.type!r}>"
