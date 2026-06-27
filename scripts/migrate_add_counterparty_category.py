#!/usr/bin/env python3
"""
Migration: Add counterparty_category column to transactions table.

This script adds support for explicit payment category classification
to enable accurate WHT exemption application per Proclamation 979/2008.

Categories: government, transport, healthcare, education, utilities,
            agriculture, fuel, residential, business
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text, inspect
from app.database import engine, get_db_context
from app.config import settings

def check_column_exists(column_name: str, table_name: str = "transactions") -> bool:
    """Check if column already exists."""
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns

def migrate_sqlite():
    """Migrate SQLite database."""
    print("🔄 Migrating SQLite database...")
    with get_db_context() as db:
        if not check_column_exists("counterparty_category"):
            db.execute(text(
                "ALTER TABLE transactions ADD COLUMN counterparty_category VARCHAR(30) NULL"
            ))
            print("✅ Added counterparty_category column to transactions table")
        else:
            print("ℹ️  counterparty_category column already exists")

def migrate_postgresql():
    """Migrate PostgreSQL/Supabase database."""
    print("🔄 Migrating PostgreSQL database...")
    with get_db_context() as db:
        if not check_column_exists("counterparty_category"):
            db.execute(text(
                "ALTER TABLE transactions ADD COLUMN counterparty_category VARCHAR(30) NULL"
            ))
            print("✅ Added counterparty_category column to transactions table")
        else:
            print("ℹ️  counterparty_category column already exists")

def main():
    print("\n" + "="*60)
    print("Migration: Add counterparty_category to transactions")
    print("="*60 + "\n")

    db_url = settings.database_url

    try:
        if "sqlite" in db_url:
            migrate_sqlite()
        elif "postgres" in db_url:
            migrate_postgresql()
        else:
            print(f"❌ Unsupported database: {db_url}")
            sys.exit(1)

        print("\n✅ Migration completed successfully!")
        print("\nNew transaction recordings can now include counterparty_category:")
        print("  - government")
        print("  - transport")
        print("  - healthcare")
        print("  - education")
        print("  - utilities")
        print("  - agriculture")
        print("  - fuel")
        print("  - residential")
        print("  - business")
        print("  - null (unknown)")

    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
