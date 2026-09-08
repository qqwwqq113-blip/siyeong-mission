"""Minty Stamp의 스타일과 선택적 시각/청각 효과."""

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

ROOT_DIR = Path(__file__).resolve().parent.parent


def inject_custom_css() -> None:
    """외부 CSS 파일을 읽어 앱 전체에 적용합니다."""
    css_path = ROOT_DIR / "assets" / "css" / "style.css"
    try:
        css = css_path.read_text(encoding="utf-8")
    except OSError:
        css = ""
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def trigger_confetti(mode: str = "normal") -> None:
    """브라우저에서 도장 획득 또는 완주 폭죽을 실행합니다."""
    if mode == "grand":
        script = """
        const end = Date.now() + 5000;
        const colors = ['#38BFA7', '#FFD166', '#FF7A72', '#7C83FD'];
        (function frame() {
          confetti({particleCount: 12, spread: 90, origin: {x: Math.random(), y: 0.25}, colors});
          if (Date.now() < end) requestAnimationFrame(frame);
        }());
        """
    else:
        script = """
        confetti({particleCount: 90, spread: 70, origin: {x: 0.08, y: 0.65}});
        confetti({particleCount: 90, spread: 70, origin: {x: 0.92, y: 0.65}});
        """
    components.html(
        "<script src='https://cdn.jsdelivr.net/npm/canvas-confetti@1.6.0/dist/confetti.browser.min.js'></script>"
        f"<script>setTimeout(() => {{{script}}}, 300);</script>",
        height=0,
    )


def play_sound(sound_key: str) -> None:
    """존재하는 MP3 효과음을 Base64 오디오 태그로 재생합니다."""
    sound_path = ROOT_DIR / "assets" / "sounds" / f"{sound_key}.mp3"
    if not sound_path.exists():
        return
    try:
        encoded = base64.b64encode(sound_path.read_bytes()).decode("ascii")
    except OSError:
        return
    st.markdown(
        f"<audio autoplay style='display:none'><source src='data:audio/mp3;base64,{encoded}'></audio>",
        unsafe_allow_html=True,
    )
