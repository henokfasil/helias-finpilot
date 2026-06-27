# Chatbot Setup Guide

This guide explains how to set up and use the new **Financial Data Chatbot** feature in FinPilot.

## Overview

The chatbot lets you ask natural language questions about your financial data:
- ✅ "Show me all expenses from last month"
- ✅ "What's my total income by category?"
- ✅ "How much did I spend on Ethio Telecom?"
- ✅ "List pending transactions"

It uses **Google Gemini** (free API with generous limits) to understand your questions and convert them to database queries.

---

## Prerequisites

1. **Google Gemini API Key** (free)
   - Go to [Google AI Studio](https://aistudio.google.com/app/apikeys)
   - Create a new API key
   - Copy the key

2. **Virtual environment** (if not already set up)
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # macOS/Linux
   # or: venv\Scripts\activate  # Windows
   ```

---

## Setup Steps

### 1. Install Dependencies

Your `requirements.txt` already includes `google-generativeai`, but make sure to install:

```bash
# Activate venv first
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Update your `.env` file with your Gemini API key:

```bash
# Copy template if you don't have .env yet
cp .env.example .env

# Edit .env and add:
GEMINI_API_KEY=your_actual_api_key_here
GEMINI_VISION_MODEL=gemini-2.0-flash
```

### 3. Initialize Database (if needed)

If you haven't seeded the database yet:

```bash
python scripts/seed_data.py
```

### 4. Run the Dashboard

```bash
streamlit run dashboard/app.py
```

The new **Chat** page will appear as the first page in the sidebar (💬 Chat).

---

## Using the Chatbot

### In the Streamlit Dashboard

1. Open the **💬 Chat** page
2. Type any natural language question about your transactions
3. The chatbot will:
   - Convert your question to a SQL query
   - Execute it against your database
   - Format the results in a readable response

### Example Questions

- "Show all transactions from last month"
- "What are my total expenses by category?"
- "Which counterparty did I spend the most on?"
- "Show income transactions from the last 6 months"
- "How much did I spend on office supplies?"
- "List all pending transactions"
- "What's my average transaction amount?"

### Quick Buttons

The sidebar includes quick-access example buttons. Click any example to auto-populate the chat.

---

## How It Works

```
User Question
    ↓
Gemini (understands question)
    ↓
Generates SQL Query
    ↓
Execute Against Database
    ↓
Gemini (formats results nicely)
    ↓
Natural Language Response
```

### Key Features

- **Only confirmed transactions** are included (draft/pending are excluded)
- **Automatic company filtering** (company_id = 1 by default)
- **Up to 1000 rows** per query (results are summarized if > 10 rows)
- **Proper JOINs** with categories and counterparties
- **Smart formatting** using Gemini to make results readable

---

## Troubleshooting

### Error: "ModuleNotFoundError: No module named 'google'"

**Solution:** Install dependencies:
```bash
pip install google-generativeai
# or
pip install -r requirements.txt
```

### Error: "I couldn't understand your question"

**Possible causes:**
- Question is too vague or off-topic
- Try rephrasing more specifically: "Show me all expenses" instead of "what's up?"

### Error: "Error querying the database"

**Possible causes:**
- Database not initialized (run `python scripts/seed_data.py`)
- Invalid SQL generated (rare) — try a simpler question

### No Gemini API Key Error

**Solution:**
1. Get a free API key from [Google AI Studio](https://aistudio.google.com/app/apikeys)
2. Add to `.env`: `GEMINI_API_KEY=your_key_here`
3. Restart Streamlit

---

## Customization

### Modify Example Questions

Edit `dashboard/pages/0_Chat.py` line ~85:

```python
examples = [
    "Your custom example 1",
    "Your custom example 2",
    # ... etc
]
```

### Adjust Response Formatting

Edit `app/agents/chatbot.py` function `format_response()` to customize how results are displayed.

### Change Database Schema Context

Edit `get_database_schema()` in `app/agents/chatbot.py` to add more tables or modify the schema description for Gemini.

---

## API Usage & Costs

**Google Gemini Free Tier:**
- **60 requests per minute**
- **1.5M tokens per day**
- **100% free** (as of 2026)

Each chatbot query uses approximately:
- 1 request to understand the question
- 1 request to format the response
- **Total: ~2 requests per question**

At this rate, you can ask **~30 questions per minute** on the free tier.

---

## Architecture

**New Files:**

```
app/agents/
├── chatbot.py          ← New! Chat logic
├── extraction.py       (existing)
└── ...

dashboard/pages/
├── 0_Chat.py          ← New! Streamlit UI
├── 1_Transactions.py  (existing)
└── ...
```

**Module Functions:**

| Function | Purpose |
|----------|---------|
| `chat()` | Main entry point (user message → response) |
| `generate_sql_query()` | NL → SQL conversion using Gemini |
| `execute_query()` | Run SQL against database |
| `format_response()` | Format results nicely using Gemini |

---

## Next Steps

1. ✅ **Set up** — Get Gemini API key and run `pip install -r requirements.txt`
2. ✅ **Test** — Open Dashboard → Chat page, ask a question
3. 🔧 **Customize** — Modify examples or response format as needed
4. 🚀 **Deploy** — Add to your Streamlit Cloud (include `GEMINI_API_KEY` in secrets)

---

## Limitations & Future Improvements

**Current Limitations:**
- Only SELECT queries (no write operations)
- Single company (company_id = 1)
- 1000 row limit per query
- Doesn't support complex multi-step queries

**Potential Improvements:**
- Multi-step reasoning ("What was my trend over Q1?")
- Chart generation from query results
- Saved query templates
- Natural language report generation
- Integration with Telegram bot

---

*For questions or issues, check the troubleshooting section or review the code comments in `app/agents/chatbot.py` and `dashboard/pages/0_Chat.py`.*
