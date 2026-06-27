#!/usr/bin/env python3
"""
Categorize existing transactions based on counterparty name and description.

This script assigns counterparty_category to transactions that don't have one yet,
using keyword matching based on Proclamation 979/2008 exemptions.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import get_db_context
from app.models.transaction import Transaction

# Exemption keywords mapped to categories
CATEGORY_KEYWORDS = {
    "government": ["dars", "dire", "addis", "government", "federal", "regional", "ministry",
                   "authority", "revenue", "customs", "immigration", "police", "defense",
                   "parliament", "senate", "council", "public", "state", "administration", "agency"],
    "transport": ["fly", "flight", "air", "airline", "aviation", "plane", "aircraft",
                  "train", "railway", "bus", "coach", "transport", "travel", "tour", "ticket"],
    "utilities": ["electricity", "electric", "power", "telecom", "phone", "water", "utility"],
    "healthcare": ["hospital", "clinic", "medical", "doctor", "pharma", "medicine", "vaccine",
                   "health", "lab", "laboratory", "nurse", "dentist", "dental"],
    "education": ["school", "university", "college", "education", "training", "course", "academy"],
    "agriculture": ["farm", "farmer", "agricultural", "crop", "livestock", "dairy", "pastoral"],
    "fuel": ["fuel", "petrol", "diesel", "gas", "gasoline"],
    "residential": ["residential", "housing", "rent", "apartment", "house", "dwelling", "home"],
}

def categorize_transaction(counterparty_name: str, description: str) -> str | None:
    """Determine category based on counterparty name and description."""
    text_to_check = f"{str(counterparty_name).lower()} {str(description).lower()}"

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_to_check:
                return category

    return None

def main():
    print("\n" + "="*70)
    print("Categorizing Existing Transactions")
    print("="*70 + "\n")

    updated_count = 0
    skipped_count = 0
    error_count = 0

    try:
        with get_db_context() as db:
            # Get transactions without counterparty_category
            transactions = db.query(Transaction).filter(
                Transaction.counterparty_category.is_(None)
            ).all()

            total = len(transactions)
            print(f"📊 Found {total} transactions without categories\n")

            for idx, txn in enumerate(transactions, 1):
                try:
                    counterparty_name = txn.counterparty.name if txn.counterparty else ""
                    description = txn.description or ""

                    category = categorize_transaction(counterparty_name, description)

                    if category:
                        txn.counterparty_category = category
                        db.add(txn)
                        updated_count += 1
                        print(f"✅ [{idx}/{total}] {counterparty_name:40} → {category:15} (desc: {description[:40]})")
                    else:
                        skipped_count += 1
                        print(f"⏭️  [{idx}/{total}] {counterparty_name:40} → No match (desc: {description[:40]})")

                except Exception as e:
                    error_count += 1
                    print(f"❌ [{idx}/{total}] Error: {e}")

            db.commit()

        print("\n" + "="*70)
        print(f"✅ Updated: {updated_count}")
        print(f"⏭️  Skipped (no match): {skipped_count}")
        print(f"❌ Errors: {error_count}")
        print("="*70 + "\n")

        if updated_count > 0:
            print("📝 Categories Applied:")
            print("  🏛️  Government: Exempt from WHT")
            print("  ✈️  Transport: Exempt from WHT")
            print("  🏥 Healthcare: Exempt from WHT")
            print("  🎓 Education: Exempt from WHT")
            print("  💡 Utilities: Exempt from WHT")
            print("  🌾 Agriculture: Exempt from WHT")
            print("  ⛽ Fuel: Exempt from WHT")
            print("  🏠 Residential: Exempt from WHT")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
