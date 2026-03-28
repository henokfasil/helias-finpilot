"""
Income Statement (Profit & Loss) — Helias FinPilot Dashboard
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.db import load_financial_data, load_company

st.set_page_config(page_title="Income Statement", page_icon="📊", layout="wide")
st.title("📊 Income Statement (Profit & Loss)")

company = load_company()
currency = company.get("base_currency", "ETB")
company_name = company.get("name", "Your Company")

# ── Sidebar controls ──────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Period")
    all_years = list(range(2023, 2030))
    year = st.selectbox("Year", all_years, index=all_years.index(2026) if 2026 in all_years else 0)
    view = st.radio("View", ["Annual", "Monthly"])
    month = None
    if view == "Monthly":
        month = st.selectbox(
            "Month",
            range(1, 13),
            format_func=lambda m: pd.Timestamp(2026, m, 1).strftime("%B"),
            index=pd.Timestamp.now().month - 1,
        )

# ── Load data ────────────────────────────────────────────────────────────────
df = load_financial_data()

if df.empty:
    st.info("No confirmed transactions yet. Confirm some transactions in the bot first.")
    st.stop()

# Filter by period
df = df[df["transaction_date"].dt.year == year]
if month:
    df = df[df["transaction_date"].dt.month == month]

income_df = df[df["transaction_type"] == "income"]
expense_df = df[df["transaction_type"] == "expense"]

revenue = income_df["amount"].sum()
expenses = expense_df["amount"].sum()
gross_profit = revenue - expenses
vat_obligation = income_df["vat_amount"].sum()
wht_obligation = expense_df[expense_df["amount"] > 10000]["withholding_tax"].sum()
net_profit = gross_profit  # tax is separate obligation, not deducted from ops

period_label = f"{year}" if not month else pd.Timestamp(year, month, 1).strftime("%B %Y")

# ── KPI strip ─────────────────────────────────────────────────────────────────
st.subheader(f"{company_name} — {period_label}")
col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Revenue", f"{revenue:,.0f} {currency}")
col2.metric("💸 Total Expenses", f"{expenses:,.0f} {currency}", delta=f"{-expenses:,.0f}")
col3.metric(
    "📈 Net Profit / Loss",
    f"{net_profit:,.0f} {currency}",
    delta=f"{net_profit:,.0f}",
    delta_color="normal",
)
col4.metric("📉 Profit Margin", f"{(net_profit/revenue*100):.1f}%" if revenue > 0 else "—")

st.divider()

# ── Formal P&L Table ─────────────────────────────────────────────────────────
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Formal Statement")

    def _row(label, amount, bold=False, indent=False):
        prefix = "  " if indent else ""
        if bold:
            return f"| **{prefix}{label}** | **{amount:,.2f}** |"
        return f"| {prefix}{label} | {amount:,.2f} |"

    lines = [
        "| Item | Amount ({}) |".format(currency),
        "|---|---:|",
        _row("REVENUE", revenue, bold=True),
        _row("Sales / Service Income", revenue, indent=True),
        "|  |  |",
        _row("OPERATING EXPENSES", expenses, bold=True),
    ]

    # Expenses by category
    if not expense_df.empty:
        for cat, grp in expense_df.groupby("category"):
            cat_name = cat if cat else "Uncategorised"
            lines.append(_row(cat_name, grp["amount"].sum(), indent=True))

    lines += [
        "|  |  |",
        _row("GROSS PROFIT / (LOSS)", gross_profit, bold=True),
        "|  |  |",
        "| **TAX OBLIGATIONS** (separate, remit to MoR) | |",
        _row("VAT Payable (15% of income)", vat_obligation, indent=True),
        _row("WHT Payable (2% on exp. > 10k)", wht_obligation, indent=True),
        "|  |  |",
        _row("NET PROFIT / (LOSS)", net_profit, bold=True),
    ]

    st.markdown("\n".join(lines))

with col_right:
    # Waterfall chart
    st.subheader("Waterfall")

    # Expense breakdown for chart
    expense_cats = (
        expense_df.groupby("category")["amount"].sum().sort_values(ascending=False)
        if not expense_df.empty
        else pd.Series(dtype=float)
    )

    x_labels = ["Revenue"] + [c if c else "Uncategorised" for c in expense_cats.index] + ["Net Profit"]
    measure = ["absolute"] + ["relative"] * len(expense_cats) + ["total"]
    values = [revenue] + [-v for v in expense_cats.values] + [net_profit]
    colors = ["#2ecc71"] + ["#e74c3c"] * len(expense_cats) + (["#2ecc71"] if net_profit >= 0 else ["#e74c3c"])

    fig = go.Figure(go.Waterfall(
        name="P&L",
        orientation="v",
        measure=measure,
        x=x_labels,
        y=values,
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#2ecc71"}},
        decreasing={"marker": {"color": "#e74c3c"}},
        totals={"marker": {"color": "#3498db"}},
    ))
    fig.update_layout(
        title=f"P&L Waterfall — {period_label}",
        yaxis_title=currency,
        showlegend=False,
        height=450,
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── Monthly trend (annual view only) ─────────────────────────────────────────
if not month and not df.empty:
    st.subheader("Monthly Trend")
    monthly = (
        df.groupby([df["transaction_date"].dt.month, "transaction_type"])["amount"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
        .rename(columns={"transaction_date": "month"})
    )
    monthly["month_label"] = monthly["month"].apply(
        lambda m: pd.Timestamp(year, int(m), 1).strftime("%b")
    )
    fig2 = go.Figure()
    if "income" in monthly.columns:
        fig2.add_trace(go.Bar(name="Income", x=monthly["month_label"], y=monthly["income"],
                              marker_color="#2ecc71"))
    if "expense" in monthly.columns:
        fig2.add_trace(go.Bar(name="Expenses", x=monthly["month_label"], y=monthly["expense"],
                              marker_color="#e74c3c"))
    net_by_month = monthly.get("income", 0) - monthly.get("expense", 0)
    fig2.add_trace(go.Scatter(name="Net Profit", x=monthly["month_label"], y=net_by_month,
                               mode="lines+markers", line=dict(color="#3498db", width=2)))
    fig2.update_layout(barmode="group", height=350, yaxis_title=currency)
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── Transaction detail tables ────────────────────────────────────────────────
col_a, col_b = st.columns(2)
with col_a:
    st.subheader(f"Income ({len(income_df)} transactions)")
    if not income_df.empty:
        st.dataframe(
            income_df[["transaction_date", "counterparty", "category", "amount", "currency"]]
            .rename(columns={"transaction_date": "Date", "counterparty": "From",
                             "category": "Category", "amount": "Amount", "currency": "CCY"})
            .assign(Date=lambda d: d["Date"].dt.strftime("%Y-%m-%d"))
            .sort_values("Amount", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

with col_b:
    st.subheader(f"Expenses ({len(expense_df)} transactions)")
    if not expense_df.empty:
        st.dataframe(
            expense_df[["transaction_date", "counterparty", "category", "amount", "currency"]]
            .rename(columns={"transaction_date": "Date", "counterparty": "To",
                             "category": "Category", "amount": "Amount", "currency": "CCY"})
            .assign(Date=lambda d: d["Date"].dt.strftime("%Y-%m-%d"))
            .sort_values("Amount", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

# ── CSV export ───────────────────────────────────────────────────────────────
st.divider()
csv = df[["transaction_date", "transaction_type", "counterparty", "category",
          "amount", "currency", "description"]].copy()
csv["transaction_date"] = csv["transaction_date"].dt.strftime("%Y-%m-%d")
st.download_button(
    "⬇️ Download CSV",
    csv.to_csv(index=False),
    file_name=f"income_statement_{period_label.replace(' ', '_')}.csv",
    mime="text/csv",
)
