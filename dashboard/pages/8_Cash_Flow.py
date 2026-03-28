"""
Cash Flow Statement — Helias FinPilot Dashboard

Groups confirmed transactions by activity_type:
  operating  (default) — day-to-day income and expenses
  investing             — equipment purchases, asset sales
  financing             — loans taken/repaid, capital injections
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from dashboard.db import load_financial_data, load_company

st.set_page_config(page_title="Cash Flow", page_icon="💧", layout="wide")
st.title("💧 Cash Flow Statement")
st.caption("Direct method — actual cash inflows and outflows")

company = load_company()
currency = company.get("base_currency", "ETB")
company_name = company.get("name", "Your Company")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Period")
    year = st.selectbox("Year", list(range(2023, 2030)),
                        index=list(range(2023, 2030)).index(2026))
    view = st.radio("View", ["Annual", "Monthly"])
    month = None
    if view == "Monthly":
        month = st.selectbox(
            "Month",
            range(1, 13),
            format_func=lambda m: pd.Timestamp(2026, m, 1).strftime("%B"),
            index=pd.Timestamp.now().month - 1,
        )
    st.info(
        "**Activity Types**\n\n"
        "All transactions default to **operating**. "
        "To tag a transaction as *investing* or *financing*, reply `/tag <id> investing` in the bot "
        "— this command is on the roadmap.\n\n"
        "**Operating**: revenue, rent, salaries, utilities\n"
        "**Investing**: equipment bought/sold, asset disposal\n"
        "**Financing**: bank loans taken/repaid, owner capital in/out"
    )

# ── Load and filter ──────────────────────────────────────────────────────────
df = load_financial_data()

if df.empty:
    st.info("No confirmed transactions yet.")
    st.stop()

df = df[df["transaction_date"].dt.year == year]
if month:
    df = df[df["transaction_date"].dt.month == month]

period_label = f"{year}" if not month else pd.Timestamp(year, month, 1).strftime("%B %Y")

# ── Compute by activity ──────────────────────────────────────────────────────
def _compute_activity(sub_df: pd.DataFrame) -> dict:
    if sub_df.empty:
        return {"inflows": 0.0, "outflows": 0.0, "net": 0.0}
    inflows = sub_df[sub_df["transaction_type"] == "income"]["amount"].sum()
    outflows = sub_df[sub_df["transaction_type"] == "expense"]["amount"].sum()
    return {"inflows": float(inflows), "outflows": float(outflows), "net": float(inflows - outflows)}

op_df = df[df["activity_type"] == "operating"]
inv_df = df[df["activity_type"] == "investing"]
fin_df = df[df["activity_type"] == "financing"]

op = _compute_activity(op_df)
inv = _compute_activity(inv_df)
fin = _compute_activity(fin_df)

net_change = op["net"] + inv["net"] + fin["net"]

# ── KPI strip ─────────────────────────────────────────────────────────────────
st.subheader(f"{company_name} — {period_label}")
k1, k2, k3, k4 = st.columns(4)
k1.metric("🔧 Operating CF", f"{op['net']:+,.0f} {currency}",
          delta_color="normal")
k2.metric("🏗 Investing CF", f"{inv['net']:+,.0f} {currency}",
          delta_color="normal")
k3.metric("🏦 Financing CF", f"{fin['net']:+,.0f} {currency}",
          delta_color="normal")
k4.metric("💰 Net Change in Cash", f"{net_change:+,.0f} {currency}",
          delta_color="normal")

st.divider()

# ── Formal statement ─────────────────────────────────────────────────────────
col_stmt, col_chart = st.columns([1, 1])

with col_stmt:
    st.subheader("Statement")

    def _line(label, amount, bold=False, indent=False):
        prefix = "&nbsp;&nbsp;&nbsp;&nbsp;" if indent else ""
        sign = "+" if amount >= 0 else ""
        if bold:
            return f"**{prefix}{label}** &nbsp;&nbsp;&nbsp; **`{sign}{amount:,.2f}`**"
        return f"{prefix}{label} &nbsp;&nbsp;&nbsp; `{sign}{amount:,.2f}`"

    st.markdown(f"*All amounts in {currency}*")
    st.markdown("---")
    st.markdown("#### A. OPERATING ACTIVITIES")
    st.markdown(_line("Cash received from customers", op["inflows"], indent=True))
    st.markdown(_line("Cash paid to suppliers/staff", -op["outflows"], indent=True))
    st.markdown(_line("Net cash from operating activities", op["net"], bold=True))
    st.markdown("---")
    st.markdown("#### B. INVESTING ACTIVITIES")
    if inv["inflows"] > 0:
        st.markdown(_line("Proceeds from asset disposal", inv["inflows"], indent=True))
    if inv["outflows"] > 0:
        st.markdown(_line("Payments for assets/equipment", -inv["outflows"], indent=True))
    st.markdown(_line("Net cash from investing activities", inv["net"], bold=True))
    st.markdown("---")
    st.markdown("#### C. FINANCING ACTIVITIES")
    if fin["inflows"] > 0:
        st.markdown(_line("Loans received / capital injected", fin["inflows"], indent=True))
    if fin["outflows"] > 0:
        st.markdown(_line("Loan repayments / capital withdrawn", -fin["outflows"], indent=True))
    st.markdown(_line("Net cash from financing activities", fin["net"], bold=True))
    st.markdown("---")
    sign = "+" if net_change >= 0 else ""
    st.markdown(f"### **NET INCREASE / (DECREASE) IN CASH &nbsp;&nbsp;&nbsp; `{sign}{net_change:,.2f} {currency}`**")

with col_chart:
    st.subheader("Cash Flow Breakdown")

    # Waterfall
    fig = go.Figure(go.Waterfall(
        name="Cash Flow",
        orientation="v",
        measure=["relative", "relative", "relative", "total"],
        x=["Operating", "Investing", "Financing", "Net Change"],
        y=[op["net"], inv["net"], fin["net"], net_change],
        connector={"line": {"color": "rgb(63, 63, 63)"}},
        increasing={"marker": {"color": "#2ecc71"}},
        decreasing={"marker": {"color": "#e74c3c"}},
        totals={"marker": {"color": "#3498db"}},
        text=[f"{v:+,.0f}" for v in [op["net"], inv["net"], fin["net"], net_change]],
        textposition="outside",
    ))
    fig.update_layout(
        title=f"Cash Flow Waterfall — {period_label}",
        yaxis_title=currency,
        showlegend=False,
        height=380,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Inflow vs outflow bar
    act_names = ["Operating", "Investing", "Financing"]
    inflows = [op["inflows"], inv["inflows"], fin["inflows"]]
    outflows = [op["outflows"], inv["outflows"], fin["outflows"]]

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(name="Inflows", x=act_names, y=inflows, marker_color="#2ecc71"))
    fig2.add_trace(go.Bar(name="Outflows", x=act_names, y=outflows, marker_color="#e74c3c"))
    fig2.update_layout(barmode="group", height=250, yaxis_title=currency, showlegend=True)
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── Monthly trend (annual view) ───────────────────────────────────────────────
if not month and not df.empty:
    st.subheader("Monthly Operating Cash Flow")
    monthly_op = op_df.copy() if not op_df.empty else pd.DataFrame()
    if not monthly_op.empty:
        monthly_op["month"] = monthly_op["transaction_date"].dt.month
        monthly_op["month_label"] = monthly_op["month"].apply(
            lambda m: pd.Timestamp(year, int(m), 1).strftime("%b")
        )
        monthly_summary = (
            monthly_op.groupby(["month_label", "transaction_type"])["amount"]
            .sum().unstack(fill_value=0).reset_index()
        )
        fig3 = go.Figure()
        if "income" in monthly_summary.columns:
            fig3.add_trace(go.Bar(name="Operating Inflows",
                                  x=monthly_summary["month_label"],
                                  y=monthly_summary["income"],
                                  marker_color="#2ecc71"))
        if "expense" in monthly_summary.columns:
            fig3.add_trace(go.Bar(name="Operating Outflows",
                                  x=monthly_summary["month_label"],
                                  y=monthly_summary["expense"],
                                  marker_color="#e74c3c"))
        fig3.update_layout(barmode="group", height=300, yaxis_title=currency)
        st.plotly_chart(fig3, use_container_width=True)

st.divider()

# ── Detail tables per activity ────────────────────────────────────────────────
st.subheader("Transaction Detail")
tabs = st.tabs(["🔧 Operating", "🏗 Investing", "🏦 Financing"])

def _show_table(sub_df: pd.DataFrame):
    if sub_df.empty:
        st.info("No transactions for this activity type.")
        return
    display = (
        sub_df[["transaction_date", "transaction_type", "counterparty", "category", "amount", "currency"]]
        .rename(columns={"transaction_date": "Date", "transaction_type": "Type",
                         "counterparty": "Party", "category": "Category",
                         "amount": "Amount", "currency": "CCY"})
        .assign(Date=lambda d: d["Date"].dt.strftime("%Y-%m-%d"))
        .sort_values("Date")
    )
    st.dataframe(display, use_container_width=True, hide_index=True)

with tabs[0]:
    st.caption(f"Inflows: {op['inflows']:,.0f} | Outflows: {op['outflows']:,.0f} | Net: {op['net']:+,.0f} {currency}")
    _show_table(op_df)
with tabs[1]:
    st.caption(f"Inflows: {inv['inflows']:,.0f} | Outflows: {inv['outflows']:,.0f} | Net: {inv['net']:+,.0f} {currency}")
    _show_table(inv_df)
with tabs[2]:
    st.caption(f"Inflows: {fin['inflows']:,.0f} | Outflows: {fin['outflows']:,.0f} | Net: {fin['net']:+,.0f} {currency}")
    _show_table(fin_df)
