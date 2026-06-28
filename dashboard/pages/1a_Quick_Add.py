"""
Quick Add Transaction — Fast entry form for recording income/expenses with tax categorization.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import date
import streamlit as st
from decimal import Decimal

from app.models.transaction import Transaction
from app.models.counterparty import Counterparty
from dashboard.db import load_company
from dashboard.components import page_header, divider
from app.database import get_db_context

st.set_page_config(page_title="Quick Add · FinPilot", page_icon="➕", layout="wide")

company = load_company()
currency = company.get("base_currency", "ETB") if company else "ETB"

page_header("Quick Add Transaction", "Record transactions quickly with automatic tax categorization")

divider()

# Category options per Proclamation 979/2008
CATEGORIES = {
    "government": ("🏛️ Government", "Exempt"),
    "transport": ("✈️ Transport", "Exempt"),
    "healthcare": ("🏥 Healthcare", "Exempt"),
    "education": ("🎓 Education", "Exempt"),
    "utilities": ("💡 Utilities", "Exempt"),
    "agriculture": ("🌾 Agriculture", "Exempt"),
    "fuel": ("⛽ Fuel", "Exempt"),
    "residential": ("🏠 Residential", "Exempt"),
    "business": ("💼 Business", "3% WHT (if > 10k)"),
}

# Main form
with st.form("quick_add_txn", border=False):
    st.subheader("Transaction Details")

    # Row 1: Type and Amount
    col1, col2 = st.columns([1, 2])
    with col1:
        txn_type = st.radio("**Type**", ["income", "expense"], index=1, horizontal=True)
    with col2:
        amount = st.number_input(
            "**Amount**",
            min_value=0.01,
            step=100.0,
            format="%.2f",
            help="Transaction amount"
        )

    # Row 2: Date and Currency
    col3, col4 = st.columns(2)
    with col3:
        txn_date = st.date_input("**Date**", value=date.today())
    with col4:
        currency_sel = st.selectbox("**Currency**", ["ETB", "USD", "EUR"], index=0)

    st.divider()
    st.subheader("Counterparty & Details")

    # Row 3: Counterparty and Description
    counterparty = st.text_input(
        "**Counterparty Name**",
        placeholder="e.g., FLY BETTER TOUR, Ministry of Revenue, Ethio Bank",
        help="Who you paid or received from"
    )

    description = st.text_area(
        "**Description**",
        placeholder="e.g., Flight to Cairo, Monthly rent, Equipment purchase",
        height=80,
        help="What the transaction was for"
    )

    # Row 4: Payment method and reference
    col5, col6 = st.columns(2)
    with col5:
        payment_method = st.selectbox(
            "**Payment Method**",
            ["bank_transfer", "cash", "check", "card", "other"],
            help="How was the payment made"
        )
    with col6:
        reference = st.text_input(
            "**Reference #** (Optional)",
            placeholder="Invoice, check #, transaction ID",
            help="For tracking purposes"
        )

    st.divider()
    st.subheader("🏛️ Tax Category (Per Proclamation 979/2008)")

    st.info(
        "**Select the category that best describes this transaction.** This determines whether WHT applies.\n\n"
        "**Exempt categories** (no WHT): Government, Transport, Healthcare, Education, Utilities, Agriculture, Fuel, Residential\n\n"
        "**Taxable** (3% WHT if > 10,000 ETB): Business transactions"
    )

    category = st.selectbox(
        "**Transaction Category**",
        options=list(CATEGORIES.keys()),
        format_func=lambda x: f"{CATEGORIES[x][0]} — {CATEGORIES[x][1]}",
        help="Choose the correct category for accurate tax calculation"
    )

    # Show WHT warning if applicable
    if txn_type == "expense" and amount > 10000 and category == "business":
        st.warning(
            f"⚠️ **WHT Will Apply**: {amount:,.2f} {currency_sel} to {counterparty or 'unknown'} "
            f"will be subject to 3% WHT ({amount * 0.03:,.2f} {currency_sel})"
        )
    elif txn_type == "expense" and category != "business":
        st.success(
            f"✅ **Exempt from WHT**: {counterparty or 'Transaction'} "
            f"({CATEGORIES[category][0]}) does not require WHT"
        )

    st.divider()

    # Submit button
    col_submit, col_cancel = st.columns(2)
    with col_submit:
        submitted = st.form_submit_button("✅ Save Transaction", use_container_width=True, type="primary")
    with col_cancel:
        st.form_submit_button("Cancel", use_container_width=True)

    if submitted:
        # Validation
        if not counterparty or not counterparty.strip():
            st.error("❌ Counterparty name is required")
            st.stop()

        if amount <= 0:
            st.error("❌ Amount must be greater than 0")
            st.stop()

        try:
            with get_db_context() as db:
                # Get or create counterparty
                cp = db.query(Counterparty).filter(
                    Counterparty.name.ilike(counterparty.strip()),
                    Counterparty.company_id == company["id"]
                ).first()

                if not cp:
                    cp = Counterparty(
                        name=counterparty.strip(),
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
                    description=description.strip() if description else None,
                    counterparty_id=cp.id,
                    payment_method=payment_method,
                    reference_number=reference.strip() if reference else None,
                    counterparty_category=category,
                    status="confirmed",
                    source="dashboard"
                )
                db.add(txn)
                db.commit()

            # Success feedback
            st.success("✅ Transaction saved successfully!")
            st.toast(f"{txn_type.title()}: {amount:,.2f} {currency_sel}", icon="✅")

            # Clear form by rerunning (Streamlit limitation)
            st.rerun()

        except Exception as e:
            st.error(f"❌ Failed to save transaction: {str(e)}")

# Help section
with st.expander("📚 Tax Rules Reference", expanded=False):
    st.markdown("""
    ### **WHT Exemptions (Per Proclamation 979/2008)**

    The following categories are **NOT subject to WHT**:
    - 🏛️ **Government** — Government offices, ministries, DARS, etc.
    - ✈️ **Transport** — Flights, trains, buses, tours, tickets
    - 🏥 **Healthcare** — Hospitals, doctors, medicines, vaccines
    - 🎓 **Education** — Schools, universities, training programs
    - 💡 **Utilities** — Electricity, telecom, water services
    - 🌾 **Agriculture** — Farm products, crops, livestock
    - ⛽ **Fuel** — Petrol, diesel, gasoline
    - 🏠 **Residential** — House sales and rentals

    ### **WHT Applies To**
    - 💼 **Business Payments**: 3% WHT if the single transaction is > 10,000 ETB

    ### **Key Rules**
    - **Filing deadline**: 30 days after month-end to Ministry of Revenues
    - **Threshold**: Goods > 20,000 ETB, Services > 10,000 ETB
    - **Non-compliant suppliers**: 30% WHT (if no TIN + valid license)
    """)
