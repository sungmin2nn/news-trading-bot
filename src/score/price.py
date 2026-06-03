"""가격·종목 해석 (P3) — 번들 KRX 상장목록 + yfinance.

종목명→yfinance 심볼: data/krx_listing.json (오프라인, 로컬에서 FDR로 주기 생성).
가격: yfinance (한국 종목 005930.KS / KOSDAQ .KQ, 코스피 지수 ^KS11).
"""

from __future__ import annotations

import json
from pathlib import Path

LISTING_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "krx_listing.json"
KOSPI_SYMBOL = "^KS11"

_listing: dict | None = None


def _load_listing() -> dict:
    global _listing
    if _listing is None:
        try:
            _listing = json.loads(LISTING_PATH.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            _listing = {}
    return _listing


def resolve(name: str) -> str | None:
    """종목명 → yfinance 심볼. 없으면 None(테마·미상장·오타)."""
    m = _load_listing()
    if not name:
        return None
    if name in m:
        return m[name]["yf"]
    nn = name.replace(" ", "")
    for k, v in m.items():
        if k.replace(" ", "") == nn:
            return v["yf"]
    return None


def fetch_closes(symbol: str, start: str, end: str) -> dict[str, float]:
    """start~end(YYYY-MM-DD, end 포함) 일별 종가 {date_iso: close}. 실패 시 {}."""
    import datetime as _dt

    import yfinance as yf

    try:
        end_excl = (_dt.date.fromisoformat(end) + _dt.timedelta(days=1)).isoformat()
        h = yf.Ticker(symbol).history(start=start, end=end_excl, auto_adjust=True)
        if h is None or len(h) == 0:
            return {}
        return {ts.strftime("%Y-%m-%d"): float(c) for ts, c in zip(h.index, h["Close"])}
    except Exception:  # noqa: BLE001
        return {}


def window_return(symbol: str, base: str, horizon: str) -> float | None:
    """base 종가 → horizon 종가 수익률(소수). 종가 없으면 가까운 거래일로 보정. 실패 시 None."""
    closes = fetch_closes(symbol, base, horizon)
    if not closes:
        return None
    dates = sorted(closes)
    # base 이상 첫 거래일, horizon 이하 마지막 거래일
    start_d = next((d for d in dates if d >= base), None)
    end_d = next((d for d in reversed(dates) if d <= horizon), None)
    if not start_d or not end_d or start_d == end_d:
        return None
    p0, p1 = closes[start_d], closes[end_d]
    if p0 <= 0:
        return None
    return (p1 - p0) / p0
