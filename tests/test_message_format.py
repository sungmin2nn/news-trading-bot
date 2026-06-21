"""텔레그램 메시지 양식 — HTML 압축 카드 + 한국식 색관습 테스트.

배경: 서술형 2~3문장 단락(무슨일/분석)이 길고 헤드라인↔본문이 안 나뉘며,
구 effect 마크(🔺🔻)가 둘 다 빨강이라 수혜/타격이 구분 안 됐다. 토픽당 4줄
압축 카드로 재배치하고, 한국 주식 색관습(상승/수혜=🔴, 하락/타격=🔵, 중립=⚪)으로
방향·effect를 통일한다. summary/analysis는 학습 루프용으로 스키마엔 남지만 렌더
에서는 제외한다. HTML 모드는 동적 텍스트에 `<`/`&`가 있으면 400이라 이스케이프 필수.
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
    # 번호(①)는 bold 밖, 제목만 굵게 — L1: "① <b>제목</b>   🔴상승"
    msg = _msg(monkeypatch, {"topics": [_topic(title="삼성 HBM")]})
    assert "① <b>삼성 HBM</b>" in msg


def test_impact_stock_name_is_bold(monkeypatch):
    msg = _msg(monkeypatch, {"topics": [_topic(impacts=[{"name": "삼성전자", "effect": "수혜"}])]})
    assert "<b>삼성전자</b>" in msg


def test_headline_rendered_on_own_line(monkeypatch):
    # 헤드라인이 본문과 분리된 단독 줄로 렌더된다(서술형 단락 대체)
    msg = _msg(monkeypatch, {"topics": [_topic(headline="HBM4 양산 앞당겨 공급 확대")]})
    assert "\nHBM4 양산 앞당겨 공급 확대\n" in msg


def test_action_is_bold_text_not_color_circle(monkeypatch):
    # 액션은 색 이모지(🟢🔴) 충돌을 피해 굵은 텍스트 태그로만 표기한다
    msg = _msg(monkeypatch, {"topics": [_topic(action="회피")]})
    assert "<b>회피</b>" in msg


def test_summary_analysis_not_rendered(monkeypatch):
    # summary/analysis 서술 단락은 메시지에서 제외(스키마엔 잔존 — 학습 루프용)
    msg = _msg(
        monkeypatch,
        {"topics": [_topic(summary="긴 서술 무슨일", analysis="긴 서술 분석")]},
    )
    assert "긴 서술 무슨일" not in msg
    assert "긴 서술 분석" not in msg
    assert "무슨일" not in msg
    assert "분석" not in msg


def test_direction_uses_korean_color(monkeypatch):
    # 상승=🔴빨강, 하락=🔵파랑 (한국 주식 관습), 구 차트 이모지 미사용
    up = _msg(monkeypatch, {"topics": [_topic(direction="상승")]})
    down = _msg(monkeypatch, {"topics": [_topic(direction="하락")]})
    assert "🔴상승" in up
    assert "🔵하락" in down
    assert "📈" not in up and "📉" not in down


def test_effect_color_contrast(monkeypatch):
    # 수혜=🔴, 타격=🔵 — 대비색으로 구분. 구 🔺🔻(둘 다 빨강)는 사라져야 한다
    msg = _msg(
        monkeypatch,
        {
            "topics": [
                _topic(
                    impacts=[
                        {"name": "삼성전자", "effect": "수혜"},
                        {"name": "LG엔솔", "effect": "타격"},
                    ]
                )
            ]
        },
    )
    assert "🔴수혜" in msg
    assert "🔵타격" in msg
    assert "🔺" not in msg and "🔻" not in msg


def test_new_tag_only_for_new(monkeypatch):
    new_msg = _msg(monkeypatch, {"topics": [_topic(status="new")]})
    cont_msg = _msg(monkeypatch, {"topics": [_topic(status="continuing")]})
    assert "NEW" in new_msg
    assert "NEW" not in cont_msg
    assert "지속" not in cont_msg  # 지속은 무표시


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
