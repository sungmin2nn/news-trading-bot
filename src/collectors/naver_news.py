"""네이버 금융 메인뉴스 수집 — 한국 주식 전반의 '지금 화제' 뉴스.

구 NaverCollector(종목별·검색)를 폐기하고 메인뉴스 N페이지만 수집한다.
실패를 조용히 삼키지 않는다(silent error 금지): 한 건도 못 모으면 CollectError.
"""

from __future__ import annotations

import time

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://finance.naver.com"
NEWS_URL = "https://finance.naver.com/news/mainnews.naver"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}


class CollectError(RuntimeError):
    pass


def _parse_page(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    out: list[dict] = []
    # 네이버 금융 메인뉴스: div.mainNewsList > li (구조 변경 대비 폴백 셀렉터)
    items = soup.select("div.mainNewsList li") or soup.select(".mainNewsList li")
    for it in items:
        # li 안에 a가 둘(썸네일 + 제목) — 제목 링크는 dd.articleSubject 안
        link_el = it.select_one("dd.articleSubject a") or it.select_one(".articleSubject a")
        if not link_el:
            continue
        title = link_el.get_text(strip=True)
        if not title:
            continue
        href = link_el.get("href", "") or ""
        if href and not href.startswith("http"):
            href = BASE_URL + href
        summ_el = it.select_one("dd.articleSummary") or it.select_one(".articleSummary")
        date_el = it.select_one("span.wdate") or it.select_one(".wdate")
        stock_el = it.select_one("span.stock")
        out.append(
            {
                "title": title,
                "url": href,
                "date": date_el.get_text(strip=True) if date_el else "",
                "summary": (summ_el.get_text(strip=True)[:200] if summ_el else ""),
                "stock_name": stock_el.get_text(strip=True) if stock_el else "",
                "source": "naver_main",
            }
        )
    return out


def fetch_main_news(pages: int = 3, delay: float = 0.5) -> list[dict]:
    """네이버 금융 메인뉴스 1..pages 페이지 수집.

    Returns: 기사 dict 리스트.
    Raises: CollectError — 전 페이지 실패 또는 수집 0건(가시화).
    """
    session = requests.Session()
    session.headers.update(HEADERS)
    out: list[dict] = []
    errors: list[str] = []
    for page in range(1, max(1, pages) + 1):
        try:
            r = session.get(f"{NEWS_URL}?page={page}", timeout=10)
            r.raise_for_status()
            out.extend(_parse_page(r.text))
            time.sleep(delay)
        except Exception as e:  # noqa: BLE001 — 페이지 단위 격리, 전체 실패만 raise
            errors.append(f"page{page}: {e}")
    if not out:
        raise CollectError(f"네이버 메인뉴스 수집 0건 — errors={errors}")
    return out
