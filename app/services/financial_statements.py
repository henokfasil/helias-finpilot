"""
Financial Statements Service
=============================
Computes the three core financial statements from transaction data:

  1. Income Statement (Profit & Loss)
     - Revenue, Operating Expenses, Net Profit

  2. Balance Sheet (Statement of Financial Position)
     - Assets = Liabilities + Equity
     - Cash is derived from transactions; other items come from AccountSnapshot

  3. Cash Flow Statement
     - Operating, Investing, Financing activities
     - Based on activity_type field on Transaction

Ethiopian context:
  - Default currency: ETB
  - VAT (15%) on income is a liability (to remit to MoR)
  - WHT (2%) on expenses > 10,000 ETB is also a liability (to remit to MoR)
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from app.models.account_snapshot import AccountSnapshot
from app.models.category import Category
from app.models.transaction import Transaction


# ── Income Statement ─────────────────────────────────────────────────────────

def income_statement(
    db: Session,
    company_id: int,
    year: int,
    month: Optional[int] = None,
) -> dict:
    """
    Returns a structured Profit & Loss statement.

    Structure:
      revenue          — total confirmed income
      expenses         — total confirmed expenses
      expenses_detail  — list of {category, amount} sorted desc
      gross_profit     — revenue - expenses (operating net)
      vat_on_income    — 15% VAT obligation on income
      wht_on_expenses  — 2% WHT on expenses > 10,000 ETB
      net_profit       — gross_profit (tax figures are shown separately for MoR)
    """
    q = db.query(Transaction).filter(
        Transaction.company_id == company_id,
        Transaction.status == "confirmed",
        extract("year", Transaction.transaction_date) == year,
    )
    if month:
        q = q.filter(extract("month", Transaction.transaction_date) == month)

    revenue = Decimal("0")
    expenses = Decimal("0")
    vat_on_income = Decimal("0")
    wht_on_expenses = Decimal("0")
    expenses_by_category: dict[str, Decimal] = {}

    for tx in q.all():
        amt = tx.amount or Decimal("0")
        if tx.transaction_type == "income":
            revenue += amt
            vat_on_income += tx.vat_amount or Decimal("0")
        elif tx.transaction_type == "expense":
            expenses += amt
            wht_on_expenses += tx.withholding_tax or Decimal("0")
            cat_name = tx.category.name if tx.category else "Uncategorised"
            expenses_by_category[cat_name] = (
                expenses_by_category.get(cat_name, Decimal("0")) + amt
            )

    gross_profit = revenue - expenses
    expenses_detail = sorted(
        [{"category": k, "amount": float(v)} for k, v in expenses_by_category.items()],
        key=lambda x: x["amount"],
        reverse=True,
    )

    return {
        "year": year,
        "month": month,
        "revenue": float(revenue),
        "expenses": float(expenses),
        "gross_profit": float(gross_profit),
        "vat_on_income": float(vat_on_income),
        "wht_on_expenses": float(wht_on_expenses),
        "net_profit": float(gross_profit),
        "expenses_detail": expenses_detail,
    }


# ── Balance Sheet ────────────────────────────────────────────────────────────

_WHT_THRESHOLD = Decimal("10000")


def balance_sheet(
    db: Session,
    company_id: int,
    as_of_date: Optional[date] = None,
) -> dict:
    """
    Returns a structured Balance Sheet.

    Assets = Liabilities + Equity

    ASSETS
      Computed:
        - Cash & Bank (net of all confirmed transactions up to as_of_date)
      Manual (AccountSnapshot, type='asset'):
        - Fixed Assets, Receivables, Other Assets

    LIABILITIES
      Computed:
        - VAT Payable (sum of vat_amount on confirmed income)
        - WHT Payable (sum of withholding_tax on qualifying expenses)
      Manual (AccountSnapshot, type='liability'):
        - Bank Loans, Other Payables

    EQUITY
      Computed:
        - Retained Earnings (cumulative net income from all confirmed transactions)
      Manual (AccountSnapshot, type='equity'):
        - Owner's Capital, Share Capital
    """
    cutoff = as_of_date or date.today()

    # ── All confirmed transactions up to cutoff ───────────────────────────────
    tx_q = db.query(Transaction).filter(
        Transaction.company_id == company_id,
        Transaction.status == "confirmed",
        Transaction.transaction_date <= cutoff,
    )

    total_income = Decimal("0")
    total_expenses = Decimal("0")
    vat_payable = Decimal("0")
    wht_payable = Decimal("0")

    for tx in tx_q.all():
        amt = tx.amount or Decimal("0")
        if tx.transaction_type == "income":
            total_income += amt
            vat_payable += tx.vat_amount or Decimal("0")
        elif tx.transaction_type == "expense":
            total_expenses += amt
            if amt > _WHT_THRESHOLD:
                wht_payable += tx.withholding_tax or Decimal("0")

    retained_earnings = total_income - total_expenses

    # ── Manual AccountSnapshot entries ───────────────────────────────────────
    snap_q = db.query(AccountSnapshot).filter(
        AccountSnapshot.company_id == company_id,
        AccountSnapshot.is_active == True,
        AccountSnapshot.entry_date <= cutoff,
    ).all()

    manual_assets: list[dict] = []
    manual_liabilities: list[dict] = []
    manual_equity: list[dict] = []

    opening_cash_adjustment = Decimal("0")

    for snap in snap_q:
        entry = {
            "name": snap.account_name,
            "subtype": snap.account_subtype or "",
            "amount": float(snap.amount),
            "currency": snap.currency,
            "notes": snap.notes or "",
        }
        if snap.account_type == "asset":
            # Opening cash balance is a special asset — it feeds into computed cash
            if "cash" in snap.account_name.lower() or "bank" in snap.account_name.lower():
                if not snap.account_subtype or snap.account_subtype == "current_asset":
                    opening_cash_adjustment += snap.amount
                    continue  # absorbed into computed cash line
            manual_assets.append(entry)
        elif snap.account_type == "liability":
            manual_liabilities.append(entry)
        elif snap.account_type == "equity":
            manual_equity.append(entry)

    # Computed cash = opening balance + all income - all expenses
    computed_cash = opening_cash_adjustment + total_income - total_expenses

    # ── Totals ────────────────────────────────────────────────────────────────
    total_assets = (
        float(computed_cash)
        + sum(a["amount"] for a in manual_assets)
    )
    total_liabilities = (
        float(vat_payable)
        + float(wht_payable)
        + sum(l["amount"] for l in manual_liabilities)
    )
    total_equity = (
        float(retained_earnings)
        + sum(e["amount"] for e in manual_equity)
    )

    return {
        "as_of_date": str(cutoff),
        "assets": {
            "computed_cash": float(computed_cash),
            "manual_items": manual_assets,
            "total": total_assets,
        },
        "liabilities": {
            "vat_payable": float(vat_payable),
            "wht_payable": float(wht_payable),
            "manual_items": manual_liabilities,
            "total": total_liabilities,
        },
        "equity": {
            "retained_earnings": float(retained_earnings),
            "manual_items": manual_equity,
            "total": total_equity,
        },
        "total_liabilities_and_equity": total_liabilities + total_equity,
        "balanced": abs(total_assets - (total_liabilities + total_equity)) < 0.01,
    }


# ── Cash Flow Statement ──────────────────────────────────────────────────────

def cash_flow_statement(
    db: Session,
    company_id: int,
    year: int,
    month: Optional[int] = None,
) -> dict:
    """
    Returns a structured Cash Flow Statement grouped by activity type.

    OPERATING ACTIVITIES (activity_type='operating'):
      + Income received
      - Expenses paid
      = Net Operating Cash Flow

    INVESTING ACTIVITIES (activity_type='investing'):
      Equipment purchases, asset sales, etc.

    FINANCING ACTIVITIES (activity_type='financing'):
      Loan drawdowns, loan repayments, capital injections

    Net Change in Cash = Operating + Investing + Financing
    """
    q = db.query(Transaction).filter(
        Transaction.company_id == company_id,
        Transaction.status == "confirmed",
        extract("year", Transaction.transaction_date) == year,
    )
    if month:
        q = q.filter(extract("month", Transaction.transaction_date) == month)

    operating_in = Decimal("0")
    operating_out = Decimal("0")
    investing_in = Decimal("0")
    investing_out = Decimal("0")
    financing_in = Decimal("0")
    financing_out = Decimal("0")

    operating_items: list[dict] = []
    investing_items: list[dict] = []
    financing_items: list[dict] = []

    for tx in q.order_by(Transaction.transaction_date).all():
        amt = tx.amount or Decimal("0")
        activity = tx.activity_type or "operating"
        is_income = tx.transaction_type == "income"
        sign = 1 if is_income else -1
        item = {
            "date": str(tx.transaction_date),
            "description": tx.description or (tx.counterparty.name if tx.counterparty else ""),
            "amount": float(amt),
            "direction": "in" if is_income else "out",
        }

        if activity == "operating":
            if is_income:
                operating_in += amt
            else:
                operating_out += amt
            operating_items.append(item)
        elif activity == "investing":
            if is_income:
                investing_in += amt
            else:
                investing_out += amt
            investing_items.append(item)
        elif activity == "financing":
            if is_income:
                financing_in += amt
            else:
                financing_out += amt
            financing_items.append(item)

    net_operating = operating_in - operating_out
    net_investing = investing_in - investing_out
    net_financing = financing_in - financing_out
    net_change = net_operating + net_investing + net_financing

    return {
        "year": year,
        "month": month,
        "operating": {
            "inflows": float(operating_in),
            "outflows": float(operating_out),
            "net": float(net_operating),
            "items": operating_items,
        },
        "investing": {
            "inflows": float(investing_in),
            "outflows": float(investing_out),
            "net": float(net_investing),
            "items": investing_items,
        },
        "financing": {
            "inflows": float(financing_in),
            "outflows": float(financing_out),
            "net": float(net_financing),
            "items": financing_items,
        },
        "net_change_in_cash": float(net_change),
    }
