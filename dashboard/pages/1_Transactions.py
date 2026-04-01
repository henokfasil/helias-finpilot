"""
Transactions page — filterable, searchable transaction ledger.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import date, timedelta
import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.db import load_transactions, load_categories, load_company, delete_transactions
from dashboard.components import page_header, divider

st.set_page_config(page_title="Transactions · FinPilot", page_icon="📋", layout="wide")

company       = load_company()
base_currency = company.get("base_currency", "ETB")
all_txns      = load_transactions()

page_header("Transactions", "Full ledger — filter, search, and export")

# ── Filters ───────────────────────────────────────────────────────────────────
with st.expander("🔍 Filters", expanded=True):
    fc1, fc2, fc3, fc4 = st.columns(4)

    with fc1:
        type_filter = st.multiselect(
            "Transaction Type",
            ["income", "expense", "transfer"],
            default=["income", "expense"],
        )
    with fc2:
        status_filter = st.multiselect(
            "Status",
            ["confirmed", "draft", "needs_clarification", "rejected"],
            default=["confirmed"],
        )
    with fc3:
        min_date = all_txns["transaction_date"].min() if not all_txns.empty else date(2025, 1, 1)
        max_date = all_txns["transaction_date"].max() if not all_txns.empty else date.today()
        date_range = st.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
    with fc4:
        categories = load_categories()
        cat_options = ["All"] + sorted(categories["name"].tolist())
        cat_filter = st.selectbox("Category", cat_options)

    keyword = st.text_input("Search description / counterparty", placeholder="e.g. Ethio Telecom")

# ── Apply filters ─────────────────────────────────────────────────────────────
df = all_txns.copy()

if type_filter:
    df = df[df["transaction_type"].isin(type_filter)]
if status_filter:
    df = df[df["status"].isin(status_filter)]
if len(date_range) == 2:
    start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
    df = df[(df["transaction_date"] >= start) & (df["transaction_date"] <= end)]
if cat_filter != "All":
    df = df[df["category"] == cat_filter]
if keyword:
    kw = keyword.lower()
    mask = (
        df["description"].str.lower().str.contains(kw, na=False) |
        df["counterparty"].str.lower().str.contains(kw, na=False)
    )
    df = df[mask]

# ── Summary strip ─────────────────────────────────────────────────────────────
if not df.empty:
    s1, s2, s3, s4 = st.columns(4)
    confirmed_df = df[df["status"] == "confirmed"]
    inc  = confirmed_df[confirmed_df["transaction_type"] == "income"]["amount"].sum()
    exp  = confirmed_df[confirmed_df["transaction_type"] == "expense"]["amount"].sum()
    s1.metric("Rows shown", len(df))
    s2.metric(f"Income ({base_currency})", f"{inc:,.2f}")
    s3.metric(f"Expenses ({base_currency})", f"{exp:,.2f}")
    s4.metric(f"Net ({base_currency})", f"{inc - exp:,.2f}")

divider()

# ── Table ─────────────────────────────────────────────────────────────────────
if df.empty:
    st.info("No transactions match your filters.")
else:
    display = df.copy()
    display["date_gr"]    = display["transaction_date"].dt.strftime("%Y-%m-%d")
    display["date_et"]    = display["transaction_date_et"].fillna("—") if "transaction_date_et" in display.columns else "—"
    display["amount_fmt"] = display.apply(lambda r: f"{r['amount']:,.2f} {r['currency']}", axis=1)

    st.dataframe(
        display[[
            "id", "date_gr", "date_et", "transaction_type", "amount_fmt",
            "counterparty", "category", "description",
            "reference_number", "payment_method", "status", "ai_confidence",
        ]].rename(columns={
            "id": "ID",
            "date_gr": "Date (GR)",
            "date_et": "Date (ET)",
            "transaction_type": "Type",
            "amount_fmt": "Amount",
            "counterparty": "Counterparty",
            "category": "Category",
            "description": "Description",
            "reference_number": "Receipt No",
            "payment_method": "Payment",
            "status": "Status",
            "ai_confidence": "AI Conf.",
        }),
        use_container_width=True,
        hide_index=True,
        height=420,
        column_config={
            "ID": st.column_config.NumberColumn(
                "ID",
                help="Use this number with /delete on Telegram or in the Delete panel below",
                width="small",
                format="%d",
            ),
        },
    )

    # ── Delete panel ───────────────────────────────────────────────────────────
    with st.expander("🗑️ Delete transactions", expanded=False):
        st.caption(
            "Enter IDs from the table above, separated by commas or spaces. "
            "Ranges like **3-7** are also supported. Example: `1, 3, 5-8`"
        )
        raw_ids = st.text_input("Transaction IDs to delete", placeholder="e.g. 4, 7, 10-13")
        if st.button("Delete selected", type="primary"):
            ids_to_delete: list[int] = []
            for part in raw_ids.replace(",", " ").split():
                part = part.strip()
                if "-" in part:
                    try:
                        a, b = part.split("-", 1)
                        ids_to_delete.extend(range(int(a), int(b) + 1))
                    except ValueError:
                        st.warning(f"Skipped unreadable range: `{part}`")
                else:
                    try:
                        ids_to_delete.append(int(part))
                    except ValueError:
                        st.warning(f"Skipped invalid ID: `{part}`")

            ids_to_delete = list(set(ids_to_delete))  # deduplicate
            if not ids_to_delete:
                st.warning("No valid IDs entered.")
            else:
                deleted = delete_transactions(ids_to_delete)
                if deleted:
                    st.success(f"Deleted {deleted} transaction(s). Refresh the page to see the updated list.")
                else:
                    st.error("No transactions were deleted. Check that the IDs exist and belong to your company.")

    # ── Export ─────────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    drop_cols = [c for c in ["transaction_date", "transaction_date_et"] if c in display.columns]
    csv = display.drop(columns=drop_cols).to_csv(index=False).encode()
    st.download_button(
        label="⬇️ Download as CSV",
        data=csv,
        file_name=f"transactions_{date.today()}.csv",
        mime="text/csv",
    )

# ── Trend chart ───────────────────────────────────────────────────────────────
if not df.empty and len(df) > 1:
    divider()
    st.markdown("#### Amount Over Time")
    trend = df[df["status"] == "confirmed"].copy()
    if not trend.empty:
        fig = px.scatter(
            trend,
            x="transaction_date",
            y="amount",
            color="transaction_type",
            size="amount",
            hover_data=["counterparty", "description", "category"],
            color_discrete_map={"income": "#27ae60", "expense": "#e94560", "transfer": "#f39c12"},
            labels={"transaction_date": "Date", "amount": f"Amount ({base_currency})", "transaction_type": "Type"},
            height=320,
        )
        fig.update_layout(plot_bgcolor="white", paper_bgcolor="white", margin=dict(t=10))
        st.plotly_chart(fig, use_container_width=True)
