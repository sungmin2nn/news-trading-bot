from src import main_brief


def test_prep_lessons_and_pnlcal(monkeypatch):
    monkeypatch.setattr(main_brief.ntr_results, "fetch_and_store", lambda *a, **k: {"trades": []})
    monkeypatch.setattr(main_brief.ntr_results, "read_history", lambda: [])
    monkeypatch.setattr(main_brief.pnl_calibration, "compute", lambda h: None)
    monkeypatch.setattr(main_brief.lessons_builder, "build_lessons_block", lambda r, s: "BLOCK")
    lessons, pnl_block = main_brief._prep_news_evo(settings=object(), btype="pre")
    assert lessons == "BLOCK"


def test_prep_skips_post_mode():
    lessons, pnl_block = main_brief._prep_news_evo(settings=object(), btype="post")
    assert lessons == ""
    assert pnl_block == ""
