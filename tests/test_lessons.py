import json

from src.state import lessons


def test_update_creates_with_calibration_and_empty_rules(tmp_path):
    p = tmp_path / "lessons.json"
    cal = {"overall": {"n": 5, "hit_rate": 0.2}}
    lessons.update_calibration(cal, path=p)
    data = lessons.load(p)
    assert data["calibration"] == cal
    assert data["rules"] == []
    assert len(data["changelog"]) == 1
    assert data["changelog"][0]["event"] == "calibration_updated"


def test_update_preserves_existing_rules(tmp_path):
    p = tmp_path / "lessons.json"
    lessons.update_calibration({"overall": {"n": 1, "hit_rate": 1.0}}, path=p)
    data = lessons.load(p)
    data["rules"].append({"id": "r1", "text": "x", "status": "active"})
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    lessons.update_calibration({"overall": {"n": 2, "hit_rate": 0.5}}, path=p)
    data2 = lessons.load(p)
    assert data2["rules"] == [{"id": "r1", "text": "x", "status": "active"}]
    assert data2["calibration"]["overall"]["n"] == 2
    assert len(data2["changelog"]) == 2


def test_load_returns_none_on_missing(tmp_path):
    assert lessons.load(tmp_path / "nope.json") is None


def test_load_returns_none_on_corrupt(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    assert lessons.load(p) is None
