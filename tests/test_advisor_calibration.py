import pytest

from src.gemini import advisor


@pytest.mark.parametrize("bad", ["garbage", [1, 2, 3], 42, {"overall": "nope"}, {"overall": [1]}])
def test_render_non_dict_shapes_return_empty(bad):
    assert advisor._render_calibration(bad) == ""


def test_render_skips_non_dict_segment_entries():
    cal = {
        "overall": {"n": 10, "hit_rate": 0.2},
        "by_effect": ["not-a-dict", {"effect": "수혜", "n": 10, "hit_rate": 0.3}],
        "by_confidence": "not-a-list",
    }
    block = advisor._render_calibration(cal)
    assert "수혜 N=10" in block      # valid entry kept
    assert "전반 N=10" in block      # block still renders, no crash


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


def test_render_returns_empty_when_overall_malformed():
    # overall present but missing n/hit_rate → skip injection, don't crash
    assert advisor._render_calibration({"overall": {}}) == ""
    assert advisor._render_calibration({"overall": {"n": 5}}) == ""  # missing hit_rate


def test_render_skips_malformed_segment_entries():
    cal = {
        "overall": {"n": 10, "hit_rate": 0.2},
        "by_effect": [
            {"effect": "수혜", "n": 10, "hit_rate": 0.3},   # ok
            {"effect": "타격", "n": 5},                       # missing hit_rate → skip
            {"n": 4, "hit_rate": 0.5},                        # missing effect key → skip
        ],
    }
    block = advisor._render_calibration(cal)
    assert "수혜 N=10" in block         # good entry kept
    assert "타격" not in block          # malformed entry skipped, no crash
    assert "전반 N=10" in block         # block still renders


def test_build_prompt_includes_calibration_block():
    prompt = advisor._build_prompt([{"title": "t"}], 8, "post", "BLOCK_MARKER")
    assert "BLOCK_MARKER" in prompt


def test_build_prompt_default_fills_placeholder():
    prompt = advisor._build_prompt([{"title": "t"}], 8, "post")
    assert "{calibration}" not in prompt
