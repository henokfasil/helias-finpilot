"""
Receipts page — browse and download stored receipt files.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from datetime import date
import zipfile
from io import BytesIO
import streamlit as st
import pandas as pd

from dashboard.db import load_attachments, load_company
from dashboard.components import page_header, divider

st.set_page_config(page_title="Receipts · FinPilot", page_icon="📎", layout="wide")

company = load_company()
page_header("Receipts & Attachments", "All uploaded files — organized for Ministry of Revenue")

df = load_attachments()

# ── Filters ───────────────────────────────────────────────────────────────────
with st.expander("🔍 Filter", expanded=True):
    f1, f2, f3 = st.columns(3)
    with f1:
        years = sorted(df["transaction_date"].dt.year.dropna().unique().astype(int).tolist(), reverse=True) if not df.empty else [date.today().year]
        sel_year = st.selectbox("Year", ["All"] + [str(y) for y in years])
    with f2:
        month_map = {0:"All",1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                     7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
        sel_month = st.selectbox("Month", list(month_map.keys()), format_func=lambda m: month_map[m])
    with f3:
        type_opts = ["All"] + sorted(df["file_type"].dropna().unique().tolist()) if not df.empty else ["All"]
        sel_type = st.selectbox("File Type", type_opts)

# Apply filters
fdf = df.copy()
if sel_year != "All" and not fdf.empty:
    fdf = fdf[fdf["transaction_date"].dt.year == int(sel_year)]
if sel_month != 0 and not fdf.empty:
    fdf = fdf[fdf["transaction_date"].dt.month == sel_month]
if sel_type != "All" and not fdf.empty:
    fdf = fdf[fdf["file_type"] == sel_type]

# ── Summary ───────────────────────────────────────────────────────────────────
s1, s2, s3 = st.columns(3)
s1.metric("Files Found", len(fdf))
total_size = fdf["file_size_kb"].sum() if not fdf.empty else 0
s2.metric("Total Size", f"{total_size:.1f} KB")
linked = fdf["transaction_id"].notna().sum() if not fdf.empty else 0
s3.metric("Linked to Transactions", int(linked))

divider()

# ── ZIP export ────────────────────────────────────────────────────────────────
if not fdf.empty:
    label = f"{sel_year}" + (f"-{sel_month:02d}" if sel_month != 0 else "")
    if st.button(f"📦 Download All as ZIP ({len(fdf)} files)", type="primary"):
        buf = BytesIO()
        missing = 0
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for _, row in fdf.iterrows():
                p = Path(row["stored_path"])
                if p.exists():
                    zf.write(p, arcname=p.name)
                else:
                    missing += 1
        if missing:
            st.warning(f"{missing} file(s) were not found on disk and excluded from the ZIP.")
        st.download_button(
            label="⬇️ Save ZIP",
            data=buf.getvalue(),
            file_name=f"helias_receipts_{label}.zip",
            mime="application/zip",
        )

divider()

# ── File list ─────────────────────────────────────────────────────────────────
if fdf.empty:
    st.info("No receipt files found for the selected period.")
else:
    for _, row in fdf.iterrows():
        file_path = Path(row["stored_path"])
        exists    = file_path.exists()

        with st.container():
            c1, c2, c3 = st.columns([1, 3, 1])

            # Icon
            icons = {"image": "🖼️", "pdf": "📄", "excel": "📊"}
            icon  = icons.get(row.get("file_type", ""), "📎")

            with c1:
                st.markdown(f"<div style='font-size:36px; text-align:center;'>{icon}</div>",
                            unsafe_allow_html=True)
            with c2:
                name = row.get("original_filename") or file_path.name
                st.markdown(f"**{name}**")
                date_str = row["transaction_date"].strftime("%Y-%m-%d") if pd.notna(row["transaction_date"]) else "—"
                cp       = row.get("counterparty") or "—"
                amt      = f"{row['amount']:,.2f} {row['currency']}" if pd.notna(row.get("amount")) else "—"
                tx_id    = f"tx#{int(row['transaction_id'])}" if pd.notna(row.get("transaction_id")) else "not linked"
                st.caption(f"📅 {date_str}  ·  👤 {cp}  ·  💰 {amt}  ·  🔗 {tx_id}  ·  {row.get('file_size_kb', 0):.1f} KB")
                if not exists:
                    st.warning("⚠️ File missing from disk", icon="⚠️")

            with c3:
                if exists:
                    file_bytes = file_path.read_bytes()
                    st.download_button(
                        "⬇️ Download",
                        data=file_bytes,
                        file_name=file_path.name,
                        key=f"dl_{row['id']}",
                    )

            st.markdown("<hr style='border:none; border-top:1px solid #f0f0f0; margin:6px 0;'>",
                        unsafe_allow_html=True)

st.caption("Files stored permanently at: uploads/{company}/{year}/{month}/")
