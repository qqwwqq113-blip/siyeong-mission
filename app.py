from __future__ import annotations

import calendar
import os
from datetime import date
from html import escape
from random import choice
from typing import Any

import streamlit as st

from utils import effects, moods, storage

st.set_page_config(page_title="시영의 반짝 미션", page_icon="🌈", layout="wide")

CHEERS = ["시영이는 매일 조금씩 더 멋져지고 있어!", "작은 한 걸음도 반짝반짝 빛나는 성공이야!", "할 수 있어! 오늘의 시영 파워 최고!", "도전하는 마음이 진짜 슈퍼파워야!"]


def cloud_secrets() -> dict[str, Any]:
    """로컬에는 secrets.toml이 없어도 앱이 실행되도록 합니다."""
    try:
        return st.secrets.to_dict()
    except FileNotFoundError:
        return {}


def configure_cloud() -> None:
    """Streamlit Cloud의 비밀값을 저장 모듈이 읽을 환경변수로 전달합니다."""
    secrets = cloud_secrets()
    for name in ("SUPABASE_URL", "SUPABASE_KEY"):
        if value := secrets.get(name):
            os.environ[name] = str(value)


def refresh_data() -> dict[str, Any]:
    if "app_data" not in st.session_state:
        try:
            st.session_state.app_data = storage.load_data()
        except storage.StorageUnavailableError:
            st.error("☁️ 저장된 기록에 잠시 연결하지 못했어요. 기록은 초기화되지 않았으니 안심하세요.")
            st.caption("잠시 후 다시 시도해주세요. 계속되면 클라우드 저장소 상태를 확인해야 합니다.")
            if st.button("🔄 다시 연결하기", use_container_width=True):
                st.rerun()
            st.stop()
    return st.session_state.app_data


def selected_challenge(data: dict[str, Any]) -> dict[str, Any]:
    challenges = data["challenges"]
    valid_ids = {item["id"] for item in challenges}
    if st.session_state.get("selected_challenge_id") not in valid_ids:
        st.session_state.selected_challenge_id = challenges[0]["id"]
    return storage.get_challenge(data, st.session_state.selected_challenge_id) or challenges[0]


def render_header(data: dict[str, Any]) -> None:
    profile = data["profile"]
    active = sum(item["status"] == "active" for item in data["challenges"])
    done = sum(item["status"] == "reward_selected" for item in data["challenges"])
    st.markdown(f"<section class='hero'><div class='eyebrow'>SIYEONG'S SPARKLE QUEST ✦</div><h1>시영의 반짝반짝 미션 놀이터 🌈</h1><p>오늘의 작은 도전이 내일의 큰 자신감이 돼요!</p></section>", unsafe_allow_html=True)
    left, middle, right = st.columns([5, 2, 1])
    with left:
        with st.form("daily_memo_form"):
            memo_column, save_column = st.columns([5, 1])
            with memo_column:
                memo = st.text_input("오늘의 각오", value=str(profile.get("daily_memo", "")), label_visibility="collapsed", placeholder="오늘 내가 해낼 멋진 일은?")
            with save_column:
                save_memo = st.form_submit_button("각오 저장", use_container_width=True)
            if save_memo:
                profile["daily_memo"] = memo.strip()
                storage.save_data(data)
                st.success("각오를 저장했어요!")
    with middle: st.metric("진행 중 미션", f"{active}개")
    with right: st.metric("받은 선물", f"{done}개")
    if st.button("✨ 오늘의 응원 뽑기"):
        st.session_state.cheer = choice(CHEERS)
    if st.session_state.get("cheer"):
        st.info(f"🦄 {st.session_state.cheer}")


def render_mission_cards(data: dict[str, Any]) -> None:
    st.subheader("🗺️ 나의 미션 지도")
    for start in range(0, len(data["challenges"]), 3):
        columns = st.columns(3)
        for column, mission in zip(columns, data["challenges"][start:start + 3]):
            state = {"active": "도전 중", "completed": "선물 고르기!", "reward_selected": "선물 선택 완료"}[mission["status"]]
            with column:
                st.markdown(f"<div class='mission-card'><div class='mission-emoji'>{escape(mission['emoji'])}</div><strong>{escape(mission['title'])}</strong><br><span>{mission['current_count']} / {mission['target_count']} {escape(mission['unit_label'])} · {state}</span></div>", unsafe_allow_html=True)
                st.progress(mission["current_count"] / mission["target_count"])
                if st.button("이 미션 보기", key=f"view-{mission['id']}", use_container_width=True):
                    st.session_state.selected_challenge_id = mission["id"]
                    st.rerun()


def render_stamp_board(mission: dict[str, Any]) -> None:
    current, target = mission["current_count"], mission["target_count"]
    st.markdown(f"## {escape(mission['emoji'])} {escape(mission['title'])}", unsafe_allow_html=True)
    st.caption(mission.get("description", ""))
    st.progress(current / target)
    st.caption(f"{current} / {target} {mission['unit_label']} 달성 · {max(0, target - current)}{mission['unit_label']} 남았어요!")
    records = mission.get("records", [])
    for row_start in range(0, target, 5):
        columns = st.columns(5)
        for offset, column in enumerate(columns):
            number = row_start + offset + 1
            if number > target: continue
            earned = number <= current
            record = next((item for item in records if item.get("count_after") == number), {})
            icon = "🌟" if earned else ("👑" if number == target else "⭐")
            label = "해냈다!" if earned else f"{number}번째 별"
            detail = escape(str(record.get("date", "기다리는 중"))) if earned else ""
            classes = "slot slot-earned" if earned else "slot slot-empty"
            if number == target: classes += " slot-finale"
            with column:
                st.markdown(f"<div class='{classes}'><div class='slot-icon'>{icon}</div><div class='slot-label'>{label}</div><div class='slot-date'>{detail}</div></div>", unsafe_allow_html=True)
    if mission["status"] == "completed":
        st.warning("🎁 미션 완성! 선물 하나를 골라보세요.")
        if st.button("🎁 선물 고르기", key=f"open-reward-{mission['id']}"):
            st.session_state.pending_reward_challenge_id = mission["id"]
            st.rerun()
    elif mission["status"] == "reward_selected": st.success("🎉 선물을 골랐어요! 부모님과 즐겁게 받아보세요.")
    if records:
        with st.expander("📖 이번 미션의 반짝 기록"):
            for record in reversed(records):
                st.write(f"{record.get('date', '')} · +{record.get('amount', 1)}{mission['unit_label']} — {record.get('note', '')}")


def render_wishlist(data: dict[str, Any]) -> None:
    st.subheader("🎁 선물 보물상자")
    st.caption("미션 하나를 완성하면 선물은 딱 하나만 골라요.")
    with st.expander("✨ 새 선물 넣기"):
        with st.form("wishlist_form", clear_on_submit=True):
            title = st.text_input("선물 이름 *")
            image_url = st.text_input("이미지 URL (선택: 이미지 파일 주소)")
            memo = st.text_area("부모님과의 약속 메모 (선택)")
            if st.form_submit_button("보물상자에 넣기", use_container_width=True):
                if storage.add_wishlist_item(title, image_url, memo):
                    st.session_state.app_data = storage.load_data(); st.rerun()
                st.error("선물 이름을 입력해주세요.")
    if not data["wishlist"]:
        st.info("아직 선물이 없어요. 갖고 싶은 선물을 보물상자에 넣어보세요!"); return
    for start in range(0, len(data["wishlist"]), 3):
        columns = st.columns(3)
        for column, item in zip(columns, data["wishlist"][start:start + 3]):
            with column:
                st.markdown("<div class='wish-card'>", unsafe_allow_html=True)
                if item.get("image_url"): st.image(item["image_url"], use_column_width="always")
                else: st.markdown("<div class='gift-icon'>🎁</div>", unsafe_allow_html=True)
                st.markdown(f"### {escape(item['title'])}", unsafe_allow_html=True)
                st.caption(item.get("memo", ""))
                claimed_by = storage.get_challenge(data, item.get("claimed_by", ""))
                if claimed_by: st.success(f"{claimed_by['emoji']} {claimed_by['title']}의 선물")
                else:
                    st.caption("아직 고를 수 있는 선물이에요")
                    if st.button("삭제", key=f"delete-{item['id']}", use_container_width=True):
                        storage.delete_wishlist_item(item["id"]); st.session_state.app_data = storage.load_data(); st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)


def _move_month(month_start: date, offset: int) -> date:
    month_index = month_start.year * 12 + month_start.month - 1 + offset
    return date(month_index // 12, month_index % 12 + 1, 1)


def _prepare_mood_date() -> date:
    pending = st.session_state.pop("pending_mood_date", None)
    if pending:
        st.session_state.mood_date_picker = pending
    elif "mood_date_picker" not in st.session_state:
        st.session_state.mood_date_picker = date.today()
    return st.session_state.mood_date_picker


def render_mood_entry_form(data: dict[str, Any]) -> date:
    st.subheader("💗 오늘의 마음 남기기")
    st.caption("기쁜 마음도 속상한 마음도 모두 소중해요. 지난 날짜의 기록도 언제든 고칠 수 있어요.")
    _prepare_mood_date()
    selected = st.date_input(
        "기록할 날짜",
        max_value=date.today(),
        key="mood_date_picker",
    )
    if st.session_state.get("last_mood_date") != selected:
        st.session_state.last_mood_date = selected
        st.session_state.mood_calendar_month = selected.replace(day=1)

    entry = moods.entries_by_date(data["mood_entries"]).get(selected.isoformat(), {})
    mood_ids = list(moods.MOODS)
    current_mood = entry.get("mood", "good")
    with st.form(f"mood-entry-{selected.isoformat()}"):
        mood_id = st.radio(
            "오늘은 어떤 마음이었나요?",
            mood_ids,
            index=mood_ids.index(current_mood) if current_mood in mood_ids else 1,
            format_func=moods.mood_text,
            horizontal=True,
        )
        memo = st.text_area(
            "짧은 메모 (선택)",
            value=str(entry.get("memo", "")),
            max_chars=300,
            placeholder="오늘 기억하고 싶은 일을 짧게 적어봐요.",
        )
        button_text = "마음 기록 수정하기" if entry else "오늘의 마음 저장하기"
        if st.form_submit_button(f"💾 {button_text}", use_container_width=True):
            success, message = storage.upsert_mood_entry(selected.isoformat(), mood_id, memo)
            if success:
                st.session_state.app_data = storage.load_data()
                st.session_state.mood_notice = message
                st.rerun()
            st.error(message)
    if notice := st.session_state.pop("mood_notice", None):
        st.success(f"🌷 {notice}")
        st.balloons()
    return selected


def render_mood_calendar(data: dict[str, Any], selected: date) -> None:
    entries = moods.entries_by_date(data["mood_entries"])
    month_start = st.session_state.get("mood_calendar_month", selected.replace(day=1))
    st.session_state.mood_calendar_month = month_start

    previous, title, today_button, next_month = st.columns([1, 3, 2, 1])
    if previous.button("◀ 이전 달", use_container_width=True):
        st.session_state.mood_calendar_month = _move_month(month_start, -1)
        st.rerun()
    title.markdown(f"### {month_start.year}년 {month_start.month}월")
    if today_button.button("이번 달", use_container_width=True):
        st.session_state.mood_calendar_month = date.today().replace(day=1)
        st.rerun()
    if next_month.button("다음 달 ▶", use_container_width=True, disabled=month_start >= date.today().replace(day=1)):
        st.session_state.mood_calendar_month = _move_month(month_start, 1)
        st.rerun()

    headers = st.columns(7)
    for column, weekday in zip(headers, ["일", "월", "화", "수", "목", "금", "토"]):
        column.markdown(f"<div class='calendar-weekday'>{weekday}</div>", unsafe_allow_html=True)

    month_weeks = calendar.Calendar(firstweekday=6).monthdayscalendar(month_start.year, month_start.month)
    for week_index, week in enumerate(month_weeks):
        columns = st.columns(7)
        for weekday_index, (column, day_number) in enumerate(zip(columns, week)):
            if day_number == 0:
                column.markdown("<div class='calendar-blank'></div>", unsafe_allow_html=True)
                continue
            day = date(month_start.year, month_start.month, day_number)
            entry = entries.get(day.isoformat())
            emoji = moods.mood_text(str(entry.get("mood", "")), False) if entry else "·"
            prefix = "🌟 " if day == date.today() else ""
            label = f"{prefix}{day_number}\n{emoji}"
            if column.button(label, key=f"mood-day-{day.isoformat()}", use_container_width=True, disabled=day > date.today()):
                st.session_state.pending_mood_date = day
                st.rerun()
            if day == selected:
                column.markdown("<div class='calendar-selected'>선택됨</div>", unsafe_allow_html=True)

    selected_entry = entries.get(selected.isoformat())
    if selected_entry:
        mood_label = moods.mood_text(str(selected_entry.get("mood", "")))
        st.info(f"{selected:%Y년 %m월 %d일} · {mood_label}\n\n{selected_entry.get('memo') or '남긴 메모는 없어요.'}")
    else:
        st.caption(f"{selected:%Y년 %m월 %d일}에는 아직 마음 기록이 없어요.")


def render_mood_stats(data: dict[str, Any], reference: date) -> None:
    st.subheader("📊 마음 기록 통계")
    period = st.radio("통계 기간", ["주별", "월별", "연도별"], horizontal=True, label_visibility="collapsed")
    start, end, period_label = moods.period_bounds(period, reference)
    entries = moods.entries_in_period(data["mood_entries"], start, end)
    counts = moods.mood_counts(entries)
    favorite = moods.favorite_mood(entries)
    effective_end = min(end, date.today())
    available_days = max(0, (effective_end - start).days + 1) if start <= effective_end else 0
    record_rate = round(len(entries) / available_days * 100) if available_days else 0

    st.caption(f"기준 기간 · {period_label}")
    metric_columns = st.columns(4)
    metric_columns[0].metric("기록한 날", f"{len(entries)}일")
    metric_columns[1].metric("기록률", f"{record_rate}%")
    metric_columns[2].metric("가장 많았던 마음", moods.mood_text(favorite) if favorite else "아직 없음")
    metric_columns[3].metric("최장 연속 기록", f"{moods.longest_streak(entries)}일")

    chart_data = [
        {"기분": moods.mood_text(mood_id), "횟수": count}
        for mood_id, count in counts.items()
    ]
    st.bar_chart(chart_data, x="기분", y="횟수")

    if entries:
        with st.expander(f"📝 {period_label}의 마음 메모 모아보기"):
            for entry in reversed(entries):
                st.markdown(f"**{entry['date']} · {moods.mood_text(entry['mood'])}**")
                st.write(entry.get("memo") or "남긴 메모는 없어요.")
    else:
        st.info("이 기간에는 아직 마음 기록이 없어요. 첫 마음을 남겨볼까요?")


def render_mood_journal(data: dict[str, Any]) -> None:
    selected = render_mood_entry_form(data)
    st.divider()
    render_mood_calendar(data, selected)
    st.divider()
    render_mood_stats(data, selected)


def render_parent_sidebar(data: dict[str, Any]) -> None:
    st.sidebar.header("🧑‍🧑‍🧒 부모님 미션 관리")
    if not st.sidebar.checkbox("부모님 확인 모드"):
        st.sidebar.info("미션 적립과 새 미션 만들기는 부모님 확인 모드에서 해요."); return
    with st.sidebar.expander("➕ 새 미션 만들기"):
        with st.form("new_challenge_form", clear_on_submit=True):
            title = st.text_input("미션 이름", placeholder="예: 피아노 연습")
            emoji = st.text_input("대표 이모지", value="🌟", max_chars=4)
            target = st.number_input("목표 횟수/개수", min_value=1, value=10)
            unit = st.text_input("단위", value="번", max_chars=8)
            description = st.text_area("미션 설명", placeholder="어떤 때 한 칸을 채우는지 적어주세요.")
            if st.form_submit_button("새 미션 출발!"):
                success, message = storage.add_challenge(title, emoji, int(target), unit, description)
                if success: st.session_state.app_data = storage.load_data(); st.success(message); st.rerun()
                st.error(message)
    active = [item for item in data["challenges"] if item["status"] == "active"]
    if active:
        labels = {f"{item['emoji']} {item['title']}": item["id"] for item in active}
        with st.sidebar.form("progress_form"):
            selected_label = st.selectbox("적립할 미션", labels)
            amount = st.number_input("이번에 적립할 수", min_value=1, value=1)
            activity_date = st.date_input("날짜", value=date.today())
            note = st.text_area("칭찬 한마디", value="오늘도 멋지게 해냈어요!")
            if st.form_submit_button("✨ 별 적립하기", use_container_width=True):
                success, message, completed = storage.add_progress(labels[selected_label], int(amount), note, activity_date.isoformat())
                if success:
                    st.session_state.app_data = storage.load_data()
                    if completed: st.session_state.pending_reward_challenge_id = labels[selected_label]; effects.trigger_confetti("grand")
                    else: effects.trigger_confetti("normal")
                    st.rerun()
                st.error(message)
    current = selected_challenge(data)
    if st.sidebar.button("↩️ 선택한 미션 마지막 적립 취소", use_container_width=True):
        success, message = storage.undo_progress(current["id"])
        if success:
            st.sidebar.success(message)
            st.session_state.app_data = storage.load_data()
            st.rerun()
        else:
            st.sidebar.error(message)
    if current["status"] == "reward_selected" and st.sidebar.button("🌱 이 미션 새 라운드 시작", use_container_width=True):
        success, message = storage.restart_challenge(current["id"])
        if success:
            st.sidebar.success(message)
            st.session_state.app_data = storage.load_data()
            st.rerun()
        else:
            st.sidebar.error(message)


@st.dialog("🎉 미션 완성! 선물 하나 고르기")
def render_reward_picker(data: dict[str, Any], mission: dict[str, Any]) -> None:
    st.balloons()
    st.markdown(f"## {mission['emoji']} {escape(mission['title'])} 완성!", unsafe_allow_html=True)
    st.write("시영아, 정말 대단해! 보물상자에서 받고 싶은 선물 **하나**를 골라봐.")
    available = [item for item in data["wishlist"] if not item.get("claimed_by")]
    if not available:
        st.info("선물 후보가 아직 없어요. 부모님이 보물상자에 선물을 넣어주시면 골라볼 수 있어요.")
        if st.button("나중에 고를게요"): st.session_state.pending_reward_challenge_id = None; st.rerun()
        return
    for item in available:
        if st.button(f"{item['title']} 받기 🎁", key=f"choose-{mission['id']}-{item['id']}", use_container_width=True):
            success, message = storage.choose_reward(mission["id"], item["id"])
            if success:
                st.session_state.app_data = storage.load_data(); st.session_state.pending_reward_challenge_id = None
                effects.trigger_confetti("grand"); st.success(message); st.rerun()
            st.error(message)


def main() -> None:
    configure_cloud()
    effects.inject_custom_css()
    data = refresh_data()
    render_header(data)
    render_parent_sidebar(data)
    data = refresh_data()
    map_tab, gift_tab, mood_tab = st.tabs(["🗺️ 미션 지도", "🎁 선물 보물상자", "😊 마음 달력"])
    with map_tab:
        render_mission_cards(data); st.divider(); render_stamp_board(selected_challenge(data))
    with gift_tab: render_wishlist(data)
    with mood_tab: render_mood_journal(data)
    pending_id = st.session_state.get("pending_reward_challenge_id")
    pending = storage.get_challenge(data, pending_id) if pending_id else None
    if pending and pending["status"] == "completed": render_reward_picker(data, pending)


if __name__ == "__main__":
    main()
