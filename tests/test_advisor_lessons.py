from src.gemini import advisor


def test_build_prompt_includes_lessons():
    p = advisor._build_prompt([{"title": "t"}], 8, "pre", calibration="", lessons="[전일 실매매] X")
    assert "[전일 실매매] X" in p


def test_build_prompt_lessons_default_empty():
    p = advisor._build_prompt([{"title": "t"}], 8, "pre")
    assert isinstance(p, str)
