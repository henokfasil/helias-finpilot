"""
Message and file handlers — the core ingestion pipeline.

Flow for a text message:
  1. Extract transaction using AI
  2. Validate completeness
  3. Show preview + ask confirmation
  4. On "yes" → confirm and save; on "no" → discard; on "edit" → ask for field

Flow for a file upload:
  1. Download and store file
  2. Extract text (PDF) or use vision (image)
  3. Same flow as text message
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.agents import extraction as extraction_agent
from app.agents.validation import validate
from app.bot import state as bot_state
from app.bot.state import PendingTransaction
from app.bot.utils import format_extraction_preview
from app.config import settings
from app.database import get_db_context
from app.models.company import Company
from app.models.transaction import Transaction
from app.models.user import User
from app.services import audit_service, file_service, transaction_service

logger = logging.getLogger(__name__)


# ── Main text message handler ─────────────────────────────────────────────────

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return

    text = (update.message.text or "").strip()
    chat_id = update.effective_chat.id  # type: ignore[union-attr]
    tg_user = update.effective_user

    # Check if we're in a conversation flow
    pending = bot_state.get_pending(chat_id)

    if pending and pending.clarification_field:
        await _handle_clarification_answer(update, ctx, pending, text, chat_id)
        return

    if pending and _is_confirmation(text):
        await _handle_confirmation(update, ctx, pending, text, chat_id)
        return

    # New transaction message
    with get_db_context() as db:
        user = _get_user(db, tg_user.id)
        if not user:
            await update.message.reply_text(
                "Please send /start to register first."
            )
            return

    await _process_text_transaction(update, ctx, text, tg_user.id)


async def _process_text_transaction(
    update: Update,
    ctx: ContextTypes.DEFAULT_TYPE,
    text: str,
    telegram_user_id: int,
) -> None:
    chat_id = update.effective_chat.id  # type: ignore[union-attr]

    await update.message.reply_text("🔍 Analysing…")  # type: ignore[union-attr]

    extracted = extraction_agent.extract_from_text(text)
    validation = validate(extracted)

    preview = format_extraction_preview(extracted)

    if not validation.is_valid and validation.clarification_questions:
        # Ask first blocking question
        field, question = validation.clarification_questions[0]
        pending = PendingTransaction(
            extracted=extracted,
            clarification_field=field,
        )
        bot_state.set_pending(chat_id, pending)
        await update.message.reply_text(  # type: ignore[union-attr]
            f"{preview}\n\n❓ *{question}*",
            parse_mode="Markdown",
        )
        return

    # Show preview and ask for confirmation
    pending = PendingTransaction(extracted=extracted)
    bot_state.set_pending(chat_id, pending)
    await update.message.reply_text(preview, parse_mode="Markdown")  # type: ignore[union-attr]


# ── File upload handler ───────────────────────────────────────────────────────

async def handle_document(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return

    tg_user = update.effective_user
    chat_id = update.effective_chat.id  # type: ignore[union-attr]

    with get_db_context() as db:
        user = _get_user(db, tg_user.id)
        if not user:
            await update.message.reply_text("Please /start first.")
            return
        company_id = user.company_id

    document = update.message.document or update.message.photo
    if update.message.photo:
        # Get largest photo
        photo = update.message.photo[-1]
        file_obj = await ctx.bot.get_file(photo.file_id)
        filename = f"photo_{photo.file_id}.jpg"
        telegram_file_id = photo.file_id
    elif update.message.document:
        doc = update.message.document
        file_obj = await ctx.bot.get_file(doc.file_id)
        filename = doc.file_name or f"file_{doc.file_id}"
        telegram_file_id = doc.file_id
    else:
        return

    await update.message.reply_text("📎 Processing file…")

    # Download
    buf = BytesIO()
    await file_obj.download_to_memory(buf)
    file_bytes = buf.getvalue()

    with get_db_context() as db:
        user2 = _get_user(db, tg_user.id)
        company = db.get(Company, company_id) if user2 else None
        company_slug = company.slug if company else "default"
        attachment = file_service.store_file(
            db,
            company_id=company_id,
            file_bytes=file_bytes,
            original_filename=filename,
            telegram_file_id=telegram_file_id,
            company_slug=company_slug,
        )
        attachment_id = attachment.id

    # Extract from file
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in ("jpg", "jpeg", "png", "webp", "gif", "bmp"):
        extracted = extraction_agent.extract_from_image(file_bytes, filename)
    else:
        # PDF or other: extract text first
        with get_db_context() as db:
            att = db.get(type(attachment), attachment_id)
            text_content = file_service.extract_text_from_attachment(att) if att else ""
        if text_content:
            extracted = extraction_agent.extract_from_text(text_content)
        else:
            extracted = extraction_agent.extract_from_image(file_bytes, filename)

    # Include any caption
    if update.message.caption:
        caption_text = update.message.caption
        extracted.raw_text = f"{extracted.raw_text}\n[caption: {caption_text}]"
        if not extracted.description:
            extracted.description = caption_text

    validation = validate(extracted)
    preview = format_extraction_preview(extracted)

    pending = PendingTransaction(extracted=extracted, attachment_id=attachment_id)
    bot_state.set_pending(chat_id, pending)

    if not validation.is_valid and validation.clarification_questions:
        field, question = validation.clarification_questions[0]
        pending.clarification_field = field
        await update.message.reply_text(
            f"{preview}\n\n❓ *{question}*",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(preview, parse_mode="Markdown")


# ── Confirmation flow ─────────────────────────────────────────────────────────

def _is_confirmation(text: str) -> bool:
    lower = text.lower().strip()
    return lower in ("yes", "y", "no", "n", "edit", "✅", "❌", "✏️", "confirm", "discard", "income", "expense", "💰", "💸", "force", "save")


async def _handle_confirmation(
    update: Update,
    ctx: ContextTypes.DEFAULT_TYPE,
    pending: PendingTransaction,
    text: str,
    chat_id: int,
) -> None:
    tg_user = update.effective_user
    lower = text.lower().strip()

    if lower in ("yes", "y", "✅", "confirm"):
        # Save to DB
        with get_db_context() as db:
            user = _get_user(db, tg_user.id)
            if not user:
                return
            company = db.get(Company, user.company_id)

            # Duplicate check
            dup = None
            if pending.extracted.amount and pending.extracted.currency:
                dup = transaction_service.check_duplicate(
                    db,
                    company_id=user.company_id,
                    amount=pending.extracted.amount,
                    currency=pending.extracted.currency,
                    transaction_date=pending.extracted.transaction_date,
                    counterparty_name=pending.extracted.counterparty,
                )

            if dup:
                bot_state.clear_pending(chat_id)
                await update.message.reply_text(  # type: ignore[union-attr]
                    f"⚠️ This looks like a duplicate of transaction *#{dup.id}* "
                    f"(`{dup.amount} {dup.currency}` on `{dup.transaction_date}`).\n\n"
                    f"Reply *force* to save anyway, or *no* to discard.",
                    parse_mode="Markdown",
                )
                pending.clarification_field = "__duplicate_check__"
                pending.tx_db_id = dup.id
                bot_state.set_pending(chat_id, pending)
                return

            tx = transaction_service.create_from_extraction(
                db,
                company_id=user.company_id,
                extracted=pending.extracted,
                user_telegram_id=tg_user.id,
                user_db_id=user.id,
            )
            tx = transaction_service.confirm_transaction(db, tx, tg_user.id)

            # Link attachment and rename file to human-readable name
            if pending.attachment_id:
                from app.models.attachment import Attachment
                att = db.get(Attachment, pending.attachment_id)
                if att:
                    att.transaction_id = tx.id
                    db.flush()
                    # Rename stored file: 2026-03-25_tx42_Ethio_Telecom.jpg
                    if tx.transaction_date:
                        file_service.rename_after_confirmation(
                            att,
                            tx_id=tx.id,
                            tx_date=tx.transaction_date,
                            counterparty=pending.extracted.counterparty,
                            company_slug=company.slug if company else "default",
                        )

            tx_id = tx.id

        bot_state.clear_pending(chat_id)
        await update.message.reply_text(  # type: ignore[union-attr]
            f"✅ Transaction *#{tx_id}* saved!\n"
            f"`{pending.extracted.amount} {pending.extracted.currency}` — "
            f"{pending.extracted.description or pending.extracted.counterparty or ''}",
            parse_mode="Markdown",
        )

    elif lower in ("no", "n", "❌", "discard"):
        bot_state.clear_pending(chat_id)
        await update.message.reply_text("❌ Transaction discarded.")  # type: ignore[union-attr]

    elif lower in ("income", "💰"):
        pending.extracted.transaction_type = "income"
        pending.clarification_field = None
        bot_state.set_pending(chat_id, pending)
        from app.bot.utils import format_extraction_preview
        preview = format_extraction_preview(pending.extracted)
        await update.message.reply_text(  # type: ignore[union-attr]
            f"💰 Marked as *income*. Updated preview:\n\n{preview}",
            parse_mode="Markdown",
        )

    elif lower in ("expense", "💸"):
        pending.extracted.transaction_type = "expense"
        pending.clarification_field = None
        bot_state.set_pending(chat_id, pending)
        from app.bot.utils import format_extraction_preview
        preview = format_extraction_preview(pending.extracted)
        await update.message.reply_text(  # type: ignore[union-attr]
            f"💸 Marked as *expense*. Updated preview:\n\n{preview}",
            parse_mode="Markdown",
        )

    elif lower in ("edit", "✏️"):
        pending.clarification_field = "__edit_menu__"
        bot_state.set_pending(chat_id, pending)
        await update.message.reply_text(  # type: ignore[union-attr]
            _edit_menu_text(pending.extracted),
            parse_mode="Markdown",
        )

    elif lower == "force":
        # Force-save despite duplicate warning
        with get_db_context() as db:
            user = _get_user(db, tg_user.id)
            if not user:
                return
            tx = transaction_service.create_from_extraction(
                db,
                company_id=user.company_id,
                extracted=pending.extracted,
                user_telegram_id=tg_user.id,
                user_db_id=user.id,
            )
            tx = transaction_service.confirm_transaction(db, tx, tg_user.id)
            tx_id = tx.id
        bot_state.clear_pending(chat_id)
        await update.message.reply_text(f"✅ Saved as transaction *#{tx_id}*.", parse_mode="Markdown")  # type: ignore[union-attr]


# ── Clarification flow ────────────────────────────────────────────────────────

async def _handle_clarification_answer(
    update: Update,
    ctx: ContextTypes.DEFAULT_TYPE,
    pending: PendingTransaction,
    answer: str,
    chat_id: int,
) -> None:
    field = pending.clarification_field
    ex = pending.extracted

    if field == "__edit_menu__":
        try:
            choice = int(answer.strip())
            if choice == 0:
                # Done editing — show final confirmation preview
                pending.clarification_field = None
                bot_state.set_pending(chat_id, pending)
                preview = format_extraction_preview(ex)
                await update.message.reply_text(  # type: ignore[union-attr]
                    preview, parse_mode="Markdown"
                )
            elif 1 <= choice <= len(_EDIT_FIELDS):
                field_key, field_label = _EDIT_FIELDS[choice - 1]
                pending.clarification_field = f"__edit_value__{field_key}"
                bot_state.set_pending(chat_id, pending)
                current = _get_field_display(ex, field_key)
                await update.message.reply_text(  # type: ignore[union-attr]
                    f"Enter new *{field_label}*:\n_(current: `{current}`)_",
                    parse_mode="Markdown",
                )
            else:
                await update.message.reply_text(  # type: ignore[union-attr]
                    f"Reply 0 to finish, or 1–{len(_EDIT_FIELDS)} to edit a field."
                )
        except ValueError:
            await update.message.reply_text(  # type: ignore[union-attr]
                "Please reply with a number from the list."
            )
        return

    if field and field.startswith("__edit_value__"):
        field_key = field[len("__edit_value__"):]
        _apply_edit(ex, field_key, answer)
        # Stay in edit menu so user can edit more fields
        pending.clarification_field = "__edit_menu__"
        bot_state.set_pending(chat_id, pending)
        await update.message.reply_text(  # type: ignore[union-attr]
            _edit_menu_text(ex),
            parse_mode="Markdown",
        )
        return

    if field == "__duplicate_check__":
        if answer.lower() in ("force", "yes", "y", "save"):
            # Force-save directly — do NOT call _handle_confirmation again
            # as that would re-run the duplicate check and loop forever
            with get_db_context() as db:
                user = _get_user(db, tg_user.id)
                if not user:
                    return
                tx = transaction_service.create_from_extraction(
                    db,
                    company_id=user.company_id,
                    extracted=pending.extracted,
                    user_telegram_id=tg_user.id,
                    user_db_id=user.id,
                )
                tx = transaction_service.confirm_transaction(db, tx, tg_user.id)
                tx_id = tx.id
            bot_state.clear_pending(chat_id)
            await update.message.reply_text(  # type: ignore[union-attr]
                f"✅ Saved as transaction *#{tx_id}*.", parse_mode="Markdown"
            )
        else:
            bot_state.clear_pending(chat_id)
            await update.message.reply_text("❌ Transaction discarded.")  # type: ignore[union-attr]
        return

    # Apply the clarification answer to the correct field
    _apply_clarification(ex, field, answer)
    pending.clarification_field = None

    # If user manually filled all fields, boost confidence so preview shows something sensible
    if ex.confidence < 0.5 and ex.amount and ex.currency and ex.transaction_type and ex.transaction_date:
        ex.confidence = 0.75
        ex.ambiguity_flags = [f for f in ex.ambiguity_flags if f not in ("ai_parse_error", "ai_error")]

    # Re-validate
    from app.agents.validation import validate
    validation = validate(ex)
    if validation.clarification_questions:
        next_field, next_question = validation.clarification_questions[0]
        pending.clarification_field = next_field
        bot_state.set_pending(chat_id, pending)
        await update.message.reply_text(  # type: ignore[union-attr]
            f"❓ *{next_question}*", parse_mode="Markdown"
        )
        return

    # All clear — show updated preview
    preview = format_extraction_preview(ex)
    bot_state.set_pending(chat_id, pending)
    await update.message.reply_text(preview, parse_mode="Markdown")  # type: ignore[union-attr]


# ── Field edit helpers ────────────────────────────────────────────────────────

_EDIT_FIELDS = [
    ("amount",       "Amount"),
    ("currency",     "Currency"),
    ("date",         "Date  (YYYY-MM-DD)"),
    ("counterparty", "Counterparty"),
    ("description",  "Description"),
    ("type",         "Type  (income / expense)"),
    ("category",     "Category"),
    ("payment",      "Payment method"),
    ("receipt_no",   "Receipt / Reference number"),
]


def _get_field_display(ex, field_key: str) -> str:
    mapping = {
        "amount":       lambda e: f"{e.amount} {e.currency}" if e.amount else "—",
        "currency":     lambda e: e.currency or "—",
        "date":         lambda e: str(e.transaction_date) if e.transaction_date else "—",
        "counterparty": lambda e: e.counterparty or "—",
        "description":  lambda e: e.description or "—",
        "type":         lambda e: e.transaction_type or "—",
        "category":     lambda e: e.category_hint or "—",
        "payment":      lambda e: e.payment_method or "—",
        "receipt_no":   lambda e: e.reference_number or "—",
    }
    fn = mapping.get(field_key)
    return fn(ex) if fn else "—"


def _edit_menu_text(ex) -> str:
    lines = ["✏️ *Edit fields — reply with a number:*\n"]
    for i, (key, label) in enumerate(_EDIT_FIELDS, 1):
        val = _get_field_display(ex, key)
        lines.append(f"{i}. {label.split('(')[0].strip()}: `{val}`")
    lines.append(f"\n*0. Done editing* → confirm / save")
    return "\n".join(lines)


def _apply_edit(ex, field: str, value: str) -> None:
    """Apply a user edit to an ExtractedTransaction."""
    field_map = {
        "amount": "amount",
        "currency": "currency",
        "date": "transaction_date",
        "counterparty": "counterparty",
        "description": "description",
        "type": "transaction_type",
        "category": "category_hint",
        "payment": "payment_method",
        "method": "payment_method",
        "receipt_no": "reference_number",
        "receipt": "reference_number",
        "reference": "reference_number",
    }
    attr = field_map.get(field.lower())
    if not attr:
        return
    _apply_clarification(ex, attr, value)


def _apply_clarification(ex, field: str, value: str) -> None:
    """Set a specific field on ExtractedTransaction from a user string."""
    if field == "amount":
        try:
            ex.amount = Decimal(value.replace(",", "").replace(" ", ""))
        except InvalidOperation:
            pass
    elif field == "currency":
        val = value.upper().strip()
        if val in ("ETB", "USD", "EUR", "BIRR", "BR"):
            ex.currency = "ETB" if val in ("BIRR", "BR") else val
    elif field == "transaction_date" or field == "date":
        try:
            ex.transaction_date = date.fromisoformat(value.strip())
        except ValueError:
            # Try common formats
            for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
                try:
                    ex.transaction_date = datetime.strptime(value.strip(), fmt).date()
                    break
                except ValueError:
                    continue
    elif field == "transaction_type" or field == "type":
        val = value.lower().strip()
        if val in ("income", "expense", "transfer", "in", "out"):
            ex.transaction_type = "income" if val == "in" else "expense" if val == "out" else val
    elif field == "counterparty":
        ex.counterparty = value.strip()
    elif field == "description":
        ex.description = value.strip()
    elif field == "category_hint" or field == "category":
        ex.category_hint = value.strip()
    elif field == "payment_method":
        ex.payment_method = value.lower().strip()
    elif field == "reference_number":
        ex.reference_number = value.strip()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_user(db, telegram_id: int) -> Optional[User]:
    return db.query(User).filter(User.telegram_id == telegram_id).first()
