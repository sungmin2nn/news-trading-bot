from src.score import calibration


def _rec(confidence, results):
    return {"confidence": confidence, "results": results}


def test_compute_overall():
    recs = [
        _rec(0.8, [{"effect": "수혜", "correct": True}, {"effect": "타격", "correct": False}]),
        _rec(0.6, [{"effect": "수혜", "correct": False}]),
    ]
    cal = calibration.compute(recs)
    assert cal["overall"]["n"] == 3
    assert cal["overall"]["hit_rate"] == round(1 / 3, 4)


def test_compute_excludes_none_correct():
    recs = [_rec(0.8, [{"effect": "수혜", "correct": None}, {"effect": "수혜", "correct": True}])]
    cal = calibration.compute(recs)
    assert cal["overall"]["n"] == 1
    assert cal["overall"]["hit_rate"] == 1.0


def test_compute_by_confidence_buckets():
    recs = [
        _rec(0.9, [{"effect": "수혜", "correct": True}]),
        _rec(0.6, [{"effect": "수혜", "correct": False}]),
        _rec(0.3, [{"effect": "수혜", "correct": True}]),
    ]
    cal = calibration.compute(recs)
    b = {x["bucket"]: x for x in cal["by_confidence"]}
    assert b[">=0.7"]["n"] == 1 and b[">=0.7"]["hit_rate"] == 1.0
    assert b["0.5-0.7"]["n"] == 1 and b["0.5-0.7"]["hit_rate"] == 0.0
    assert b["<0.5"]["n"] == 1 and b["<0.5"]["hit_rate"] == 1.0


def test_compute_missing_confidence_excluded_from_buckets_but_in_overall():
    recs = [_rec(None, [{"effect": "수혜", "correct": True}])]
    cal = calibration.compute(recs)
    assert cal["overall"]["n"] == 1
    assert cal["by_confidence"] == []


def test_compute_by_effect():
    recs = [_rec(0.8, [{"effect": "수혜", "correct": True}, {"effect": "타격", "correct": False}])]
    cal = calibration.compute(recs)
    e = {x["effect"]: x for x in cal["by_effect"]}
    assert e["수혜"]["hit_rate"] == 1.0 and e["타격"]["hit_rate"] == 0.0


def test_compute_returns_none_when_no_scored_results():
    assert calibration.compute([]) is None
    assert calibration.compute([_rec(0.8, [{"effect": "수혜", "correct": None}])]) is None
