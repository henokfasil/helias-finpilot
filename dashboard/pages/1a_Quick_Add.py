"""
Quick Add Transaction — Record expenses/income with WHT category classification.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import date
import streamlit as st
import pandas as pd
from decimal import Decimal

from app.models.transaction import Transaction
from app.models.counterparty import Counterparty
from dashboard.db import load_company
from dashboard.components import page_header, divider
from app.database import get_db_context
from app.config import settings

st.set_page_config(page_title="Quick Add · FinPilot", page_icon="➕", layout="wide")

company = load_company()
currency = company.get("base_currency", "ETB") if company else "ETB"

page_header("Quick Add Transaction", "Record expenses & income with WHT category for accurate tax compliance")

# Category options based on Proclamation 979/2008 exemptions
COUNTERPARTY_CATEGORIES = [
    ("unknown", "❓ Not Sure (Keyword Matching)"),
    ("government", "🏛️ Government Service"),
    ("transport", "✈️ Transport (Flights, Trains, Tours)"),
    ("healthcare", "🏥 Healthcare (Hospital, Doctor, Medicine)"),
    ("education", "🎓 Education (School, University, Training)"),
    ("utilities", "💡 Utilities (Electricity, Telecom, Water)"),
    ("agriculture", "🌾 Agriculture (Farm, Crops, Livestock)"),
    ("fuel", "⛽ Fuel (Petrol, Diesel, Gas)"),
    ("residential", "🏠 Residential Property"),
    ("business", "💼 Business (Regular Business Transaction)"),
]

with st.form("quick_add_form", border=True):
    st.markdown("### Transaction Details")

    col1, col2 = st.columns(2)
    with col1:
        txn_type = st.radio("Type", ["income", "expense"], index=1, horizontal=True)
        amount = st.number_input("Amount", min_value=0.0, step=100.0)

    with col2:
        txn_date = st.date_input("Date", value=date.today())
        currency_sel = st.selectbox("Currency", ["ETB", "USD", "EUR"])

    st.markdown("---")
    st.markdown("### Counterparty & Description")

    col3, col4 = st.columns(2)
    with col3:
        counterparty = st.text_input("Counterparty Name", placeholder="e.g., FLY BETTER TOUR & TRAVEL PLC, Ministry of Revenue, etc.")
    with col4:
        description = st.text_area("Description", placeholder="e.g., Flight ticket to Cairo, Government office rent, etc.", height=100)

    st.markdown("---")
    st.markdown("### **⚠️ WHT Classification (For Tax Compliance)**")
    st.markdown("""
    **Important**: Selecting the correct category ensures the transaction is classified properly under Proclamation 979/2008.

    ✅ **Exempt from WHT** (3%): Government, Transport, Healthcare, Education, Utilities, Agriculture, Fuel, Residential
    ❌ **Taxable** (3% WHT): Business payments above threshold
    """)

    category_select = st.selectbox(
        "What type of payment is this?",
        options=[cat[0] for cat in COUNTERPARTY_CATEGORIES],
        format_func=lambda x: next((cat[1] for cat in COUNTERPARTY_CATEGORIES if cat[0] == x), x),
        help="Choose the correct category for automatic tax calculation"
    )

    st.markdown("---")
    st.markdown("### Additional Details")

    col5, col6, col7 = st.columns(3)
    with col5:
        payment_method = st.selectbox("Payment Method", ["bank_transfer", "cash", "check", "card", "other"])
    with col6:
        reference = st.text_input("Reference #", placeholder="Invoice, check #, etc.")
    with col7:
        vat_amount = st.number_input("VAT Amount (if any)", min_value=0.0, step=10.0)

    # For expenses: show WHT info
    if txn_type == "expense" and amount > 10000:
        st.warning(
            f"⚠️ **WHT Calculation**: This {amount:,.0f} {currency_sel} payment to **{category_select or 'business'}** "
            f"is {'✅ EXEMPT' if category_select != 'business' else '❌ SUBJECT to 3% WHT'}"
        )

    st.markdown("---")
    submitted = st.form_submit_button("✅ Save Transaction", use_container_width=True, type="primary")

    if submitted:
        if not counterparty or not amount:
            st.error("❌ Please fill in counterparty and amount")
        else:
            try:
                with get_db_context() as db:
                    # Get or create counterparty
                    cp = db.query(Counterparty).filter(
                        Counterparty.name.ilike(counterparty),
                        Counterparty.company_id == company["id"]
                    ).first()

                    if not cp:
                        cp = Counterparty(
                            name=counterparty,
                            type="vendor" if txn_type == "expense" else "customer",
                            company_id=company["id"]
                        )
                        db.add(cp)
                        db.flush()

                    # Create transaction
                    txn = Transaction(
                        company_id=company["id"],
                        transaction_type=txn_type,
                        transaction_date=txn_date,
                        amount=Decimal(str(amount)),
                        currency=currency_sel,
                        description=description,
                        counterparty_id=cp.id,
                        payment_method=payment_method,
                        reference_number=reference if reference else None,
                        vat_amount=Decimal(str(vat_amount)) if vat_amount > 0 else None,
                        counterparty_category=category_select if category_select != "unknown" else None,
                        status="confirmed",
                        source="dashboard"
                    )
                    db.add(txn)
                    db.commit()

                st.success(
                    f"✅ Transaction saved!\n\n"
                    f"**{txn_type.upper()}**: {amount:,.0f} {currency_sel} "
                    f"to {counterparty}\n\n"
                    f"**Category**: {next((cat[1] for cat in COUNTERPARTY_CATEGORIES if cat[0] == category_select), category_select)}\n\n"
                    f"{'✅ EXEMPT from WHT' if category_select != 'business' else '❌ Subject to 3% WHT (if > 10k)'}"
                )

            except Exception as e:
                st.error(f"❌ Error saving transaction: {e}")

st.markdown("---")
st.markdown("""
### 📚 Tax Rules Reminder
Per **Proclamation 979/2008** (Withholding Tax):
- **Government services**: Exempt ✅
- **Transport**: Exempt (flights, trains, tours) ✅
- **Healthcare**: Exempt (hospitals, medicines, doctors) ✅
- **Education**: Exempt (schools, universities) ✅
- **Utilities**: Exempt (electricity, water, telecom) ✅
- **Agriculture**: Exempt (farm products) ✅
- **Fuel**: Exempt ✅
- **Residential**: Exempt (house sales, rentals) ✅
- **Business payments**: 3% WHT if > 10,000 ETB ❌

👉 Correctly categorizing transactions ensures accurate tax compliance!
""")
