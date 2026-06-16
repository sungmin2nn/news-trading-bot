"""P4 캘리브레이션 — scores.jsonl 채점 실측에서 결정적 통계 산출.

confidence를 실측 적중에 맞춰 보정하도록 분석 프롬프트에 주입할 통계를 만든다.
채점 단위는 종목(results[] 원소). correct가 None(미성숙·kind≠종목)인 결과는 제외.
순수 함수(compute) + 러너(run). 무작위·외부 호출 없음.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pytz

from src.state import lessons

KST = pytz.timezone("Asia/Seoul")
SCORES = Path(__file__).resolve().parent.parent.parent / "data" / "scores.jsonl"


def _bucket(conf):
    if conf is None:
        return None
    if conf >= 0.7:
        return ">=0.7"
    if conf >= 0.5:
        return "0.5-0.7"
    return "<0.5"


def compute(records: list[dict]):
    """채점 레코드 → calibration dict. 종목 결과 0건이면 None(콜드스타트)."""
    flat = []  # (confidence, effect, correct_bool)
    for rec in records:
        conf = rec.get("confidence")
        for res in rec.get("results") or []:
            if res.get("correct") is None:
                continue
            flat.append((conf, res.get("effect"), res.get("correct") is True))
    if not flat:
        return None

    def _rate(items):
        return {"n": len(items), "hit_rate": round(sum(1 for c in items if c) / len(items), 4)}

    cal = {
        "updated_at": datetime.now(KST).isoformat(timespec="seconds"),
        "overall": _rate([c for _, _, c in flat]),
        "by_confidence": [],
        "by_effect": [],
    }
    for label in (">=0.7", "0.5-0.7", "<0.5"):
        sub = [c for conf, _, c in flat if _bucket(conf) == label]
        if sub:
            cal["by_confidence"].append({"bucket": label, **_rate(sub)})
    for eff in ("수혜", "타격", "중립"):
        sub = [c for _, e, c in flat if e == eff]
        if sub:
            cal["by_effect"].append({"effect": eff, **_rate(sub)})
    return cal


def _read_scores(path: Path = SCORES) -> list[dict]:
    if not path.exists():
        return []
    out = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def run() -> int:
    """scores.jsonl → compute → lessons.json 갱신. compute None이면 미갱신(직전 유지)."""
    cal = compute(_read_scores())
    if cal is None:
        print("[calibration] 채점 데이터 부족 — lessons 미갱신", file=sys.stderr)
        return 0
    lessons.update_calibration(cal)
    print(f"[calibration] updated: N={cal['overall']['n']} hit={cal['overall']['hit_rate']}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
