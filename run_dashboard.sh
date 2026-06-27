#!/bin/bash

# Quick start script for Helias FinPilot dashboard with chatbot

echo "🚀 Starting Helias FinPilot Dashboard..."
echo ""

# Activate virtual environment
source venv/bin/activate

echo "✅ Virtual environment activated"
echo "📊 Starting Streamlit dashboard..."
echo ""
echo "💡 The dashboard will open in your browser"
echo "💬 Look for the 'Chat' page in the sidebar to use the chatbot!"
echo ""

# Run Streamlit
streamlit run dashboard/app.py
