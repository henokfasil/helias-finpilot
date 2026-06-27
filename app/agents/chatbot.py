"""
Financial chatbot agent — converts natural language queries to SQL and generates responses.
Uses Google Gemini for query understanding and response generation.
"""
import json
import logging
from typing import Optional
from datetime import datetime, timedelta
import google.generativeai as genai
from sqlalchemy import text, create_engine
from app.config import settings

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.gemini_api_key)


def get_database_schema() -> str:
    """Return database schema for Gemini context."""
    return """
    DATABASE SCHEMA:

    transactions (core financial records):
    - id: INTEGER
    - transaction_date: DATE
    - transaction_type: ENUM('income', 'expense', 'transfer')
    - amount: DECIMAL
    - currency: VARCHAR
    - description: TEXT
    - payment_method: VARCHAR
    - status: ENUM('confirmed', 'draft', 'needs_clarification')
    - category_id: INTEGER (foreign key to categories)
    - counterparty_id: INTEGER (foreign key to counterparties)
    - created_at: TIMESTAMP

    categories:
    - id: INTEGER
    - name: VARCHAR
    - type: ENUM('income', 'expense', 'transfer')
    - is_active: BOOLEAN

    counterparties:
    - id: INTEGER
    - name: VARCHAR
    - contact_info: VARCHAR

    companies:
    - id: INTEGER
    - name: VARCHAR
    - base_currency: VARCHAR
    - created_at: TIMESTAMP

    EXAMPLE QUERIES:
    - "Show transactions from last month" → Filter by transaction_date >= now() - interval '1 month'
    - "Total expenses for Ethio Telecom" → SUM(amount) WHERE counterparty.name LIKE 'Ethio Telecom' AND transaction_type = 'expense'
    - "Income by category" → SELECT category.name, SUM(amount) GROUP BY category_id WHERE transaction_type = 'income'
    - "Pending transactions" → WHERE status = 'draft' OR status = 'needs_clarification'
    """


def generate_sql_query(user_query: str, company_id: int = 1) -> Optional[str]:
    """
    Convert natural language query to SQL using Gemini.
    Returns SQL query string or None if unable to generate.
    """
    try:
        prompt = f"""You are a SQL expert for a financial transaction database.
Your job is to convert natural language questions into correct SQL queries.

{get_database_schema()}

User's question: "{user_query}"

RULES:
1. ALWAYS return a valid SQL SELECT statement
2. Filter by: company_id = {company_id} AND status = 'confirmed'
3. Use proper JOINs for categories and counterparties
4. Handle date filters (last month, last year, etc.)
5. ALWAYS include LIMIT 1000
6. Return ONLY the SQL query, nothing else
7. No markdown, no backticks, no explanation

COMMON QUESTION PATTERNS:
- "Show me transactions from [period]" → Filter by transaction_date
- "Total expenses/income by [field]" → Use GROUP BY and SUM
- "[Company name]" → Filter by counterparty.name LIKE '%[name]%'
- "How much" → Use SUM(amount)
- "List/Show" → SELECT appropriate fields
- "Pending" → status = 'draft' OR status = 'needs_clarification'

EXAMPLE QUERIES:
- Last month: WHERE transaction_date >= date('now', '-1 month')
- By category: GROUP BY c.name, sum(amount) as total
- Search counterparty: WHERE cp.name LIKE '%search%'

Generate the SQL now:"""

        model = genai.GenerativeModel("gemini-pro")
        response = model.generate_content(prompt)
        sql_query = response.text.strip()

        # Clean up response
        if not sql_query:
            logger.warning("Empty SQL response from Gemini")
            return None

        # Remove markdown code blocks if present
        if "```" in sql_query:
            sql_query = sql_query.replace("```sql", "").replace("```", "").strip()

        # Validate it looks like SQL
        if not sql_query.upper().startswith("SELECT"):
            logger.warning(f"Response doesn't start with SELECT: {sql_query[:50]}")
            return None

        logger.info(f"Generated SQL: {sql_query[:150]}...")
        return sql_query
    except Exception as e:
        logger.error(f"Error generating SQL: {e}")
        return None


def execute_query(sql_query: str, db_url: str) -> Optional[list[dict]]:
    """Execute SQL query and return results as list of dicts."""
    try:
        engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
        )
        with engine.connect() as conn:
            result = conn.execute(text(sql_query))
            rows = result.fetchall()

            if not rows:
                return []

            columns = result.keys()
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return None


def format_response(user_query: str, query_results: list[dict]) -> str:
    """
    Use Gemini to format query results into a natural, readable response.
    """
    if not query_results:
        return "No transactions found matching your criteria."

    try:
        model = genai.GenerativeModel("gemini-pro")

        # Limit results for context window
        display_results = query_results[:50]
        results_json = json.dumps(display_results, indent=2, default=str)

        prompt = f"""You are a financial analyst assistant.

User's question: "{user_query}"

Database query results:
{results_json}

TASK: Generate a clear, concise, and insightful response to the user's question based on these results.
- Highlight key numbers and trends
- Use currency amounts in a readable format
- Keep response under 200 words
- If there are many results (>10), summarize instead of listing all
- Use markdown formatting for tables if helpful"""

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Error formatting response: {e}")
        # Fallback: format as simple table
        return f"Found {len(query_results)} results:\n\n" + str(query_results[:5])


def chat(user_message: str, company_id: int = 1, db_url: str = None) -> str:
    """
    Main chatbot function. Takes user message and returns AI response.

    Args:
        user_message: Natural language query from user
        company_id: Company/tenant ID
        db_url: Database URL (defaults to settings.database_url)

    Returns:
        Formatted response string
    """
    if not db_url:
        db_url = settings.database_url

    try:
        # Step 1: Generate SQL from natural language
        logger.info(f"Processing query: {user_message[:50]}...")
        sql_query = generate_sql_query(user_message, company_id)

        if not sql_query:
            return "❌ I couldn't understand your question. Try being more specific:\n\n- 'Show me all expenses from last month'\n- 'What are my total expenses by category?'\n- 'Which counterparty did I spend the most on?'"

        # Step 2: Execute query
        logger.info(f"Executing SQL: {sql_query[:100]}...")
        results = execute_query(sql_query, db_url)

        if results is None:
            return "❌ Error connecting to the database. Make sure DATABASE_URL is configured correctly in Streamlit Secrets."

        if not results:
            return f"✅ Query executed successfully, but no results found. Try a different question or date range."

        # Step 3: Format response
        logger.info(f"Formatting response with {len(results)} results...")
        response = format_response(user_message, results)
        return response

    except Exception as e:
        logger.error(f"Chatbot error: {e}", exc_info=True)
        return f"⚠️ Error processing your question: {str(e)[:100]}\n\nPlease try rephrasing or check the app logs."
