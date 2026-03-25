"""
Tax Compliance page — Ethiopian VAT (15% on income) and WHT (2% on expenses > 10,000 ETB).
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
page_header("Tax Compliance", "Ethiopian VAT (15%) on Income · WHT (2%) on Expenses > 10,000 ETB")

df = load_tax_data()

WHT_THRESHOLD = 10_000  # ETB

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
    auto_estimate = st.toggle("Auto-estimate where not on invoice", value=True,
        help="If VAT/WHT not explicitly on a receipt, estimate from the transaction amount.")

    st.markdown("---")
    st.info(
        "**Ethiopian Tax Law**\n\n"
        "- **VAT 15%** — on income/sales only\n"
        "- **WHT 2%** — on expense payments **> 10,000 ETB** only\n"
        "- Filing deadline: **30th** of following month\n"
        "- VAT registration threshold: **ETB 1,000,000/yr**"
    )

# ── Filter data ────────────────────────────────────────────────────────────────
fdf = df[df["transaction_date"].dt.year == sel_year].copy() if not df.empty else df.copy()
if sel_month != 0 and not fdf.empty:
    fdf = fdf[fdf["transaction_date"].dt.month == sel_month]
period_label = f"{sel_year}-{sel_month:02d}" if sel_month != 0 else str(sel_year)

income_df  = fdf[fdf["transaction_type"] == "income"].copy()
expense_df = fdf[fdf["transaction_type"] == "expense"].copy()

# ── VAT: income only ──────────────────────────────────────────────────────────
if auto_estimate:
    income_df["vat_used"] = income_df.apply(
        lambda r: r["vat_amount"] if r["vat_amount"] > 0 else r["amount"] * 0.15, axis=1
    )
else:
    income_df["vat_used"] = income_df["vat_amount"]

# ── WHT: expenses > 10,000 ETB only ──────────────────────────────────────────
eligible_expense = expense_df[expense_df["amount"] > WHT_THRESHOLD].copy()
if auto_estimate:
    eligible_expense["wht_used"] = eligible_expense.apply(
        lambda r: r["withholding_tax"] if r["withholding_tax"] > 0 else r["amount"] * 0.02, axis=1
    )
else:
    eligible_expense["wht_used"] = eligible_expense["withholding_tax"]

vat_total  = income_df["vat_used"].sum() if not income_df.empty else 0
wht_total  = eligible_expense["wht_used"].sum() if not eligible_expense.empty else 0
total_oblig = vat_total + wht_total

# ── Info banner ────────────────────────────────────────────────────────────────
if auto_estimate:
    st.info("💡 **Estimation ON** — VAT computed as 15% of income; WHT as 2% of expenses > 10,000 ETB where not explicitly on invoice.")

# ── KPI strip ──────────────────────────────────────────────────────────────────
k1, k2, k3, k4 = st.columns(4)
k1.metric("VAT on Income (15%)", f"{vat_total:,.2f} {currency}",
          help="15% of your sales revenue — remit to MoR")
k2.metric("WHT on Expenses (2%)", f"{wht_total:,.2f} {currency}",
          help="2% withheld from supplier payments > 10,000 ETB")
k3.metric("Expenses below WHT threshold", f"{len(expense_df) - len(eligible_expense)}",
          help=f"Expense transactions ≤ {WHT_THRESHOLD:,} ETB — WHT does not apply")
k4.metric("Total MoR Obligation", f"{total_oblig:,.2f} {currency}",
          help="VAT on income + WHT on large expenses")

divider()

# ── Charts ─────────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Tax Obligation Breakdown")
    fig = go.Figure(go.Bar(
        x=["VAT on Income (15%)", f"WHT on Expenses >10k (2%)"],
        y=[vat_total, wht_total],
        marker_color=["#e94560", "#3498db"],
        text=[f"{vat_total:,.0f}", f"{wht_total:,.0f}"],
        textposition="outside",
    ))
    fig.update_layout(yaxis_title=f"Amount ({currency})", height=300,
                      margin=dict(t=20, b=20), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    if sel_month == 0 and not fdf.empty:
        st.markdown("#### Monthly VAT on Income")
        income_df["month"] = income_df["transaction_date"].dt.month
        monthly_vat = income_df.groupby("month")["vat_used"].sum()
        month_labels = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        fig2 = go.Figure(go.Bar(
            x=month_labels,
            y=[monthly_vat.get(m, 0) for m in range(1, 13)],
            marker_color="#e94560",
        ))
        fig2.update_layout(yaxis_title=f"VAT ({currency})", height=300, margin=dict(t=20, b=20))
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.markdown("#### Tax Rule Summary")
        st.markdown(f"""
        | Transaction | VAT (15%) | WHT (2%) |
        |---|---|---|
        | **Income** | ✅ Applies — remit to MoR | ❌ Does not apply |
        | **Expense ≤ 10,000 ETB** | ❌ Does not apply | ❌ Does not apply |
        | **Expense > 10,000 ETB** | ❌ Does not apply | ✅ Withhold from supplier |
        """)

divider()

# ── VAT table (income only) ────────────────────────────────────────────────────
st.markdown("#### Income Transactions — VAT (15%)")
if income_df.empty:
    st.info("No income transactions for this period.")
else:
    disp = income_df.copy()
    disp["date"] = disp["transaction_date"].dt.strftime("%Y-%m-%d")
    disp["source"] = disp["vat_amount"].apply(lambda v: "From invoice" if v > 0 else "Estimated")
    cols = ["date", "amount", "vat_used", "currency", "counterparty", "description"]
    if auto_estimate:
        cols.insert(3, "source")
    st.dataframe(
        disp[cols].rename(columns={
            "date": "Date", "amount": f"Gross ({currency})",
            "vat_used": f"VAT 15% ({currency})", "source": "Source",
            "currency": "Curr", "counterparty": "Counterparty", "description": "Description",
        }),
        use_container_width=True, hide_index=True,
    )

divider()

# ── WHT table (expenses > 10,000 ETB only) ────────────────────────────────────
st.markdown(f"#### Expense Transactions — WHT (2%) — Only amounts > {WHT_THRESHOLD:,} ETB")
if eligible_expense.empty:
    st.success(f"✅ No expense transactions above {WHT_THRESHOLD:,} ETB — WHT does not apply.")
else:
    disp2 = eligible_expense.copy()
    disp2["date"] = disp2["transaction_date"].dt.strftime("%Y-%m-%d")
    disp2["net_paid"] = disp2["amount"] - disp2["wht_used"]
    disp2["source"] = disp2["withholding_tax"].apply(lambda v: "From invoice" if v > 0 else "Estimated")
    cols2 = ["date", "amount", "wht_used", "net_paid", "currency", "counterparty", "description"]
    if auto_estimate:
        cols2.insert(3, "source")
    st.dataframe(
        disp2[cols2].rename(columns={
            "date": "Date", "amount": f"Gross ({currency})",
            "wht_used": f"WHT 2% ({currency})", "source": "Source",
            "net_paid": f"Net Paid ({currency})", "currency": "Curr",
            "counterparty": "Supplier", "description": "Description",
        }),
        use_container_width=True, hide_index=True,
    )

if not expense_df[expense_df["amount"] <= WHT_THRESHOLD].empty:
    skipped = expense_df[expense_df["amount"] <= WHT_THRESHOLD]
    st.caption(f"ℹ️ {len(skipped)} expense transaction(s) ≤ {WHT_THRESHOLD:,} ETB excluded — WHT does not apply.")

divider()

# ── Filing checklist ───────────────────────────────────────────────────────────
st.markdown("#### MoR Filing Summary")
c1, c2 = st.columns(2)
with c1:
    est = " _(est.)_" if auto_estimate else ""
    st.markdown(f"""
    | Obligation | Amount ({currency}){est} | Due |
    |---|---|---|
    | VAT on income | **{vat_total:,.2f}** | 30th next month |
    | WHT on large expenses | **{wht_total:,.2f}** | 30th next month |
    | **Total to MoR** | **{total_oblig:,.2f}** | |
    """)
with c2:
    if total_oblig > 0:
        st.warning(
            f"⚠️ **{total_oblig:,.2f} {currency}** due to MoR for **{period_label}**.\n\n"
            "Bring to your MoR branch:\n"
            "- VAT declaration form (for income VAT)\n"
            "- Withholding tax schedule (for WHT)\n"
            "- Supporting invoices"
        )
    else:
        st.success(f"✅ No tax obligation for {period_label}.")
