from src.gemini import advisor


def test_render_pnl_none_empty():
    assert advisor._render_pnl_calibration(None) == ""


def test_render_pnl_shows_winrate():
    cal = {"overall": {"n": 12, "win_rate": 0.33, "avg_pnl_pct": -1.2},
           "by_exit_reason": [{"reason": "loss", "n": 6, "win_rate": 0.0, "avg_pnl_pct": -3.1}],
           "by_score_bucket": []}
    out = advisor._render_pnl_calibration(cal)
    assert "33%" in out and "loss" in out
