from src.score.pnl_calibration import compute


def _hist(trades):
    return [{"date": "20260618", "strategy": "news_evo", "trades": trades, "skipped": []}]


def test_overall_win_rate_and_avg():
    h = _hist([
        {"status": "filled", "realized_pnl_pct": 2.0, "exit_reason": "trailing_5", "selected_score": 0.8, "code": "1", "name": "a"},
        {"status": "filled", "realized_pnl_pct": -3.0, "exit_reason": "loss", "selected_score": 0.4, "code": "2", "name": "b"},
    ])
    cal = compute(h)
    assert cal["overall"]["n"] == 2
    assert abs(cal["overall"]["win_rate"] - 0.5) < 1e-9
    assert abs(cal["overall"]["avg_pnl_pct"] - (-0.5)) < 1e-9


def test_holding_excluded():
    h = _hist([{"status": "holding", "realized_pnl_pct": None, "exit_reason": None,
                "selected_score": 0.7, "code": "1", "name": "a"}])
    assert compute(h) is None  # 성숙 청산 0건 → 콜드스타트


def test_avg_monotonic_in_pnl():
    low = compute(_hist([{"status": "filled", "realized_pnl_pct": -5.0, "exit_reason": "loss",
                          "selected_score": 0.6, "code": "1", "name": "a"}]))
    high = compute(_hist([{"status": "filled", "realized_pnl_pct": 5.0, "exit_reason": "trailing_5",
                           "selected_score": 0.6, "code": "1", "name": "a"}]))
    assert high["overall"]["avg_pnl_pct"] > low["overall"]["avg_pnl_pct"]
