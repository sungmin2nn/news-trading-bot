"""Telegram 송신 — 4096자 분할, 실패 가시화(NotifyError)."""

from __future__ import annotations

import requests

from src.config import Settings


class NotifyError(RuntimeError):
    pass


def _split(text: str, limit: int) -> list[str]:
    """줄 경계 기준으로 limit 이하 청크 분할."""
    parts: list[str] = []
    cur = ""
    for line in text.split("\n"):
        # 한 줄이 limit보다 길면 강제로 잘라 넣는다
        while len(line) > limit:
            if cur:
                parts.append(cur)
                cur = ""
            parts.append(line[:limit])
            line = line[limit:]
        if len(cur) + len(line) + 1 > limit:
            parts.append(cur)
            cur = line
        else:
            cur = f"{cur}\n{line}" if cur else line
    if cur:
        parts.append(cur)
    return parts


def send(settings: Settings, text: str) -> int:
    """텔레그램 송신. 보낸 청크 수 반환. 미설정·실패 시 NotifyError."""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        raise NotifyError("TELEGRAM_BOT_TOKEN/CHAT_ID missing")
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    chunks = _split(text, settings.telegram_max_len)
    sent = 0
    for chunk in chunks:
        r = requests.post(
            url,
            data={
                "chat_id": settings.TELEGRAM_CHAT_ID,
                "text": chunk,
                "parse_mode": "HTML",
            },
            timeout=15,
        )
        if r.status_code != 200:
            raise NotifyError(
                f"telegram {r.status_code}: {r.text[:200]} (sent {sent}/{len(chunks)})"
            )
        sent += 1
    return sent
