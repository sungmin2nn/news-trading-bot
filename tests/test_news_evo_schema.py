import json
from pathlib import Path
from src.contract.news_evo_schema import validate_results, validate_candidates

_FIX = Path(__file__).parent / "fixtures"

def test_golden_results_valid():
    validate_results(json.loads((_FIX / "results_news_golden.json").read_text(encoding="utf-8")))

def test_results_rejects_bad_exit_reason():
    bad = json.loads((_FIX / "results_news_golden.json").read_text(encoding="utf-8"))
    bad["trades"][0]["exit_reason"] = "target"
    try:
        validate_results(bad); assert False
    except ValueError:
        pass

def test_golden_candidates_valid():
    validate_candidates(json.loads((_FIX / "candidates_news_golden.json").read_text(encoding="utf-8")))
