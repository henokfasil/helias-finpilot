"""
Helias FinPilot — Dashboard
Main page: Overview (KPIs + charts)

Run:
    streamlit run dashboard/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
from datetime import date
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from dashboard.db import load_transactions, load_company
from dashboard.components import page_header, kpi_card, divider

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Helias FinPilot",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.shields.io/badge/Helias-FinPilot-0f3460?style=for-the-badge", use_container_width=True)
    st.markdown("### Navigation")
    st.markdown("""
    - 🏠 **Overview** ← you are here
    - 📋 **Transactions**
    - 📊 **Reports**
    - 📎 **Receipts**
    - ⚙️ **Settings**
    """)
    divider_year = st.selectbox("Fiscal Year", options=list(range(date.today().year, 2023, -1)))
    st.caption("Data refreshes every 30 seconds.")

# ── Load data ─────────────────────────────────────────────────────────────────
company  = load_company()
all_txns = load_transactions()

company_name     = company.get("name", "Helias AI and Analytics")
base_currency    = company.get("base_currency", "ETB")

# Filter to selected year, confirmed only
if all_txns.empty:
    confirmed = all_txns.copy()
else:
    confirmed = all_txns[
        (all_txns["status"] == "confirmed") &
        (all_txns["transaction_date"].dt.year == divider_year)
    ]

income_df   = confirmed[confirmed["transaction_type"] == "income"]
expense_df  = confirmed[confirmed["transaction_type"] == "expense"]

total_income   = income_df["amount"].sum()
total_expenses = expense_df["amount"].sum()
net_result     = total_income - total_expenses
tx_count       = len(all_txns[all_txns["status"] != "rejected"]) if not all_txns.empty else 0
pending_count  = len(all_txns[all_txns["status"].isin(["draft", "needs_clarification"])]) if not all_txns.empty else 0

# ── Header ────────────────────────────────────────────────────────────────────
page_header(
    f"Financial Overview — {divider_year}",
    company_name,
)

# ── KPI Cards ─────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
with c1:
    kpi_card("Total Income", f"{total_income:,.0f} {base_currency}", color="#27ae60")
with c2:
    kpi_card("Total Expenses", f"{total_expenses:,.0f} {base_currency}", color="#e94560")
with c3:
    sign = "+" if net_result >= 0 else ""
    color = "#27ae60" if net_result >= 0 else "#e94560"
    kpi_card("Net Result", f"{sign}{net_result:,.0f} {base_currency}", color=color)
with c4:
    kpi_card("Transactions", str(tx_count), delta=f"⏳ {pending_count} pending" if pending_count else "", color="#0f3460")

st.markdown("<br>", unsafe_allow_html=True)

# ── Monthly bar chart ─────────────────────────────────────────────────────────
st.markdown("#### Monthly Income vs Expenses")

if not confirmed.empty:
    monthly = (
        confirmed.groupby([confirmed["transaction_date"].dt.month, "transaction_type"])["amount"]
        .sum()
        .reset_index()
    )
    monthly.columns = ["month", "type", "amount"]
    month_names = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                   7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
    monthly["month_name"] = monthly["month"].map(month_names)

    fig_bar = px.bar(
        monthly,
        x="month_name",
        y="amount",
        color="type",
        barmode="group",
        color_discrete_map={"income": "#27ae60", "expense": "#e94560", "transfer": "#f39c12"},
        labels={"amount": f"Amount ({base_currency})", "month_name": "Month", "type": "Type"},
        height=340,
    )
    fig_bar.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend_title_text="",
        margin=dict(l=0, r=0, t=10, b=0),
        font=dict(family="sans-serif", size=13),
        xaxis=dict(categoryorder="array", categoryarray=list(month_names.values())),
    )
    st.plotly_chart(fig_bar, use_container_width=True)
else:
    st.info("No confirmed transactions yet for this year.")

# ── Two charts side by side ───────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("#### Expenses by Category")
    if not expense_df.empty and expense_df["category"].notna().any():
        cat_df = (
            expense_df.groupby("category")["amount"]
            .sum()
            .reset_index()
            .sort_values("amount", ascending=False)
        )
        fig_pie = px.pie(
            cat_df,
            values="amount",
            names="category",
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Set3,
            height=320,
        )
        fig_pie.update_layout(
            margin=dict(l=0, r=0, t=10, b=0),
            showlegend=True,
            legend=dict(orientation="v", x=1, y=0.5),
            paper_bgcolor="white",
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No categorised expenses yet.")

with col_right:
    st.markdown("#### Income Sources")
    if not income_df.empty and income_df["counterparty"].notna().any():
        src_df = (
            income_df.groupby("counterparty")["amount"]
            .sum()
            .reset_index()
            .sort_values("amount", ascending=False)
            .head(8)
        )
        fig_hbar = px.bar(
            src_df,
            x="amount",
            y="counterparty",
            orientation="h",
            color_discrete_sequence=["#0f3460"],
            labels={"amount": f"Amount ({base_currency})", "counterparty": ""},
            height=320,
        )
        fig_hbar.update_layout(
            plot_bgcolor="white",
            paper_bgcolor="white",
            margin=dict(l=0, r=0, t=10, b=0),
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig_hbar, use_container_width=True)
    else:
        st.info("No income sources recorded yet.")

# ── Recent transactions ───────────────────────────────────────────────────────
st.markdown("#### Recent Transactions")
visible_txns = all_txns[all_txns["status"] != "rejected"] if not all_txns.empty else all_txns
if not visible_txns.empty:
    recent = visible_txns.head(10).copy()
    recent["date"]   = recent["transaction_date"].dt.strftime("%Y-%m-%d")
    recent["amount"] = recent.apply(lambda r: f"{r['amount']:,.2f} {r['currency']}", axis=1)
    st.dataframe(
        recent[["date", "transaction_type", "amount", "counterparty", "category", "description", "status"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "transaction_type": st.column_config.TextColumn("Type"),
            "counterparty":     st.column_config.TextColumn("Counterparty"),
            "category":         st.column_config.TextColumn("Category"),
            "description":      st.column_config.TextColumn("Description"),
            "status":           st.column_config.TextColumn("Status"),
        }
    )
else:
    st.info("No transactions yet. Send a message to your Telegram bot to get started.")

st.caption(f"Helias FinPilot Dashboard · {company_name} · Data auto-refreshes every 30s")

# Auto-refresh: wait 30 s then rerun this page so KPIs and charts stay live
time.sleep(30)
st.rerun()
