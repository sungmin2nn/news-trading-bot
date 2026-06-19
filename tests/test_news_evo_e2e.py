import json
from pathlib import Path
from src.publish import candidates_emitter as ce
from src.contract.news_evo_schema import validate_candidates, validate_results
from src.score.pnl_calibration import compute


def test_full_contract_roundtrip(monkeypatch):
    monkeypatch.setattr(ce, "_resolve_price", lambda name: ("005930", 71000, 1.2))
    topics = [{"headline": "반도체", "action": "관심", "confidence": 0.78,
               "impacts": [{"name": "삼성전자", "kind": "종목", "effect": "수혜"}]}]
    cand = ce.build_candidates("20260619", topics)
    validate_candidates(cand)
    # NTR이 체결·청산했다고 가정한 results
    results = {"date": "20260619", "strategy": "news_evo", "trades": [
        {"code": "005930", "name": "삼성전자", "status": "filled", "entry": 71000,
         "exit": 69200, "realized_pnl_pct": -2.54, "exit_reason": "loss",
         "held_min": 210, "selected_score": 0.78}], "skipped": []}
    validate_results(results)
    cal = compute([results])
    assert cal["overall"]["n"] == 1
