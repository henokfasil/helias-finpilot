"""
Financial Data Chatbot — Natural language queries to financial database.
Ask questions about transactions, expenses, income, and more.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from dashboard.db import load_company, get_engine
from app.agents.chatbot import chat

st.set_page_config(page_title="Chat · FinPilot", page_icon="💬", layout="wide")

# ── Page Header ─────────────────────────────────────────────────────────────
st.title("💬 Financial Data Chatbot")
st.markdown("Ask natural language questions about your transactions, expenses, and financial data.")

company = load_company()
company_id = company.get("id", 1)
base_currency = company.get("base_currency", "ETB")

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Display chat history ────────────────────────────────────────────────────
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ── Chat input ──────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask about your transactions, expenses, income...", key="chat_input"):
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Analyzing your data..."):
            try:
                db_url = st.secrets.get("DATABASE_URL", None) if "DATABASE_URL" in st.secrets else None
                if not db_url:
                    from app.config import settings
                    db_url = settings.database_url

                response = chat(prompt, company_id=company_id, db_url=db_url)
                st.markdown(response)

                # Add assistant message to history
                st.session_state.messages.append({"role": "assistant", "content": response})

            except Exception as e:
                error_msg = f"⚠️ Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

# ── Example queries sidebar ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📝 Example Queries")

    examples = [
        "Show me all transactions from last month",
        "What are my total expenses by category?",
        "Which counterparty did I spend the most on?",
        "Show income transactions from this year",
        "What's my average transaction amount?",
        "List all pending transactions",
        "Show transactions for Ethio Telecom",
        "How much did I spend on office supplies?",
    ]

    st.markdown("Try asking about:")
    for i, example in enumerate(examples, 1):
        if st.button(f"{i}. {example}", key=f"example_{i}", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": example})
            st.rerun()

    st.markdown("---")
    st.markdown("### ℹ️ About this chatbot")
    st.markdown("""
    This chatbot uses **Google Gemini** to understand your questions and convert them into queries against your financial database.

    **Capabilities:**
    - Search transactions by date, counterparty, or category
    - Analyze spending patterns
    - Generate summaries and insights
    - Answer natural language financial questions

    **Note:** Only "confirmed" transactions are included in responses.
    """)

    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
