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
import logging

st.set_page_config(page_title="Chat · FinPilot", page_icon="💬", layout="wide")

# ── Custom styling ──────────────────────────────────────────────────────────
st.markdown("""
<style>
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        gap: 1rem;
    }
    .chat-message.user {
        background-color: #e3f2fd;
        flex-direction: row-reverse;
    }
    .chat-message.assistant {
        background-color: #f5f5f5;
    }
    .chat-message.error {
        background-color: #ffebee;
        color: #c62828;
    }
    .message-content {
        flex: 1;
    }
    .streaming-cursor {
        animation: blink 0.7s infinite;
    }
    @keyframes blink {
        0%, 49% { opacity: 1; }
        50%, 100% { opacity: 0; }
    }
</style>
""", unsafe_allow_html=True)

# ── Page Header ─────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 4])
with col1:
    st.image("https://cdn-icons-png.flaticon.com/512/747/747376.png", width=60)
with col2:
    st.title("Financial Data Chatbot")
    st.markdown("💡 Ask questions about your transactions, expenses, and financial data")

st.divider()

company = load_company()
company_id = company.get("id", 1)
base_currency = company.get("base_currency", "ETB")

# Initialize chat history in session state
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Display chat history with better formatting ──────────────────────────────
chat_container = st.container()
with chat_container:
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar="🧑‍💼" if message["role"] == "user" else "🤖"):
            st.markdown(message["content"])

# ── Chat input ──────────────────────────────────────────────────────────────
prompt_input = st.chat_input(
    "💬 Ask about your transactions, expenses, income...",
    key="chat_input"
)

if prompt_input:
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": prompt_input})

    # Display user message immediately
    with st.chat_message("user", avatar="🧑‍💼"):
        st.markdown(prompt_input)

    # Generate and stream response
    with st.chat_message("assistant", avatar="🤖"):
        message_placeholder = st.empty()

        try:
            # Get database URL from secrets or config
            db_url = None
            if "DATABASE_URL" in st.secrets:
                db_url = st.secrets["DATABASE_URL"]
            else:
                from app.config import settings
                db_url = settings.database_url

            # Check if Gemini API key is configured
            gemini_key = None
            if "GEMINI_API_KEY" in st.secrets:
                gemini_key = st.secrets["GEMINI_API_KEY"]
            else:
                from app.config import settings
                gemini_key = settings.gemini_api_key

            if not gemini_key:
                error_msg = "⚠️ **Gemini API Key not configured.** Please add `GEMINI_API_KEY` to Streamlit Cloud Secrets."
                message_placeholder.markdown(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
            else:
                # Show thinking indicator
                message_placeholder.markdown("🔍 **Analyzing your question...**")

                # Get response
                response = chat(prompt_input, company_id=company_id, db_url=db_url)

                # Stream the response (simulate typing effect)
                message_placeholder.empty()
                full_response = ""

                # Simulate streaming by typing out the response
                for chunk in response.split(" "):
                    full_response += chunk + " "
                    message_placeholder.markdown(full_response + " ▌")

                # Final message without cursor
                message_placeholder.markdown(response)

                # Add assistant message to history
                st.session_state.messages.append({"role": "assistant", "content": response})

        except Exception as e:
            error_msg = f"⚠️ **Error**: {str(e)}\n\n**Debug Info:**\n- Check that your database is accessible\n- Verify transactions exist in your database\n- Make sure Gemini API key is valid"
            message_placeholder.markdown(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})

            # Log error for debugging
            st.warning(f"Error details: {type(e).__name__}: {str(e)}")

# ── Example queries sidebar ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📝 Quick Questions")
    st.markdown("Click any example to ask instantly:")

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

    for i, example in enumerate(examples, 1):
        if st.button(
            f"💬 {example}",
            key=f"example_{i}",
            use_container_width=True,
            help=f"Ask: {example}"
        ):
            st.session_state.messages.append({"role": "user", "content": example})
            st.rerun()

    st.markdown("---")

    # Stats section
    st.markdown("### 📊 Chat Stats")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Messages", len(st.session_state.messages))
    with col2:
        st.metric("Database", f"Company #{company_id}")

    st.markdown("---")

    st.markdown("### ℹ️ About")
    st.markdown("""
    **AI-Powered Financial Analysis**

    This chatbot uses Google Gemini to understand natural language questions and convert them into database queries.

    ✨ **Features:**
    - Natural language processing
    - Instant query execution
    - Real-time analysis
    - Formatted insights

    🔒 **Security:**
    - Only reads confirmed transactions
    - Company-isolated data
    - No write operations

    📈 **Free Tier:**
    - 60 requests/minute
    - Unlimited conversations
    """)

    st.markdown("---")

    if st.button("🗑️ Clear History", use_container_width=True, help="Clear all messages"):
        st.session_state.messages = []
        st.rerun()
