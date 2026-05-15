from __future__ import annotations

from pathlib import Path

import streamlit as st


CSS_PATH = Path(__file__).resolve().parent.parent / 'assets' / 'style.css'


def load_css() -> None:
    if CSS_PATH.exists():
        st.markdown(f'<style>{CSS_PATH.read_text(encoding="utf-8")}</style>', unsafe_allow_html=True)


def render_metric_card(title: str, value: str, subtitle: str = '') -> None:
    st.markdown(
        f'''
        <div class="metric-card">
            <div class="metric-title">{title}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-subtitle">{subtitle}</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def render_info_card(title: str, content: str) -> None:
    st.markdown(
        f'''
        <div class="info-card">
            <div class="info-card-title">{title}</div>
            <div class="info-card-content">{content}</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )
