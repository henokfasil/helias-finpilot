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
from app.models.company import Company
from app.models.transaction import Transaction
from app.models.user import User
from app.services import report_service, transaction_service

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
/new — start a new transaction entry
/transactions — list recent transactions
/pending — show unconfirmed items
/summary — quick financial snapshot
/monthly\_report — this month's report
/annual\_report — full year report
/report YYYY-MM — report for specific month
/tax\_summary — Ethiopian VAT & WHT obligations
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
        txns = transaction_service.list_transactions(db, user.company_id, limit=15)
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
    today = date.today()
    with get_db_context() as db:
        user = _get_user(db, update.effective_user.id)
        if not user:
            await update.message.reply_text("Please /start first.")
            return
        company = db.get(Company, user.company_id)
        summary = transaction_service.monthly_summary(
            db, user.company_id, today.year, today.month
        )
        currency = company.base_currency if company else "ETB"
        income = summary.get("income", {}).get(currency, 0)
        expenses = summary.get("expense", {}).get(currency, 0)
        net = income - expenses
        sign = "+" if net >= 0 else ""
        text = (
            f"📊 *{today.strftime('%B %Y')} Snapshot*\n\n"
            f"💰 Income:   `{income:>12,.2f} {currency}`\n"
            f"💸 Expenses: `{expenses:>12,.2f} {currency}`\n"
            f"📈 Net:      `{sign}{net:>11,.2f} {currency}`"
        )
        await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_monthly_report(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return
    today = date.today()
    year, month = today.year, today.month

    # Allow /report YYYY-MM
    if ctx.args:
        try:
            parts = ctx.args[0].split("-")
            year, month = int(parts[0]), int(parts[1])
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
    /delete <id>  — marks a transaction as rejected (soft delete).
    Usage: /delete 42
    """
    if not update.effective_user or not update.message:
        return
    if not ctx.args:
        await update.message.reply_text(
            "Usage: `/delete <transaction_id>`\n\nFind the ID with /transactions",
            parse_mode="Markdown",
        )
        return
    try:
        tx_id = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("Please provide a numeric transaction ID.")
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
        if tx.status == "rejected":
            await update.message.reply_text(f"Transaction #{tx_id} is already deleted.")
            return
        transaction_service.reject_transaction(db, tx, update.effective_user.id, reason="deleted by user")

    await update.message.reply_text(
        f"🗑 Transaction *#{tx_id}* has been deleted.\n"
        f"_(It remains in the audit log for compliance.)_",
        parse_mode="Markdown",
    )


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
    net_vat = tax["net_vat_payable"]
    net_sign = "+" if net_vat >= 0 else ""

    lines = [
        f"🧾 *Ethiopian Tax Summary — {period}*",
        f"_(Confirmed transactions only)_",
        "",
        f"*VAT (15%)*",
        f"  Output VAT collected (income): `{tax['output_vat']:>12,.2f} {currency}`",
        f"  Input VAT paid (expenses):     `{tax['input_vat']:>12,.2f} {currency}`",
        f"  ─────────────────────────────────────",
        f"  Net VAT payable to MoR:        `{net_sign}{net_vat:>11,.2f} {currency}`",
        "",
        f"*Withholding Tax (2%)*",
        f"  WHT withheld from suppliers:   `{tax['wht_collected']:>12,.2f} {currency}`",
        "",
        f"*Total obligation to MoR:        `{tax['total_tax_obligation']:>12,.2f} {currency}`*",
        "",
        "_File and pay at your local MoR branch by the 30th of the following month._",
    ]

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_user(db, telegram_id: int) -> Optional[User]:
    return db.query(User).filter(User.telegram_id == telegram_id).first()


async def _send_long(update: Update, text: str) -> None:
    """Split long messages for Telegram's 4096-char limit."""
    MAX = 4096
    chunks = [text[i:i + MAX] for i in range(0, len(text), MAX)]
    for chunk in chunks:
        await update.message.reply_text(chunk, parse_mode="Markdown")  # type: ignore[union-attr]
