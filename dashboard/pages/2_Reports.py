"""
Reports page — generate and view monthly / annual reports.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import date
import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.db import load_transactions, load_company, load_reports
from dashboard.components import page_header, divider

st.set_page_config(page_title="Reports · FinPilot", page_icon="📊", layout="wide")

company       = load_company()
company_name  = company.get("name", "Helias AI and Analytics")
base_currency = company.get("base_currency", "ETB")

page_header("Reports", "Monthly and annual financial summaries")

tab1, tab2, tab3 = st.tabs(["📅 Monthly Report", "📆 Annual Report", "🗃️ Saved Reports"])

all_txns = load_transactions()
confirmed = all_txns[all_txns["status"] == "confirmed"].copy()

MONTH_NAMES = ["","January","February","March","April","May","June",
               "July","August","September","October","November","December"]

# ── Monthly Report ────────────────────────────────────────────────────────────
with tab1:
    c1, c2 = st.columns([1, 3])
    with c1:
        year  = st.selectbox("Year",  list(range(date.today().year, 2023, -1)), key="m_year")
        month = st.selectbox("Month", list(range(1, 13)),
                             format_func=lambda m: MONTH_NAMES[m],
                             index=date.today().month - 1, key="m_month")
        gen = st.button("Generate Report", type="primary", use_container_width=True)

    with c2:
        period = confirmed[
            (confirmed["transaction_date"].dt.year  == year) &
            (confirmed["transaction_date"].dt.month == month)
        ]
        inc = period[period["transaction_type"] == "income"]["amount"].sum()
        exp = period[period["transaction_type"] == "expense"]["amount"].sum()
        net = inc - exp

        m1, m2, m3 = st.columns(3)
        m1.metric(f"Income ({base_currency})",   f"{inc:,.2f}", delta=None)
        m2.metric(f"Expenses ({base_currency})", f"{exp:,.2f}", delta=None)
        m3.metric(f"Net ({base_currency})",      f"{net:+,.2f}")

    divider()

    if not period.empty:
        col_l, col_r = st.columns(2)

        # Category breakdown
        with col_l:
            st.markdown(f"**Expense Breakdown — {MONTH_NAMES[month]} {year}**")
            cat_df = (
                period[period["transaction_type"] == "expense"]
                .groupby("category")["amount"].sum()
                .reset_index().sort_values("amount", ascending=False)
            )
            if not cat_df.empty:
                fig = px.bar(cat_df, x="category", y="amount",
                             color_discrete_sequence=["#e94560"],
                             labels={"amount": base_currency, "category": ""},
                             height=280)
                fig.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                                  margin=dict(t=10, b=0), xaxis_tickangle=-30)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No expenses this month.")

        # Income by counterparty
        with col_r:
            st.markdown(f"**Income Sources — {MONTH_NAMES[month]} {year}**")
            src_df = (
                period[period["transaction_type"] == "income"]
                .groupby("counterparty")["amount"].sum()
                .reset_index().sort_values("amount", ascending=False)
            )
            if not src_df.empty:
                fig2 = px.pie(src_df, values="amount", names="counterparty",
                              hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel,
                              height=280)
                fig2.update_layout(margin=dict(t=10), paper_bgcolor="white")
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No income this month.")

        # Transaction list
        st.markdown("**All Transactions This Month**")
        display = period.copy()
        display["date"] = display["transaction_date"].dt.strftime("%Y-%m-%d")
        display["amount_fmt"] = display.apply(lambda r: f"{r['amount']:,.2f} {r['currency']}", axis=1)
        st.dataframe(
            display[["date","transaction_type","amount_fmt","counterparty","category","description"]],
            use_container_width=True, hide_index=True,
        )

        # Download
        csv = period.drop(columns=["transaction_date"]).to_csv(index=False).encode()
        st.download_button("⬇️ Download CSV", data=csv,
                           file_name=f"report_{year}_{month:02d}.csv", mime="text/csv")
    else:
        st.info(f"No confirmed transactions for {MONTH_NAMES[month]} {year}.")

# ── Annual Report ─────────────────────────────────────────────────────────────
with tab2:
    year_a = st.selectbox("Fiscal Year", list(range(date.today().year, 2023, -1)), key="a_year")
    annual = confirmed[confirmed["transaction_date"].dt.year == year_a]

    if not annual.empty:
        a1, a2, a3, a4 = st.columns(4)
        inc_a = annual[annual["transaction_type"] == "income"]["amount"].sum()
        exp_a = annual[annual["transaction_type"] == "expense"]["amount"].sum()
        net_a = inc_a - exp_a
        a1.metric(f"Total Income ({base_currency})",   f"{inc_a:,.0f}")
        a2.metric(f"Total Expenses ({base_currency})", f"{exp_a:,.0f}")
        a3.metric(f"Net Result ({base_currency})",     f"{net_a:+,.0f}")
        a4.metric("Transactions", len(annual))

        divider()

        # Monthly trend
        st.markdown("**Monthly Trend**")
        monthly = (
            annual.groupby([annual["transaction_date"].dt.month, "transaction_type"])["amount"]
            .sum().reset_index()
        )
        monthly.columns = ["month", "type", "amount"]
        monthly["month_name"] = monthly["month"].map(
            {i: MONTH_NAMES[i][:3] for i in range(1, 13)}
        )
        fig_trend = px.bar(monthly, x="month_name", y="amount", color="type",
                           barmode="group",
                           color_discrete_map={"income":"#27ae60","expense":"#e94560","transfer":"#f39c12"},
                           labels={"amount": base_currency, "month_name": "", "type": ""},
                           height=300)
        fig_trend.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                                margin=dict(t=10),
                                xaxis=dict(categoryorder="array",
                                           categoryarray=[MONTH_NAMES[i][:3] for i in range(1,13)]))
        st.plotly_chart(fig_trend, use_container_width=True)

        col_l2, col_r2 = st.columns(2)
        with col_l2:
            st.markdown("**Annual Expense Breakdown**")
            cat_a = (annual[annual["transaction_type"] == "expense"]
                     .groupby("category")["amount"].sum()
                     .reset_index().sort_values("amount", ascending=False))
            if not cat_a.empty:
                fig_cat = px.pie(cat_a, values="amount", names="category", hole=0.4,
                                 color_discrete_sequence=px.colors.qualitative.Set2, height=320)
                fig_cat.update_layout(paper_bgcolor="white", margin=dict(t=10))
                st.plotly_chart(fig_cat, use_container_width=True)

        with col_r2:
            st.markdown("**Top Counterparties by Volume**")
            cp_a = (annual.groupby("counterparty")["amount"].sum()
                    .reset_index().sort_values("amount", ascending=False).head(10))
            if not cp_a.empty and cp_a["counterparty"].notna().any():
                fig_cp = px.bar(cp_a, x="amount", y="counterparty", orientation="h",
                                color_discrete_sequence=["#0f3460"], height=320,
                                labels={"amount": base_currency, "counterparty": ""})
                fig_cp.update_layout(plot_bgcolor="white", paper_bgcolor="white",
                                     margin=dict(t=10), yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig_cp, use_container_width=True)

        # Download full year CSV
        csv_a = annual.drop(columns=["transaction_date"]).to_csv(index=False).encode()
        st.download_button("⬇️ Download Full Year CSV", data=csv_a,
                           file_name=f"annual_report_{year_a}.csv", mime="text/csv")
    else:
        st.info(f"No confirmed transactions for {year_a}.")

# ── Saved Reports ─────────────────────────────────────────────────────────────
with tab3:
    reports_df = load_reports()
    if reports_df.empty:
        st.info("No saved reports yet. Use /monthly_report or /annual_report in Telegram to generate one.")
    else:
        reports_df["label"] = reports_df.apply(
            lambda r: f"{r['report_type'].title()} — {r['period_year']}" +
                      (f"-{r['period_month']:02d}" if pd.notna(r["period_month"]) else ""),
            axis=1
        )
        selected = st.selectbox("Select a saved report", reports_df["label"].tolist())
        row = reports_df[reports_df["label"] == selected].iloc[0]
        st.markdown("---")
        st.text(row["content"])
        st.download_button(
            "⬇️ Download Report",
            data=row["content"].encode(),
            file_name=f"{selected.replace(' ', '_').replace('—','').strip()}.txt",
            mime="text/plain",
        )
