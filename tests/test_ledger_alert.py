"""원장 적재 실패 가시화 테스트 (error-visibility).

배경: prediction_ledger.record()는 적재 실패 시 stderr에만 찍고 0을 반환한다
(브리핑 발송을 깨지 않으려는 의도). 그런데 main()은 그래도 return 0(green) →
**브리핑은 나갔는데 회고·학습 활주로(predictions.jsonl)는 조용히 유실**되고
GH 런은 초록, telegram 경보도 없다. shadow_exits incident와 동일한 silent-loss.
적재 건수가 예측 건수보다 적으면 사용자 가시 채널(telegram)로 경보해야 한다.
"""

import pytest

from src import main_brief


class _Tel:
    def __init__(self):
        self.sent = []

    def send(self, settings, msg):
        self.sent.append(msg)
        return 1


@pytest.fixture
def fake_tel(monkeypatch):
    t = _Tel()
    monkeypatch.setattr(main_brief.telegram, "send", t.send)
    return t


def test_alerts_when_ledger_records_fewer_than_topics(fake_tel):
    topics = [{"title": "a"}, {"title": "b"}, {"title": "c"}]
    alerted = main_brief._alert_if_ledger_gap(
        settings=object(), topics=topics, recorded=0, dry_run=False
    )
    assert alerted is True
    assert len(fake_tel.sent) == 1
    assert "원장" in fake_tel.sent[0]


def test_no_alert_when_all_recorded(fake_tel):
    topics = [{"title": "a"}]
    alerted = main_brief._alert_if_ledger_gap(
        settings=object(), topics=topics, recorded=1, dry_run=False
    )
    assert alerted is False
    assert fake_tel.sent == []


def test_no_alert_when_no_topics(fake_tel):
    alerted = main_brief._alert_if_ledger_gap(
        settings=object(), topics=[], recorded=0, dry_run=False
    )
    assert alerted is False
    assert fake_tel.sent == []


def test_partial_shortfall_alerts(fake_tel):
    topics = [{"title": "a"}, {"title": "b"}]
    alerted = main_brief._alert_if_ledger_gap(
        settings=object(), topics=topics, recorded=1, dry_run=False
    )
    assert alerted is True
    assert len(fake_tel.sent) == 1
