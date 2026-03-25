"""
Tax Compliance page — Ethiopian VAT (15%) and Withholding Tax (2%) dashboard.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import date
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from dashboard.db import load_tax_data, load_company
from dashboard.components import page_header, divider

st.set_page_config(page_title="Tax · FinPilot", page_icon="🧾", layout="wide")

company = load_company()
currency = company.get("base_currency", "ETB") if company else "ETB"
page_header("Tax Compliance", "Ethiopian VAT (15%) & Withholding Tax (2%) — MoR Filing Overview")

df = load_tax_data()

# ── Period selector ────────────────────────────────────────────────────────────
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
    st.markdown("### Tax Estimation Mode")
    auto_estimate = st.toggle(
        "Auto-estimate from amounts",
        value=True,
        help=(
            "ON: Calculate VAT (15%) and WHT (2%) from transaction amounts "
            "when not explicitly recorded on a receipt.\n\n"
            "OFF: Show only VAT/WHT values extracted directly from invoices."
        ),
    )
    st.markdown("---")
    st.info(
        "**Ethiopian Tax Rates**\n\n"
        "- VAT: **15%** (threshold: ETB 1M/yr)\n"
        "- WHT: **2%** on supplier payments\n"
        "- Filing deadline: **30th** of following month"
    )
    if auto_estimate:
        st.caption(
            "Estimation assumes your income amounts are **VAT-exclusive** "
            "(i.e. VAT = amount × 15%) and all expenses have 2% WHT applied."
        )

# Filter data
fdf = df[df["transaction_date"].dt.year == sel_year].copy()
if sel_month != 0:
    fdf = fdf[fdf["transaction_date"].dt.month == sel_month]

period_label = f"{sel_year}-{sel_month:02d}" if sel_month != 0 else str(sel_year)

# ── Tax calculations ───────────────────────────────────────────────────────────
income_df  = fdf[fdf["transaction_type"] == "income"].copy()
expense_df = fdf[fdf["transaction_type"] == "expense"].copy()

if auto_estimate:
    # Where VAT not explicitly recorded, estimate it from the amount
    income_df["vat_used"]  = income_df.apply(
        lambda r: r["vat_amount"] if r["vat_amount"] > 0 else r["amount"] * 0.15, axis=1
    )
    expense_df["vat_used"] = expense_df.apply(
        lambda r: r["vat_amount"] if r["vat_amount"] > 0 else r["amount"] * 0.15, axis=1
    )
    expense_df["wht_used"] = expense_df.apply(
        lambda r: r["withholding_tax"] if r["withholding_tax"] > 0 else r["amount"] * 0.02, axis=1
    )
else:
    income_df["vat_used"]  = income_df["vat_amount"]
    expense_df["vat_used"] = expense_df["vat_amount"]
    expense_df["wht_used"] = expense_df["withholding_tax"]

output_vat   = income_df["vat_used"].sum()
input_vat    = expense_df["vat_used"].sum()
net_vat      = output_vat - input_vat
wht_total    = expense_df["wht_used"].sum()
total_oblig  = max(net_vat, 0) + wht_total

estimated_badge = " _(estimated)_" if auto_estimate else ""

# ── KPI strip ─────────────────────────────────────────────────────────────────
if auto_estimate:
    st.info("💡 **Estimation mode ON** — VAT and WHT are calculated automatically from transaction amounts. Toggle off in the sidebar to show only explicitly-recorded values.")

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric(f"Output VAT{estimated_badge}", f"{output_vat:,.2f} {currency}", help="VAT you collected on income — must remit to MoR")
k2.metric(f"Input VAT{estimated_badge}", f"{input_vat:,.2f} {currency}", help="VAT you paid on purchases — deductible credit")
delta_color = "inverse" if net_vat > 0 else "normal"
k3.metric("Net VAT Payable", f"{net_vat:,.2f} {currency}",
          delta=f"{'+' if net_vat >= 0 else ''}{net_vat:,.2f}", delta_color=delta_color,
          help="Output VAT − Input VAT = amount to pay MoR")
k4.metric(f"WHT Collected (2%){estimated_badge}", f"{wht_total:,.2f} {currency}", help="Withholding tax withheld from supplier payments")
k5.metric("Total MoR Obligation", f"{total_oblig:,.2f} {currency}", help="Net VAT payable + WHT to remit")

divider()

# ── Two-column layout ─────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

# ── VAT breakdown chart ───────────────────────────────────────────────────────
with col1:
    st.markdown("#### VAT Breakdown")
    vat_fig = go.Figure(go.Bar(
        x=["Output VAT\n(collected on income)", "Input VAT\n(paid on expenses)", "Net VAT Payable"],
        y=[output_vat, input_vat, max(net_vat, 0)],
        marker_color=["#2ecc71", "#e74c3c", "#e94560"],
        text=[f"{v:,.2f}" for v in [output_vat, input_vat, max(net_vat, 0)]],
        textposition="outside",
    ))
    vat_fig.update_layout(
        yaxis_title=f"Amount ({currency})",
        showlegend=False,
        height=320,
        margin=dict(t=20, b=20),
    )
    st.plotly_chart(vat_fig, use_container_width=True)

# ── Monthly VAT trend (only for full year) ────────────────────────────────────
with col2:
    if sel_month == 0 and not fdf.empty:
        st.markdown("#### Monthly VAT Trend")
        monthly = fdf.copy()
        monthly["month"] = monthly["transaction_date"].dt.month
        out_m = monthly[monthly["transaction_type"] == "income"].groupby("month")["vat_amount"].sum()
        inp_m = monthly[monthly["transaction_type"] == "expense"].groupby("month")["vat_amount"].sum()

        months = list(range(1, 13))
        month_labels = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        trend_fig = go.Figure()
        trend_fig.add_trace(go.Bar(name="Output VAT", x=month_labels,
                                   y=[out_m.get(m, 0) for m in months], marker_color="#2ecc71"))
        trend_fig.add_trace(go.Bar(name="Input VAT", x=month_labels,
                                   y=[inp_m.get(m, 0) for m in months], marker_color="#e74c3c"))
        trend_fig.update_layout(barmode="group", height=320,
                                 yaxis_title=f"VAT Amount ({currency})",
                                 margin=dict(t=20, b=20))
        st.plotly_chart(trend_fig, use_container_width=True)
    else:
        st.markdown("#### Tax Obligation Summary")
        pie_fig = px.pie(
            names=["Net VAT Payable", "WHT to Remit"],
            values=[max(net_vat, 0), wht_total],
            color_discrete_sequence=["#e94560", "#3498db"],
            hole=0.5,
        )
        pie_fig.update_traces(textinfo="label+value+percent")
        pie_fig.update_layout(height=320, margin=dict(t=20, b=20))
        st.plotly_chart(pie_fig, use_container_width=True)

divider()

# ── VAT transaction table ─────────────────────────────────────────────────────
vat_label = "Transactions with VAT" + (" (estimated where not on invoice)" if auto_estimate else "")
st.markdown(f"#### {vat_label}")

all_tax_txns = pd.concat([income_df, expense_df], ignore_index=True)
all_tax_txns = all_tax_txns[all_tax_txns["vat_used"] > 0].copy()

if all_tax_txns.empty:
    st.info("No VAT transactions for this period.")
else:
    all_tax_txns["date"] = all_tax_txns["transaction_date"].dt.strftime("%Y-%m-%d")
    all_tax_txns["vat_type"] = all_tax_txns["transaction_type"].map(
        {"income": "Output (collect)", "expense": "Input (credit)"}
    ).fillna("—")
    all_tax_txns["source"] = all_tax_txns["vat_amount"].apply(
        lambda v: "From invoice" if v > 0 else "Estimated (15%)"
    )
    disp_cols = ["date", "transaction_type", "vat_type", "amount", "vat_used", "currency", "counterparty", "description"]
    if auto_estimate:
        disp_cols.insert(5, "source")
    st.dataframe(
        all_tax_txns[disp_cols].rename(columns={
            "date": "Date", "transaction_type": "Type", "vat_type": "VAT Type",
            "amount": f"Gross ({currency})", "vat_used": f"VAT ({currency})",
            "source": "Source", "currency": "Curr",
            "counterparty": "Counterparty", "description": "Description",
        }),
        use_container_width=True,
        hide_index=True,
    )

divider()

# ── WHT transaction table ─────────────────────────────────────────────────────
wht_label = "Transactions with Withholding Tax (2%)" + (" (estimated where not on invoice)" if auto_estimate else "")
st.markdown(f"#### {wht_label}")
wht_txns = expense_df[expense_df["wht_used"] > 0].copy()
if wht_txns.empty:
    st.info("No WHT transactions for this period.")
else:
    wht_txns["date"] = wht_txns["transaction_date"].dt.strftime("%Y-%m-%d")
    wht_txns["net_paid"] = wht_txns["amount"] - wht_txns["wht_used"]
    wht_txns["wht_source"] = wht_txns["withholding_tax"].apply(
        lambda v: "From invoice" if v > 0 else "Estimated (2%)"
    )
    disp_cols = ["date", "amount", "wht_used", "net_paid", "currency", "counterparty", "description"]
    if auto_estimate:
        disp_cols.insert(3, "wht_source")
    st.dataframe(
        wht_txns[disp_cols].rename(columns={
            "date": "Date", "amount": f"Gross ({currency})",
            "wht_used": f"WHT Withheld ({currency})", "wht_source": "Source",
            "net_paid": f"Net Paid ({currency})", "currency": "Curr",
            "counterparty": "Supplier", "description": "Description",
        }),
        use_container_width=True,
        hide_index=True,
    )

divider()

# ── Filing reminder ───────────────────────────────────────────────────────────
st.markdown("#### MoR Filing Checklist")
c1, c2 = st.columns(2)
with c1:
    est_note = " _(est.)_" if auto_estimate else ""
    st.markdown(f"""
    | Obligation | Amount ({currency}){est_note} | Due Date |
    |---|---|---|
    | Net VAT Payable | **{max(net_vat, 0):,.2f}** | 30th of next month |
    | Withholding Tax | **{wht_total:,.2f}** | 30th of next month |
    | **Total** | **{total_oblig:,.2f}** | |
    """)
with c2:
    if total_oblig > 0:
        st.warning(
            f"⚠️ **{total_oblig:,.2f} {currency}** is due to the Ministry of Revenue "
            f"for **{period_label}**.\n\n"
            "Remember to bring:\n"
            "- VAT declaration form\n"
            "- Withholding tax schedule\n"
            "- Supporting invoices/receipts"
        )
    else:
        st.success(f"✅ No tax obligation recorded for {period_label}.")
