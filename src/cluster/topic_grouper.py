"""기사 중복제거 + 입력 상한.

정밀 주제 클러스터링은 Gemini가 담당한다. 여기서는 토큰 통제를 위해
근접 중복 제거 + 상위 N개 캡 + 제목 절단만 수행한다.
"""

from __future__ import annotations

import re

_STRIP = re.compile(r"[\[\]()<>·,.!?\"'‘’“”\-\s]+")


def _norm(title: str) -> str:
    return _STRIP.sub("", title).lower()


def dedup_and_cap(
    articles: list[dict], max_articles: int, max_title_len: int
) -> list[dict]:
    """근접 중복 제거 후 상위 max_articles개로 캡, 제목 절단."""
    seen: set[str] = set()
    out: list[dict] = []
    for a in articles:
        title = (a.get("title") or "").strip()
        if not title:
            continue
        key = _norm(title)[:40]
        if not key or key in seen:
            continue
        seen.add(key)
        item = dict(a)
        item["title"] = title[:max_title_len]
        out.append(item)
        if len(out) >= max_articles:
            break
    return out
