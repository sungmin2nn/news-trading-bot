"""Gemini 호출 재시도/백오프 동작 테스트.

배경: 2026-06-07~12 GH Actions postmarket 실패 클러스터의 근본 원인은
Gemini 503/500/429(일시 장애)에 대한 재시도 부재였다. 한 번의 transient 에러가
brief 전체를 exit 1로 죽여 그날 예측 1건이 통째 유실됐다.
(출처: vault/50_Projects/self-evolving-trading-loop.md, log.md 2026-06-16 fix entry)
"""

import json

import pytest
import requests

from src.gemini import advisor
from src.gemini.advisor import GeminiError


class FakeResponse:
    def __init__(self, status_code, text="", payload=None):
        self.status_code = status_code
        self.text = text
        self._payload = payload if payload is not None else {}

    def json(self):
        return self._payload


def _make_post(sequence):
    """sequence의 각 원소가 Exception이면 raise, 아니면 반환하는 가짜 post."""
    calls = {"n": 0}

    def fake_post(*args, **kwargs):
        item = sequence[calls["n"]]
        calls["n"] += 1
        if isinstance(item, Exception):
            raise item
        return item

    fake_post.calls = calls
    return fake_post


def _no_sleep(_seconds):
    _no_sleep.total += 1


_no_sleep.total = 0


@pytest.fixture(autouse=True)
def _reset_sleep_counter():
    _no_sleep.total = 0
    yield


def _post(monkeypatch, sequence, **kw):
    fake = _make_post(sequence)
    monkeypatch.setattr(advisor.requests, "post", fake)
    resp = advisor._post_with_retry(
        "http://x",
        params={},
        headers={},
        data="{}",
        timeout=1,
        sleep=_no_sleep,
        **kw,
    )
    return resp, fake


def test_returns_immediately_on_200(monkeypatch):
    resp, fake = _post(monkeypatch, [FakeResponse(200, payload={"ok": 1})])
    assert resp.status_code == 200
    assert fake.calls["n"] == 1
    assert _no_sleep.total == 0


def test_retries_on_503_then_succeeds(monkeypatch):
    resp, fake = _post(
        monkeypatch,
        [FakeResponse(503, "high demand"), FakeResponse(503), FakeResponse(200)],
    )
    assert resp.status_code == 200
    assert fake.calls["n"] == 3
    assert _no_sleep.total == 2  # 실패 2회마다 백오프


def test_retries_on_429_and_500_then_succeeds(monkeypatch):
    resp, fake = _post(
        monkeypatch,
        [FakeResponse(429), FakeResponse(500), FakeResponse(200)],
    )
    assert resp.status_code == 200
    assert fake.calls["n"] == 3


def test_raises_geminierror_after_exhausting(monkeypatch):
    fake = _make_post([FakeResponse(503, "down")] * 3)
    monkeypatch.setattr(advisor.requests, "post", fake)
    with pytest.raises(GeminiError):
        advisor._post_with_retry(
            "http://x", params={}, headers={}, data="{}", timeout=1,
            max_attempts=3, sleep=_no_sleep,
        )
    assert fake.calls["n"] == 3


def test_no_retry_on_client_error_400(monkeypatch):
    resp, fake = _post(monkeypatch, [FakeResponse(400, "bad request")])
    assert resp.status_code == 400
    assert fake.calls["n"] == 1  # 4xx는 결정적 — 재시도 안 함
    assert _no_sleep.total == 0


def test_retries_on_network_exception_then_succeeds(monkeypatch):
    resp, fake = _post(
        monkeypatch,
        [requests.ConnectionError("reset"), FakeResponse(200)],
    )
    assert resp.status_code == 200
    assert fake.calls["n"] == 2


def test_raises_on_persistent_network_exception(monkeypatch):
    fake = _make_post([requests.Timeout("t")] * 3)
    monkeypatch.setattr(advisor.requests, "post", fake)
    with pytest.raises(GeminiError):
        advisor._post_with_retry(
            "http://x", params={}, headers={}, data="{}", timeout=1,
            max_attempts=3, sleep=_no_sleep,
        )
    assert fake.calls["n"] == 3
