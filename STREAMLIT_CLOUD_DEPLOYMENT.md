# Streamlit Cloud Deployment Guide

This guide covers deploying the Financial Data Chatbot to your existing Streamlit Cloud app at `https://helias-finpilot.streamlit.app/`

## Prerequisites

Your Streamlit Cloud app is already connected to your GitHub repository. The chatbot code has been pushed to `main` branch.

## Setup Steps

### 1. Add Gemini API Key to Streamlit Cloud Secrets

1. Go to [https://share.streamlit.io/](https://share.streamlit.io/) and find your app
2. Click on your app's settings (gear icon)
3. Go to **Secrets** tab
4. Add the Gemini API key in TOML format:

```toml
GEMINI_API_KEY = "AIzaSyBGwJ1PZnz0GjHQbBroAoGRE98ErVUQ_fo"
GEMINI_VISION_MODEL = "gemini-2.0-flash"
```

5. Click **Save**

### 2. Rerun Your App

Your Streamlit Cloud app will automatically redeploy when you saved the secrets. If not, click the **"Rerun"** button at the top right.

### 3. Verify Deployment

1. Open your app at **https://helias-finpilot.streamlit.app/**
2. Look for the new **💬 Chat** page in the left sidebar
3. Try asking a question: "Show me all transactions from last month"
4. The chatbot should respond with data from your database

## What Changed

**New Files in Repository:**
- `app/agents/chatbot.py` — Chatbot logic using Gemini
- `dashboard/pages/0_Chat.py` — Chat interface in Streamlit
- `CHATBOT_SETUP.md` — Local setup documentation
- `run_dashboard.sh` — Quick start script (local only)

**Updated Files:**
- `.env.example` — Added Gemini API key placeholder
- `.streamlit/secrets.toml.example` — Added Gemini secrets template

## Troubleshooting

### App shows error: "ModuleNotFoundError: google.generativeai"

**Solution:** Make sure `requirements.txt` includes `google-genai`. It should already be there, but if not:
1. Add `google-genai>=0.1.0` to `requirements.txt`
2. Commit and push to GitHub
3. Streamlit Cloud will auto-redeploy

### Chat page doesn't appear

**Possible causes:**
- Streamlit cache not cleared (try hard refresh: Ctrl+Shift+R or Cmd+Shift+R)
- Streamlit Cloud still deploying (wait a few minutes)
- GEMINI_API_KEY not set in secrets

**Solution:** 
1. Check that GEMINI_API_KEY is in Streamlit Cloud Secrets
2. Click "Rerun" button in your app
3. If still not working, restart the app from Streamlit Cloud admin panel

### "I couldn't understand your question" error

This means the Gemini API call succeeded, but the query is too vague. Try:
- More specific questions: "Show me all expenses" instead of "transactions"
- Include time ranges: "Last 30 days" instead of just "transactions"
- Mention categories: "Show me office supplies expenses"

### "Error querying the database"

This means the generated SQL is invalid. Could indicate:
- Database connection issue (check DATABASE_URL in secrets)
- Column name mismatch (rare)

**Solution:** Check your database is accessible and has transactions in it.

## Database Configuration

Make sure your Streamlit Cloud secrets include:

```toml
DATABASE_URL = "postgresql://user:password@host:5432/finpilot"
```

The chatbot queries this database to answer questions.

## Free Tier Limits

**Gemini Free Tier:**
- 60 requests per minute
- 1.5M tokens per day
- 100% free

**Streamlit Cloud Free Tier:**
- Up to 3 apps
- Always-on (24/7)
- Community support

## Monitoring

To monitor your app's performance:
1. Go to [Streamlit Cloud dashboard](https://share.streamlit.io/)
2. Click on your app
3. View logs and app health

## Making Changes

To modify the chatbot:

1. **Modify example questions** → Edit `dashboard/pages/0_Chat.py`
2. **Change response format** → Edit `app/agents/chatbot.py` (function `format_response`)
3. **Add more context** → Edit `get_database_schema()` in `app/agents/chatbot.py`

Then:
```bash
git add .
git commit -m "Update chatbot configuration"
git push origin main
```

Streamlit Cloud will auto-redeploy within seconds.

## Next Steps

✅ Secrets configured  
✅ Code deployed to GitHub  
⏳ Streamlit Cloud auto-redeploying  
✅ Chat page live at your app URL

Your chatbot is ready to use! Open https://helias-finpilot.streamlit.app/ and find the Chat page.

---

For local development, see `CHATBOT_SETUP.md`.
