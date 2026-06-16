from src.gemini import advisor


def test_render_empty_when_none():
    assert advisor._render_calibration(None) == ""
    assert advisor._render_calibration({}) == ""


def test_render_includes_overall_and_instruction():
    cal = {"overall": {"n": 59, "hit_rate": 0.20}, "by_confidence": [], "by_effect": []}
    block = advisor._render_calibration(cal)
    assert "N=59" in block
    assert "20%" in block
    assert "confidence" in block


def test_render_marks_low_n_with_reference_tag():
    cal = {"overall": {"n": 59, "hit_rate": 0.2},
           "by_effect": [{"effect": "타격", "n": 5, "hit_rate": 0.4}]}
    block = advisor._render_calibration(cal)
    assert "(참고)" in block


def test_build_prompt_includes_calibration_block():
    prompt = advisor._build_prompt([{"title": "t"}], 8, "post", "BLOCK_MARKER")
    assert "BLOCK_MARKER" in prompt


def test_build_prompt_default_fills_placeholder():
    prompt = advisor._build_prompt([{"title": "t"}], 8, "post")
    assert "{calibration}" not in prompt
