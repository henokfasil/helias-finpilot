"""
Debug page — shows configuration status
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

st.set_page_config(page_title="Debug · FinPilot", page_icon="🔧", layout="wide")

st.title("🔧 Debug & Configuration")

# ── Secrets Status ──────────────────────────────────────────────────────────
st.header("Streamlit Secrets")

col1, col2, col3 = st.columns(3)

with col1:
    if "DATABASE_URL" in st.secrets:
        st.success("✅ DATABASE_URL configured")
        st.code(f"postgresql://...{st.secrets['DATABASE_URL'][-30:]}")
    else:
        st.error("❌ DATABASE_URL missing")

with col2:
    if "GEMINI_API_KEY" in st.secrets:
        st.success("✅ GEMINI_API_KEY configured")
        st.code(f"AIza...{st.secrets['GEMINI_API_KEY'][-10:]}")
    else:
        st.error("❌ GEMINI_API_KEY missing")

with col3:
    if "GEMINI_VISION_MODEL" in st.secrets:
        st.success("✅ GEMINI_VISION_MODEL configured")
        st.code(st.secrets["GEMINI_VISION_MODEL"])
    else:
        st.info("ℹ️ GEMINI_VISION_MODEL not set (using default)")

# ── Test Database Connection ───────────────────────────────────────────────
st.header("Database Connection Test")

if "DATABASE_URL" in st.secrets:
    if st.button("🧪 Test Database Connection"):
        try:
            from sqlalchemy import create_engine, text

            db_url = st.secrets["DATABASE_URL"]
            st.info(f"Testing connection to: {db_url[:50]}...")

            engine = create_engine(db_url, pool_pre_ping=True)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) as count FROM transactions WHERE status = 'confirmed'"))
                count = result.scalar()

            st.success(f"✅ Database connected! Found {count} confirmed transactions")

        except Exception as e:
            st.error(f"❌ Connection failed: {type(e).__name__}: {str(e)[:200]}")
else:
    st.warning("Add DATABASE_URL to Streamlit Secrets first")

# ── Test Gemini Connection ──────────────────────────────────────────────────
st.header("Gemini API Test")

if "GEMINI_API_KEY" in st.secrets:
    if st.button("🧪 Test Gemini API"):
        try:
            import google.generativeai as genai

            genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
            model = genai.GenerativeModel("models/gemini-2.5-flash")
            response = model.generate_content("Say 'Hello from Gemini!' in exactly those words.")

            st.success(f"✅ Gemini API working!\n\nResponse: {response.text}")

        except Exception as e:
            st.error(f"❌ Gemini API failed: {type(e).__name__}: {str(e)[:200]}")
else:
    st.warning("Add GEMINI_API_KEY to Streamlit Secrets first")

# ── Configuration Summary ───────────────────────────────────────────────────
st.header("Configuration Summary")

status = {
    "Streamlit Secrets": "✅" if "DATABASE_URL" in st.secrets and "GEMINI_API_KEY" in st.secrets else "❌",
    "Database": "✅ Supabase PostgreSQL" if "DATABASE_URL" in st.secrets else "❌",
    "Gemini API": "✅" if "GEMINI_API_KEY" in st.secrets else "❌",
}

for component, status_text in status.items():
    st.write(f"{status_text} {component}")
