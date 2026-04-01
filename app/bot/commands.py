"""
Telegram command handlers (/start, /help, /report, etc.)
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.utils import format_transaction_list
from app.database import get_db_context
from app.models.account_snapshot import AccountSnapshot
from app.models.company import Company
from app.models.transaction import Transaction
from app.models.user import User
from app.services import report_service, transaction_service, financial_statements
from app.utils.ethiopian_calendar import gregorian_to_et_string, gregorian_to_et_label

logger = logging.getLogger(__name__)

HELP_TEXT = """
*Helias FinPilot* — AI Financial Assistant

*How to add a transaction:*
Just send a message like:
  • `Paid 3,500 ETB to Ethio Telecom for internet`
  • `Received $400 from Addis Tech for consulting`
  • Or attach an invoice/receipt

*Commands:*
/start — register and get started
/help — show this help
/transactions — list recent transactions
/pending — show unconfirmed items
/summary — quick financial snapshot
/monthly\_report — this month's report
/annual\_report — full year report
/report YYYY-MM — report for specific month
/tax\_summary — Ethiopian VAT & WHT obligations

*Financial Statements:*
/income\_statement — Profit & Loss
/balance\_sheet — Assets, Liabilities & Equity
/cashflow — Cash Flow statement

*Balance Sheet entries:*
/add\_asset name amount — e.g. /add\_asset "Laptop" 75000
/add\_liability name amount — e.g. /add\_liability "Bank Loan" 200000
/add\_equity name amount — e.g. /add\_equity "Owner Capital" 500000
/loan lender amount — e.g. /loan "Henok" 1000000 (records inflow + liability)

*Cash Flow tagging:*
/tag id type — tag tx as investing or financing
  e.g. /tag 12 investing
  e.g. /tag 15 financing

/search keyword — search transactions
/export — export transaction data
"""


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    tg_user = update.effective_user
    chat_id = update.effective_chat.id  # type: ignore[union-attr]

    with get_db_context() as db:
        # Get or create user
        user = db.query(User).filter(User.telegram_id == tg_user.id).first()
        if not user:
            # First user → attach to default company
            company = db.query(Company).first()
            if not company:
                await update.message.reply_text(
                    "⚠️ System not yet initialised. Run `python scripts/seed_data.py` first."
                )
                return
            user = User(
                company_id=company.id,
                telegram_id=tg_user.id,
                telegram_username=tg_user.username,
                full_name=tg_user.full_name,
                role="admin",
            )
            db.add(user)
            db.flush()
            await update.message.reply_text(
                f"👋 Welcome, *{tg_user.first_name}*!\n\n"
                f"You're registered with *{company.name}*.\n\n"
                f"Send me any transaction and I'll extract it for you.\n\n"
                f"Type /help for all commands.",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                f"👋 Welcome back, *{tg_user.first_name}*!\n"
                f"Send a transaction or /help for commands.",
                parse_mode="Markdown",
            )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")


async def cmd_transactions(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    with get_db_context() as db:
        user = _get_user(db, update.effective_user.id)
        if not user:
            await update.message.reply_text("Please /start first.")
            return
        txns = transaction_service.list_transactions(
            db, user.company_id, exclude_statuses=["rejected"], limit=15
        )
        text = format_transaction_list(txns)
        await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_pending(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    with get_db_context() as db:
        user = _get_user(db, update.effective_user.id)
        if not user:
            await update.message.reply_text("Please /start first.")
            return
        txns = transaction_service.list_transactions(
            db, user.company_id, status="draft", limit=10
        )
        if not txns:
            await update.message.reply_text("✅ No pending transactions.")
            return
        text = f"⏳ *{len(txns)} pending transaction(s):*\n\n" + format_transaction_list(txns)
        await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_summary(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    from calendar import monthrange
    today = date.today()
    with get_db_context() as db:
        user = _get_user(db, update.effective_user.id)
        if not user:
            await update.message.reply_text("Please /start first.")
            return
        company = db.get(Company, user.company_id)
        currency = company.base_currency if company else "ETB"

        year, month = today.year, today.month
        summary = transaction_service.monthly_summary(db, user.company_id, year, month)
        income   = summary.get("income",  {}).get(currency, 0)
        expenses = summary.get("expense", {}).get(currency, 0)

        # If current month is empty, fall back to last month
        fallback_note = ""
        if income == 0 and expenses == 0:
            if month == 1:
                year, month = year - 1, 12
            else:
                year, month = year, month - 1
            summary  = transaction_service.monthly_summary(db, user.company_id, year, month)
            income   = summary.get("income",  {}).get(currency, 0)
            expenses = summary.get("expense", {}).get(currency, 0)
            fallback_note = "\n_ℹ️ No data for current month — showing last month._"

        period = date(year, month, 1).strftime("%B %Y")
        net  = income - expenses
        sign = "+" if net >= 0 else ""
        text = (
            f"📊 *{period} Snapshot*\n\n"
            f"💰 Income:   `{income:>12,.2f} {currency}`\n"
            f"💸 Expenses: `{expenses:>12,.2f} {currency}`\n"
            f"📈 Net:      `{sign}{net:>11,.2f} {currency}`"
            f"{fallback_note}"
        )
        await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_monthly_report(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    today = date.today()
    year, month = today.year, today.month
    explicit = False

    # Allow /report YYYY-MM
    if ctx.args:
        try:
            parts = ctx.args[0].split("-")
            year, month = int(parts[0]), int(parts[1])
            explicit = True
        except Exception:
            await update.message.reply_text("Usage: /report YYYY-MM")
            return

    with get_db_context() as db:
        user = _get_user(db, update.effective_user.id)
        if not user:
            await update.message.reply_text("Please /start first.")
            return
        company = db.get(Company, user.company_id)
        if not company:
            return

        # If no explicit period given and current month is empty, use last month
        if not explicit:
            summary = transaction_service.monthly_summary(db, user.company_id, year, month)
            currency = company.base_currency or "ETB"
            if not summary.get("income", {}).get(currency) and not summary.get("expense", {}).get(currency):
                if month == 1:
                    year, month = year - 1, 12
                else:
                    year, month = year, month - 1

        await update.message.reply_text("⏳ Generating report…")
        content = report_service.generate_monthly_report(
            db,
            company_id=company.id,
            company_name=company.name,
            base_currency=company.base_currency,
            year=year,
            month=month,
            requested_by_telegram_id=update.effective_user.id,
        )
    await _send_long(update, content)


async def cmd_annual_report(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    year = date.today().year
    if ctx.args:
        try:
            year = int(ctx.args[0])
        except ValueError:
            await update.message.reply_text("Usage: /annual_report YYYY")
            return

    with get_db_context() as db:
        user = _get_user(db, update.effective_user.id)
        if not user:
            await update.message.reply_text("Please /start first.")
            return
        company = db.get(Company, user.company_id)
        if not company:
            return
        await update.message.reply_text("⏳ Generating annual report…")
        content = report_service.generate_annual_report(
            db,
            company_id=company.id,
            company_name=company.name,
            base_currency=company.base_currency,
            year=year,
            requested_by_telegram_id=update.effective_user.id,
        )
    await _send_long(update, content)


async def cmd_search(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    keyword = " ".join(ctx.args) if ctx.args else ""
    if not keyword:
        await update.message.reply_text("Usage: /search keyword")
        return

    with get_db_context() as db:
        user = _get_user(db, update.effective_user.id)
        if not user:
            await update.message.reply_text("Please /start first.")
            return
        txns = (
            db.query(Transaction)
            .filter(
                Transaction.company_id == user.company_id,
                Transaction.description.ilike(f"%{keyword}%"),
            )
            .order_by(Transaction.transaction_date.desc())
            .limit(10)
            .all()
        )
        text = f"🔍 *Search: `{keyword}`*\n\n" + format_transaction_list(txns)
        await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_export(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """Export recent confirmed transactions as a CSV-like text."""
    if not update.effective_user or not update.message:
        return
    with get_db_context() as db:
        user = _get_user(db, update.effective_user.id)
        if not user:
            await update.message.reply_text("Please /start first.")
            return
        txns = transaction_service.list_transactions(
            db, user.company_id, status="confirmed", limit=100
        )
        if not txns:
            await update.message.reply_text("No confirmed transactions to export.")
            return
        lines = ["date,type,amount,currency,counterparty,description,category,status"]
        for t in txns:
            cp = t.counterparty.name if t.counterparty else ""
            cat = t.category.name if t.category else ""
            lines.append(
                f"{t.transaction_date},{t.transaction_type},"
                f"{t.amount},{t.currency},{cp!r},{(t.description or '')!r},{cat},{t.status}"
            )
        csv_text = "\n".join(lines)
        await update.message.reply_document(
            document=csv_text.encode(),
            filename="transactions_export.csv",
            caption="Transaction export",
        )


async def cmd_receipts(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /receipts          — list all receipts for this year
    /receipts 2026-03  — list receipts for a specific month
    """
    if not update.effective_user or not update.message:
        return
    today = date.today()
    year, month = today.year, None

    if ctx.args:
        try:
            parts = ctx.args[0].split("-")
            year = int(parts[0])
            month = int(parts[1]) if len(parts) > 1 else None
        except Exception:
            await update.message.reply_text("Usage: /receipts or /receipts YYYY-MM")
            return

    from app.services.file_service import list_attachments_for_period
    from app.models.counterparty import Counterparty

    with get_db_context() as db:
        user = _get_user(db, update.effective_user.id)
        if not user:
            await update.message.reply_text("Please /start first.")
            return

        attachments = list_attachments_for_period(db, user.company_id, year, month)

        if not attachments:
            period = f"{year}-{month:02d}" if month else str(year)
            await update.message.reply_text(f"No receipts found for {period}.")
            return

        period_label = f"{year}-{month:02d}" if month else str(year)
        lines = [f"🗂 *Receipts — {period_label}* ({len(attachments)} files)\n"]
        for att in attachments:
            tx = att.transaction
            if tx:
                cp = tx.counterparty.name if tx.counterparty else "—"
                lines.append(
                    f"📎 `{tx.transaction_date}` · {att.file_type or 'file'} · "
                    f"{cp} · tx#{tx.id}"
                )
            else:
                lines.append(f"📎 `{att.original_filename}` (not yet linked to a transaction)")

        lines.append(f"\n_Use /export\\_receipts {year} to download all as a ZIP file._")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_export_receipts(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /export_receipts        — ZIP all receipts for this year
    /export_receipts 2026   — ZIP all receipts for a specific year
    /export_receipts 2026-03 — ZIP receipts for a specific month
    """
    if not update.effective_user or not update.message:
        return
    today = date.today()
    year, month = today.year, None

    if ctx.args:
        try:
            parts = ctx.args[0].split("-")
            year = int(parts[0])
            month = int(parts[1]) if len(parts) > 1 else None
        except Exception:
            await update.message.reply_text("Usage: /export_receipts YYYY or /export_receipts YYYY-MM")
            return

    from app.services.file_service import build_zip_for_period

    period_label = f"{year}-{month:02d}" if month else str(year)
    await update.message.reply_text(f"⏳ Bundling receipts for {period_label}…")

    with get_db_context() as db:
        user = _get_user(db, update.effective_user.id)
        if not user:
            await update.message.reply_text("Please /start first.")
            return
        zip_bytes, zip_filename = build_zip_for_period(db, user.company_id, year, month)

    if not zip_bytes:
        await update.message.reply_text(f"No receipt files found for {period_label}.")
        return

    size_kb = len(zip_bytes) / 1024
    await update.message.reply_document(
        document=zip_bytes,
        filename=zip_filename,
        caption=(
            f"📦 *Receipts — {period_label}*\n"
            f"Size: {size_kb:.1f} KB\n"
            f"_Keep this ZIP file as evidence for the Ministry of Revenue._"
        ),
        parse_mode="Markdown",
    )


async def cmd_delete(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /delete <id>          — delete one transaction
    /delete 1 2 3         — delete multiple transactions
    /delete 1-5           — delete a range
    """
    if not update.effective_user or not update.message:
        return
    if not ctx.args:
        await update.message.reply_text(
            "Usage:\n"
            "  `/delete 5` — delete one\n"
            "  `/delete 1 2 3` — delete multiple\n"
            "  `/delete 1-5` — delete a range\n\n"
            "Find IDs with /transactions",
            parse_mode="Markdown",
        )
        return

    # Parse IDs — support: "1 2 3", "1,2,3", "1-5", or any mix
    ids_to_delete: list[int] = []
    # Flatten all args, splitting by commas too (Telegram may send "1,2,3" as one arg)
    raw_tokens = " ".join(ctx.args).replace(",", " ").split()
    for arg in raw_tokens:
        arg = arg.strip()
        if not arg:
            continue
        if "-" in arg:
            try:
                start, end = arg.split("-", 1)
                ids_to_delete.extend(range(int(start), int(end) + 1))
            except ValueError:
                await update.message.reply_text(f"Invalid range: `{arg}`. Use format: 1-5", parse_mode="Markdown")
                return
        else:
            try:
                ids_to_delete.append(int(arg))
            except ValueError:
                await update.message.reply_text(f"Invalid ID: `{arg}`. Must be a number.", parse_mode="Markdown")
                return

    ids_to_delete = list(set(ids_to_delete))  # deduplicate

    deleted, not_found, already_deleted = [], [], []

    with get_db_context() as db:
        user = _get_user(db, update.effective_user.id)
        if not user:
            await update.message.reply_text("Please /start first.")
            return
        for tx_id in ids_to_delete:
            tx = db.query(Transaction).filter(
                Transaction.id == tx_id,
                Transaction.company_id == user.company_id,
            ).first()
            if not tx:
                not_found.append(tx_id)
            elif tx.status == "rejected":
                already_deleted.append(tx_id)
            else:
                transaction_service.reject_transaction(db, tx, update.effective_user.id, reason="deleted by user")
                deleted.append(tx_id)

    lines = []
    if deleted:
        ids_str = ", ".join(f"#{i}" for i in deleted)
        lines.append(f"🗑 Deleted: *{ids_str}*")
    if already_deleted:
        ids_str = ", ".join(f"#{i}" for i in already_deleted)
        lines.append(f"⚠️ Already deleted: {ids_str}")
    if not_found:
        ids_str = ", ".join(f"#{i}" for i in not_found)
        lines.append(f"❌ Not found: {ids_str}")
    lines.append("_(Deleted transactions remain in audit log for compliance.)_")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_tax_summary(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /tax_summary         — current month
    /tax_summary YYYY-MM — specific month
    /tax_summary YYYY    — full year
    """
    if not update.effective_user or not update.message:
        return

    today = date.today()
    year, month = today.year, today.month

    if ctx.args:
        try:
            parts = ctx.args[0].split("-")
            year = int(parts[0])
            month = int(parts[1]) if len(parts) > 1 else None  # type: ignore[assignment]
        except Exception:
            await update.message.reply_text("Usage: /tax_summary, /tax_summary YYYY-MM, or /tax_summary YYYY")
            return
    else:
        month = today.month

    with get_db_context() as db:
        user = _get_user(db, update.effective_user.id)
        if not user:
            await update.message.reply_text("Please /start first.")
            return
        company = db.get(Company, user.company_id)
        currency = company.base_currency if company else "ETB"
        tax = transaction_service.tax_summary(db, user.company_id, year, month)

    period = f"{year}-{month:02d}" if month else str(year)

    lines = [
        f"🧾 *Ethiopian Tax Summary — {period}*",
        f"_(Confirmed transactions only)_",
        "",
        f"*VAT (15%) — on income only*",
        f"  VAT on sales/income:     `{tax['vat_on_income']:>12,.2f} {currency}`",
        "",
        f"*WHT (2%) — expenses > 10,000 ETB only*",
        f"  WHT on large expenses:   `{tax['wht_on_expenses']:>12,.2f} {currency}`",
        "",
        f"  ────────────────────────────────────",
        f"*Total to remit to MoR:   `{tax['total_tax_obligation']:>12,.2f} {currency}`*",
        "",
        "_File and pay at your local MoR branch by the 30th of the following month._",
    ]

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ── Cash Flow tagging ────────────────────────────────────────────────────────

async def cmd_tag(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /tag <id> <type>
    Tag a transaction's activity type for the Cash Flow Statement.
    Types: operating (default) | investing | financing

    Examples:
      /tag 12 investing   — laptop purchase
      /tag 15 financing   — bank loan received
      /tag 8 operating    — reset to default
    """
    if not update.effective_user or not update.message:
        return

    if not ctx.args or len(ctx.args) < 2:
        await update.message.reply_text(
            "Usage: `/tag <id> <type>`\n\n"
            "Types: `operating`, `investing`, `financing`\n\n"
            "Examples:\n"
            "  `/tag 12 investing` — equipment purchase\n"
            "  `/tag 15 financing` — bank loan\n\n"
            "Find IDs with /transactions",
            parse_mode="Markdown",
        )
        return

    try:
        tx_id = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("First argument must be a transaction ID number.")
        return

    activity = ctx.args[1].lower().strip()
    if activity not in ("operating", "investing", "financing"):
        await update.message.reply_text(
            "Activity type must be one of: `operating`, `investing`, `financing`",
            parse_mode="Markdown",
        )
        return

    with get_db_context() as db:
        user = _get_user(db, update.effective_user.id)
        if not user:
            await update.message.reply_text("Please /start first.")
            return
        tx = db.query(Transaction).filter(
            Transaction.id == tx_id,
            Transaction.company_id == user.company_id,
        ).first()
        if not tx:
            await update.message.reply_text(f"Transaction #{tx_id} not found.")
            return
        old_type = tx.activity_type or "operating"
        tx.activity_type = activity

    emoji = {"operating": "🔧", "investing": "🏗", "financing": "🏦"}.get(activity, "")
    await update.message.reply_text(
        f"{emoji} Transaction *#{tx_id}* tagged as *{activity}*.\n"
        f"_(was: {old_type})_\n\n"
        f"Amount: `{tx.amount:,.2f} {tx.currency}` — {tx.description or ''}",
        parse_mode="Markdown",
    )


# ── Balance Sheet manual entries ──────────────────────────────────────────────

async def _add_balance_sheet_entry(
    update: Update,
    ctx: ContextTypes.DEFAULT_TYPE,
    account_type: str,
    subtype: str,
    type_label: str,
    emoji: str,
) -> None:
    """Shared logic for /add_asset, /add_liability, /add_equity."""
    if not update.effective_user or not update.message:
        return

    # Usage: /add_asset "Laptop & Equipment" 75000
    # or:    /add_asset Laptop 75000
    if not ctx.args or len(ctx.args) < 2:
        await update.message.reply_text(
            f"Usage: `/{type_label} \"Account Name\" amount [currency] [YYYY-MM-DD]`\n\n"
            f"Examples:\n"
            f"  `/{type_label} \"Laptop & Equipment\" 75000`\n"
            f"  `/{type_label} \"Bank Loan\" 200000 ETB 2026-01-15`\n\n"
            f"Currency defaults to ETB. Date defaults to today.",
            parse_mode="Markdown",
        )
        return

    # Parse: name may be quoted or just a single word; amount is last numeric arg
    args = ctx.args
    # Find the amount (last numeric-looking arg before optional currency/date)
    amount_idx = None
    for i, a in enumerate(args):
        try:
            float(a.replace(",", ""))
            amount_idx = i
            break
        except ValueError:
            continue

    if amount_idx is None:
        await update.message.reply_text("Could not parse amount. Example: `/add_asset \"Equipment\" 75000`",
                                        parse_mode="Markdown")
        return

    name = " ".join(args[:amount_idx]).strip('"').strip("'").strip()
    if not name:
        await update.message.reply_text("Please provide an account name before the amount.")
        return

    try:
        from decimal import Decimal
        amount = Decimal(args[amount_idx].replace(",", ""))
    except Exception:
        await update.message.reply_text("Invalid amount.")
        return

    # Optional: currency and date from remaining args
    remaining = args[amount_idx + 1:]
    currency = "ETB"
    entry_date = date.today()
    for r in remaining:
        if r.upper() in ("ETB", "USD", "EUR"):
            currency = r.upper()
        else:
            try:
                entry_date = date.fromisoformat(r)
            except ValueError:
                pass

    with get_db_context() as db:
        user = _get_user(db, update.effective_user.id)
        if not user:
            await update.message.reply_text("Please /start first.")
            return
        snap = AccountSnapshot(
            company_id=user.company_id,
            account_name=name,
            account_type=account_type,
            account_subtype=subtype,
            amount=amount,
            currency=currency,
            entry_date=entry_date,
            is_active=True,
        )
        db.add(snap)
        db.flush()
        snap_id = snap.id

    await update.message.reply_text(
        f"{emoji} *{account_type.capitalize()}* entry saved (ID: {snap_id})\n\n"
        f"Name:     `{name}`\n"
        f"Amount:   `{amount:,.2f} {currency}`\n"
        f"Date:     `{entry_date}`\n"
        f"Type:     `{account_type} / {subtype}`\n\n"
        f"This will appear in your Balance Sheet immediately.\n"
        f"Use `/remove_entry {snap_id}` to delete it.",
        parse_mode="Markdown",
    )


async def cmd_add_asset(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /add_asset "Name" amount [currency] [date]
    Add a fixed or current asset to the Balance Sheet.

    Examples:
      /add_asset "Laptop & Equipment" 75000
      /add_asset "Accounts Receivable" 50000 ETB 2026-03-01
      /add_asset "Opening Cash Balance" 100000
    """
    await _add_balance_sheet_entry(update, ctx, "asset", "fixed_asset", "add_asset", "🏢")


async def cmd_add_liability(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /add_liability "Name" amount [currency] [date]
    Add a liability to the Balance Sheet.

    Examples:
      /add_liability "CBE Bank Loan" 500000
      /add_liability "Accounts Payable" 30000 ETB 2026-03-15
    """
    await _add_balance_sheet_entry(update, ctx, "liability", "long_term_liability", "add_liability", "📋")


async def cmd_add_equity(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /add_equity "Name" amount [currency] [date]
    Add an equity entry (owner's capital, share capital) to the Balance Sheet.

    Examples:
      /add_equity "Owner Capital Injection" 500000
      /add_equity "Share Capital" 1000000 ETB 2026-01-01
    """
    await _add_balance_sheet_entry(update, ctx, "equity", "capital", "add_equity", "💼")


async def cmd_loan(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /loan "Lender Name" amount [currency] [YYYY-MM-DD]

    Records a loan received in one step:
      1. A confirmed 'transfer' transaction (financing) — cash inflow
      2. A 'Loan Payable' liability in the Balance Sheet

    Examples:
      /loan "Henok" 1000000
      /loan "CBE Bank" 500000 ETB 2026-04-01
    """
    if not update.effective_user or not update.message:
        return

    if not ctx.args or len(ctx.args) < 2:
        await update.message.reply_text(
            "Usage: `/loan \"Lender Name\" amount [currency] [YYYY-MM-DD]`\n\n"
            "Examples:\n"
            "  `/loan \"Henok\" 1000000`\n"
            "  `/loan \"CBE Bank\" 500000 ETB 2026-04-01`\n\n"
            "This records:\n"
            "  • Cash inflow transaction (financing)\n"
            "  • Loan Payable liability on Balance Sheet",
            parse_mode="Markdown",
        )
        return

    args = ctx.args
    # Find amount (first numeric arg)
    amount_idx = None
    for i, a in enumerate(args):
        try:
            float(a.replace(",", ""))
            amount_idx = i
            break
        except ValueError:
            continue

    if amount_idx is None:
        await update.message.reply_text("Could not parse amount. Example: `/loan \"Henok\" 1000000`", parse_mode="Markdown")
        return

    lender = " ".join(args[:amount_idx]).strip('"').strip("'").strip()
    if not lender:
        await update.message.reply_text("Please provide a lender name before the amount.")
        return

    try:
        from decimal import Decimal
        amount = Decimal(args[amount_idx].replace(",", ""))
    except Exception:
        await update.message.reply_text("Invalid amount.")
        return

    remaining = args[amount_idx + 1:]
    currency = "ETB"
    entry_date = date.today()
    for r in remaining:
        if r.upper() in ("ETB", "USD", "EUR"):
            currency = r.upper()
        else:
            try:
                entry_date = date.fromisoformat(r)
            except ValueError:
                pass

    with get_db_context() as db:
        user = _get_user(db, update.effective_user.id)
        if not user:
            await update.message.reply_text("Please /start first.")
            return

        # 1. Cash inflow transaction (transfer, financing activity)
        counterparty = transaction_service.get_or_create_counterparty(db, user.company_id, lender)
        tx = Transaction(
            company_id=user.company_id,
            created_by_id=user.id,
            counterparty_id=counterparty.id,
            transaction_type="transfer",
            activity_type="financing",
            transaction_date=entry_date,
            transaction_date_et=gregorian_to_et_string(entry_date),
            amount=amount,
            currency=currency,
            description=f"Loan received from {lender}",
            status="confirmed",
            ai_confidence=1.0,
        )
        db.add(tx)
        db.flush()
        tx_id = tx.id

        # 2. Loan Payable liability on Balance Sheet
        snap = AccountSnapshot(
            company_id=user.company_id,
            account_name=f"Loan Payable — {lender}",
            account_type="liability",
            account_subtype="long_term_liability",
            amount=amount,
            currency=currency,
            entry_date=entry_date,
            notes=f"Linked to transaction #{tx_id}",
            is_active=True,
        )
        db.add(snap)
        db.flush()
        snap_id = snap.id

    await update.message.reply_text(
        f"🏦 *Loan recorded successfully*\n\n"
        f"Lender:    `{lender}`\n"
        f"Amount:    `{amount:,.2f} {currency}`\n"
        f"Date:      `{entry_date}`\n\n"
        f"✅ Transaction *#{tx_id}* — cash inflow (financing)\n"
        f"📋 Balance Sheet entry *#{snap_id}* — Loan Payable\n\n"
        f"_When you repay the loan, use /loan\\_repay or record the expense manually._",
        parse_mode="Markdown",
    )


async def cmd_remove_entry(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /remove_entry <id>
    Deactivate (soft-delete) a Balance Sheet entry from account_snapshots.
    """
    if not update.effective_user or not update.message:
        return

    if not ctx.args:
        await update.message.reply_text("Usage: `/remove_entry <id>`", parse_mode="Markdown")
        return

    try:
        entry_id = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("ID must be a number.")
        return

    with get_db_context() as db:
        user = _get_user(db, update.effective_user.id)
        if not user:
            await update.message.reply_text("Please /start first.")
            return
        snap = db.query(AccountSnapshot).filter(
            AccountSnapshot.id == entry_id,
            AccountSnapshot.company_id == user.company_id,
        ).first()
        if not snap:
            await update.message.reply_text(f"Entry #{entry_id} not found.")
            return
        snap.is_active = False
        name = snap.account_name
        amount = snap.amount
        currency = snap.currency

    await update.message.reply_text(
        f"🗑 Entry *#{entry_id}* (`{name}` — `{amount:,.2f} {currency}`) removed from Balance Sheet.",
        parse_mode="Markdown",
    )


async def cmd_bs_entries(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /bs_entries
    List all active Balance Sheet manual entries (account_snapshots).
    """
    if not update.effective_user or not update.message:
        return

    with get_db_context() as db:
        user = _get_user(db, update.effective_user.id)
        if not user:
            await update.message.reply_text("Please /start first.")
            return
        entries = (
            db.query(AccountSnapshot)
            .filter(
                AccountSnapshot.company_id == user.company_id,
                AccountSnapshot.is_active == True,
            )
            .order_by(AccountSnapshot.account_type, AccountSnapshot.account_name)
            .all()
        )

    if not entries:
        await update.message.reply_text(
            "No Balance Sheet entries yet.\n\n"
            "Add some with:\n"
            "  `/add_asset \"Equipment\" 75000`\n"
            "  `/add_liability \"Bank Loan\" 200000`\n"
            "  `/add_equity \"Owner Capital\" 500000`",
            parse_mode="Markdown",
        )
        return

    type_emoji = {"asset": "🏢", "liability": "📋", "equity": "💼"}
    current_type = None
    lines = ["📊 *Balance Sheet Manual Entries*\n"]

    for e in entries:
        if e.account_type != current_type:
            current_type = e.account_type
            lines.append(f"\n*{current_type.upper()}S*")
        lines.append(
            f"  `#{e.id}` {type_emoji.get(e.account_type, '')} {e.account_name[:25]:<25} "
            f"`{e.amount:>10,.0f} {e.currency}`"
        )

    lines.append(f"\n_Use /remove\\_entry <id> to delete an entry._")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ── Financial Statements ──────────────────────────────────────────────────────

async def cmd_income_statement(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /income_statement         — current year P&L
    /income_statement YYYY    — specific year
    /income_statement YYYY-MM — specific month
    """
    if not update.effective_user or not update.message:
        return
    today = date.today()
    year, month = today.year, None

    if ctx.args:
        try:
            parts = ctx.args[0].split("-")
            year = int(parts[0])
            month = int(parts[1]) if len(parts) > 1 else None
        except Exception:
            await update.message.reply_text("Usage: /income_statement, /income_statement YYYY, or /income_statement YYYY-MM")
            return

    with get_db_context() as db:
        user = _get_user(db, update.effective_user.id)
        if not user:
            await update.message.reply_text("Please /start first.")
            return
        company = db.get(Company, user.company_id)
        currency = company.base_currency if company else "ETB"
        stmt = financial_statements.income_statement(db, user.company_id, year, month)

    period = f"{year}-{month:02d}" if month else str(year)
    margin = (stmt["net_profit"] / stmt["revenue"] * 100) if stmt["revenue"] > 0 else 0

    lines = [
        f"📊 *Income Statement — {period}*",
        f"_(Confirmed transactions only)_",
        "",
        f"*REVENUE*",
        f"  Sales / Service Income:   `{stmt['revenue']:>12,.2f} {currency}`",
        "",
        f"*OPERATING EXPENSES*",
    ]
    for item in stmt["expenses_detail"][:8]:
        lines.append(f"  {item['category'][:20]:<20} `{item['amount']:>10,.2f}`")
    lines += [
        f"  {'TOTAL EXPENSES':<20} `{stmt['expenses']:>10,.2f} {currency}`",
        "",
        f"  ────────────────────────────────────",
        f"*GROSS PROFIT:  `{stmt['gross_profit']:>11,.2f} {currency}`*",
        "",
        f"*TAX OBLIGATIONS (separate — remit to MoR)*",
        f"  VAT Payable (15%):   `{stmt['vat_on_income']:>12,.2f} {currency}`",
        f"  WHT Payable (2%):    `{stmt['wht_on_expenses']:>12,.2f} {currency}`",
        "",
        f"  ────────────────────────────────────",
        f"*NET PROFIT:    `{stmt['net_profit']:>11,.2f} {currency}`*",
        f"  Margin: `{margin:.1f}%`",
    ]

    await _send_long(update, "\n".join(lines))


async def cmd_balance_sheet(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /balance_sheet            — as of today
    /balance_sheet YYYY-MM-DD — as of specific date
    """
    if not update.effective_user or not update.message:
        return

    as_of = date.today()
    if ctx.args:
        try:
            as_of = date.fromisoformat(ctx.args[0])
        except Exception:
            await update.message.reply_text("Usage: /balance_sheet or /balance_sheet YYYY-MM-DD")
            return

    with get_db_context() as db:
        user = _get_user(db, update.effective_user.id)
        if not user:
            await update.message.reply_text("Please /start first.")
            return
        company = db.get(Company, user.company_id)
        currency = company.base_currency if company else "ETB"
        bs = financial_statements.balance_sheet(db, user.company_id, as_of)

    balance_icon = "✅" if bs["balanced"] else "⚠️"
    lines = [
        f"⚖️ *Balance Sheet — {as_of}* {balance_icon}",
        f"_(Confirmed transactions up to this date)_",
        "",
        f"*ASSETS*",
        f"  Cash & Bank:   `{bs['assets']['computed_cash']:>12,.2f} {currency}`",
    ]
    for item in bs["assets"]["manual_items"]:
        lines.append(f"  {item['name'][:22]:<22} `{item['amount']:>8,.2f}`")
    lines += [
        f"  {'TOTAL ASSETS':<22} `{bs['assets']['total']:>8,.2f} {currency}`",
        "",
        f"*LIABILITIES*",
        f"  VAT Payable (15%): `{bs['liabilities']['vat_payable']:>10,.2f} {currency}`",
        f"  WHT Payable (2%):  `{bs['liabilities']['wht_payable']:>10,.2f} {currency}`",
    ]
    for item in bs["liabilities"]["manual_items"]:
        lines.append(f"  {item['name'][:22]:<22} `{item['amount']:>8,.2f}`")
    lines += [
        f"  {'TOTAL LIABILITIES':<22} `{bs['liabilities']['total']:>8,.2f} {currency}`",
        "",
        f"*EQUITY*",
        f"  Retained Earnings: `{bs['equity']['retained_earnings']:>10,.2f} {currency}`",
    ]
    for item in bs["equity"]["manual_items"]:
        lines.append(f"  {item['name'][:22]:<22} `{item['amount']:>8,.2f}`")
    lines += [
        f"  {'TOTAL EQUITY':<22} `{bs['equity']['total']:>8,.2f} {currency}`",
        "",
        f"  ────────────────────────────────────",
        f"  L + E:              `{bs['total_liabilities_and_equity']:>8,.2f} {currency}`",
    ]
    if not bs["balanced"]:
        diff = bs["assets"]["total"] - bs["total_liabilities_and_equity"]
        lines.append(f"\n⚠️ Difference: `{diff:+,.2f}` — add capital/assets in account\\_snapshots table.")

    await _send_long(update, "\n".join(lines))


async def cmd_cashflow(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /cashflow         — current year
    /cashflow YYYY    — specific year
    /cashflow YYYY-MM — specific month
    """
    if not update.effective_user or not update.message:
        return
    today = date.today()
    year, month = today.year, None

    if ctx.args:
        try:
            parts = ctx.args[0].split("-")
            year = int(parts[0])
            month = int(parts[1]) if len(parts) > 1 else None
        except Exception:
            await update.message.reply_text("Usage: /cashflow, /cashflow YYYY, or /cashflow YYYY-MM")
            return

    with get_db_context() as db:
        user = _get_user(db, update.effective_user.id)
        if not user:
            await update.message.reply_text("Please /start first.")
            return
        company = db.get(Company, user.company_id)
        currency = company.base_currency if company else "ETB"
        cf = financial_statements.cash_flow_statement(db, user.company_id, year, month)

    period = f"{year}-{month:02d}" if month else str(year)

    def _sign(v: float) -> str:
        return f"+{v:,.2f}" if v >= 0 else f"{v:,.2f}"

    lines = [
        f"💧 *Cash Flow Statement — {period}*",
        f"_(Confirmed transactions only)_",
        "",
        f"*A. OPERATING ACTIVITIES*",
        f"  Cash received:    `{cf['operating']['inflows']:>12,.2f} {currency}`",
        f"  Cash paid:        `{-cf['operating']['outflows']:>11,.2f} {currency}`",
        f"  *Net Operating:   `{_sign(cf['operating']['net']):>11} {currency}`*",
        "",
        f"*B. INVESTING ACTIVITIES*",
        f"  Proceeds:         `{cf['investing']['inflows']:>12,.2f} {currency}`",
        f"  Payments:         `{-cf['investing']['outflows']:>11,.2f} {currency}`",
        f"  *Net Investing:   `{_sign(cf['investing']['net']):>11} {currency}`*",
        "",
        f"*C. FINANCING ACTIVITIES*",
        f"  Received:         `{cf['financing']['inflows']:>12,.2f} {currency}`",
        f"  Repaid/Withdrawn: `{-cf['financing']['outflows']:>11,.2f} {currency}`",
        f"  *Net Financing:   `{_sign(cf['financing']['net']):>11} {currency}`*",
        "",
        f"  ────────────────────────────────────",
        f"*NET CHANGE IN CASH: `{_sign(cf['net_change_in_cash']):>8} {currency}`*",
    ]

    await _send_long(update, "\n".join(lines))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_user(db, telegram_id: int) -> Optional[User]:
    return db.query(User).filter(User.telegram_id == telegram_id).first()


async def _send_long(update: Update, text: str) -> None:
    """Split long messages for Telegram's 4096-char limit."""
    MAX = 4096
    chunks = [text[i:i + MAX] for i in range(0, len(text), MAX)]
    for chunk in chunks:
        await update.message.reply_text(chunk, parse_mode="Markdown")  # type: ignore[union-attr]
