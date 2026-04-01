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
    Parse JSON from model output robustly.
    Handles: clean JSON, ```json ... ```, ``` ... ```, or JSON buried in text.
    """
    import re
    text = content.strip()

    # 1. Try direct parse first (clean response)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. Extract from ```json ... ``` or ``` ... ``` anywhere in the text
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if m:
        return json.loads(m.group(1))

    # 3. Find first {...} block anywhere in the text
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        return json.loads(m.group(0))

    raise json.JSONDecodeError("No JSON found in model response", text, 0)


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
    Extract transaction data from an image.
    Uses Gemini 2.0 Flash if GEMINI_API_KEY is configured (better Amharic/multilingual support),
    falls back to GPT-4o vision otherwise.
    """
    if settings.gemini_api_key:
        return _extract_from_image_gemini(image_bytes, filename)
    return _extract_from_image_openai(image_bytes, filename)


def _extract_from_image_gemini(image_bytes: bytes, filename: str) -> ExtractedTransaction:
    """Use Gemini 2.0 Flash for image extraction — superior Amharic/multilingual support."""
    import io
    import PIL.Image
    import google.generativeai as genai

    today_str = date.today().isoformat()
    prompt = (
        EXTRACTION_SYSTEM_PROMPT.format(today=today_str)
        + "\n\nExtract transaction data from this receipt/document. "
        "The document may be in Amharic, English, or mixed. Return valid JSON only."
    )

    content = ""
    try:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_vision_model)
        image = PIL.Image.open(io.BytesIO(image_bytes))
        response = model.generate_content(
            [prompt, image],
            generation_config={"temperature": 0.0, "max_output_tokens": 800},
        )
        content = response.text or ""
        data = _parse_json(content)
        return _parse_extraction(data, f"[image: {filename}]")

    except json.JSONDecodeError as exc:
        logger.error("Gemini (vision): JSON parse error: %s | raw: %.200s", exc, content)
        return ExtractedTransaction(
            raw_text=f"[image: {filename}]",
            confidence=0.0,
            ambiguity_flags=["ai_parse_error"],
        )
    except Exception as exc:
        logger.error("Gemini (vision): unexpected error: %s — falling back to GPT-4o", exc)
        return _extract_from_image_openai(image_bytes, filename)


def _extract_from_image_openai(image_bytes: bytes, filename: str) -> ExtractedTransaction:
    """GPT-4o vision fallback for image extraction."""
    import base64

    today_str = date.today().isoformat()
    system_prompt = EXTRACTION_SYSTEM_PROMPT.format(today=today_str)
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    mime = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
    content = ""

    try:
        response = _client.chat.completions.create(
            model=settings.openai_vision_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract transaction data from this document/receipt. Return valid JSON only."},
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
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
        logger.error("GPT-4o (vision): JSON parse error: %s | raw: %.200s", exc, content)
        return ExtractedTransaction(
            raw_text=f"[image: {filename}]",
            confidence=0.0,
            ambiguity_flags=["ai_parse_error"],
        )
    except Exception as exc:
        logger.error("GPT-4o (vision): unexpected error: %s", exc)
        return ExtractedTransaction(
            raw_text=f"[image: {filename}]",
            confidence=0.0,
            ambiguity_flags=["ai_error"],
        )


def _et_to_gregorian(d: date) -> tuple[date, bool]:
    """
    If a date's year looks like an Ethiopian calendar year (2010–2020),
    convert it to Gregorian.

    Ethiopian year N spans:
      - Gregorian Sept 11 of (N+7) through Sept 10 of (N+8)
    Conversion rule:
      - Month 9–12 (Sept–Dec) → Gregorian year = ET year + 7
      - Month 1–8  (Jan–Aug)  → Gregorian year = ET year + 8

    Returns (converted_date, was_converted).
    """
    ET_MIN, ET_MAX = 2010, 2020
    if not (ET_MIN <= d.year <= ET_MAX):
        return d, False
    gregorian_year = d.year + 7 if d.month >= 9 else d.year + 8
    try:
        return d.replace(year=gregorian_year), True
    except ValueError:
        # Feb 29 edge case
        return d.replace(year=gregorian_year, day=28), True


def _parse_extraction(data: dict, raw_text: str) -> ExtractedTransaction:
    """Convert raw JSON dict from AI into typed ExtractedTransaction."""
    tx_date = None
    ambiguity_flags = list(data.get("ambiguity_flags", []))

    if data.get("transaction_date"):
        try:
            tx_date = date.fromisoformat(data["transaction_date"])
            # Safety net: if AI returned an Ethiopian-range year, convert it
            tx_date, converted = _et_to_gregorian(tx_date)
            if converted and "date_converted_from_ethiopian" not in ambiguity_flags:
                ambiguity_flags.append("date_converted_from_ethiopian")
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
        ambiguity_flags=ambiguity_flags,
        raw_text=raw_text,
    )
