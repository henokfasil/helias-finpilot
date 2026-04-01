"""
Validation Agent — checks an ExtractedTransaction for completeness and
returns a list of fields that need clarification.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.agents.extraction import ExtractedTransaction


CONFIDENCE_THRESHOLD = 0.6  # below this → always ask for confirmation


@dataclass
class ValidationResult:
    is_valid: bool
    missing_fields: list[str]
    clarification_questions: list[tuple[str, str]]  # (field_name, question_text)


def validate(extracted: "ExtractedTransaction") -> ValidationResult:
    """
    Inspect the extracted data.  Returns missing fields and questions
    that the bot should ask the user.
    """
    missing: list[str] = []
    questions: list[tuple[str, str]] = []

    if extracted.amount is None:
        missing.append("amount")
        questions.append(("amount", "What was the exact amount?"))

    if extracted.currency is None:
        missing.append("currency")
        questions.append(("currency", "What currency? (ETB / USD / EUR)"))

    if extracted.transaction_type is None:
        missing.append("transaction_type")
        questions.append(("transaction_type", "Is this income, expense, or transfer?"))

    if extracted.transaction_date is None:
        missing.append("transaction_date")
        questions.append(
            ("transaction_date", "What date did this transaction occur? (YYYY-MM-DD)")
        )

    # Counterparty is important but not blocking — just flag it
    if not extracted.counterparty:
        missing.append("counterparty")

    # Low confidence is shown in the preview (Confidence: X%) and the user
    # is already asked to reply yes/no/edit — no extra question needed here.

    is_valid = len([f for f in missing if f in ("amount", "currency", "transaction_type")]) == 0

    return ValidationResult(
        is_valid=is_valid,
        missing_fields=missing,
        clarification_questions=questions,
    )
