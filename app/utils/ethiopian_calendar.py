"""
Ethiopian (Ge'ez) Calendar ↔ Gregorian converter.

Ethiopian calendar facts:
  - 13 months: 12 × 30 days + Pagume (5 or 6 days)
  - Leap year: every ET year divisible by 4 (Pagume has 6 days)
  - New Year (Enkutatash / Meskerem 1) falls ~September 11 Gregorian
  - Currently ET 2018 ≈ Gregorian 2025/2026

Epoch reference:
  Meskerem 1, 1 EC = Julian Day Number 1724221
"""
from __future__ import annotations
from datetime import date
from typing import Optional

ET_EPOCH_JDN = 1724221  # JDN of Meskerem 1, 1 EC

ET_MONTH_NAMES = [
    "", "Meskerem", "Tikimt", "Hidar", "Tahsas",
    "Tir", "Yekatit", "Megabit", "Miazia", "Ginbot",
    "Sene", "Hamle", "Nehase", "Pagume",
]

ET_MONTH_NAMES_AM = [
    "", "መስከረም", "ጥቅምት", "ህዳር", "ታህሳስ",
    "ጥር", "የካቲት", "መጋቢት", "ሚያዚያ", "ግንቦት",
    "ሰኔ", "ሐምሌ", "ነሐሴ", "ጳጉሜ",
]


# ── JDN helpers ──────────────────────────────────────────────────────────────

def _gregorian_to_jdn(year: int, month: int, day: int) -> int:
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    return day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045


def _jdn_to_gregorian(jdn: int) -> tuple[int, int, int]:
    l = jdn + 68569
    n = (4 * l) // 146097
    l = l - (146097 * n + 3) // 4
    i = (4000 * (l + 1)) // 1461001
    l = l - (1461 * i) // 4 + 31
    j = (80 * l) // 2447
    day = l - (2447 * j) // 80
    l = j // 11
    month = j + 2 - 12 * l
    year = 100 * (n - 49) + i + l
    return year, month, day


def _ethiopian_to_jdn(et_year: int, et_month: int, et_day: int) -> int:
    return (
        ET_EPOCH_JDN
        + 365 * (et_year - 1)
        + (et_year - 1) // 4
        + 30 * (et_month - 1)
        + (et_day - 1)
    )


def _jdn_to_ethiopian(jdn: int) -> tuple[int, int, int]:
    delta = jdn - ET_EPOCH_JDN
    quad = delta // 1461          # complete 4-year cycles
    remainder = delta % 1461
    year_in_quad = min(remainder // 365, 3)   # 0-3
    et_year = 4 * quad + year_in_quad + 1
    day_of_year = remainder - 365 * year_in_quad   # 0-indexed within ET year
    et_month = day_of_year // 30 + 1
    et_day = day_of_year % 30 + 1
    return et_year, et_month, et_day


# ── Public API ────────────────────────────────────────────────────────────────

def gregorian_to_ethiopian(g_date: date) -> tuple[int, int, int]:
    """Convert a Gregorian date to (et_year, et_month, et_day)."""
    jdn = _gregorian_to_jdn(g_date.year, g_date.month, g_date.day)
    return _jdn_to_ethiopian(jdn)


def ethiopian_to_gregorian(et_year: int, et_month: int, et_day: int) -> date:
    """Convert an Ethiopian date to a Gregorian date object."""
    jdn = _ethiopian_to_jdn(et_year, et_month, et_day)
    y, m, d = _jdn_to_gregorian(jdn)
    return date(y, m, d)


def gregorian_to_et_string(g_date: date) -> str:
    """Return the Ethiopian date as 'DD/MM/YYYY EC', e.g. '23/07/2018 EC'."""
    et_y, et_m, et_d = gregorian_to_ethiopian(g_date)
    return f"{et_d:02d}/{et_m:02d}/{et_y} EC"


def gregorian_to_et_label(g_date: date) -> str:
    """Return a human-readable Ethiopian date, e.g. 'Megabit 23, 2018 EC'."""
    et_y, et_m, et_d = gregorian_to_ethiopian(g_date)
    month_name = ET_MONTH_NAMES[et_m] if et_m <= 13 else "?"
    return f"{month_name} {et_d}, {et_y} EC"


def et_string_to_gregorian(et_str: str) -> Optional[date]:
    """
    Parse an Ethiopian date string (DD/MM/YYYY or DD/MM/YYYY EC)
    and return the Gregorian equivalent.
    Returns None if parsing fails.
    """
    try:
        parts = et_str.replace(" EC", "").strip().split("/")
        et_d, et_m, et_y = int(parts[0]), int(parts[1]), int(parts[2])
        return ethiopian_to_gregorian(et_y, et_m, et_d)
    except Exception:
        return None


def is_ethiopian_year(year: int) -> bool:
    """
    Heuristic: years in range 2010–2020 are almost certainly Ethiopian calendar
    years in the context of this application (current ET year is 2018).
    """
    return 2010 <= year <= 2020
