"""
Prompt templates for AI-generated report narratives.
"""

NARRATIVE_SYSTEM_PROMPT = """
You are a financial reporting assistant for Helias FinPilot.
Your job is to write a concise, professional narrative summary of financial data.

RULES:
1. Base your narrative ONLY on the provided numbers. Do NOT add facts not in the data.
2. Be factual and neutral. Avoid exaggeration.
3. Flag anomalies only if they appear in the data.
4. Write in clear English. 3–5 sentences maximum for each section.
5. Never speculate about reasons for numbers unless clearly stated in the data.
"""

MONTHLY_NARRATIVE_PROMPT = """
Write a 3-sentence financial narrative for {company_name} for {month_name} {year}.

Data:
- Total Income: {total_income} {currency}
- Total Expenses: {total_expenses} {currency}
- Net Result: {net_result} {currency}
- Top expense categories: {top_expense_categories}
- Top income sources: {top_income_sources}
- Pending/unconfirmed transactions: {pending_count}

Write the narrative now.
"""

ANNUAL_NARRATIVE_PROMPT = """
Write a professional 5-sentence annual financial summary for {company_name} for fiscal year {year}.

Data:
- Total Income: {total_income} {currency}
- Total Expenses: {total_expenses} {currency}
- Net Result: {net_result} {currency}
- Best revenue month: {best_month}
- Highest expense category: {top_expense_category}
- Total transactions recorded: {transaction_count}
- Unresolved/pending items: {pending_count}
- Flagged issues: {flagged_count}

Write the summary now.
"""
