"""
Classification Agent — resolves a category_hint string to an actual Category row.
Uses fuzzy matching first; falls back to AI if needed.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.category import Category

logger = logging.getLogger(__name__)


def find_best_category(
    db: Session,
    company_id: int,
    category_hint: Optional[str],
    transaction_type: Optional[str],
) -> Optional[Category]:
    """
    Match a free-text hint to a Category row.
    Returns None if no reasonable match found (caller will leave category blank).
    """
    if not category_hint:
        return None

    hint_lower = category_hint.lower().strip()

    # Load active categories for this company
    categories: list[Category] = (
        db.query(Category)
        .filter(
            Category.company_id == company_id,
            Category.is_active == True,  # noqa: E712
        )
        .all()
    )

    if not categories:
        return None

    # Filter by transaction type if we know it
    typed = categories
    if transaction_type in ("income", "expense", "transfer"):
        typed = [c for c in categories if c.type == transaction_type] or categories

    # Exact match
    for cat in typed:
        if cat.name.lower() == hint_lower:
            return cat

    # Substring match
    for cat in typed:
        if hint_lower in cat.name.lower() or cat.name.lower() in hint_lower:
            return cat

    # Word overlap match (at least one word shared)
    hint_words = set(hint_lower.split())
    best: Optional[Category] = None
    best_score = 0
    for cat in typed:
        cat_words = set(cat.name.lower().split())
        overlap = len(hint_words & cat_words)
        if overlap > best_score:
            best_score = overlap
            best = cat

    if best_score > 0:
        return best

    logger.debug("ClassificationAgent: no match for hint=%r", category_hint)
    return None
