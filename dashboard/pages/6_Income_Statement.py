"""
Income Statement (Profit & Loss) — Helias FinPilot Dashboard
Ethiopian Fiscal Year aware: Hamle 1 (≈8 Jul) → Sene 30 (≈7 Jul)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.db import load_financial_data, load_company
from dashboard.components import page_header

st.set_page_config(page_title="Income Statement · FinPilot", page_icon="📊", layout="wide")

# ── Ethiopian FY helpers ──────────────────────────────────────────────────────
def et_fy(date: pd.Timestamp) -> int:
    """Return Ethiopian fiscal year (e.g. 2018) for a Gregorian date."""
    return date.year - 2007 if date.month >= 7 else date.year - 2008

def fy_label(fy: int) -> str:
    return f"FY{fy} E.C.  ({fy + 2007}/07/08 – {fy + 2008}/07/07)"

# ── Company & data ────────────────────────────────────────────────────────────
company      = load_company()
currency     = company.get("base_currency", "ETB") if company else "ETB"
company_name = company.get("name", "Helias AI and Analytics PLC") if company else "Helias AI and Analytics PLC"

page_header("Income Statement", "Profit & Loss — Ethiopian Fiscal Year")

df_all = load_financial_data()

if df_all.empty:
    st.info("No confirmed transactions yet.")
    st.stop()

df_all["et_fy"] = df_all["transaction_date"].apply(et_fy)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Period")
    available_fy = sorted(df_all["et_fy"].dropna().unique().astype(int), reverse=True)
    fy = st.selectbox("Ethiopian Fiscal Year", available_fy,
                      format_func=fy_label, index=0)
    view = st.radio("View", ["Annual", "Monthly breakdown"])

# ── Filter ────────────────────────────────────────────────────────────────────
df = df_all[df_all["et_fy"] == fy].copy()

# Exclude financing transfers from P&L
df = df[df["activity_type"].isin(["operating", "investing"]) &
        df["transaction_type"].isin(["income", "expense"])]

income_df  = df[df["transaction_type"] == "income"]
expense_df = df[df["transaction_type"] == "expense"]

revenue   = income_df["amount"].sum()
expenses  = expense_df["amount"].sum()

# Depreciation allowance (20% pool on equipment) — Ethiopian pool method
equip_cost = expense_df[
    expense_df["description"].str.contains("laptop|device|furniture|equip|computer",
                                            case=False, na=False)
]["amount"].sum()
depreciation = round(equip_cost * 0.20, 2)

# Adjust: remove equipment CAPEX from opex if tagged as investing
capex_df = df[df["activity_type"] == "investing"]
opex_df  = expense_df[expense_df["activity_type"] == "operating"]
opex     = opex_df["amount"].sum()

pbt       = revenue - opex - depreciation
tax_gross = round(max(pbt, 0) * 0.30, 2)
wht_credit = income_df["withholding_tax"].sum()
tax_net   = round(max(tax_gross - wht_credit, 0), 2)
npat      = round(pbt - tax_gross, 2)

# ── KPI strip ─────────────────────────────────────────────────────────────────
st.subheader(f"{company_name}  —  {fy_label(fy)}")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Revenue",        f"{revenue:,.0f} {currency}")
c2.metric("Expenses",       f"{opex + depreciation:,.0f} {currency}")
c3.metric("Profit (pre-tax)", f"{pbt:,.0f} {currency}")
c4.metric("Tax to pay",     f"{tax_net:,.0f} {currency}",
          help="30% on taxable profit − WHT credit")
c5.metric("Net profit",     f"{npat:,.0f} {currency}",
          delta=f"{npat/revenue*100:.1f}% margin" if revenue else "—")

st.divider()

# ── Formal P&L table ──────────────────────────────────────────────────────────
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Formal Statement")

    def _row(label, amount, bold=False, indent=False):
        p = "  " if indent else ""
        if bold:
            return f"| **{p}{label}** | **{amount:,.2f}** |"
        return f"| {p}{label} | {amount:,.2f} |"

    lines = [
        f"| Item | {currency} |", "|---|---:|",
        _row("REVENUE", revenue, bold=True),
    ]
    for _, r in income_df.iterrows():
        lines.append(_row(r.get("counterparty") or r.get("description", "—")[:40],
                          r["amount"], indent=True))
    lines += ["|  |  |", _row("OPERATING EXPENSES", opex + depreciation, bold=True)]
    if not opex_df.empty:
        for cat, grp in opex_df.groupby("category"):
            lines.append(_row(cat or "Uncategorised", grp["amount"].sum(), indent=True))
    lines.append(_row("Depreciation — equipment (20% pool)", depreciation, indent=True))
    lines += [
        "|  |  |",
        _row("NET PROFIT BEFORE TAX", pbt, bold=True),
        _row("Income tax expense  (@30%)", -tax_gross, indent=True),
        _row("  Less: WHT credit (withheld by clients)", -wht_credit, indent=True),
        "|  |  |",
        _row("NET PROFIT AFTER TAX", npat, bold=True),
    ]
    st.markdown("\n".join(lines))

with col_right:
    st.subheader("Waterfall")
    cats = opex_df.groupby("category")["amount"].sum().sort_values(ascending=False)
    x  = ["Revenue"] + [c or "Other" for c in cats.index] + ["Depreciation"] + ["Net Profit"]
    m  = ["absolute"] + ["relative"] * len(cats) + ["relative"] + ["total"]
    y  = [revenue] + [-v for v in cats.values] + [-depreciation] + [npat]
    fig = go.Figure(go.Waterfall(
        orientation="v", measure=m, x=x, y=y,
        connector={"line": {"color": "#aaa"}},
        increasing={"marker": {"color": "#27ae60"}},
        decreasing={"marker": {"color": "#e74c3c"}},
        totals={"marker": {"color": "#2980b9"}},
    ))
    fig.update_layout(title=fy_label(fy), yaxis_title=currency,
                      showlegend=False, height=460)
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Monthly breakdown ─────────────────────────────────────────────────────────
if view == "Monthly breakdown" and not df.empty:
    st.subheader("Monthly Breakdown")
    monthly = (df.groupby([df["transaction_date"].dt.to_period("M"), "transaction_type"])
               ["amount"].sum().unstack(fill_value=0).reset_index())
    monthly["month"] = monthly["transaction_date"].astype(str)
    fig2 = go.Figure()
    if "income" in monthly.columns:
        fig2.add_trace(go.Bar(name="Income", x=monthly["month"],
                              y=monthly["income"], marker_color="#27ae60"))
    if "expense" in monthly.columns:
        fig2.add_trace(go.Bar(name="Expenses", x=monthly["month"],
                              y=monthly["expense"], marker_color="#e74c3c"))
    fig2.update_layout(barmode="group", height=340, yaxis_title=currency)
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── Detail tables ─────────────────────────────────────────────────────────────
ca, cb = st.columns(2)
with ca:
    st.subheader(f"Income  ({len(income_df)} lines)")
    if not income_df.empty:
        st.dataframe(income_df[["transaction_date","counterparty","amount"]]
                     .assign(Date=income_df["transaction_date"].dt.strftime("%Y-%m-%d"))
                     [["Date","counterparty","amount"]]
                     .rename(columns={"counterparty":"From","amount":currency})
                     .sort_values(currency, ascending=False),
                     use_container_width=True, hide_index=True)
with cb:
    st.subheader(f"Expenses  ({len(opex_df)} lines)")
    if not opex_df.empty:
        st.dataframe(opex_df[["transaction_date","counterparty","amount"]]
                     .assign(Date=opex_df["transaction_date"].dt.strftime("%Y-%m-%d"))
                     [["Date","counterparty","amount"]]
                     .rename(columns={"counterparty":"To","amount":currency})
                     .sort_values(currency, ascending=False),
                     use_container_width=True, hide_index=True)

st.divider()

# ── Download ──────────────────────────────────────────────────────────────────
report_path = Path(__file__).parent.parent.parent / "reports" / f"fy{fy}" / \
              f"Helias_FY{fy}_Financial_Report_ETB.xlsx"
if report_path.exists():
    st.download_button(
        f"⬇️  Download FY{fy} Excel Report",
        report_path.read_bytes(),
        file_name=report_path.name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
csv = df[["transaction_date","transaction_type","counterparty","category",
          "amount","currency","description"]].copy()
csv["transaction_date"] = csv["transaction_date"].dt.strftime("%Y-%m-%d")
st.download_button("⬇️  Download CSV", csv.to_csv(index=False),
                   file_name=f"is_fy{fy}.csv", mime="text/csv")
