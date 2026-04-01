"""
Migration: add transaction_date_et column and fix existing Ethiopian calendar dates.

Run once on the production DB:
    python scripts/migrate_et_dates.py

What it does:
  1. Adds column  transaction_date_et VARCHAR(20)  to the transactions table
     (safe to re-run — skips if column already exists)
  2. For each existing transaction:
     a. If transaction_date year is 2010–2020 (Ethiopian calendar leaked into DB):
        - Treats the stored date as an Ethiopian date
        - Computes the correct Gregorian date  →  updates transaction_date
        - Stores the original ET string        →  sets  transaction_date_et
     b. If transaction_date year is > 2020 (already Gregorian):
        - Computes the Ethiopian equivalent    →  sets  transaction_date_et
        - Leaves transaction_date unchanged
"""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datetime import date
from sqlalchemy import create_engine, text
from app.config import settings
from app.utils.ethiopian_calendar import (
    gregorian_to_et_string,
    ethiopian_to_gregorian,
    is_ethiopian_year,
)


def run_migration() -> None:
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    )

    with engine.begin() as conn:
        # ── Step 1: add column if not present ────────────────────────────────
        # PostgreSQL
        if "sqlite" not in settings.database_url:
            existing = conn.execute(text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'transactions'
                  AND column_name = 'transaction_date_et'
            """)).fetchone()
            if not existing:
                conn.execute(text(
                    "ALTER TABLE transactions ADD COLUMN transaction_date_et VARCHAR(20)"
                ))
                print("✅ Column transaction_date_et added.")
            else:
                print("ℹ️  Column transaction_date_et already exists.")
        else:
            # SQLite: recreate is complex — just try adding
            try:
                conn.execute(text(
                    "ALTER TABLE transactions ADD COLUMN transaction_date_et VARCHAR(20)"
                ))
                print("✅ Column transaction_date_et added (SQLite).")
            except Exception:
                print("ℹ️  Column transaction_date_et already exists (SQLite).")

        # ── Step 2: fetch all transactions with a date ────────────────────────
        rows = conn.execute(text(
            "SELECT id, transaction_date FROM transactions WHERE transaction_date IS NOT NULL"
        )).fetchall()

        print(f"\nProcessing {len(rows)} transactions…\n")

        fixed_et = 0
        computed_et = 0
        skipped = 0

        updates = []   # (new_gregorian_date, et_string, tx_id)

        for row in rows:
            tx_id = row[0]
            stored_date = row[1]

            # SQLAlchemy may return date or string depending on driver
            if isinstance(stored_date, str):
                try:
                    stored_date = date.fromisoformat(stored_date)
                except ValueError:
                    print(f"  ⚠️  ID {tx_id}: cannot parse date '{stored_date}' — skipping")
                    skipped += 1
                    continue

            if stored_date is None:
                skipped += 1
                continue

            if is_ethiopian_year(stored_date.year):
                # The stored date is actually an Ethiopian date — fix it
                try:
                    gregorian = ethiopian_to_gregorian(
                        stored_date.year, stored_date.month, stored_date.day
                    )
                    et_string = f"{stored_date.day:02d}/{stored_date.month:02d}/{stored_date.year} EC"
                    updates.append((gregorian, et_string, tx_id))
                    print(
                        f"  🔄 ID {tx_id}: {stored_date} (ET) → {gregorian} (GR)  [{et_string}]"
                    )
                    fixed_et += 1
                except Exception as e:
                    print(f"  ⚠️  ID {tx_id}: ET→GR conversion failed: {e}")
                    skipped += 1
            else:
                # Already Gregorian — just compute ET equivalent
                try:
                    et_string = gregorian_to_et_string(stored_date)
                    updates.append((stored_date, et_string, tx_id))
                    computed_et += 1
                except Exception as e:
                    print(f"  ⚠️  ID {tx_id}: GR→ET conversion failed: {e}")
                    skipped += 1

        # ── Step 3: apply updates ─────────────────────────────────────────────
        for gregorian_date, et_string, tx_id in updates:
            conn.execute(text("""
                UPDATE transactions
                   SET transaction_date    = :gdate,
                       transaction_date_et = :etstr
                 WHERE id = :tid
            """), {"gdate": gregorian_date, "etstr": et_string, "tid": tx_id})

        print(f"\n{'─'*50}")
        print(f"✅ Fixed ET→GR dates:   {fixed_et}")
        print(f"✅ Computed ET strings:  {computed_et}")
        print(f"⚠️  Skipped:             {skipped}")
        print(f"{'─'*50}")
        print("Migration complete.")


if __name__ == "__main__":
    run_migration()
