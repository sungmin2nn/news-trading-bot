import json

from src.publish import candidates_emitter as ce
from src.contract.news_evo_schema import validate_candidates


def test_emit_maps_confidence_to_score(monkeypatch, tmp_path):
    monkeypatch.setattr(ce, "_resolve_price", lambda name: ("005930", 71000, 1.2))
    topics = [{"headline": "반도체 수출 급증", "action": "관심", "confidence": 0.78,
               "impacts": [{"name": "삼성전자", "kind": "종목", "effect": "수혜"}]}]
    out = ce.build_candidates("20260619", topics)
    c = out["strategies"]["news_evo"]["candidates"][0]
    assert c["score"] == 0.78 and c["confidence"] == 0.78
    assert c["code"] == "005930" and c["price"] == 71000 and c["direction"] == "long"
    validate_candidates(out)


def test_emit_filters_non_tradeable(monkeypatch):
    monkeypatch.setattr(ce, "_resolve_price", lambda name: ("005930", 71000, 1.2))
    topics = [
        {"headline": "x", "action": "무시", "confidence": 0.9,
         "impacts": [{"name": "삼성전자", "kind": "종목", "effect": "수혜"}]},
        {"headline": "y", "action": "관심", "confidence": 0.6,
         "impacts": [{"name": "테마X", "kind": "테마", "effect": "수혜"}]},
    ]
    out = ce.build_candidates("20260619", topics)
    assert out["strategies"]["news_evo"]["candidates"] == []


def test_unresolved_price_skipped(monkeypatch):
    monkeypatch.setattr(ce, "_resolve_price", lambda name: None)
    topics = [{"headline": "x", "action": "관심", "confidence": 0.7,
               "impacts": [{"name": "없는종목", "kind": "종목", "effect": "수혜"}]}]
    out = ce.build_candidates("20260619", topics)
    assert out["strategies"]["news_evo"]["candidates"] == []
