"""선정 topics → candidates_{T}_news.json(score 0~1).

거래가능(action 관심/관찰)·종목·수혜·long만, 가격해석 성공분만 후보로 emit.
score=confidence(별도 가중식 없음 — pnl 보정은 프롬프트에서 이미 반영).
NTR이 fetch할 포맷으로 변환. price.py resolve/fetch_closes 재사용.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

from src.score import price

KST = timezone(timedelta(hours=9))
_TRADEABLE = {"관심", "관찰"}
OUT_DIR = Path(__file__).resolve().parents[2] / "data" / "news_evo"


def _resolve_price(name: str):
    """종목명 → (code 6자리, price int, change_pct float) 또는 None.

    price.resolve는 yfinance 심볼("005930.KS")을 돌려준다. '.' 앞 6자리 code 추출.
    price.fetch_closes(symbol, start, end)는 start/end가 YYYY-MM-DD str, 키도 date_iso str.
    """
    symbol = price.resolve(name)
    if not symbol:
        return None
    code = symbol.split(".")[0]
    if not (code.isdigit() and len(code) == 6):
        return None
    today = datetime.now(KST).date()
    closes = price.fetch_closes(
        symbol, (today - timedelta(days=10)).isoformat(), today.isoformat()
    )
    if not closes:
        return None
    days = sorted(closes)  # 키가 YYYY-MM-DD str이라 사전식=시간순 일치
    last = int(round(closes[days[-1]]))
    prev = closes[days[-2]] if len(days) >= 2 else closes[days[-1]]
    change = round((closes[days[-1]] - prev) / prev * 100, 2) if prev else 0.0
    return code, last, change


def build_candidates(date_ymd: str, topics: list[dict]) -> dict:
    cands = []
    for t in topics:
        if t.get("action") not in _TRADEABLE:
            continue
        conf = round(float(t.get("confidence", 0.0)), 4)
        for imp in t.get("impacts") or []:
            if imp.get("kind") != "종목" or imp.get("effect") != "수혜":
                continue
            resolved = _resolve_price(imp.get("name", ""))
            if not resolved:
                continue
            code, px, change = resolved
            cands.append({
                "code": code,
                "name": imp["name"],
                "score": conf,
                "price": px,
                "change_pct": change,
                "themes": [],
                "direction": "long",
                "reason": str(t.get("headline", ""))[:120],
                "confidence": conf,
            })
    return {
        "date": date_ymd,
        "generated_at": datetime.now(KST).isoformat(timespec="seconds"),
        "strategies": {"news_evo": {"candidates": cands}},
    }


def emit(date_ymd: str, topics: list[dict]) -> Path:
    from src.contract.news_evo_schema import validate_candidates

    data = build_candidates(date_ymd, topics)
    validate_candidates(data)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"candidates_{date_ymd}_news.json"
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
