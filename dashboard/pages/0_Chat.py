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

# ── Page Header ─────────────────────────────────────────────────────────────
st.title("💬 Financial Data Chatbot")
st.markdown("Ask questions about your transactions, expenses, and financial data")
st.divider()

company = load_company()
company_id = company.get("id", 1)

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

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
            # Get DB URL from secrets first, then fallback to config
            db_url = st.secrets.get("DATABASE_URL", None)
            if not db_url:
                from app.config import settings
                db_url = settings.database_url

            # Get Gemini API key from secrets first, then fallback to config
            gemini_key = st.secrets.get("GEMINI_API_KEY", None)
            if not gemini_key:
                from app.config import settings
                gemini_key = settings.gemini_api_key

            # Validate configuration
            if not gemini_key:
                response = "❌ **Gemini API Key Missing**\n\nPlease add `GEMINI_API_KEY` to Streamlit Cloud Secrets."
            elif not db_url:
                response = "❌ **Database URL Missing**\n\nPlease add `DATABASE_URL` to Streamlit Cloud Secrets."
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
        if st.button(example, use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": example})
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
