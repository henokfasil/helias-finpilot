"""
Report Service — assembles financial report data from the DB and formats it
as Telegram-friendly Markdown text.  AI narrative is injected by reporting agent.
"""
from __future__ import annotations

import calendar
import logging
from collections import defaultdict
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from app.agents import reporting as reporting_agent
from app.models.category import Category
from app.models.counterparty import Counterparty
from app.models.report import Report
from app.models.transaction import Transaction
from app.services import audit_service

logger = logging.getLogger(__name__)

MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


# ── Monthly Report ────────────────────────────────────────────────────────────

def generate_monthly_report(
    db: Session,
    company_id: int,
    company_name: str,
    base_currency: str,
    year: int,
    month: int,
    requested_by_telegram_id: Optional[int] = None,
) -> str:
    month_name = MONTH_NAMES[month]

    # Pull confirmed transactions for the month
    txns = (
        db.query(Transaction)
        .filter(
            Transaction.company_id == company_id,
            Transaction.status == "confirmed",
            extract("year", Transaction.transaction_date) == year,
            extract("month", Transaction.transaction_date) == month,
        )
        .all()
    )

    income = sum(float(t.amount) for t in txns if t.transaction_type == "income")
    expenses = sum(float(t.amount) for t in txns if t.transaction_type == "expense")
    net = income - expenses

    # Category breakdown
    cat_totals: dict[str, float] = defaultdict(float)
    for t in txns:
        if t.transaction_type == "expense":
            cat_name = _category_name(db, t.category_id) or "Uncategorised"
            cat_totals[cat_name] += float(t.amount)

    income_sources: dict[str, float] = defaultdict(float)
    for t in txns:
        if t.transaction_type == "income":
            cp = _counterparty_name(db, t.counterparty_id) or "Unknown"
            income_sources[cp] += float(t.amount)

    pending_count = (
        db.query(func.count(Transaction.id))
        .filter(
            Transaction.company_id == company_id,
            Transaction.status.in_(["draft", "needs_clarification"]),
            extract("year", Transaction.transaction_date) == year,
            extract("month", Transaction.transaction_date) == month,
        )
        .scalar()
        or 0
    )

    # AI narrative
    top_expenses_str = ", ".join(
        f"{k}: {v:,.0f}" for k, v in sorted(cat_totals.items(), key=lambda x: -x[1])[:3]
    ) or "none"
    top_income_str = ", ".join(
        f"{k}: {v:,.0f}" for k, v in sorted(income_sources.items(), key=lambda x: -x[1])[:3]
    ) or "none"

    narrative = reporting_agent.generate_monthly_narrative(
        company_name=company_name,
        month_name=month_name,
        year=year,
        total_income=income,
        total_expenses=expenses,
        currency=base_currency,
        top_expense_categories=top_expenses_str,
        top_income_sources=top_income_str,
        pending_count=pending_count,
    )

    # Format Markdown
    lines = [
        f"📊 *Monthly Report — {month_name} {year}*",
        f"_{company_name}_",
        "",
        f"💰 Income:    `{income:>12,.2f} {base_currency}`",
        f"💸 Expenses:  `{expenses:>12,.2f} {base_currency}`",
        f"📈 Net:       `{net:>12,.2f} {base_currency}`",
        "",
    ]

    if cat_totals:
        lines.append("*Expense Breakdown:*")
        for cat, total in sorted(cat_totals.items(), key=lambda x: -x[1]):
            lines.append(f"  • {cat}: `{total:,.2f}`")
        lines.append("")

    if income_sources:
        lines.append("*Income Sources:*")
        for src, total in sorted(income_sources.items(), key=lambda x: -x[1]):
            lines.append(f"  • {src}: `{total:,.2f}`")
        lines.append("")

    if pending_count:
        lines.append(f"⚠️ Pending/unconfirmed transactions: *{pending_count}*")
        lines.append("")

    lines.append("*Summary:*")
    lines.append(narrative)

    content = "\n".join(lines)

    # Persist the report
    report = Report(
        company_id=company_id,
        report_type="monthly",
        period_year=year,
        period_month=month,
        content=content,
        generated_by_telegram_id=requested_by_telegram_id,
    )
    db.add(report)
    db.flush()

    audit_service.log_event(
        db,
        company_id=company_id,
        action="report_generated",
        entity_type="report",
        entity_id=report.id,
        user_telegram_id=requested_by_telegram_id,
        notes=f"monthly {month_name} {year}",
    )

    return content


# ── Annual Report ─────────────────────────────────────────────────────────────

def generate_annual_report(
    db: Session,
    company_id: int,
    company_name: str,
    base_currency: str,
    year: int,
    requested_by_telegram_id: Optional[int] = None,
) -> str:
    txns = (
        db.query(Transaction)
        .filter(
            Transaction.company_id == company_id,
            Transaction.status == "confirmed",
            extract("year", Transaction.transaction_date) == year,
        )
        .all()
    )

    total_income = sum(float(t.amount) for t in txns if t.transaction_type == "income")
    total_expenses = sum(float(t.amount) for t in txns if t.transaction_type == "expense")
    net = total_income - total_expenses

    # Monthly breakdown
    monthly: dict[int, dict] = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
    for t in txns:
        if t.transaction_date:
            m = t.transaction_date.month
            if t.transaction_type == "income":
                monthly[m]["income"] += float(t.amount)
            elif t.transaction_type == "expense":
                monthly[m]["expense"] += float(t.amount)

    best_month_num = max(monthly, key=lambda m: monthly[m]["income"], default=0)
    best_month = MONTH_NAMES[best_month_num] if best_month_num else "N/A"

    cat_totals: dict[str, float] = defaultdict(float)
    for t in txns:
        if t.transaction_type == "expense":
            cat = _category_name(db, t.category_id) or "Uncategorised"
            cat_totals[cat] += float(t.amount)

    top_expense_cat = max(cat_totals, key=cat_totals.get, default="N/A")  # type: ignore[arg-type]

    pending_count = (
        db.query(func.count(Transaction.id))
        .filter(
            Transaction.company_id == company_id,
            Transaction.status.in_(["draft", "needs_clarification"]),
            extract("year", Transaction.transaction_date) == year,
        )
        .scalar()
        or 0
    )

    flagged_count = (
        db.query(func.count(Transaction.id))
        .filter(
            Transaction.company_id == company_id,
            Transaction.is_duplicate == True,  # noqa: E712
            extract("year", Transaction.transaction_date) == year,
        )
        .scalar()
        or 0
    )

    narrative = reporting_agent.generate_annual_narrative(
        company_name=company_name,
        year=year,
        total_income=total_income,
        total_expenses=total_expenses,
        currency=base_currency,
        best_month=best_month,
        top_expense_category=top_expense_cat,
        transaction_count=len(txns),
        pending_count=pending_count,
        flagged_count=flagged_count,
    )

    lines = [
        f"📋 *Annual Financial Report — {year}*",
        f"_{company_name}_",
        "─" * 35,
        "",
        f"💰 Total Income:    `{total_income:>14,.2f} {base_currency}`",
        f"💸 Total Expenses:  `{total_expenses:>14,.2f} {base_currency}`",
        f"📈 Net Result:      `{net:>14,.2f} {base_currency}`",
        "",
        "*Monthly Breakdown:*",
    ]

    for m in range(1, 13):
        if m in monthly:
            inc = monthly[m]["income"]
            exp = monthly[m]["expense"]
            net_m = inc - exp
            sign = "+" if net_m >= 0 else ""
            lines.append(
                f"  {MONTH_NAMES[m][:3]}: inc `{inc:,.0f}` | exp `{exp:,.0f}` | net `{sign}{net_m:,.0f}`"
            )

    lines.append("")
    if cat_totals:
        lines.append("*Expense by Category:*")
        for cat, total in sorted(cat_totals.items(), key=lambda x: -x[1]):
            pct = (total / total_expenses * 100) if total_expenses else 0
            lines.append(f"  • {cat}: `{total:,.2f}` ({pct:.1f}%)")
        lines.append("")

    if pending_count:
        lines.append(f"⚠️ Unresolved items: *{pending_count}*")
    if flagged_count:
        lines.append(f"🚩 Flagged duplicates: *{flagged_count}*")
    lines.append("")
    lines.append("*Executive Summary:*")
    lines.append(narrative)

    content = "\n".join(lines)

    report = Report(
        company_id=company_id,
        report_type="annual",
        period_year=year,
        period_month=None,
        content=content,
        generated_by_telegram_id=requested_by_telegram_id,
    )
    db.add(report)
    db.flush()

    audit_service.log_event(
        db,
        company_id=company_id,
        action="report_generated",
        entity_type="report",
        entity_id=report.id,
        user_telegram_id=requested_by_telegram_id,
        notes=f"annual {year}",
    )

    return content


# ── Helpers ───────────────────────────────────────────────────────────────────

def _category_name(db: Session, category_id: Optional[int]) -> Optional[str]:
    if not category_id:
        return None
    cat = db.get(Category, category_id)
    return cat.name if cat else None


def _counterparty_name(db: Session, counterparty_id: Optional[int]) -> Optional[str]:
    if not counterparty_id:
        return None
    cp = db.get(Counterparty, counterparty_id)
    return cp.name if cp else None
