"""news_evo 두 JSON 계약 검증기. 외부 입력(신뢰 불가) 방어 — security.md."""
import re

_CODE_RE = re.compile(r"^\d{6}$")
# exit_reason은 NTR TRAILING_LEVELS config에서 trailing_<트리거>로 동적 생성된다.
# 하드코딩 집합 대신 정규식으로 trailing_<digits>를 허용해 config 변경에도 발행이 안 깨지게 한다.
_EXIT_REASON_RE = re.compile(r"^(trailing_\d+|loss|close)$")


def _num(v):
    return (isinstance(v, (int, float)) and not isinstance(v, bool)
            and v == v and v not in (float("inf"), float("-inf")))


def validate_candidates(data: dict) -> None:
    if not isinstance(data, dict) or "strategies" not in data:
        raise ValueError("candidates: strategies 누락")
    block = data["strategies"].get("news_evo")
    if not isinstance(block, dict):
        raise ValueError("candidates: strategies.news_evo 누락")
    for c in block.get("candidates", []):
        if not _CODE_RE.match(str(c.get("code", ""))):
            raise ValueError(f"candidates: code 형식 오류 {c.get('code')}")
        s = c.get("score")
        if not _num(s) or not (0.0 <= s <= 1.0):
            raise ValueError(f"candidates: score 0~1 위반 {s}")
        if not _num(c.get("price")) or not _num(c.get("change_pct")):
            raise ValueError("candidates: price/change_pct 누락·비수치")


def validate_results(data: dict) -> None:
    if not isinstance(data, dict) or data.get("strategy") != "news_evo":
        raise ValueError("results: strategy=news_evo 아님")
    for t in data.get("trades", []):
        if not _CODE_RE.match(str(t.get("code", ""))):
            raise ValueError(f"results: code 형식 오류 {t.get('code')}")
        if t.get("status") not in {"filled", "holding"}:
            raise ValueError(f"results: status 오류 {t.get('status')}")
        ss = t.get("selected_score")
        if not _num(ss) or not (0.0 <= ss <= 1.0):
            raise ValueError(f"results: selected_score 0~1 위반 {ss}")
        if t["status"] == "filled":
            if not _EXIT_REASON_RE.match(str(t.get("exit_reason", ""))):
                raise ValueError(f"results: exit_reason 위반 {t.get('exit_reason')}")
            if not _num(t.get("realized_pnl_pct")):
                raise ValueError("results: realized_pnl_pct 비수치")
    for sk in data.get("skipped", []):
        if not _CODE_RE.match(str(sk.get("code", ""))):
            raise ValueError(f"results.skipped: code 오류 {sk.get('code')}")
