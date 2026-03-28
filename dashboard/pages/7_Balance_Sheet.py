"""
Balance Sheet (Statement of Financial Position) — Helias FinPilot Dashboard

ASSETS = LIABILITIES + EQUITY

Computed automatically from:
  - Confirmed transactions (cash, VAT payable, WHT payable, retained earnings)
  - Manual AccountSnapshot entries (equipment, loans, owner's capital, etc.)

To add manual entries (equipment, loans, etc.), use the bot:
  /add_asset, /add_liability, /add_equity  — coming in next release
  or ask Henok to insert them directly into the account_snapshots table.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from dashboard.db import load_financial_data, load_account_snapshots, load_company

st.set_page_config(page_title="Balance Sheet", page_icon="⚖️", layout="wide")
st.title("⚖️ Balance Sheet")
st.caption("Statement of Financial Position — Assets = Liabilities + Equity")

company = load_company()
currency = company.get("base_currency", "ETB")
company_name = company.get("name", "Your Company")

# ── Sidebar: as-of date ───────────────────────────────────────────────────────
with st.sidebar:
    st.header("As of Date")
    as_of = st.date_input("Balance Sheet date", value=pd.Timestamp.now().date())
    st.info(
        "**How it works**\n\n"
        "Cash is computed from all confirmed transactions up to the selected date.\n\n"
        "VAT Payable and WHT Payable are derived from transaction tax fields.\n\n"
        "To add assets (equipment), liabilities (loans), or equity (capital injection), "
        "insert into the `account_snapshots` table — a UI is coming soon."
    )

# ── Load data ────────────────────────────────────────────────────────────────
df = load_financial_data()
snaps = load_account_snapshots()

# Filter transactions up to as_of date
if not df.empty:
    df = df[df["transaction_date"].dt.date <= as_of]

income_df = df[df["transaction_type"] == "income"] if not df.empty else pd.DataFrame()
expense_df = df[df["transaction_type"] == "expense"] if not df.empty else pd.DataFrame()

# ── Computed figures ─────────────────────────────────────────────────────────
total_income = income_df["amount"].sum() if not income_df.empty else 0.0
total_expenses = expense_df["amount"].sum() if not expense_df.empty else 0.0
retained_earnings = total_income - total_expenses

vat_payable = income_df["vat_amount"].sum() if not income_df.empty else 0.0
wht_payable = (
    expense_df[expense_df["amount"] > 10000]["withholding_tax"].sum()
    if not expense_df.empty else 0.0
)

# ── Manual AccountSnapshot entries ──────────────────────────────────────────
def _snap_items(snap_df: pd.DataFrame, account_type: str) -> list[dict]:
    if snap_df.empty:
        return []
    rows = snap_df[snap_df["account_type"] == account_type]
    return [
        {"name": r["account_name"], "amount": r["amount"],
         "subtype": r.get("account_subtype", "") or "", "notes": r.get("notes", "") or ""}
        for _, r in rows.iterrows()
    ]

asset_snaps = _snap_items(snaps, "asset")
liability_snaps = _snap_items(snaps, "liability")
equity_snaps = _snap_items(snaps, "equity")

# Opening cash from snapshots (cash/bank type)
opening_cash = sum(
    s["amount"] for s in asset_snaps
    if "cash" in s["name"].lower() or "bank" in s["name"].lower()
)
non_cash_assets = [s for s in asset_snaps
                   if "cash" not in s["name"].lower() and "bank" not in s["name"].lower()]

computed_cash = opening_cash + total_income - total_expenses

# ── Totals ───────────────────────────────────────────────────────────────────
total_assets = computed_cash + sum(s["amount"] for s in non_cash_assets)
total_liabilities = vat_payable + wht_payable + sum(s["amount"] for s in liability_snaps)
total_equity = retained_earnings + sum(s["amount"] for s in equity_snaps)
total_L_plus_E = total_liabilities + total_equity
difference = total_assets - total_L_plus_E
is_balanced = abs(difference) < 0.50

# ── Balance check banner ─────────────────────────────────────────────────────
if is_balanced:
    st.success(f"✅ Balance Sheet is balanced — As of {as_of}")
else:
    st.warning(
        f"⚠️ Difference of {difference:,.2f} {currency} between Assets and L+E. "
        "This is expected if you have assets or equity not yet recorded in account_snapshots "
        "(e.g. opening capital injection, fixed assets, outstanding loans)."
    )

st.subheader(f"{company_name} — {as_of}")
st.divider()

# ── Three-column layout ──────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)

# ASSETS
with col1:
    st.markdown("### 🏦 ASSETS")
    st.markdown(f"**Cash & Bank** &nbsp;&nbsp;&nbsp; `{computed_cash:,.2f} {currency}`")
    st.caption(f"↳ Opening {opening_cash:,.0f} + Income {total_income:,.0f} − Expenses {total_expenses:,.0f}")
    for s in non_cash_assets:
        st.markdown(f"**{s['name']}** &nbsp;&nbsp;&nbsp; `{s['amount']:,.2f} {currency}`")
        if s["notes"]:
            st.caption(f"↳ {s['notes']}")
    st.divider()
    st.markdown(f"### TOTAL ASSETS &nbsp;&nbsp;&nbsp; `{total_assets:,.2f} {currency}`")

# LIABILITIES
with col2:
    st.markdown("### 📋 LIABILITIES")
    if vat_payable > 0:
        st.markdown(f"**VAT Payable (15%)** &nbsp;&nbsp;&nbsp; `{vat_payable:,.2f} {currency}`")
        st.caption("↳ Remit to Ministry of Revenue")
    if wht_payable > 0:
        st.markdown(f"**WHT Payable (2%)** &nbsp;&nbsp;&nbsp; `{wht_payable:,.2f} {currency}`")
        st.caption("↳ Remit to Ministry of Revenue")
    for s in liability_snaps:
        st.markdown(f"**{s['name']}** &nbsp;&nbsp;&nbsp; `{s['amount']:,.2f} {currency}`")
        if s["notes"]:
            st.caption(f"↳ {s['notes']}")
    st.divider()
    st.markdown(f"### TOTAL LIABILITIES &nbsp;&nbsp;&nbsp; `{total_liabilities:,.2f} {currency}`")

# EQUITY
with col3:
    st.markdown("### 💼 EQUITY")
    for s in equity_snaps:
        st.markdown(f"**{s['name']}** &nbsp;&nbsp;&nbsp; `{s['amount']:,.2f} {currency}`")
        if s["notes"]:
            st.caption(f"↳ {s['notes']}")
    ret_sign = "+" if retained_earnings >= 0 else ""
    st.markdown(
        f"**Retained Earnings** &nbsp;&nbsp;&nbsp; `{ret_sign}{retained_earnings:,.2f} {currency}`"
    )
    st.caption(f"↳ Cumulative net profit from all transactions")
    st.divider()
    st.markdown(f"### TOTAL EQUITY &nbsp;&nbsp;&nbsp; `{total_equity:,.2f} {currency}`")
    st.markdown(f"### L + E &nbsp;&nbsp;&nbsp; `{total_L_plus_E:,.2f} {currency}`")

st.divider()

# ── Summary KPIs ─────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Assets", f"{total_assets:,.0f} {currency}")
k2.metric("Total Liabilities", f"{total_liabilities:,.0f} {currency}")
k3.metric("Total Equity", f"{total_equity:,.0f} {currency}")
debt_ratio = (total_liabilities / total_assets * 100) if total_assets > 0 else 0
k4.metric("Debt Ratio", f"{debt_ratio:.1f}%", help="Liabilities ÷ Assets × 100")

# ── Pie chart: composition of assets ─────────────────────────────────────────
st.divider()
col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    st.subheader("Asset Composition")
    asset_data = {"Cash & Bank": max(computed_cash, 0)}
    for s in non_cash_assets:
        asset_data[s["name"]] = s["amount"]
    if sum(asset_data.values()) > 0:
        fig = px.pie(
            names=list(asset_data.keys()),
            values=list(asset_data.values()),
            color_discrete_sequence=px.colors.sequential.Blues_r,
        )
        fig.update_traces(textinfo="label+percent")
        fig.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig, use_container_width=True)

with col_chart2:
    st.subheader("Funding Structure")
    funding_data = {}
    if total_liabilities > 0:
        funding_data["Liabilities"] = total_liabilities
    if total_equity > 0:
        funding_data["Equity"] = total_equity
    if sum(funding_data.values()) > 0:
        fig2 = px.pie(
            names=list(funding_data.keys()),
            values=list(funding_data.values()),
            color_discrete_map={"Liabilities": "#e74c3c", "Equity": "#2ecc71"},
        )
        fig2.update_traces(textinfo="label+percent")
        fig2.update_layout(showlegend=False, height=300)
        st.plotly_chart(fig2, use_container_width=True)

# ── Add manual items note ─────────────────────────────────────────────────────
st.divider()
with st.expander("➕ How to add Assets, Liabilities, or Equity entries"):
    st.markdown("""
    The Balance Sheet pulls from the `account_snapshots` table in your database.

    **Example SQL to add an owner's capital injection:**
    ```sql
    INSERT INTO account_snapshots (company_id, account_name, account_type, account_subtype, amount, currency, entry_date, notes, is_active)
    VALUES (1, 'Owner Capital Injection', 'equity', 'capital', 500000, 'ETB', '2026-01-01', 'Initial capital', true);
    ```

    **Example: add equipment as a fixed asset:**
    ```sql
    INSERT INTO account_snapshots (company_id, account_name, account_type, account_subtype, amount, currency, entry_date, notes, is_active)
    VALUES (1, 'Laptop & Equipment', 'asset', 'fixed_asset', 75000, 'ETB', '2026-03-01', 'MacBook + peripherals', true);
    ```

    A bot command `/add_asset` / `/add_liability` / `/add_equity` is on the roadmap.
    """)
