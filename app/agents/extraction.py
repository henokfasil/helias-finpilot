"""
Extraction Agent — parses raw text (or OCR'd file content) into a structured
ExtractedTransaction using OpenAI.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

from openai import OpenAI

from app.config import settings
from app.prompts.extraction import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT

logger = logging.getLogger(__name__)

_client = OpenAI(api_key=settings.openai_api_key)


def _parse_json(content: str) -> dict:
    """
    Parse JSON from model output, stripping markdown code fences if present.
    GPT-4o sometimes wraps output in ```json ... ``` even when asked not to.
    """
    text = content.strip()
    # Strip ```json ... ``` or ``` ... ```
    if text.startswith("```"):
        text = text.split("```", 2)[1]          # drop opening fence
        if text.lower().startswith("json"):
            text = text[4:]                      # drop "json" language tag
        if "```" in text:
            text = text[:text.rindex("```")]     # drop closing fence
    return json.loads(text.strip())


@dataclass
class ExtractedTransaction:
    """Value object produced by the extraction agent."""
    transaction_type: Optional[str] = None
    transaction_date: Optional[date] = None
    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    counterparty: Optional[str] = None
    description: Optional[str] = None
    category_hint: Optional[str] = None
    payment_method: Optional[str] = None
    reference_number: Optional[str] = None
    is_tax_relevant: bool = False
    # Ethiopian tax fields
    vat_amount: Optional[Decimal] = None
    withholding_tax: Optional[Decimal] = None
    is_vat_inclusive: bool = False
    confidence: float = 0.0
    ambiguity_flags: list[str] = field(default_factory=list)
    raw_text: str = ""


def extract_from_text(raw_text: str) -> ExtractedTransaction:
    """
    Call OpenAI to extract a structured transaction from free-form text.
    Returns an ExtractedTransaction; never raises — logs errors and returns
    a low-confidence object instead.
    """
    today_str = date.today().isoformat()
    system_prompt = EXTRACTION_SYSTEM_PROMPT.format(today=today_str)
    user_prompt = EXTRACTION_USER_PROMPT.format(input_text=raw_text)

    try:
        response = _client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=500,
        )
        content = response.choices[0].message.content or ""
        data = _parse_json(content)
        return _parse_extraction(data, raw_text)

    except json.JSONDecodeError as exc:
        logger.error("ExtractionAgent: JSON parse error: %s | raw: %.200s", exc, content if 'content' in dir() else "")
        return ExtractedTransaction(
            raw_text=raw_text,
            confidence=0.0,
            ambiguity_flags=["ai_parse_error"],
        )
    except Exception as exc:
        logger.error("ExtractionAgent: unexpected error: %s", exc)
        return ExtractedTransaction(
            raw_text=raw_text,
            confidence=0.0,
            ambiguity_flags=["ai_error"],
        )


def extract_from_image(image_bytes: bytes, filename: str) -> ExtractedTransaction:
    """
    Use GPT-4o vision to extract transaction data from an image.
    """
    import base64

    today_str = date.today().isoformat()
    system_prompt = EXTRACTION_SYSTEM_PROMPT.format(today=today_str)
    b64 = base64.b64encode(image_bytes).decode("utf-8")

    mime = "image/png" if filename.lower().endswith(".png") else "image/jpeg"

    try:
        response = _client.chat.completions.create(
            model=settings.openai_vision_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Extract transaction data from this document/receipt. Return valid JSON only.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{b64}"},
                        },
                    ],
                },
            ],
            temperature=0.0,
            max_tokens=800,
        )
        content = response.choices[0].message.content or ""
        data = _parse_json(content)
        return _parse_extraction(data, f"[image: {filename}]")

    except json.JSONDecodeError as exc:
        logger.error("ExtractionAgent (vision): JSON parse error: %s | raw: %.200s", exc, content if 'content' in dir() else "")
        return ExtractedTransaction(
            raw_text=f"[image: {filename}]",
            confidence=0.0,
            ambiguity_flags=["ai_parse_error"],
        )
    except Exception as exc:
        logger.error("ExtractionAgent (vision): unexpected error: %s", exc)
        return ExtractedTransaction(
            raw_text=f"[image: {filename}]",
            confidence=0.0,
            ambiguity_flags=["ai_error"],
        )


def _parse_extraction(data: dict, raw_text: str) -> ExtractedTransaction:
    """Convert raw JSON dict from AI into typed ExtractedTransaction."""
    tx_date = None
    if data.get("transaction_date"):
        try:
            tx_date = date.fromisoformat(data["transaction_date"])
        except ValueError:
            pass

    def _to_decimal(val) -> Optional[Decimal]:
        if val is None:
            return None
        try:
            return Decimal(str(val))
        except Exception:
            return None

    amount = _to_decimal(data.get("amount"))
    vat_amount = _to_decimal(data.get("vat_amount"))
    withholding_tax = _to_decimal(data.get("withholding_tax"))

    return ExtractedTransaction(
        transaction_type=data.get("transaction_type"),
        transaction_date=tx_date,
        amount=amount,
        currency=data.get("currency"),
        counterparty=data.get("counterparty"),
        description=data.get("description"),
        category_hint=data.get("category_hint"),
        payment_method=data.get("payment_method"),
        reference_number=data.get("reference_number"),
        is_tax_relevant=bool(data.get("is_tax_relevant", False)),
        vat_amount=vat_amount,
        withholding_tax=withholding_tax,
        is_vat_inclusive=bool(data.get("is_vat_inclusive", False)),
        confidence=float(data.get("confidence", 0.5)),
        ambiguity_flags=list(data.get("ambiguity_flags", [])),
        raw_text=raw_text,
    )
