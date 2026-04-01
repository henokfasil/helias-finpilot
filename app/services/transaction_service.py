"""
Transaction Service — CRUD and business logic for transactions.
"""
from __future__ import annotations

import json
import logging
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, extract, and_
from sqlalchemy.orm import Session

from app.agents.classification import find_best_category
from app.agents.extraction import ExtractedTransaction
from app.models.counterparty import Counterparty
from app.models.transaction import Transaction
from app.services import audit_service
from app.utils.ethiopian_calendar import gregorian_to_et_string

logger = logging.getLogger(__name__)


# ── Duplicate detection ──────────────────────────────────────────────────────

def check_duplicate(
    db: Session,
    company_id: int,
    amount: Decimal,
    currency: str,
    transaction_date: Optional[date],
    counterparty_name: Optional[str],
) -> Optional[Transaction]:
    """
    Returns an existing transaction that looks like a duplicate.
    Matches on: amount + currency + date (if known) + counterparty name.
    """
    q = db.query(Transaction).filter(
        Transaction.company_id == company_id,
        Transaction.amount == amount,
        Transaction.currency == currency,
        Transaction.status != "rejected",
    )
    if transaction_date:
        q = q.filter(Transaction.transaction_date == transaction_date)
    if counterparty_name:
        q = q.join(Counterparty, isouter=True).filter(
            func.lower(Counterparty.name) == counterparty_name.lower()
        )
    return q.first()


# ── Counterparty helpers ─────────────────────────────────────────────────────

def get_or_create_counterparty(
    db: Session, company_id: int, name: str
) -> Counterparty:
    obj = (
        db.query(Counterparty)
        .filter(
            Counterparty.company_id == company_id,
            func.lower(Counterparty.name) == name.lower(),
        )
        .first()
    )
    if not obj:
        obj = Counterparty(company_id=company_id, name=name)
        db.add(obj)
        db.flush()
    return obj


# ── Create ───────────────────────────────────────────────────────────────────

def create_from_extraction(
    db: Session,
    company_id: int,
    extracted: ExtractedTransaction,
    user_telegram_id: Optional[int] = None,
    user_db_id: Optional[int] = None,
) -> Transaction:
    """
    Persist a new Transaction (status=draft) from an extracted value object.
    Handles counterparty creation and category matching.
    """
    counterparty = None
    if extracted.counterparty:
        counterparty = get_or_create_counterparty(db, company_id, extracted.counterparty)

    category = find_best_category(
        db, company_id, extracted.category_hint, extracted.transaction_type
    )

    et_date_str = None
    if extracted.transaction_date:
        try:
            et_date_str = gregorian_to_et_string(extracted.transaction_date)
        except Exception:
            pass

    tx = Transaction(
        company_id=company_id,
        created_by_id=user_db_id,
        category_id=category.id if category else None,
        counterparty_id=counterparty.id if counterparty else None,
        transaction_type=extracted.transaction_type or "expense",
        transaction_date=extracted.transaction_date,
        transaction_date_et=et_date_str,
        amount=extracted.amount or Decimal("0"),
        currency=extracted.currency or "ETB",
        description=extracted.description,
        payment_method=extracted.payment_method,
        reference_number=extracted.reference_number,
        is_tax_relevant=extracted.is_tax_relevant,
        vat_amount=extracted.vat_amount,
        withholding_tax=extracted.withholding_tax,
        is_vat_inclusive=extracted.is_vat_inclusive,
        raw_text=extracted.raw_text,
        ai_confidence=extracted.confidence,
        ai_ambiguity_flags=json.dumps(extracted.ambiguity_flags),
        status="draft",
    )
    db.add(tx)
    db.flush()

    audit_service.log_event(
        db,
        company_id=company_id,
        action="transaction_created",
        transaction_id=tx.id,
        user_telegram_id=user_telegram_id,
        after_state=_tx_snapshot(tx),
    )
    return tx


# ── Confirm / Reject ─────────────────────────────────────────────────────────

def confirm_transaction(
    db: Session,
    tx: Transaction,
    user_telegram_id: Optional[int] = None,
) -> Transaction:
    before = _tx_snapshot(tx)
    tx.status = "confirmed"
    db.flush()
    audit_service.log_event(
        db,
        company_id=tx.company_id,
        action="transaction_confirmed",
        transaction_id=tx.id,
        user_telegram_id=user_telegram_id,
        before_state=before,
        after_state=_tx_snapshot(tx),
    )
    return tx


def reject_transaction(
    db: Session,
    tx: Transaction,
    user_telegram_id: Optional[int] = None,
    reason: Optional[str] = None,
) -> Transaction:
    before = _tx_snapshot(tx)
    tx.status = "rejected"
    db.flush()
    audit_service.log_event(
        db,
        company_id=tx.company_id,
        action="transaction_rejected",
        transaction_id=tx.id,
        user_telegram_id=user_telegram_id,
        before_state=before,
        notes=reason,
    )
    return tx


# ── Query helpers ────────────────────────────────────────────────────────────

def list_transactions(
    db: Session,
    company_id: int,
    status: Optional[str] = None,
    exclude_statuses: Optional[list] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    limit: int = 20,
    offset: int = 0,
) -> list[Transaction]:
    q = db.query(Transaction).filter(Transaction.company_id == company_id)
    if status:
        q = q.filter(Transaction.status == status)
    if exclude_statuses:
        q = q.filter(Transaction.status.notin_(exclude_statuses))
    if year:
        q = q.filter(extract("year", Transaction.transaction_date) == year)
    if month:
        q = q.filter(extract("month", Transaction.transaction_date) == month)
    return (
        q.order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def monthly_summary(
    db: Session, company_id: int, year: int, month: int
) -> dict:
    """Returns income/expense totals for a given month (confirmed only)."""
    rows = (
        db.query(
            Transaction.transaction_type,
            func.sum(Transaction.amount).label("total"),
            Transaction.currency,
        )
        .filter(
            Transaction.company_id == company_id,
            Transaction.status == "confirmed",
            extract("year", Transaction.transaction_date) == year,
            extract("month", Transaction.transaction_date) == month,
        )
        .group_by(Transaction.transaction_type, Transaction.currency)
        .all()
    )
    result: dict = {"income": {}, "expense": {}, "transfer": {}}
    for row in rows:
        result.setdefault(row.transaction_type, {})[row.currency] = float(row.total or 0)
    return result


def annual_summary(db: Session, company_id: int, year: int) -> dict:
    """Returns full-year income/expense/net and per-month breakdown."""
    rows = (
        db.query(
            Transaction.transaction_type,
            extract("month", Transaction.transaction_date).label("month"),
            Transaction.currency,
            func.sum(Transaction.amount).label("total"),
        )
        .filter(
            Transaction.company_id == company_id,
            Transaction.status == "confirmed",
            extract("year", Transaction.transaction_date) == year,
        )
        .group_by(
            Transaction.transaction_type,
            extract("month", Transaction.transaction_date),
            Transaction.currency,
        )
        .all()
    )
    return {"rows": [dict(r._mapping) for r in rows]}


WHT_THRESHOLD = Decimal("10000")  # ETB — WHT applies only above this amount


def tax_summary(db: Session, company_id: int, year: int, month: Optional[int] = None) -> dict:
    """
    Returns Ethiopian tax obligations for a period (confirmed transactions only).

    Ethiopian law:
    - VAT (15%): on INCOME only — businesses remit 15% of sales revenue to MoR
    - WHT (2%):  on EXPENSE payments > 10,000 ETB only — withheld from supplier payment
    """
    q = db.query(Transaction).filter(
        Transaction.company_id == company_id,
        Transaction.status == "confirmed",
        extract("year", Transaction.transaction_date) == year,
    )
    if month:
        q = q.filter(extract("month", Transaction.transaction_date) == month)

    vat_on_income = Decimal("0")
    wht_on_expenses = Decimal("0")

    for tx in q.all():
        if tx.transaction_type == "income":
            vat_on_income += tx.vat_amount or Decimal("0")
        elif tx.transaction_type == "expense":
            # WHT only applies on expenses > 10,000 ETB
            if (tx.amount or Decimal("0")) > WHT_THRESHOLD:
                wht_on_expenses += tx.withholding_tax or Decimal("0")

    return {
        "vat_on_income": float(vat_on_income),
        "wht_on_expenses": float(wht_on_expenses),
        "total_tax_obligation": float(vat_on_income + wht_on_expenses),
    }


def _tx_snapshot(tx: Transaction) -> dict:
    return {
        "id": tx.id,
        "status": tx.status,
        "amount": str(tx.amount),
        "currency": tx.currency,
        "type": tx.transaction_type,
        "date": str(tx.transaction_date),
    }
