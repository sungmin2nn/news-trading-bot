"""발송 주제 누적 — 직전 회차 대비 NEW / 지속(ongoing) 판정.

Gemini가 status를 추측하게 두지 않고, 실제 발송 이력(해시)으로 판정한다.
data/sent_topics.json 에 최근 N개 주제 해시를 보존(워크플로가 commit).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

STORE = Path(__file__).resolve().parent.parent.parent / "data" / "sent_topics.json"
WINDOW = 60  # 최근 주제 해시 보존 개수

_WS = re.compile(r"\s+")


def _key(title: str) -> str:
    norm = _WS.sub("", title or "").lower()
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:12]


def _load() -> list[str]:
    if STORE.exists():
        try:
            return json.loads(STORE.read_text(encoding="utf-8")).get("hashes", [])
        except Exception:  # noqa: BLE001 — 깨진 상태면 빈 이력으로 시작
            return []
    return []


def mark_status(topics: list[dict]) -> list[dict]:
    """각 topic에 status('new'|'ongoing') 주입 + 신규 해시 저장."""
    hashes = _load()
    prev = set(hashes)
    for t in topics:
        h = _key(t.get("title", ""))
        t["status"] = "ongoing" if h in prev else "new"
        if h not in hashes:
            hashes.append(h)
    hashes = hashes[-WINDOW:]
    try:
        STORE.parent.mkdir(parents=True, exist_ok=True)
        STORE.write_text(
            json.dumps({"hashes": hashes}, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as e:  # noqa: BLE001
        # 상태 저장 실패는 치명적이지 않으나 가시화 (다음 회차 NEW/지속 부정확)
        print(f"[sent_store] 상태 저장 실패: {e}")
    return topics
