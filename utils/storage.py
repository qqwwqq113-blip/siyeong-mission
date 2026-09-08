"""Minty Quest의 로컬 JSON 저장소와 미션·선물 로직."""

from __future__ import annotations

import copy
import json
import logging
import os
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)
ROOT_DIR = Path(__file__).resolve().parent.parent
STATE_ID = "siyeong-family"


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def get_data_filepath() -> Path:
    data_dir = ROOT_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "app_data.json"


def _cloud_client() -> Any | None:
    """배포 환경에서만 Supabase 클라이언트를 늦게 생성합니다."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        return None
    try:
        from supabase import create_client

        return create_client(url, key)
    except (ImportError, ValueError) as error:
        LOGGER.warning("Supabase 연결을 준비하지 못했습니다: %s", error)
        return None


def _load_cloud_data() -> dict[str, Any] | None:
    client = _cloud_client()
    if client is None:
        return None
    try:
        response = client.table("app_state").select("data").eq("id", STATE_ID).maybe_single().execute()
        return response.data.get("data") if response.data else None
    except Exception as error:  # 네트워크 및 SDK 오류는 로컬 사용을 위해 안전하게 처리합니다.
        LOGGER.warning("Supabase 데이터를 읽지 못했습니다: %s", error)
        return None


def _save_cloud_data(data: dict[str, Any]) -> bool | None:
    client = _cloud_client()
    if client is None:
        return None
    try:
        client.table("app_state").upsert({"id": STATE_ID, "data": data}).execute()
        return True
    except Exception as error:
        LOGGER.error("Supabase 저장 실패: %s", error)
        return False


def _new_challenge(title: str, emoji: str, target: int, unit: str, description: str = "") -> dict[str, Any]:
    return {"id": f"challenge-{uuid.uuid4()}", "title": title, "emoji": emoji or "🌟", "description": description,
            "target_count": target, "current_count": 0, "unit_label": unit or "번", "records": [], "status": "active",
            "selected_reward_id": None, "created_at": _now(), "completed_at": None}


def get_initial_schema() -> dict[str, Any]:
    return {"schema_version": 2, "profile": {"child_name": "시영", "daily_memo": "오늘도 작은 도전을 멋지게 해내자!", "updated_at": _now()},
            "wishlist": [], "challenges": [_new_challenge("영어 단어 100점", "📚", 10, "번", "100점 시험을 볼 때마다 별을 하나 받아요."),
                                           _new_challenge("일찍 일어나기", "🌞", 10, "번", "스스로 일어난 아침마다 반짝이는 별!"),
                                           _new_challenge("문제집 A 완주", "🚀", 4, "권", "A1부터 A4까지 한 권씩 완성해요.")]}


def _migrate_legacy(data: dict[str, Any]) -> dict[str, Any]:
    """예전 단어 도장판 데이터를 잃지 않고 첫 미션으로 옮깁니다."""
    profile, legacy_history = data.get("profile", {}), data.get("history", []) or []
    challenge = _new_challenge("영어 단어 100점", "📚", int(profile.get("target_stamps", 10)), "번", "100점 시험을 볼 때마다 별을 하나 받아요.")
    challenge["current_count"] = min(int(profile.get("current_stamps", 0)), challenge["target_count"])
    challenge["records"] = [{"id": item.get("id", f"record-{uuid.uuid4()}"), "date": item.get("date", ""), "amount": 1,
                             "count_after": index, "note": item.get("note", "참 잘했어요!"),
                             "detail": f"{item.get('score', 100)}점 · 단어 {item.get('word_count', 0)}개"}
                            for index, item in enumerate(reversed(legacy_history[-challenge["current_count"]:]), start=1)]
    redeemed = next((item for item in data.get("wishlist", []) if item.get("is_redeemed")), None)
    if challenge["current_count"] >= challenge["target_count"]:
        challenge["completed_at"] = _now()
        if redeemed:
            challenge["status"], challenge["selected_reward_id"], redeemed["claimed_by"] = "reward_selected", redeemed.get("id"), challenge["id"]
        else:
            challenge["status"] = "completed"
    return {"schema_version": 2, "profile": {"child_name": "시영", "daily_memo": profile.get("daily_memo", "오늘도 작은 도전을 멋지게 해내자!"), "updated_at": _now()},
            "wishlist": data.get("wishlist", []) or [], "challenges": [challenge]}


def _normalize_data(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        return get_initial_schema()
    if not data.get("schema_version") or "challenges" not in data:
        return _migrate_legacy(copy.deepcopy(data))
    normalized = copy.deepcopy(data)
    normalized["schema_version"] = 2
    normalized.setdefault("profile", {})
    normalized["profile"]["child_name"] = "시영"
    normalized["profile"].setdefault("daily_memo", "오늘도 작은 도전을 멋지게 해내자!")
    normalized.setdefault("wishlist", [])
    normalized.setdefault("challenges", [])
    for challenge in normalized["challenges"]:
        challenge.setdefault("id", f"challenge-{uuid.uuid4()}")
        challenge.setdefault("emoji", "🌟")
        challenge.setdefault("description", "")
        challenge["target_count"] = max(1, int(challenge.get("target_count", 10)))
        challenge["current_count"] = max(0, min(int(challenge.get("current_count", 0)), challenge["target_count"]))
        challenge.setdefault("unit_label", "번")
        challenge.setdefault("records", [])
        challenge.setdefault("selected_reward_id", None)
        challenge.setdefault("completed_at", None)
        challenge.setdefault("created_at", _now())
        challenge.setdefault("status", "reward_selected" if challenge["selected_reward_id"] else ("completed" if challenge["current_count"] >= challenge["target_count"] else "active"))
    return normalized


def load_data() -> dict[str, Any]:
    cloud_data = _load_cloud_data()
    if cloud_data is not None:
        data = _normalize_data(cloud_data)
        if data != cloud_data:
            save_data(data)
        return data
    filepath = get_data_filepath()
    try:
        if not filepath.exists():
            data = get_initial_schema(); save_data(data); return data
        with filepath.open("r", encoding="utf-8") as file:
            raw_data = json.load(file)
        data = _normalize_data(raw_data)
        if data != raw_data:
            save_data(data)
        return data
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
        LOGGER.warning("데이터를 읽지 못해 초기화합니다: %s", error)
        data = get_initial_schema(); save_data(data); return data


def save_data(data: dict[str, Any]) -> bool:
    data["profile"]["updated_at"] = _now()
    cloud_saved = _save_cloud_data(data)
    if cloud_saved is not None:
        return cloud_saved
    filepath, temporary_path = get_data_filepath(), get_data_filepath().with_suffix(".json.tmp")
    try:
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2); file.write("\n")
        os.replace(temporary_path, filepath)
        return True
    except (OSError, TypeError, ValueError, KeyError) as error:
        LOGGER.error("데이터 저장 실패: %s", error)
        temporary_path.unlink(missing_ok=True)
        return False


def get_challenge(data: dict[str, Any], challenge_id: str) -> dict[str, Any] | None:
    return next((item for item in data["challenges"] if item.get("id") == challenge_id), None)


def add_challenge(title: str, emoji: str, target: int, unit: str, description: str) -> tuple[bool, str]:
    if not title.strip(): return False, "미션 이름을 입력해주세요."
    if target < 1: return False, "목표 횟수는 1 이상이어야 해요."
    data = load_data(); data["challenges"].append(_new_challenge(title.strip(), emoji.strip() or "🌟", target, unit.strip() or "번", description.strip()))
    return (True, "새 미션을 만들었어요!") if save_data(data) else (False, "저장하지 못했어요.")


def add_progress(challenge_id: str, amount: int, note: str, activity_date: str | None = None) -> tuple[bool, str, bool]:
    if amount < 1: return False, "적립 수는 1 이상이어야 해요.", False
    data = load_data(); challenge = get_challenge(data, challenge_id)
    if not challenge: return False, "미션을 찾지 못했어요.", False
    if challenge["status"] != "active": return False, "이 미션은 이미 완성했어요. 선물을 받고 새 라운드를 시작해주세요.", False
    applied = min(amount, challenge["target_count"] - challenge["current_count"])
    challenge["current_count"] += applied
    challenge["records"].append({"id": f"record-{uuid.uuid4()}", "date": activity_date or date.today().isoformat(), "amount": applied,
                                 "count_after": challenge["current_count"], "note": note.strip() or "오늘도 멋지게 해냈어요!", "detail": ""})
    completed = challenge["current_count"] >= challenge["target_count"]
    if completed: challenge["status"], challenge["completed_at"] = "completed", _now()
    if not save_data(data): return False, "저장하지 못했어요.", False
    return True, f"{challenge['emoji']} {applied}{challenge['unit_label']} 적립! {challenge['current_count']}/{challenge['target_count']}", completed


def undo_progress(challenge_id: str) -> tuple[bool, str]:
    data = load_data(); challenge = get_challenge(data, challenge_id)
    if not challenge or not challenge["records"]: return False, "되돌릴 기록이 없어요."
    if challenge.get("selected_reward_id"): return False, "이미 선물을 받은 미션은 되돌릴 수 없어요."
    record = challenge["records"].pop()
    challenge["current_count"] = max(0, challenge["current_count"] - int(record.get("amount", 1)))
    challenge["status"], challenge["completed_at"] = "active", None
    return (True, "마지막 적립을 되돌렸어요.") if save_data(data) else (False, "저장하지 못했어요.")


def add_wishlist_item(title: str, image_url: str = "", memo: str = "") -> bool:
    if not title.strip(): return False
    data = load_data(); data["wishlist"].append({"id": f"wish-{uuid.uuid4()}", "title": title.strip(), "image_url": image_url.strip(), "memo": memo.strip(), "claimed_by": None, "created_at": _now()})
    return save_data(data)


def delete_wishlist_item(item_id: str) -> bool:
    data = load_data(); item = next((item for item in data["wishlist"] if item.get("id") == item_id), None)
    if not item or item.get("claimed_by"): return False
    data["wishlist"] = [item for item in data["wishlist"] if item.get("id") != item_id]
    return save_data(data)


def choose_reward(challenge_id: str, item_id: str) -> tuple[bool, str]:
    data = load_data(); challenge, item = get_challenge(data, challenge_id), next((item for item in data["wishlist"] if item.get("id") == item_id), None)
    if not challenge or not item or challenge["status"] != "completed" or item.get("claimed_by"): return False, "지금은 이 선물을 고를 수 없어요."
    challenge["selected_reward_id"], challenge["status"], item["claimed_by"] = item_id, "reward_selected", challenge_id
    item["is_redeemed"], item["redeemed_at"] = True, _now()
    return (True, f"{item['title']} 선물을 골랐어요!") if save_data(data) else (False, "저장하지 못했어요.")


def restart_challenge(challenge_id: str) -> tuple[bool, str]:
    data = load_data(); challenge = get_challenge(data, challenge_id)
    if not challenge or challenge["status"] != "reward_selected": return False, "선물을 고른 완성 미션만 새로 시작할 수 있어요."
    challenge["current_count"], challenge["records"], challenge["status"] = 0, [], "active"
    challenge["selected_reward_id"], challenge["completed_at"] = None, None
    return (True, "새 라운드를 시작했어요. 또 반짝이는 목표를 채워봐요!") if save_data(data) else (False, "저장하지 못했어요.")
