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
from src.state import prediction_ledger, sent_store
from src.utils import krx_calendar

KST = pytz.timezone("Asia/Seoul")
_WEEKDAY = ["월", "화", "수", "목", "금", "토", "일"]
_ACTION_EMOJI = {"관심": "🟢", "관찰": "🟡", "회피": "🔴", "무시": "⚪"}
_DIR_EMOJI = {"상승": "📈", "하락": "📉", "중립": "➡️", "혼조": "🔀"}
_EFFECT_MARK = {"수혜": "🔺", "타격": "🔻", "중립": "▪️"}


def _circled(i: int) -> str:
    return chr(0x2460 + i - 1) if 1 <= i <= 20 else f"{i}."


def _impacts_str(impacts: list) -> str:
    parts = []
    for im in impacts or []:
        if not isinstance(im, dict):
            continue
        name = im.get("name", "")
        if not name:
            continue
        parts.append(f"{name}{_EFFECT_MARK.get(im.get('effect', ''), '')}")
    return " ".join(parts)


def build_message(result: dict, mode: str) -> str:
    now = datetime.now(KST)
    # 라벨은 거래일이면 '장전/장후', 휴장일(주말·공휴일)이면 '아침/저녁'으로 — 매일 발송
    trading = krx_calendar.is_krx_business_day(now)
    if mode == "pre":
        label = "장전 이슈 브리핑" if trading else "아침 이슈 브리핑"
    else:
        label = "장후 이슈 브리핑" if trading else "저녁 이슈 브리핑"
    wd = _WEEKDAY[now.weekday()]
    topics = result.get("topics") or []

    lines = [f"📰 {label} · {now.month}/{now.day}({wd}) {now.strftime('%H:%M')}"]
    # 상단 한눈 스캔 — 주제 제목 + 방향 이모지
    if topics:
        digest = "  ".join(
            f"{_circled(i)}{t.get('title', '')}{_DIR_EMOJI.get(t.get('direction', ''), '')}"
            for i, t in enumerate(topics, 1)
        )
        lines.append(f"핵심 ▸ {digest}")
    lines.append("━━━━━━━━━━━━")

    if not topics:
        lines.append("\n추려낼 이슈가 없습니다.")

    for i, t in enumerate(topics, 1):
        emoji = _ACTION_EMOJI.get(t.get("action", ""), "•")
        direction = t.get("direction", "")
        dmark = _DIR_EMOJI.get(direction, "")
        tag = "NEW" if t.get("status") == "new" else "지속"
        conf = t.get("confidence")
        conf_s = f" · 확신{conf:.0%}" if isinstance(conf, (int, float)) else ""
        # 스캔 헤더: 액션 + 번호 + 제목 + 방향 + 액션 + 확신
        lines.append(
            f"\n{emoji} {_circled(i)} {t.get('title', '(제목없음)')}"
            f"  ·  {dmark}{direction} · {t.get('action', '-')}{conf_s} [{tag}]"
        )
        # 헤드라인(한 줄 gist)
        if t.get("headline"):
            lines.append(f"▸ {t['headline']}")
        # 세부
        if t.get("summary"):
            lines.append(f" ㆍ무슨일: {t['summary']}")
        if t.get("analysis"):
            priced = t.get("priced_in")
            tail = f" (반영:{priced})" if priced else ""
            lines.append(f" ㆍ분석: {t['analysis']}{tail}")
        # 결론: 영향 종목/테마 + 방향 근거
        impacts_s = _impacts_str(t.get("impacts"))
        reason = t.get("direction_reason", "")
        if impacts_s or reason:
            concl = " ㆍ결론: "
            concl += impacts_s
            if impacts_s and reason:
                concl += " — "
            concl += reason
            lines.append(concl)
        if t.get("risk"):
            lines.append(f" ㆍ리스크: {t['risk']}")

    noise = result.get("noise_filtered_count") or 0
    lines.append("\n━━━━━━━━━━━━")
    if noise:
        lines.append(f"⚪ 노이즈 {noise}건 제외")
    lines.append("🔺수혜 🔻타격 · 자동 자문, 판단·책임은 본인")
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
    # 뉴스/이슈는 매일 발생하므로 휴장일에도 발송한다(라벨만 거래일/휴장일로 분기).
    # --force는 하위호환용으로 받기만 한다.

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
    # 예측 원장 적재(P2) — 회고·학습 루프의 데이터 활주로
    recorded = prediction_ledger.record(topics, args.mode)
    print(
        f"sent={n} chunk(s) · topics={len(topics)} · articles={len(articles)} "
        f"· ledger+{recorded}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
