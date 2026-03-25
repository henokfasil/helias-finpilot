"""
Audit Service — every state change in the system MUST be logged here.
Records are append-only and never modified.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


def log_event(
    db: Session,
    company_id: int,
    action: str,
    transaction_id: Optional[int] = None,
    user_telegram_id: Optional[int] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    before_state: Optional[Any] = None,
    after_state: Optional[Any] = None,
    notes: Optional[str] = None,
) -> AuditLog:
    """
    Append a single audit log entry.  Serialises before/after to JSON.
    """
    entry = AuditLog(
        company_id=company_id,
        transaction_id=transaction_id,
        user_telegram_id=user_telegram_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_state=json.dumps(before_state, default=str) if before_state is not None else None,
        after_state=json.dumps(after_state, default=str) if after_state is not None else None,
        notes=notes,
    )
    db.add(entry)
    db.flush()
    logger.debug("AuditLog: action=%s tx_id=%s", action, transaction_id)
    return entry
