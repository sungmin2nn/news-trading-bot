"""예측 원장 (P2) — 봇이 낸 결론을 '채점 가능한 형태'로 기록한다.

회고·학습 루프(P3 알파 채점 → P4 규칙북 → P5 메타학습)의 데이터 활주로.
지금은 기록만 한다(채점은 P3). 발송 성공 후에만 적재 — 안 보낸 예측은 안 남긴다.

채점 단위(P3 예정): 각 impacts 종목 × direction 기대 → horizon_days 내 코스피 대비
알파로 적중/오답 판정. 종목명→코드 매핑·테마 제외는 채점 시점에 처리한다.

형식: data/predictions.jsonl (1줄 1예측, append-only).
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import pytz

LEDGER = Path(__file__).resolve().parent.parent.parent / "data" / "predictions.jsonl"
KST = pytz.timezone("Asia/Seoul")
DEFAULT_HORIZON_DAYS = 3


def _entry(topic: dict, date_iso: str, ts_iso: str, mode: str) -> dict:
    impacts = [
        {
            "name": im.get("name", ""),
            "kind": im.get("kind", "테마"),
            "effect": im.get("effect", ""),
        }
        for im in (topic.get("impacts") or [])
        if isinstance(im, dict) and im.get("name")
    ]
    title = topic.get("title", "")
    pid = hashlib.sha1(f"{date_iso}|{mode}|{title}".encode("utf-8")).hexdigest()[:12]
    return {
        "id": pid,
        "date": date_iso,
        "ts": ts_iso,
        "briefing": mode,
        "title": title,
        "headline": topic.get("headline", ""),
        "direction": topic.get("direction", ""),
        "direction_reason": topic.get("direction_reason", ""),
        "priced_in": topic.get("priced_in", ""),
        "action": topic.get("action", ""),
        "confidence": topic.get("confidence", 0.0),
        "impacts": impacts,
        "horizon_days": DEFAULT_HORIZON_DAYS,
        "status": "pending",  # P3에서 scored/—로 전이
    }


def record(topics: list[dict], mode: str) -> int:
    """이번 회차 결론을 원장에 append. 적재 건수 반환. 발송 성공 후 호출."""
    if not topics:
        return 0
    now = datetime.now(KST)
    date_iso = now.strftime("%Y-%m-%d")
    ts_iso = now.isoformat(timespec="seconds")
    try:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with LEDGER.open("a", encoding="utf-8") as f:
            for t in topics:
                f.write(json.dumps(_entry(t, date_iso, ts_iso, mode), ensure_ascii=False) + "\n")
        return len(topics)
    except Exception as e:  # noqa: BLE001
        print(f"[prediction_ledger] 적재 실패: {e}", file=sys.stderr)
        return 0
