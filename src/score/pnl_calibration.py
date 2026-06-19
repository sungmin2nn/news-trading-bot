"""실현손익(연속값) 기반 calibration. P4 calibration.py(binary hit-rate)의 자매 — pnl 차원."""
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))


def _bucket(score):
    if score is None:
        return None
    if score >= 0.7:
        return ">=0.7"
    if score >= 0.5:
        return "0.5-0.7"
    return "<0.5"


def _agg(pnls):
    n = len(pnls)
    return {"n": n,
            "win_rate": round(sum(1 for p in pnls if p > 0) / n, 4),
            "avg_pnl_pct": round(sum(pnls) / n, 4)}


def compute(history: list[dict]):
    """ntr_results 누적 history → pnl calibration dict. 성숙 청산(filled) 0건 → None."""
    flat = []  # (score_bucket, exit_reason, pnl)
    for rec in history:
        for t in rec.get("trades") or []:
            if t.get("status") != "filled" or t.get("realized_pnl_pct") is None:
                continue
            flat.append((_bucket(t.get("selected_score")), t.get("exit_reason"),
                         float(t["realized_pnl_pct"])))
    if not flat:
        return None
    cal = {
        "updated_at": datetime.now(KST).isoformat(timespec="seconds"),
        "overall": _agg([p for _, _, p in flat]),
        "by_score_bucket": [],
        "by_exit_reason": [],
    }
    for label in (">=0.7", "0.5-0.7", "<0.5"):
        sub = [p for b, _, p in flat if b == label]
        if sub:
            cal["by_score_bucket"].append({"bucket": label, **_agg(sub)})
    for reason in ("trailing_10", "trailing_5", "trailing_3", "loss", "close"):
        sub = [p for _, r, p in flat if r == reason]
        if sub:
            cal["by_exit_reason"].append({"reason": reason, **_agg(sub)})
    return cal
