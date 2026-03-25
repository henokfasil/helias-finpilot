"""
Reusable UI components for the Helias FinPilot dashboard.
"""
from __future__ import annotations

import streamlit as st


def page_header(title: str, subtitle: str = "") -> None:
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #0f3460 0%, #16213e 100%);
        padding: 28px 32px 20px;
        border-radius: 12px;
        margin-bottom: 28px;
        color: white;
    ">
        <div style="font-size:11px; letter-spacing:3px; text-transform:uppercase; opacity:0.6; margin-bottom:6px;">
            Helias FinPilot
        </div>
        <div style="font-size:26px; font-weight:700; margin-bottom:4px;">{title}</div>
        <div style="font-size:14px; opacity:0.7;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)


def kpi_card(label: str, value: str, delta: str = "", color: str = "#0f3460") -> None:
    delta_html = f'<div style="font-size:12px; color:#27ae60; margin-top:4px;">{delta}</div>' if delta else ""
    st.markdown(f"""
    <div style="
        background: white;
        border-radius: 10px;
        padding: 20px 22px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.07);
        border-left: 4px solid {color};
    ">
        <div style="font-size:12px; color:#888; text-transform:uppercase; letter-spacing:1px;">{label}</div>
        <div style="font-size:24px; font-weight:700; color:{color}; margin-top:4px;">{value}</div>
        {delta_html}
    </div>
    """, unsafe_allow_html=True)


def status_badge(status: str) -> str:
    colors = {
        "confirmed":          ("#d4edda", "#155724"),
        "draft":              ("#fff3cd", "#856404"),
        "needs_clarification":("#cce5ff", "#004085"),
        "rejected":           ("#f8d7da", "#721c24"),
    }
    bg, fg = colors.get(status, ("#eee", "#333"))
    return f'<span style="background:{bg}; color:{fg}; padding:2px 8px; border-radius:12px; font-size:12px; font-weight:600;">{status}</span>'


def divider() -> None:
    st.markdown("<hr style='border:none; border-top:1px solid #eee; margin:20px 0;'>", unsafe_allow_html=True)
