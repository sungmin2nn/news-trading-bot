"""KRX 영업일 캘린더 (news-trade-runner engine/krx_calendar.py 이식, 로직 변경 0).

데이터 소스: hyunbinseo/holidays-kr 원격 JSON (정부 출처 자동 반영, 임시공휴일 포함)
캐시: data/holidays_cache/<year>.json (1일 디스크 + 메모리)
폴백: 네트워크 실패 시 하드코딩 (2025·2026·2027)
KRX 영업 공휴일(제헌절·선거)은 키워드로 제외.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

# 캐시: __file__(src/utils/krx_calendar.py) → parent×3 = repo root, + data/holidays_cache
_HOLIDAYS_CACHE_DIR = Path(__file__).parent.parent.parent / "data" / "holidays_cache"
_HOLIDAYS_MEMORY_CACHE: dict = {}
_HOLIDAYS_REMOTE_URL = "https://raw.githubusercontent.com/hyunbinseo/holidays-kr/main/public/{year}.json"
# '선거' 제거: 전국단위 선거일(대선·총선·전국동시지방선거)은 공휴일이라 KRX 휴장.
# holidays-kr는 공휴일만 싣는 데이터셋이라 거기 뜨는 선거일=휴장. (NTR 이식 시 '선거' 포함됐던 버그)
_KRX_OPEN_HOLIDAY_KEYWORDS = ("제헌절",)


def _is_krx_open_holiday(names):
    return any(any(kw in n for kw in _KRX_OPEN_HOLIDAY_KEYWORDS) for n in names)


def _parse_holidays_json(data, year):
    return {
        k[5:]
        for k, names in data.items()
        if k.startswith(f"{year}-") and not _is_krx_open_holiday(names)
    }


def _load_remote_holidays(year):
    try:
        _HOLIDAYS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = _HOLIDAYS_CACHE_DIR / f"{year}.json"
        if cache_file.exists():
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            if datetime.now() - mtime < timedelta(days=1):
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                return _parse_holidays_json(data, year)
        url = _HOLIDAYS_REMOTE_URL.format(year=year)
        with urllib.request.urlopen(url, timeout=5) as r:
            raw = r.read().decode("utf-8")
        data = json.loads(raw)
        cache_file.write_text(raw, encoding="utf-8")
        return _parse_holidays_json(data, year)
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        json.JSONDecodeError,
        OSError,
        TimeoutError,
        ValueError,
    ):
        try:
            cache_file = _HOLIDAYS_CACHE_DIR / f"{year}.json"
            if cache_file.exists():
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                return _parse_holidays_json(data, year)
        except Exception:
            pass
        return None


def _get_holidays(year):
    if year in _HOLIDAYS_MEMORY_CACHE:
        return _HOLIDAYS_MEMORY_CACHE[year]
    remote = _load_remote_holidays(year)
    if remote is not None:
        _HOLIDAYS_MEMORY_CACHE[year] = remote
        return remote
    # 폴백 (오프라인/장애 시) — 매년 수동 갱신
    fixed = {
        "01-01", "03-01", "05-01", "05-05", "06-06",
        "08-15", "10-03", "10-09", "12-25",
    }
    variable = {
        2025: {"01-28", "01-29", "01-30", "05-05", "05-06",
               "09-05", "09-06", "09-07", "09-08"},
        2026: {"02-16", "02-17", "02-18", "03-02", "05-24", "05-25",
               "08-17", "09-24", "09-25", "09-26", "10-05"},
        2027: {"02-05", "02-06", "02-07", "05-13", "09-14", "09-15", "09-16"},
    }
    holidays = set(fixed)
    if year in variable:
        holidays.update(variable[year])
    _HOLIDAYS_MEMORY_CACHE[year] = holidays
    return holidays


def is_krx_business_day(dt: datetime) -> bool:
    """KRX 영업일이면 True. 주말 + 공휴일 모두 휴장."""
    if dt.weekday() >= 5:
        return False
    return dt.strftime("%m-%d") not in _get_holidays(dt.year)
