"""
Financial Data Chatbot — Natural language queries to financial database.
Ask questions about transactions, expenses, income, and more.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from dashboard.db import load_company
from app.agents.chatbot import chat

st.set_page_config(page_title="Chat · FinPilot", page_icon="💬", layout="wide")

# ── Get configuration ───────────────────────────────────────────────────────
from app.config import settings

# Database URL - try multiple sources
db_url = None
if "DATABASE_URL" in st.secrets:
    db_url = st.secrets["DATABASE_URL"]

# Debug info (will be shown if issues occur)
debug_info = {
    "has_secrets": "DATABASE_URL" in st.secrets,
    "db_url_preview": db_url[:30] + "..." if db_url else "None",
    "config_db_url": settings.database_url[:30] if settings.database_url else "None"
}

# Gemini API Key
if "GEMINI_API_KEY" in st.secrets:
    gemini_key = st.secrets["GEMINI_API_KEY"]
else:
    gemini_key = settings.gemini_api_key

# ── Page Header ─────────────────────────────────────────────────────────────
st.title("💬 Financial Data Chatbot")
st.markdown("Ask questions about your transactions, expenses, and financial data")
st.divider()

try:
    company = load_company()
    company_id = company.get("id", 1)
except Exception as e:
    st.warning(f"Could not load company info: {e}")
    company_id = 1

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# Handle example button clicks from sidebar
if "selected_example" in st.session_state and st.session_state.selected_example:
    prompt = st.session_state.selected_example
    st.session_state.selected_example = None  # Reset

    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Get response
    try:
        if not gemini_key:
            response = "❌ **Gemini API Key Missing**\n\nPlease add `GEMINI_API_KEY` to Streamlit Cloud Secrets."
        elif not db_url:
            response = """❌ **Database URL Missing**

Please add your production database URL to Streamlit Cloud Secrets:

**Option 1: PostgreSQL**
```
DATABASE_URL = postgresql://user:pass@host:5432/dbname
```

**Option 2: Supabase**
```
DATABASE_URL = postgresql://user:pass@db.supabase.co:5432/postgres
```"""
        else:
            response = chat(prompt, company_id=company_id, db_url=db_url)
    except Exception as e:
        response = f"⚠️ **Error**: {str(e)[:200]}"

    st.session_state.messages.append({"role": "assistant", "content": response})

# ── Display chat history ────────────────────────────────────────────────────
for message in st.session_state.messages:
    with st.chat_message(message["role"], avatar="🧑‍💼" if message["role"] == "user" else "🤖"):
        st.markdown(message["content"])

# ── Chat input ──────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask about your transactions, expenses, income..."):
    # Add user message to history and display
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑‍💼"):
        st.markdown(prompt)

    # Get response
    with st.chat_message("assistant", avatar="🤖"):
        status_placeholder = st.empty()
        status_placeholder.info("🔍 Analyzing your question...")

        try:
            # Validate configuration
            if not gemini_key:
                response = "❌ **Gemini API Key Missing**\n\nPlease add `GEMINI_API_KEY` to Streamlit Cloud Secrets."
            elif not db_url:
                response = """❌ **Database URL Missing**

Please add your production database URL to Streamlit Cloud Secrets:

**Option 1: PostgreSQL (Recommended)**
```
DATABASE_URL = postgresql://username:password@host:5432/dbname
```

**Option 2: Supabase (Free Tier)**
```
DATABASE_URL = postgresql://user:password@db.xxxxx.supabase.co:5432/postgres
```

Go to your app settings → Secrets → add the DATABASE_URL above.

For help getting your database URL, check the docs!"""
            else:
                # Call chatbot
                response = chat(prompt, company_id=company_id, db_url=db_url)

            # Clear status and show response
            status_placeholder.empty()
            st.markdown(response)

            # Add to history
            st.session_state.messages.append({"role": "assistant", "content": response})

        except Exception as e:
            status_placeholder.empty()
            error_msg = f"⚠️ **Error**: {str(e)[:200]}"
            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})

# ── Sidebar with examples ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📝 Example Queries")

    examples = [
        "Show me all transactions",
        "What are my total expenses by category?",
        "Which counterparty did I spend the most on?",
        "Show income transactions from this year",
        "Show transactions for Ethio Telecom",
    ]

    for example in examples:
        if st.button(example, use_container_width=True, key=f"btn_{example}"):
            st.session_state.selected_example = example
            st.rerun()

    st.divider()

    st.markdown("### ℹ️ About")
    st.markdown("""
    Uses **Google Gemini** to understand your questions and query your financial database.

    **Features:**
    - Natural language queries
    - Real-time data analysis
    - Multi-field filtering

    **Security:**
    - Confirmed transactions only
    - Company-isolated
    - Read-only access
    """)

    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
