"""
Seed script — creates the default company and category tree for Helias AI.

Run standalone:
    python scripts/seed_data.py

Or call seed(db) from application code.
"""
from __future__ import annotations

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db_context, init_db
from app.models.category import Category
from app.models.company import Company

logger = logging.getLogger(__name__)


# ── Category definitions ──────────────────────────────────────────────────────
# Format: (name, type, parent_name_or_None)
CATEGORIES = [
    # Income
    ("Consulting", "income", None),
    ("AI Products", "income", None),
    ("Training", "income", None),
    ("Research", "income", None),
    ("Other Income", "income", None),

    # Expenses
    ("Cloud & API Costs", "expense", None),
    ("Software Subscriptions", "expense", None),
    ("Hosting", "expense", None),
    ("Contractors", "expense", None),
    ("Salaries", "expense", None),
    ("Internet & Telecom", "expense", None),
    ("Travel", "expense", None),
    ("Marketing", "expense", None),
    ("Legal & Accounting", "expense", None),
    ("Equipment", "expense", None),
    ("Office Supplies", "expense", None),
    ("Other Expenses", "expense", None),

    # Transfer
    ("Internal Transfer", "transfer", None),
]


def seed(db: Session) -> Company:
    """Create company + categories. Safe to call if they already exist."""
    # Company
    company = db.query(Company).filter(Company.slug == "helias-ai").first()
    if not company:
        company = Company(
            name=settings.default_company_name,
            slug="helias-ai",
            base_currency=settings.default_company_currency,
            country="Ethiopia",
            fiscal_year_start_month=7,
        )
        db.add(company)
        db.flush()
        logger.info("Created company: %s (id=%d)", company.name, company.id)
    else:
        logger.info("Company already exists: %s", company.name)

    # Categories
    existing_names = {
        c.name.lower()
        for c in db.query(Category).filter(Category.company_id == company.id).all()
    }
    created = 0
    for name, cat_type, _ in CATEGORIES:
        if name.lower() not in existing_names:
            cat = Category(company_id=company.id, name=name, type=cat_type)
            db.add(cat)
            created += 1

    db.flush()
    if created:
        logger.info("Created %d categories.", created)

    return company


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    init_db()
    with get_db_context() as db:
        company = seed(db)
        name, cid = company.name, company.id
    print(f"\n✅ Seed complete. Company: {name} (id={cid})")
    print("Now set your TELEGRAM_BOT_TOKEN in .env and run: python -m app.main")
