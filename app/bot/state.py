"""
In-memory conversation state for the Telegram bot.
Maps chat_id → pending transaction data so the bot can ask follow-up questions.

For Phase 1 (single-user MVP), in-memory state is sufficient.
Phase 2: migrate to Redis or DB-backed sessions.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PendingTransaction:
    """Holds a not-yet-confirmed transaction in mid-conversation."""
    extracted: Any  # ExtractedTransaction
    attachment_id: Optional[int] = None
    clarification_field: Optional[str] = None  # which field we're asking about
    tx_db_id: Optional[int] = None             # set once row is written


# chat_id → PendingTransaction
_pending: dict[int, PendingTransaction] = {}


def set_pending(chat_id: int, pending: PendingTransaction) -> None:
    _pending[chat_id] = pending


def get_pending(chat_id: int) -> Optional[PendingTransaction]:
    return _pending.get(chat_id)


def clear_pending(chat_id: int) -> None:
    _pending.pop(chat_id, None)
