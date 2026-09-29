"""마음 기록의 표시 정보와 기간별 통계 계산."""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from typing import Any, Iterable


MOODS: dict[str, dict[str, str]] = {
    "excited": {"emoji": "😄", "label": "신나요", "color": "#FFD166"},
    "good": {"emoji": "🙂", "label": "좋아요", "color": "#7ED6B4"},
    "okay": {"emoji": "😐", "label": "보통이에요", "color": "#A9D8CE"},
    "sad": {"emoji": "😢", "label": "속상해요", "color": "#8FB8DE"},
    "angry": {"emoji": "😡", "label": "화나요", "color": "#FF9B91"},
}


def mood_text(mood_id: str, include_label: bool = True) -> str:
    mood = MOODS.get(mood_id, MOODS["okay"])
    return f"{mood['emoji']} {mood['label']}" if include_label else mood["emoji"]


def entries_by_date(entries: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(entry.get("date", "")): entry for entry in entries if entry.get("date")}


def period_bounds(period: str, reference: date) -> tuple[date, date, str]:
    if period == "주별":
        start = reference - timedelta(days=reference.weekday())
        end = start + timedelta(days=6)
        label = f"{start:%Y.%m.%d} ~ {end:%m.%d}"
    elif period == "연도별":
        start, end = date(reference.year, 1, 1), date(reference.year, 12, 31)
        label = f"{reference.year}년"
    else:
        start = reference.replace(day=1)
        next_month = date(reference.year + (reference.month == 12), reference.month % 12 + 1, 1)
        end = next_month - timedelta(days=1)
        label = f"{reference.year}년 {reference.month}월"
    return start, end, label


def entries_in_period(entries: Iterable[dict[str, Any]], start: date, end: date) -> list[dict[str, Any]]:
    selected = []
    for entry in entries:
        try:
            entry_date = date.fromisoformat(str(entry.get("date", "")))
        except ValueError:
            continue
        if start <= entry_date <= end:
            selected.append(entry)
    return sorted(selected, key=lambda item: item["date"])


def mood_counts(entries: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(str(entry.get("mood", "")) for entry in entries)
    return {mood_id: counts.get(mood_id, 0) for mood_id in MOODS}


def favorite_mood(entries: Iterable[dict[str, Any]]) -> str | None:
    counts = mood_counts(entries)
    highest = max(counts.values(), default=0)
    if highest == 0:
        return None
    return next(mood_id for mood_id in MOODS if counts[mood_id] == highest)


def longest_streak(entries: Iterable[dict[str, Any]]) -> int:
    days = sorted({date.fromisoformat(str(entry["date"])) for entry in entries if entry.get("date")})
    if not days:
        return 0
    longest = current = 1
    for previous, current_day in zip(days, days[1:]):
        current = current + 1 if current_day - previous == timedelta(days=1) else 1
        longest = max(longest, current)
    return longest
