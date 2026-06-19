import json
from pathlib import Path
from src.state import ntr_results

class FakeResp:
    def __init__(self, status, payload): self.status_code = status; self._p = payload
    def json(self): return self._p
    @property
    def text(self): return json.dumps(self._p)

def test_fetch_valid_results_appends(tmp_path, monkeypatch):
    golden = json.loads((Path(__file__).parent / "fixtures" / "results_news_golden.json").read_text(encoding="utf-8"))
    monkeypatch.setattr(ntr_results.requests, "get", lambda *a, **k: FakeResp(200, golden))
    hist = tmp_path / "ntr_results.jsonl"
    monkeypatch.setattr(ntr_results, "HISTORY", hist)
    out = ntr_results.fetch_and_store("20260618", base_url="http://x")
    assert out["date"] == "20260619"
    assert hist.exists() and len(hist.read_text(encoding="utf-8").strip().splitlines()) == 1

def test_missing_results_graceful_none(tmp_path, monkeypatch):
    monkeypatch.setattr(ntr_results.requests, "get", lambda *a, **k: FakeResp(404, {}))
    monkeypatch.setattr(ntr_results, "HISTORY", tmp_path / "h.jsonl")
    assert ntr_results.fetch_and_store("20260618", base_url="http://x") is None

def test_invalid_schema_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(ntr_results.requests, "get",
                        lambda *a, **k: FakeResp(200, {"strategy": "wrong"}))
    monkeypatch.setattr(ntr_results, "HISTORY", tmp_path / "h.jsonl")
    try:
        ntr_results.fetch_and_store("20260618", base_url="http://x"); assert False
    except ntr_results.NtrResultsError:
        pass
