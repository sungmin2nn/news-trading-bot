"""NTR results_{T}.json fetch·누적. error-visibility §6: 원시 예외→도메인 예외 변환.
외부 입력 신뢰 경계: 스키마 검증 통과분만 누적."""
import json
import sys
import time
from pathlib import Path

import requests

from src.contract.news_evo_schema import validate_results

HISTORY = Path(__file__).resolve().parents[2] / "data" / "ntr_results.jsonl"
_BASE = "https://raw.githubusercontent.com/sungmin2nn/news-trade-runner/main/data/news_evo"
_RETRY = frozenset({429, 500, 502, 503, 504})


class NtrResultsError(RuntimeError):
    pass


def fetch_and_store(date_ymd: str, *, base_url: str = _BASE, max_attempts: int = 3,
                    sleep=time.sleep) -> dict | None:
    """results_{date}.json 조회. 200+검증통과 → 누적·반환. 404 등 부재 → None(graceful).
    네트워크·검증 실패 → NtrResultsError(가시화)."""
    url = f"{base_url}/results_{date_ymd}.json"
    last = None
    for attempt in range(max_attempts):
        try:
            r = requests.get(url, timeout=10)
        except requests.RequestException as e:
            last = e
            if attempt < max_attempts - 1:
                sleep(2.0 * (2 ** attempt)); continue
            raise NtrResultsError(f"ntr results fetch 네트워크 실패: {e}") from e
        if r.status_code == 404:
            return None
        if r.status_code in _RETRY and attempt < max_attempts - 1:
            sleep(2.0 * (2 ** attempt)); continue
        if r.status_code != 200:
            raise NtrResultsError(f"ntr results HTTP {r.status_code}")
        try:
            data = r.json()
        except ValueError as e:
            raise NtrResultsError(f"ntr results JSON 파싱 실패: {e}") from e
        # 외부 입력 신뢰 경계: 검증 실패(ValueError)를 도메인 예외로 변환 (§6).
        try:
            validate_results(data)
        except ValueError as e:
            raise NtrResultsError(f"ntr results 스키마 검증 실패: {e}") from e
        _append(data)
        return data
    raise NtrResultsError(f"ntr results fetch 소진: {last}")


def _append(data: dict) -> None:
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def read_history(path: Path = None) -> list[dict]:
    p = path or HISTORY
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"[ntr_results] 손상 라인 skip: {e}", file=sys.stderr)
    return out
