"""
Migration: Financial Statements Extension
==========================================
Adds:
  1. `activity_type` column to transactions table (operating/investing/financing)
  2. `account_snapshots` table (for Balance Sheet manual entries)

Run on:
  - Local SQLite:    python scripts/migrate_financial_statements.py
  - Supabase (VPS):  python scripts/migrate_financial_statements.py
                     (uses DATABASE_URL from .env or environment)

Safe to run multiple times — skips if already applied.
"""
import sys
import os
from pathlib import Path

# Ensure project root on path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import text
from app.database import engine
from app.models import Base  # noqa — ensures all models are registered


def column_exists(conn, table: str, column: str) -> bool:
    """Works for both SQLite and PostgreSQL."""
    db_url = str(engine.url)
    if "sqlite" in db_url:
        result = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        return any(row[1] == column for row in result)
    else:
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = :tbl AND column_name = :col"
        ), {"tbl": table, "col": column}).fetchone()
        return result is not None


def table_exists(conn, table: str) -> bool:
    db_url = str(engine.url)
    if "sqlite" in db_url:
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=:t"
        ), {"t": table}).fetchone()
        return result is not None
    else:
        result = conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name = :t"
        ), {"t": table}).fetchone()
        return result is not None


def run_migration():
    with engine.begin() as conn:
        # 1. Add activity_type to transactions
        if not column_exists(conn, "transactions", "activity_type"):
            print("Adding activity_type column to transactions...")
            conn.execute(text(
                "ALTER TABLE transactions ADD COLUMN activity_type VARCHAR(20) DEFAULT 'operating'"
            ))
            print("  ✅ Done.")
        else:
            print("  ⏭ activity_type already exists — skipping.")

        # 2. Create account_snapshots table
        if not table_exists(conn, "account_snapshots"):
            print("Creating account_snapshots table...")
            conn.execute(text("""
                CREATE TABLE account_snapshots (
                    id               SERIAL PRIMARY KEY,
                    company_id       INTEGER NOT NULL REFERENCES companies(id),
                    account_name     VARCHAR(150) NOT NULL,
                    account_type     VARCHAR(20)  NOT NULL,
                    account_subtype  VARCHAR(40),
                    amount           NUMERIC(18, 2) NOT NULL,
                    currency         VARCHAR(3)   DEFAULT 'ETB',
                    entry_date       DATE         NOT NULL,
                    notes            TEXT,
                    is_active        BOOLEAN      DEFAULT true,
                    created_at       TIMESTAMP    DEFAULT now(),
                    updated_at       TIMESTAMP    DEFAULT now()
                )
            """) if "postgresql" in str(engine.url) else text("""
                CREATE TABLE account_snapshots (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    company_id       INTEGER NOT NULL REFERENCES companies(id),
                    account_name     VARCHAR(150) NOT NULL,
                    account_type     VARCHAR(20)  NOT NULL,
                    account_subtype  VARCHAR(40),
                    amount           NUMERIC(18, 2) NOT NULL,
                    currency         VARCHAR(3)   DEFAULT 'ETB',
                    entry_date       DATE         NOT NULL,
                    notes            TEXT,
                    is_active        BOOLEAN      DEFAULT 1,
                    created_at       DATETIME     DEFAULT CURRENT_TIMESTAMP,
                    updated_at       DATETIME     DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("  ✅ Done.")
        else:
            print("  ⏭ account_snapshots already exists — skipping.")

    print("\n✅ Migration complete. Financial statements are ready.")
    print("\nNext steps:")
    print("  1. Restart the bot:  sudo systemctl restart finpilot")
    print("  2. Push to GitHub:   git add -A && git commit -m 'feat: financial statements' && git push")
    print("  3. Streamlit will auto-deploy the new pages (6, 7, 8).")
    print("  4. Add opening balances / equipment in account_snapshots table (see Balance Sheet page).")


if __name__ == "__main__":
    run_migration()
