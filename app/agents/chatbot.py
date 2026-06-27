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

{get_database_schema()}

User's natural language query: "{user_query}"

TASK: Convert this query to a SQL SELECT statement that:
1. Filters by company_id = {company_id}
2. Only includes 'confirmed' transactions (status = 'confirmed')
3. Joins with categories and counterparties tables as needed
4. Returns relevant fields
5. Orders results meaningfully (usually by transaction_date DESC)

IMPORTANT:
- Return ONLY valid SQL, no explanation
- Use snake_case for column names
- Use single quotes for string literals
- Include JOINs as needed
- Limit to 1000 rows

If the query is about transactions, make sure to JOIN:
LEFT JOIN categories c ON t.category_id = c.id
LEFT JOIN counterparties cp ON t.counterparty_id = cp.id

Example output format:
SELECT t.id, t.transaction_date, t.amount, t.description, c.name as category, cp.name as counterparty
FROM transactions t
LEFT JOIN categories c ON t.category_id = c.id
LEFT JOIN counterparties cp ON t.counterparty_id = cp.id
WHERE t.company_id = {company_id} AND t.status = 'confirmed'
ORDER BY t.transaction_date DESC
LIMIT 100"""

        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content(prompt)
        sql_query = response.text.strip()

        # Remove markdown code blocks if present
        if sql_query.startswith("```"):
            sql_query = sql_query.split("\n", 1)[1]
        if sql_query.endswith("```"):
            sql_query = sql_query.rsplit("\n", 1)[0]

        logger.info(f"Generated SQL: {sql_query}")
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
        model = genai.GenerativeModel("gemini-2.0-flash")

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

    # Step 1: Generate SQL from natural language
    sql_query = generate_sql_query(user_message, company_id)
    if not sql_query:
        return "I couldn't understand your question. Try asking about transactions, expenses, income, or specific counterparties."

    # Step 2: Execute query
    results = execute_query(sql_query, db_url)
    if results is None:
        return "Error querying the database. Please try again."

    # Step 3: Format response
    response = format_response(user_message, results)
    return response
