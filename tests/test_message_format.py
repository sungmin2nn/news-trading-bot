"""텔레그램 메시지 양식 — HTML 서식 + 구조 재배치 테스트.

배경: plain text 양식을 HTML(parse_mode=HTML)로 전환하면서 제목·라벨·종목명을
굵게 처리하고 한눈 스캔 구조로 재배치한다. HTML 모드는 기사 제목에 `<`/`&`가
있으면 발송이 400으로 실패하므로 동적 텍스트는 반드시 이스케이프해야 한다.
"""

from src import main_brief
from src.config import Settings
from src.notify import telegram


def _topic(**kw):
    base = {
        "title": "제목",
        "direction": "상승",
        "action": "관심",
        "status": "new",
        "headline": "한 줄 헤드라인",
        "summary": "무슨 일이 있었나",
        "analysis": "왜 중요한가",
        "impacts": [{"name": "삼성전자", "effect": "수혜"}],
        "direction_reason": "근거",
        "risk": "리스크",
        "confidence": 0.72,
    }
    base.update(kw)
    return base


def _msg(monkeypatch, result, mode="post"):
    # 거래일 분기를 고정해 라벨/날짜에 의존하지 않게 한다
    monkeypatch.setattr(
        main_brief.krx_calendar, "is_krx_business_day", lambda _now: True
    )
    return main_brief.build_message(result, mode)


# ---- build_message: HTML 서식 ----

def test_topic_title_is_bold(monkeypatch):
    msg = _msg(monkeypatch, {"topics": [_topic(title="삼성 HBM")]})
    assert "<b>① 삼성 HBM</b>" in msg


def test_impact_stock_name_is_bold(monkeypatch):
    msg = _msg(monkeypatch, {"topics": [_topic(impacts=[{"name": "삼성전자", "effect": "수혜"}])]})
    assert "<b>삼성전자</b>" in msg


def test_section_labels_are_bold(monkeypatch):
    msg = _msg(monkeypatch, {"topics": [_topic()]})
    assert "<b>무슨일</b>" in msg
    assert "<b>분석</b>" in msg
    assert "<b>결론</b>" in msg


def test_escapes_html_special_chars(monkeypatch):
    # Gemini가 준 제목에 < 와 & 가 섞여도 깨지지 않게 이스케이프해야 한다
    msg = _msg(monkeypatch, {"topics": [_topic(title="A<b> & C")]})
    assert "&lt;" in msg
    assert "&amp;" in msg
    # 원문 그대로(미이스케이프)는 남아있으면 안 된다 → 발송 400 유발
    assert "A<b> & C" not in msg


def test_empty_topics_message_preserved(monkeypatch):
    msg = _msg(monkeypatch, {"topics": []})
    assert "추려낼 이슈가 없습니다" in msg


# ---- telegram.send: parse_mode ----

def test_send_sets_html_parse_mode(monkeypatch):
    captured = {}

    class _Resp:
        status_code = 200
        text = "ok"

    def fake_post(url, data=None, timeout=None):
        captured.update(data or {})
        return _Resp()

    monkeypatch.setattr(telegram.requests, "post", fake_post)
    s = Settings(TELEGRAM_BOT_TOKEN="tok", TELEGRAM_CHAT_ID="chat")
    n = telegram.send(s, "<b>hi</b>")

    assert captured.get("parse_mode") == "HTML"
    assert n == 1
