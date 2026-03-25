"""
Reporting Agent — generates AI narrative summaries for financial reports.
All numbers come from the database; AI only writes prose.
"""
from __future__ import annotations

import logging

from openai import OpenAI

from app.config import settings
from app.prompts.reporting import (
    NARRATIVE_SYSTEM_PROMPT,
    MONTHLY_NARRATIVE_PROMPT,
    ANNUAL_NARRATIVE_PROMPT,
)

logger = logging.getLogger(__name__)

_client = OpenAI(api_key=settings.openai_api_key)


def generate_monthly_narrative(
    company_name: str,
    month_name: str,
    year: int,
    total_income: float,
    total_expenses: float,
    currency: str,
    top_expense_categories: str,
    top_income_sources: str,
    pending_count: int,
) -> str:
    """Returns a 3-sentence narrative for a monthly report."""
    net_result = total_income - total_expenses
    user_prompt = MONTHLY_NARRATIVE_PROMPT.format(
        company_name=company_name,
        month_name=month_name,
        year=year,
        total_income=f"{total_income:,.2f}",
        total_expenses=f"{total_expenses:,.2f}",
        net_result=f"{net_result:,.2f}",
        currency=currency,
        top_expense_categories=top_expense_categories,
        top_income_sources=top_income_sources,
        pending_count=pending_count,
    )
    return _call_ai(user_prompt)


def generate_annual_narrative(
    company_name: str,
    year: int,
    total_income: float,
    total_expenses: float,
    currency: str,
    best_month: str,
    top_expense_category: str,
    transaction_count: int,
    pending_count: int,
    flagged_count: int,
) -> str:
    """Returns a 5-sentence narrative for an annual report."""
    net_result = total_income - total_expenses
    user_prompt = ANNUAL_NARRATIVE_PROMPT.format(
        company_name=company_name,
        year=year,
        total_income=f"{total_income:,.2f}",
        total_expenses=f"{total_expenses:,.2f}",
        net_result=f"{net_result:,.2f}",
        currency=currency,
        best_month=best_month,
        top_expense_category=top_expense_category,
        transaction_count=transaction_count,
        pending_count=pending_count,
        flagged_count=flagged_count,
    )
    return _call_ai(user_prompt)


def _call_ai(user_prompt: str) -> str:
    try:
        response = _client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": NARRATIVE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=300,
        )
        return response.choices[0].message.content or "Narrative unavailable."
    except Exception as exc:
        logger.error("ReportingAgent: AI narrative failed: %s", exc)
        return "AI narrative unavailable — please review the figures above."
