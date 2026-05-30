"""발송 주제 누적 — 직전 회차 대비 NEW / 지속(ongoing) 판정.

판정 기준은 Gemini가 생성한 title 문자열 그대로가 아니다(매 호출 표현이 흔들려
같은 이슈도 매번 NEW로 떠버린다). 대신 관련 종목(tickers) 겹침 + 제목 핵심
토큰 자카드 유사도로 같은 이슈인지 본다.

판정(mark_status)과 영속(persist)을 분리한다 — 영속은 텔레그램 발송 성공 후에만.
이렇게 해야 발송 실패/ dry-run이 NEW 태깅을 오염시키지 않는다.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

STORE = Path(__file__).resolve().parent.parent.parent / "data" / "sent_topics.json"
WINDOW = 40  # 최근 주제 보존 개수
_JACCARD_MIN = 0.5  # 제목 토큰 유사도 임계
_TOKEN = re.compile(r"[가-힣A-Za-z0-9]{2,}")


def _tokens(title: str) -> set[str]:
    return set(_TOKEN.findall((title or "").lower()))


def _tickers(tickers) -> set[str]:
    return {re.sub(r"\s+", "", t).lower() for t in (tickers or []) if t}


def _load() -> list[dict]:
    if STORE.exists():
        try:
            return json.loads(STORE.read_text(encoding="utf-8")).get("topics", [])
        except Exception:  # noqa: BLE001 — 깨진 상태면 빈 이력으로 시작
            return []
    return []


def _is_ongoing(toks: set[str], tks: set[str], prev: list[dict]) -> bool:
    for p in prev:
        if tks and (tks & set(p.get("tickers", []))):
            return True
        ptoks = set(p.get("tokens", []))
        if toks and ptoks:
            union = toks | ptoks
            if union and len(toks & ptoks) / len(union) >= _JACCARD_MIN:
                return True
    return False


def mark_status(topics: list[dict]) -> list[dict]:
    """각 topic에 status('new'|'ongoing') 주입. 저장은 하지 않는다(판정 전용)."""
    prev = _load()
    for t in topics:
        toks = _tokens(t.get("title", ""))
        tks = _tickers(t.get("tickers"))
        t["status"] = "ongoing" if _is_ongoing(toks, tks, prev) else "new"
    return topics


def persist(topics: list[dict]) -> None:
    """발송 성공 후 호출 — 이번 회차 주제를 이력에 추가 저장."""
    prev = _load()
    for t in topics:
        prev.append(
            {
                "tokens": sorted(_tokens(t.get("title", ""))),
                "tickers": sorted(_tickers(t.get("tickers"))),
            }
        )
    prev = prev[-WINDOW:]
    try:
        STORE.parent.mkdir(parents=True, exist_ok=True)
        STORE.write_text(
            json.dumps({"topics": prev}, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as e:  # noqa: BLE001
        print(f"[sent_store] 상태 저장 실패: {e}", file=sys.stderr)
