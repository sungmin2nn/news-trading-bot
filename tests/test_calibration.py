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


def test_read_scores_skips_corrupt_lines(tmp_path):
    from src.score import calibration as c
    p = tmp_path / "scores.jsonl"
    p.write_text(
        '{"confidence": 0.8, "results": [{"effect": "수혜", "correct": true}]}\n'
        "{ broken json\n"
        '{"confidence": 0.5, "results": [{"effect": "타격", "correct": false}]}\n',
        encoding="utf-8",
    )
    recs = c._read_scores(p)
    assert len(recs) == 2  # corrupt middle line skipped, not raised


def test_run_writes_lessons(monkeypatch, tmp_path):
    from src.score import calibration as c
    from src.state import lessons

    scores = tmp_path / "scores.jsonl"
    import json
    scores.write_text(
        json.dumps({"confidence": 0.8, "results": [{"effect": "수혜", "correct": True}]}) + "\n",
        encoding="utf-8",
    )
    lessons_path = tmp_path / "lessons.json"
    monkeypatch.setattr(c, "SCORES", scores)
    monkeypatch.setattr(lessons, "LESSONS", lessons_path)

    rc = c.run()
    assert rc == 0
    data = lessons.load(lessons_path)
    assert data["calibration"]["overall"]["n"] == 1


def test_run_skips_when_no_data(monkeypatch, tmp_path):
    from src.score import calibration as c
    from src.state import lessons

    scores = tmp_path / "scores.jsonl"
    scores.write_text("", encoding="utf-8")
    lessons_path = tmp_path / "lessons.json"
    monkeypatch.setattr(c, "SCORES", scores)
    monkeypatch.setattr(lessons, "LESSONS", lessons_path)

    rc = c.run()
    assert rc == 0
    assert not lessons_path.exists()  # 콜드스타트 — 미갱신
