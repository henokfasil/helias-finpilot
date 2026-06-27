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
        # More specific prompt with examples for different query types
        prompt = f"""You are a SQL expert. Convert this question to PostgreSQL:

Question: "{user_query}"

Database schema:
- transactions: id, transaction_date, transaction_type, amount, currency, description, category_id, counterparty_id, status, company_id
- categories: id, name, type
- counterparties: id, name

RULES:
1. ALWAYS include: WHERE t.company_id={company_id} AND t.status='confirmed'
2. Always use table aliases: t=transactions, c=categories, cp=counterparties
3. Always use LEFT JOIN for categories and counterparties
4. For "total/sum by category": GROUP BY c.name, SELECT c.name, SUM(t.amount) as total
5. For "by counterparty": GROUP BY cp.name, SELECT cp.name, SUM(t.amount) as total
6. Return ONLY valid SQL, no markdown or explanation

EXAMPLES:

Example 1 - "Show all transactions":
SELECT t.id, t.transaction_date, t.amount, t.description, c.name as category, cp.name as counterparty
FROM transactions t
LEFT JOIN categories c ON t.category_id=c.id
LEFT JOIN counterparties cp ON t.counterparty_id=cp.id
WHERE t.company_id={company_id} AND t.status='confirmed'
ORDER BY t.transaction_date DESC
LIMIT 100

Example 2 - "Total expenses by category":
SELECT c.name as category, SUM(t.amount) as total_amount, COUNT(*) as count
FROM transactions t
LEFT JOIN categories c ON t.category_id=c.id
WHERE t.company_id={company_id} AND t.status='confirmed' AND t.transaction_type='expense'
GROUP BY c.id, c.name
ORDER BY total_amount DESC
LIMIT 100

Example 3 - "Spending by counterparty":
SELECT cp.name as counterparty, SUM(t.amount) as total_spent, COUNT(*) as transaction_count
FROM transactions t
LEFT JOIN counterparties cp ON t.counterparty_id=cp.id
WHERE t.company_id={company_id} AND t.status='confirmed'
GROUP BY cp.id, cp.name
ORDER BY total_spent DESC
LIMIT 100

Now generate the SQL:"""

        logger.info(f"Calling Gemini for: {user_query[:50]}")
        # Use latest flash model (free tier)
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        response = model.generate_content(prompt)
        sql_query = response.text.strip() if response.text else ""

        logger.info(f"Gemini response: {sql_query[:100]}")

        # Clean up response
        if not sql_query:
            logger.warning("Empty SQL response from Gemini")
            return None

        # Remove markdown code blocks
        for delim in ["```sql", "```", "SQL"]:
            sql_query = sql_query.replace(delim, "")
        sql_query = sql_query.strip()

        # Try to extract SQL if wrapped in text
        if "SELECT" in sql_query.upper():
            start_idx = sql_query.upper().find("SELECT")
            sql_query = sql_query[start_idx:].split("\n")[0]  # Get first line

        # Final validation
        if not sql_query.upper().startswith("SELECT"):
            logger.error(f"Invalid SQL response: {sql_query[:80]}")
            return None

        logger.info(f"✅ Generated SQL: {sql_query[:120]}")
        return sql_query

    except Exception as e:
        logger.error(f"SQL generation error: {type(e).__name__}: {str(e)}")
        return None


def execute_query(sql_query: str, db_url: str) -> Optional[list[dict]]:
    """Execute SQL query and return results as list of dicts."""
    try:
        if not db_url:
            logger.error("No database URL provided")
            return None

        logger.info(f"Connecting to database: {db_url[:50]}...")
        engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
            pool_pre_ping=True,  # Test connection before using
        )
        with engine.connect() as conn:
            logger.info(f"Executing query: {sql_query[:80]}...")
            result = conn.execute(text(sql_query))
            rows = result.fetchall()

            if not rows:
                logger.info("Query returned 0 rows")
                return []

            columns = result.keys()
            logger.info(f"Query returned {len(rows)} rows")
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"Database error: {type(e).__name__}: {str(e)[:100]}")
        raise


def format_response(user_query: str, query_results: list[dict]) -> str:
    """
    Use Gemini to format query results into a natural, readable response.
    Falls back to simple formatting if Gemini fails.
    """
    if not query_results:
        return "✅ No transactions found matching your criteria."

    try:
        model = genai.GenerativeModel("gemini-pro")

        # Limit results for context and speed
        display_results = query_results[:20]  # Reduced from 50
        results_json = json.dumps(display_results, indent=2, default=str)

        prompt = f"""Summarize these financial query results in 3-5 sentences:

Question: {user_query}

Results: {results_json}

Be concise and highlight key numbers."""

        # Set timeout implicitly through smaller prompt
        response = model.generate_content(prompt, safety_settings=[
            {"category": "HARM_CATEGORY_UNSPECIFIED", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ])
        if response.text:
            return response.text
        else:
            return _simple_format(query_results)
    except Exception as e:
        logger.error(f"Error formatting response: {e}")
        return _simple_format(query_results)


def _simple_format(results: list[dict]) -> str:
    """Simple fallback formatting without Gemini."""
    if not results:
        return "✅ Query completed with no results."

    # Simple summary
    if len(results) > 10:
        return f"✅ Found {len(results)} transactions. Showing first 10:\n\n{_format_table(results[:10])}"
    else:
        return f"✅ Found {len(results)} transaction(s):\n\n{_format_table(results)}"


def _format_table(results: list[dict]) -> str:
    """Format results as a simple markdown table."""
    if not results:
        return "No data"

    # Get first row's keys as headers
    headers = list(results[0].keys())[:5]  # Limit to 5 columns
    lines = ["|" + "|".join(headers) + "|"]
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")

    for row in results[:10]:
        values = [str(row.get(h, ""))[:30] for h in headers]
        lines.append("|" + "|".join(values) + "|")

    return "\n".join(lines)


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
