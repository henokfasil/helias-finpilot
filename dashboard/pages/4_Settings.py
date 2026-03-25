"""
Settings page — view company info, categories, and system status.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import date
import streamlit as st
import pandas as pd

from dashboard.db import load_company, load_categories, load_transactions, load_attachments
from dashboard.components import page_header, divider

st.set_page_config(page_title="Settings · FinPilot", page_icon="⚙️", layout="wide")

company = load_company()
page_header("Settings & System Info", "Company configuration and health overview")

tab1, tab2, tab3 = st.tabs(["🏢 Company", "🏷️ Categories", "🩺 System Health"])

# ── Company Info ──────────────────────────────────────────────────────────────
with tab1:
    st.markdown("#### Company Profile")
    if company:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"""
            | Field | Value |
            |---|---|
            | **Name** | {company.get('name', '—')} |
            | **Currency** | {company.get('base_currency', '—')} |
            | **Country** | {company.get('country', '—')} |
            | **Fiscal Year Start** | Month {company.get('fiscal_year_start_month', '—')} |
            | **Status** | {'✅ Active' if company.get('is_active') else '❌ Inactive'} |
            """)
        with c2:
            st.info("To change company settings, update the `.env` file and restart the bot.")
            st.markdown("""
            **Database location:**
            ```
            finpilot.db  (SQLite)
            ```
            **Uploads location:**
            ```
            uploads/{company-slug}/{year}/{month}/
            ```
            """)
    else:
        st.error("Company not found. Run `python scripts/seed_data.py` first.")

# ── Categories ────────────────────────────────────────────────────────────────
with tab2:
    cats = load_categories()
    if cats.empty:
        st.info("No categories found.")
    else:
        st.markdown("#### Income Categories")
        income_cats = cats[cats["type"] == "income"][["name", "is_active"]].copy()
        income_cats["is_active"] = income_cats["is_active"].map({1: "✅", 0: "❌"})
        st.dataframe(income_cats.rename(columns={"name": "Category", "is_active": "Active"}),
                     use_container_width=True, hide_index=True)

        st.markdown("#### Expense Categories")
        expense_cats = cats[cats["type"] == "expense"][["name", "is_active"]].copy()
        expense_cats["is_active"] = expense_cats["is_active"].map({1: "✅", 0: "❌"})
        st.dataframe(expense_cats.rename(columns={"name": "Category", "is_active": "Active"}),
                     use_container_width=True, hide_index=True)

        st.caption("To add or modify categories, use the database directly or update seed_data.py.")

# ── System Health ─────────────────────────────────────────────────────────────
with tab3:
    st.markdown("#### System Health Check")

    all_txns = load_transactions()
    all_att  = load_attachments()

    h1, h2, h3, h4 = st.columns(4)
    h1.metric("Total Transactions", len(all_txns))
    h2.metric("Confirmed", len(all_txns[all_txns["status"] == "confirmed"]) if not all_txns.empty else 0)
    h3.metric("Pending", len(all_txns[all_txns["status"].isin(["draft","needs_clarification"])]) if not all_txns.empty else 0)
    h4.metric("Total Attachments", len(all_att))

    divider()

    # Missing files check
    st.markdown("#### Attachment File Check")
    if all_att.empty:
        st.success("No attachments yet.")
    else:
        missing = []
        for _, row in all_att.iterrows():
            if not Path(row["stored_path"]).exists():
                missing.append(row["original_filename"])

        if missing:
            st.error(f"⚠️ {len(missing)} file(s) missing from disk:")
            for f in missing:
                st.markdown(f"  - `{f}`")
        else:
            st.success(f"✅ All {len(all_att)} attachment files are present on disk.")

    divider()

    # Unlinked attachments
    st.markdown("#### Unlinked Attachments")
    if not all_att.empty:
        unlinked = all_att[all_att["transaction_id"].isna()]
        if unlinked.empty:
            st.success("✅ All attachments are linked to transactions.")
        else:
            st.warning(f"⚠️ {len(unlinked)} attachment(s) not yet linked to a transaction:")
            st.dataframe(
                unlinked[["id", "original_filename", "file_type", "created_at"]],
                use_container_width=True, hide_index=True,
            )

    divider()

    # Low confidence transactions
    st.markdown("#### Low AI Confidence Transactions (< 60%)")
    if not all_txns.empty:
        low_conf = all_txns[
            (all_txns["ai_confidence"].notna()) &
            (pd.to_numeric(all_txns["ai_confidence"], errors="coerce") < 0.6)
        ]
        if low_conf.empty:
            st.success("✅ No low-confidence transactions.")
        else:
            st.warning(f"⚠️ {len(low_conf)} transaction(s) extracted with low confidence:")
            disp = low_conf.copy()
            disp["date"] = disp["transaction_date"].dt.strftime("%Y-%m-%d")
            disp["conf"] = (pd.to_numeric(disp["ai_confidence"]) * 100).round(0).astype(str) + "%"
            st.dataframe(
                disp[["id","date","transaction_type","amount","currency","description","conf","status"]],
                use_container_width=True, hide_index=True,
            )
