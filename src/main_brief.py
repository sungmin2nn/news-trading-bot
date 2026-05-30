"""엔트리포인트 — 수집 → 주제화 → Gemini 종합 자문 → 텔레그램 발송.

실행:
    python -m src.main_brief --mode pre     # 장전 브리핑
    python -m src.main_brief --mode post    # 장후 브리핑
    python -m src.main_brief --mode post --dry-run   # 발송 없이 메시지 출력

단계 실패는 조용히 삼키지 않는다(error-visibility): stderr + 가능하면 텔레그램 경보.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime

import pytz

from src.cluster import topic_grouper
from src.collectors import naver_news
from src.config import load_settings
from src.gemini import advisor
from src.notify import telegram
from src.state import sent_store
from src.utils import krx_calendar

KST = pytz.timezone("Asia/Seoul")
_WEEKDAY = ["월", "화", "수", "목", "금", "토", "일"]
_ACTION_EMOJI = {"관심": "🟢", "관찰": "🟡", "회피": "🔴", "무시": "⚪"}


def build_message(result: dict, mode: str) -> str:
    now = datetime.now(KST)
    label = "장전 이슈 브리핑" if mode == "pre" else "장후 이슈 브리핑"
    wd = _WEEKDAY[now.weekday()]
    lines = [
        f"📰 {label} · {now.month}/{now.day}({wd}) {now.strftime('%H:%M')}",
        "━━━━━━━━━━━━━━",
    ]
    topics = result.get("topics") or []
    if not topics:
        lines.append("추려낼 이슈가 없습니다.")
    for i, t in enumerate(topics, 1):
        emoji = _ACTION_EMOJI.get(t.get("action", ""), "•")
        tag = " (NEW)" if t.get("status") == "new" else " (지속)"
        lines.append(f"\n{emoji} {i}. {t.get('title', '(제목없음)')}{tag}")
        if t.get("summary"):
            lines.append(f"  📄 {t['summary']}")
        deb = t.get("debate") or {}
        if any(deb.get(k) for k in ("bull", "bear", "neutral")):
            lines.append("  💬 팀 토론")
            if deb.get("bull"):
                lines.append(f"   · 낙관: {deb['bull']}")
            if deb.get("bear"):
                lines.append(f"   · 비관: {deb['bear']}")
            if deb.get("neutral"):
                lines.append(f"   · 중립: {deb['neutral']}")
        if t.get("verdict"):
            lines.append(f"  🧭 종합: {t['verdict']}")
        act = f"  ✅ 제안: {t.get('action', '-')}"
        tickers = ", ".join(t.get("tickers") or [])
        if tickers:
            act += f" ({tickers})"
        conf = t.get("confidence")
        if isinstance(conf, (int, float)):
            act += f" · 확신 {conf:.0%}"
        lines.append(act)
    noise = result.get("noise_filtered_count") or 0
    if noise:
        lines.append(f"\n⚪ 노이즈로 거른 것: {noise}건")
    lines.append("\n※ 자동 생성 자문 — 투자 판단·책임은 본인.")
    return "\n".join(lines)


def _alert(settings, msg: str, dry_run: bool) -> None:
    """오류를 stderr + (가능하면) 텔레그램으로 가시화."""
    print(msg, file=sys.stderr)
    if dry_run:
        return
    try:
        telegram.send(settings, f"⚠️ 뉴스 브리핑 오류\n{msg}")
    except Exception as e:  # noqa: BLE001
        print(f"[오류 알림도 실패] {e}", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description="주식 이슈 뉴스 브리핑")
    ap.add_argument("--mode", choices=["pre", "post"], default="post")
    ap.add_argument("--dry-run", action="store_true", help="발송 없이 메시지만 출력")
    ap.add_argument("--force", action="store_true", help="휴장일에도 실행")
    args = ap.parse_args()

    settings = load_settings()
    btype = "pre" if args.mode == "pre" else "post"

    # 휴장일(주말·공휴일)엔 '장전/장후' 라벨이 거짓이 되므로 생략 (--force/--dry-run 예외)
    now = datetime.now(KST)
    if not args.dry_run and not args.force and not krx_calendar.is_krx_business_day(now):
        print(f"[skip] 휴장일({now.date()}) — 브리핑 생략")
        return 0

    # 1) 수집
    try:
        articles = naver_news.fetch_main_news(pages=settings.naver_main_pages)
    except Exception as e:  # noqa: BLE001
        _alert(settings, f"[수집 실패] {e}", args.dry_run)
        return 1

    # 2) 주제화(입력 정리·캡)
    articles = topic_grouper.dedup_and_cap(
        articles, settings.max_articles, settings.max_article_title_len
    )
    if not articles:
        _alert(settings, "[수집 0건] dedup 후 기사 없음", args.dry_run)
        return 1

    # 3) Gemini 종합 자문
    try:
        result = advisor.advise(settings, articles, btype)
    except Exception as e:  # noqa: BLE001
        _alert(settings, f"[Gemini 실패] {e}", args.dry_run)
        return 1

    # NEW/지속 태깅 (판정만 — 영속은 발송 성공 후)
    topics = sent_store.mark_status(result.get("topics") or [])
    result["topics"] = topics

    # 4) 메시지 조립 + 발송
    message = build_message(result, args.mode)
    if args.dry_run:
        print(message)
        return 0
    try:
        n = telegram.send(settings, message)
    except Exception as e:  # noqa: BLE001
        _alert(settings, f"[텔레그램 발송 실패] {e}", args.dry_run)
        return 1

    # 발송 성공 후에만 상태 영속 — 미발송 이슈가 다음 회차 '지속'으로 둔갑하지 않게
    sent_store.persist(topics)
    print(f"sent={n} chunk(s) · topics={len(topics)} · articles={len(articles)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
