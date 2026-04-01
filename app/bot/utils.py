"""
Formatting helpers for the Telegram bot.
"""
from __future__ import annotations

from datetime import date
from typing import Optional

from app.agents.extraction import ExtractedTransaction
from app.utils.ethiopian_calendar import gregorian_to_et_label


TRANSACTION_TYPE_EMOJI = {
    "income": "💰",
    "expense": "💸",
    "transfer": "🔄",
}

STATUS_EMOJI = {
    "draft": "📝",
    "confirmed": "✅",
    "needs_clarification": "❓",
    "rejected": "❌",
}


def format_extraction_preview(ex: ExtractedTransaction) -> str:
    """Format an ExtractedTransaction as a readable Telegram message."""
    emoji = TRANSACTION_TYPE_EMOJI.get(ex.transaction_type or "", "📄")
    lines = [
        f"{emoji} *Extracted Transaction*",
        "",
        f"Type:         `{ex.transaction_type or '?'}`",
        f"Amount:       `{ex.amount or '?'} {ex.currency or '?'}`",
        f"Date (GR):    `{ex.transaction_date or 'unknown'}`",
        f"Date (ET):    `{gregorian_to_et_label(ex.transaction_date) if ex.transaction_date else 'unknown'}`",
        f"Counterparty: `{ex.counterparty or 'unknown'}`",
        f"Description:  `{ex.description or '—'}`",
        f"Category:     `{ex.category_hint or '—'}`",
        f"Payment:      `{ex.payment_method or '—'}`",
        f"Receipt No:   `{ex.reference_number or '—'}`",
        f"Confidence:   `{ex.confidence:.0%}`",
    ]

    # Tax fields (show only if detected)
    if ex.vat_amount:
        vat_label = "VAT (output — to remit)" if ex.transaction_type == "income" else "VAT (input — credit)"
        lines.append(f"🧾 {vat_label}: `{ex.vat_amount:,.2f} {ex.currency or 'ETB'}`")
    if ex.withholding_tax:
        lines.append(f"🏦 Withholding Tax (2%): `{ex.withholding_tax:,.2f} {ex.currency or 'ETB'}`")
    if ex.is_vat_inclusive:
        lines.append("ℹ️ _Amount is VAT-inclusive_")

    other_flags = [f for f in ex.ambiguity_flags if f != "date_converted_from_ethiopian"]
    if "date_converted_from_ethiopian" in ex.ambiguity_flags:
        lines.append("🗓 _Date converted from Ethiopian calendar to Gregorian_")
    if other_flags:
        lines.append(f"⚠️ Unclear: `{', '.join(other_flags)}`")

    lines += [
        "",
        "Is this correct? Reply:",
        "  ✅ *yes* — save it",
        "  ❌ *no* — discard it",
        "  ✏️ *edit* — correct a field",
        "  💰 *income* — mark as income",
        "  💸 *expense* — mark as expense",
    ]
    return "\n".join(lines)


def format_transaction_list(transactions: list) -> str:
    """Format a list of Transaction rows as a compact Telegram table."""
    if not transactions:
        return "_No transactions found._"

    lines = ["*Recent Transactions:*", ""]
    for tx in transactions[:15]:
        emoji = TRANSACTION_TYPE_EMOJI.get(tx.transaction_type, "📄")
        status_e = STATUS_EMOJI.get(tx.status, "")
        date_str = str(tx.transaction_date) if tx.transaction_date else "?"
        lines.append(
            f"{emoji} `{date_str}` | `{tx.amount:,.0f} {tx.currency}` | "
            f"{status_e} ID: `{tx.id}`"
        )
        if tx.description:
            lines.append(f"   _{tx.description[:60]}_")
        if tx.reference_number:
            lines.append(f"   🧾 Receipt: `{tx.reference_number}`")

    lines.append("")
    lines.append("_To delete: /delete <ID>  e.g. /delete 1_")

    return "\n".join(lines)


def escape_md(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special = r"_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{c}" if c in special else c for c in text)
