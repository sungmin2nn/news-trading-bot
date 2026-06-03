"""알파 채점 (P3) — 성숙한 예측을 코스피 대비 알파로 채점.

규칙(디폴트):
- 호라이즌 = 3 거래일 (예측 base 거래일의 종가 → +3 거래일 종가)
- 채점 = 종목 알파(종목 수익률 − 코스피 수익률). 시장 통째 상승/하락의 베타 함정 회피.
- effect 기대: 수혜→알파>+밴드 / 타격→알파<−밴드 / 중립→|알파|≤밴드
- kind='종목'만 채점(테마는 가격 없어 skip).
- 표본 부족·과적합 경계는 P4/P5의 몫. P3는 결과(scores.jsonl)만 적재.

입력: data/predictions.jsonl (pending)
출력: data/scores.jsonl (append-only, 이미 채점된 id는 skip)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta

import pytz

from src.score import price
from src.state.prediction_ledger import LEDGER
from src.utils import krx_calendar

KST = pytz.timezone("Asia/Seoul")
SCORES = LEDGER.parent / "scores.jsonl"
DEADBAND = 0.005  # ±0.5% 중립 구간
_EFFECT_EXPECT = {"수혜": "up", "타격": "down", "중립": "flat"}


def _base_trading_day(d):
    while not krx_calendar.is_krx_business_day(d):
        d += timedelta(days=1)
    return d


def _trading_days_after(d, n):
    cnt = 0
    while cnt < n:
        d += timedelta(days=1)
        if krx_calendar.is_krx_business_day(d):
            cnt += 1
    return d


def _load_predictions() -> list[dict]:
    if not LEDGER.exists():
        return []
    out = []
    for line in LEDGER.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except Exception:  # noqa: BLE001
                pass
    return out


def _scored_ids() -> set[str]:
    if not SCORES.exists():
        return set()
    ids = set()
    for line in SCORES.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                ids.add(json.loads(line)["id"])
            except Exception:  # noqa: BLE001
                pass
    return ids


def _score_one(p: dict) -> dict | None:
    """성숙했으면 채점 결과 dict, 아직이면 None."""
    base = _base_trading_day(datetime.strptime(p["date"], "%Y-%m-%d").date())
    horizon = _trading_days_after(base, int(p.get("horizon_days", 3)))
    today = datetime.now(KST).date()
    if horizon >= today:
        return None  # 미성숙 (horizon 종가 아직 없음)

    base_s, horizon_s = base.isoformat(), horizon.isoformat()
    kospi = price.window_return(price.KOSPI_SYMBOL, base_s, horizon_s)
    results = []
    for im in p.get("impacts", []):
        if im.get("kind") != "종목":
            continue
        name = im.get("name", "")
        sym = price.resolve(name)
        if not sym:
            results.append({"name": name, "status": "unresolved"})
            continue
        r = price.window_return(sym, base_s, horizon_s)
        if r is None or kospi is None:
            results.append({"name": name, "symbol": sym, "status": "no_price"})
            continue
        alpha = r - kospi
        expect = _EFFECT_EXPECT.get(im.get("effect", ""), "flat")
        if expect == "up":
            correct = alpha > DEADBAND
        elif expect == "down":
            correct = alpha < -DEADBAND
        else:
            correct = abs(alpha) <= DEADBAND
        results.append(
            {
                "name": name, "symbol": sym, "effect": im.get("effect"),
                "expect": expect, "stock_ret": round(r, 4),
                "alpha": round(alpha, 4), "correct": bool(correct),
            }
        )
    scored = [x for x in results if "correct" in x]
    hit = round(sum(x["correct"] for x in scored) / len(scored), 3) if scored else None
    return {
        "id": p["id"], "date": p["date"], "briefing": p.get("briefing"),
        "title": p.get("title"), "direction": p.get("direction"),
        "priced_in": p.get("priced_in"), "confidence": p.get("confidence"),
        "base": base_s, "horizon": horizon_s, "horizon_days": int(p.get("horizon_days", 3)),
        "kospi_ret": round(kospi, 4) if kospi is not None else None,
        "results": results, "hit": hit,
        "scored_at": datetime.now(KST).isoformat(timespec="seconds"),
    }


def run() -> int:
    preds = _load_predictions()
    done = _scored_ids()
    pending = [p for p in preds if p.get("id") and p["id"] not in done]
    newly = []
    for p in pending:
        try:
            res = _score_one(p)
        except Exception as e:  # noqa: BLE001
            print(f"[scorer] {p.get('id')} 채점 실패: {e}", file=sys.stderr)
            continue
        if res:
            newly.append(res)
    if newly:
        with SCORES.open("a", encoding="utf-8") as f:
            for r in newly:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
    hits = [r["hit"] for r in newly if r["hit"] is not None]
    avg = round(sum(hits) / len(hits), 3) if hits else None
    print(
        f"scored +{len(newly)} (pending {len(pending)}, matured {len(newly)}) "
        f"· 종목적중률 {avg if avg is not None else 'n/a'}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(run())
