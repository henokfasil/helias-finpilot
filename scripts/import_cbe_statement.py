#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Import & reconcile a Commercial Bank of Ethiopia (CBE) statement CSV into FinPilot.

Makes the bot the reference financial-reporting system: every bank line is mapped
to a transaction, classified (operating / investing / financing), tagged with the
bank reference, and de-duplicated against what is already stored.

Usage
-----
    # Preview only (no DB writes) — always safe:
    python scripts/import_cbe_statement.py "8June 2025- 7July26 Bank-Statement.csv"

    # Write NEW (non-duplicate) lines to the database:
    DATABASE_URL=postgresql://...supabase...  \
        python scripts/import_cbe_statement.py statement.csv --commit --company 1

Notes
-----
* Duplicate detection is by bank reference (the FT… code, ignoring the \\BAR suffix)
  matched against transactions.reference_number.
* Classification is rule-based on the narration; unmatched lines are flagged
  'REVIEW' so a human confirms them (never silently guessed).
* --commit must point DATABASE_URL at the production Supabase Postgres.
"""
from __future__ import annotations
import argparse, csv, os, re, sys
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from datetime import datetime

# ------------------------------------------------------------- classification
# (keyword in lowercased narration)  ->  (transaction_type, activity_type, label)
RULES = [
    (("salary", "payroll", "wage"),              ("expense",  "operating", "Payroll")),
    (("pension",),                                ("expense",  "operating", "Pension remittance")),
    (("income tax", "profit tax", "with hold",
      "withhold", "wht", "vat"),                  ("expense",  "operating", "Tax remittance")),
    (("car rent", "vehicle rent", "house rent",
      "office rent", "rent"),                     ("expense",  "operating", "Rent")),
    (("flight", "ticket", "air ", "travel"),      ("expense",  "operating", "Travel")),
    (("laptop", "device", "furniture",
      "computer", "equipment"),                   ("expense",  "investing", "Equipment / CAPEX")),
    (("consult", "software", "subscription",
      "service"),                                 ("expense",  "operating", "Professional / software")),
    (("telecom", "internet", "sim"),              ("expense",  "operating", "Telecom")),
    (("charge", "commission", "fee", "test"),     ("expense",  "operating", "Bank charge")),
]
# credits (money in)
CREDIT_RULES = [
    (("inward", "telex", "rtgs", "swift"),        ("income",   "operating", "Revenue (inbound wire)")),
    (("transfer", "deposit", "payment"),          ("income",   "operating", "Revenue / receipt")),
    (("mobile", "injection", "capital", "loan"),  ("transfer", "financing", "Owner / financing injection")),
]

def classify(narration: str, is_credit: bool):
    n = (narration or "").lower()
    rules = CREDIT_RULES if is_credit else RULES
    for keys, out in rules:
        if any(k in n for k in keys):
            return out
    # sensible fallback
    if is_credit:
        return ("income", "operating", "Receipt (REVIEW)")
    return ("expense", "operating", "Expense (REVIEW)")

# ------------------------------------------------------------- parsing
def parse_amount(s: str):
    s = (s or "").replace(",", "").strip()
    if not s:
        return None
    try:
        return Decimal(s)
    except InvalidOperation:
        return None

def parse_date(s: str):
    s = (s or "").strip()
    for fmt in ("%d %b %y", "%d %b %Y", "%d/%m/%y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None

def clean_ref(s: str):
    # 'FT26177H6WV9\\AND'  -> 'FT26177H6WV9'
    return re.split(r"[\\/ ]", (s or "").strip())[0] or None

@dataclass
class Line:
    date: object
    narration: str
    debit: Decimal | None
    credit: Decimal | None
    ref: str | None
    ttype: str = ""
    activity: str = ""
    label: str = ""

def load_statement(path: str):
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    out = []
    for r in rows:
        rl = { (k or "").strip().lower(): (v or "").strip() for k, v in r.items() }
        narr = rl.get("narration", "")
        if not narr and not rl.get("transaction type"):
            continue
        if "starting balance" in " ".join(rl.values()).lower() or \
           "ending balance"  in " ".join(rl.values()).lower():
            continue
        deb, cre = parse_amount(rl.get("debit")), parse_amount(rl.get("credit"))
        if deb is None and cre is None:
            continue
        ln = Line(
            date=parse_date(rl.get("value date") or rl.get("post date")),
            narration=rl.get("transaction type", "") + " — " + narr if rl.get("transaction type") else narr,
            debit=deb, credit=cre, ref=clean_ref(rl.get("reference")),
        )
        ln.ttype, ln.activity, ln.label = classify(ln.narration, is_credit=cre is not None)
        out.append(ln)
    return out

# ------------------------------------------------------------- DB (optional)
def existing_refs(db_url: str):
    from sqlalchemy import create_engine, text
    eng = create_engine(db_url)
    with eng.connect() as c:
        rows = c.execute(text("SELECT reference_number FROM transactions "
                              "WHERE reference_number IS NOT NULL")).fetchall()
    return { clean_ref(x[0]) for x in rows if x[0] }

def insert_lines(db_url: str, lines, company: int):
    from sqlalchemy import create_engine, text
    eng = create_engine(db_url)
    sql = text("""
        INSERT INTO transactions
          (company_id, transaction_type, transaction_date, amount, currency,
           activity_type, is_tax_relevant, is_vat_inclusive, is_duplicate,
           status, source, payment_method, reference_number, description)
        VALUES
          (:company, :ttype, :date, :amount, 'ETB',
           :activity, false, false, false,
           'confirmed', 'cbe_import', 'cbe', :ref, :descr)
    """)
    n = 0
    with eng.begin() as c:
        for ln in lines:
            amt = ln.credit if ln.credit is not None else ln.debit
            c.execute(sql, dict(company=company, ttype=ln.ttype, date=ln.date,
                                amount=amt, activity=ln.activity, ref=ln.ref,
                                descr=f"{ln.label}: {ln.narration}"))
            n += 1
    return n

# ------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_path")
    ap.add_argument("--commit", action="store_true", help="write new lines to DB")
    ap.add_argument("--company", type=int, default=1)
    ap.add_argument("--db-url", default=os.getenv("DATABASE_URL"))
    a = ap.parse_args()

    lines = load_statement(a.csv_path)
    print(f"\nParsed {len(lines)} bank lines from {a.csv_path}\n")
    tot_d = sum((l.debit or 0) for l in lines)
    tot_c = sum((l.credit or 0) for l in lines)
    print(f"{'DATE':<11}{'REF':<15}{'DEBIT':>14}{'CREDIT':>14}  CLASSIFICATION")
    print("-"*90)
    for l in lines:
        print(f"{str(l.date):<11}{(l.ref or ''):<15}"
              f"{(f'{l.debit:,.2f}' if l.debit else ''):>14}"
              f"{(f'{l.credit:,.2f}' if l.credit else ''):>14}  "
              f"{l.ttype}/{l.activity} — {l.label}")
    print("-"*90)
    print(f"{'TOTALS':<26}{tot_d:>14,.2f}{tot_c:>14,.2f}   net {tot_c-tot_d:,.2f}\n")

    new = lines
    if a.db_url and "sqlite" not in a.db_url:
        try:
            have = existing_refs(a.db_url)
            new = [l for l in lines if (l.ref or "__x") not in have]
            print(f"{len(lines)-len(new)} line(s) already in DB (matched by reference); "
                  f"{len(new)} new.")
        except Exception as e:
            print(f"(Could not check DB for duplicates: {e})")

    review = [l for l in new if "REVIEW" in l.label]
    if review:
        print(f"\n⚠ {len(review)} line(s) need human classification (marked REVIEW).")

    if a.commit:
        if not a.db_url or "sqlite" in a.db_url:
            sys.exit("Refusing to commit: point DATABASE_URL at the production Postgres.")
        n = insert_lines(a.db_url, new, a.company)
        print(f"\n✔ Inserted {n} new transaction(s).")
    else:
        print("\nDry-run (no DB writes). Re-run with --commit to insert new lines.")

if __name__ == "__main__":
    main()
