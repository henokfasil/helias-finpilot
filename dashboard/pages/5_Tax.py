"""
Tax Compliance page — Ethiopian VAT (15%) and WHT (3%).
Based on: Proclamations 1341/2016 (VAT), 979/2008, 983/2008, 1395/2017 (WHT).
Source: Ministry of Revenues official documentation.

Key Rules:
- VAT: 15% on all income/sales
- WHT: 3% on domestic payments (goods > 20k, services > 10k)
- Exemptions: Transport, utilities, healthcare, education, government, agriculture, fuel
- Registration: Mandatory at 2M ETB, voluntary at 1M ETB
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import date
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from dashboard.db import load_tax_data, load_company
from dashboard.components import page_header, divider

st.set_page_config(page_title="Tax · FinPilot", page_icon="🧾", layout="wide")

company = load_company()
currency = company.get("base_currency", "ETB") if company else "ETB"
page_header("Tax Compliance", "Ethiopian VAT (15%) on Income · WHT (3%) on Expenses per Proclamations 1341/2016, 979/2008, 1395/2017")

df = load_tax_data()

# ── WHT Configuration ──────────────────────────────────────────────────────────
WHT_RATE = 0.03  # 3%
WHT_THRESHOLD_GOODS = 20_000  # ETB
WHT_THRESHOLD_SERVICES = 10_000  # ETB

# Keyword-based exemptions per Proclamation 979/2008, Section 3.3.6
WHT_EXEMPT_KEYWORDS = [
    "fly", "flight", "air", "airline", "aviation", "plane", "aircraft",
    "train", "railway", "bus", "coach", "transport", "travel", "tour", "ticket",
    "electricity", "electric", "power", "telecom", "phone", "water", "utility",
    "hospital", "clinic", "medical", "doctor", "pharma", "medicine", "vaccine", "health",
    "school", "university", "college", "education", "training", "course",
    "government", "federal", "regional", "ministry", "office", "public",
    "farm", "farmer", "agricultural", "crop", "livestock", "dairy",
    "fuel", "petrol", "diesel", "gas",
]

def is_exempt_from_wht(description, counterparty):
    """Check if transaction is exempt from WHT."""
    text = f"{str(description).lower()} {str(counterparty).lower()}"
    return any(keyword in text for keyword in WHT_EXEMPT_KEYWORDS)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Period")
    available_years = sorted(
        df["transaction_date"].dt.year.dropna().unique().astype(int).tolist(), reverse=True
    ) if not df.empty else [date.today().year]

    sel_year = st.selectbox("Year", available_years, index=0)
    month_map = {0: "Full Year", 1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
                 5: "May", 6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep",
                 10: "Oct", 11: "Nov", 12: "Dec"}
    sel_month = st.selectbox("Month", list(month_map.keys()), format_func=lambda m: month_map[m])

    st.markdown("---")
    auto_estimate = st.toggle("Auto-estimate VAT/WHT from amounts", value=True,
        help="If not explicitly on invoice, calculate from transaction amount")

    st.markdown("---")
    with st.expander("📋 **Tax Rules (Master Blueprint)**"):
        st.markdown("""
        ## **VAT (15%)** — Proclamation 1341/2016
        - **Applies to**: All income/sales
        - **Registration**: Mandatory if > 2,000,000 ETB; Voluntary if > 1,000,000 ETB
        - **Filing**: Last day of following month
        - **Exemptions**: Food, utilities (≤200 kWh), healthcare, education, housing, government

        ## **WHT (3%)** — Proclamations 979/2008, 1395/2017
        - **Goods**: 3% if transaction > 20,000 ETB
        - **Services**: 3% if transaction > 10,000 ETB
        - **Non-compliant**: 30% (if no TIN + valid license)

        ### Exemptions (NO WHT):
        - Transport (flights, trains, buses, tours, tickets)
        - Utilities (electricity, telecom, water)
        - Healthcare (hospitals, doctors, medicines)
        - Education (schools, universities)
        - Government services
        - Agriculture (farm products)
        - Fuel (petrol, diesel)
        - Residential sales

        ### Compliance
        - **Remittance**: Within 30 days of month-end
        - **Penalties**: 10% for non-compliance, 5% for late filing
        """)

# ── Filter Data ────────────────────────────────────────────────────────────────
fdf = df[df["transaction_date"].dt.year == sel_year].copy() if not df.empty else df.copy()
if sel_month != 0 and not fdf.empty:
    fdf = fdf[fdf["transaction_date"].dt.month == sel_month]

income_df = fdf[fdf["transaction_type"] == "income"].copy()
expense_df = fdf[fdf["transaction_type"] == "expense"].copy()

# ── VAT Calculation (15% on income) ────────────────────────────────────────────
if auto_estimate:
    income_df["vat_used"] = income_df.apply(
        lambda r: r["vat_amount"] if r["vat_amount"] > 0 else r["amount"] * 0.15, axis=1
    )
else:
    income_df["vat_used"] = income_df["vat_amount"]

vat_total = income_df["vat_used"].sum() if not income_df.empty else 0

# ── WHT Calculation with Exemptions ────────────────────────────────────────────
def is_eligible_for_wht(row):
    """Check if expense qualifies for WHT (not exempt, above threshold)."""
    # Check exemption first
    if is_exempt_from_wht(row.get("description", ""), row.get("counterparty", "")):
        return False
    # Check amount threshold
    return row["amount"] > WHT_THRESHOLD_SERVICES

# Split into taxable and exempt
expense_df["wht_eligible"] = expense_df.apply(is_eligible_for_wht, axis=1)
taxable_expense = expense_df[expense_df["wht_eligible"]].copy()
exempt_expense = expense_df[~expense_df["wht_eligible"]].copy()

# Calculate WHT on taxable expenses
if auto_estimate:
    taxable_expense["wht_used"] = taxable_expense.apply(
        lambda r: r["withholding_tax"] if r["withholding_tax"] > 0 else r["amount"] * WHT_RATE, axis=1
    )
else:
    taxable_expense["wht_used"] = taxable_expense["withholding_tax"]

wht_total = taxable_expense["wht_used"].sum() if not taxable_expense.empty else 0
total_obligation = vat_total + wht_total

# ── Summary Banner ────────────────────────────────────────────────────────────
if auto_estimate:
    st.info(f"💡 **Auto-Estimation ON** — VAT: 15% of income; WHT: {WHT_RATE*100:.0f}% of taxable expenses where not on invoice. Exempt transactions excluded.")

# ── KPI Metrics ────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("VAT on Income (15%)", f"{vat_total:,.2f} {currency}",
          help="15% of sales revenue — due within 30 days")
k2.metric("WHT on Expenses (3%)", f"{wht_total:,.2f} {currency}",
          help="3% on payments above thresholds (20k goods, 10k services)")
k3.metric("Exempt Transactions", f"{len(exempt_expense)}",
          help="Transport, utilities, healthcare, education, government, etc.")
k4.metric("Total MoR Obligation", f"{total_obligation:,.2f} {currency}",
          help="VAT + WHT due within 30 days of month-end")

divider()

# ── Income VAT Section ─────────────────────────────────────────────────────────
st.markdown("#### Income Transactions — VAT (15%)")
if income_df.empty:
    st.info("No income transactions for this period.")
else:
    disp_income = income_df.copy()
    disp_income["date"] = disp_income["transaction_date"].dt.strftime("%Y-%m-%d")
    disp_income["source"] = disp_income["vat_amount"].apply(lambda v: "From invoice" if v > 0 else "Estimated")
    cols_income = ["date", "amount", "vat_used", "currency", "counterparty", "description"]
    if auto_estimate:
        cols_income.insert(3, "source")
    st.dataframe(
        disp_income[cols_income].rename(columns={
            "date": "Date", "amount": f"Gross ({currency})",
            "vat_used": f"VAT 15% ({currency})", "source": "Source",
            "currency": "Curr", "counterparty": "Counterparty", "description": "Description",
        }),
        use_container_width=True, hide_index=True,
    )

divider()

# ── Taxable Expenses (WHT applies) ─────────────────────────────────────────────
st.markdown(f"#### Expense Transactions — WHT (3%) — {len(taxable_expense)} taxable items")
if taxable_expense.empty:
    st.success("✅ No taxable expenses — WHT does not apply.")
else:
    disp_taxable = taxable_expense.copy()
    disp_taxable["date"] = disp_taxable["transaction_date"].dt.strftime("%Y-%m-%d")
    disp_taxable["net_paid"] = disp_taxable["amount"] - disp_taxable["wht_used"]
    disp_taxable["source"] = disp_taxable["withholding_tax"].apply(lambda v: "From invoice" if v > 0 else "Estimated")
    cols_taxable = ["date", "amount", "wht_used", "net_paid", "currency", "counterparty", "description"]
    if auto_estimate:
        cols_taxable.insert(3, "source")
    st.dataframe(
        disp_taxable[cols_taxable].rename(columns={
            "date": "Date", "amount": f"Gross ({currency})",
            "wht_used": f"WHT 3% ({currency})", "source": "Source",
            "net_paid": f"Net Paid ({currency})", "currency": "Curr",
            "counterparty": "Supplier", "description": "Description",
        }),
        use_container_width=True, hide_index=True,
    )

divider()

# ── Exempt Transactions (WHT does NOT apply) ──────────────────────────────────
st.markdown(f"#### Exempt Transactions — NO WHT ({len(exempt_expense)} items)")
if exempt_expense.empty:
    st.success("✅ No exempt transactions.")
else:
    disp_exempt = exempt_expense.copy()
    disp_exempt["date"] = disp_exempt["transaction_date"].dt.strftime("%Y-%m-%d")
    cols_exempt = ["date", "amount", "currency", "counterparty", "description"]
    st.dataframe(
        disp_exempt[cols_exempt].rename(columns={
            "date": "Date", "amount": f"Amount ({currency})",
            "currency": "Curr", "counterparty": "Party", "description": "Category/Description",
        }),
        use_container_width=True, hide_index=True,
    )
    st.caption("✅ Exempt per Proclamation 979/2008: Transport, utilities, healthcare, education, government, agriculture, fuel, residential")

divider()

# ── MoR Filing Summary ─────────────────────────────────────────────────────────
st.markdown("#### MoR Filing Summary (Due within 30 days of month-end)")
c1, c2 = st.columns(2)
with c1:
    est = " _(est.)_" if auto_estimate else ""
    st.markdown(f"""
    | Obligation | Amount ({currency}){est} |
    |---|---|
    | VAT on Income (15%) | **{vat_total:,.2f}** |
    | WHT on Taxable Expenses (3%) | **{wht_total:,.2f}** |
    | **Total to MoR** | **{total_obligation:,.2f}** |
    """)
with c2:
    if total_obligation > 0:
        st.warning(
            f"⚠️ **{total_obligation:,.2f} {currency}** due to Ministry of Revenues\n\n"
            "**Documents to file:**\n"
            "- VAT declaration form\n"
            "- WHT remittance schedule\n"
            "- Supporting invoices & receipts"
        )
    else:
        st.success("✅ No tax obligation for this period.")
