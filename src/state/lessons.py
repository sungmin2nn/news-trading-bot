"""lessons.json — 진화하는 규칙북(P4 calibration + P5 rules).

P4는 calibration만 채운다. rules[]는 P5(LLM 메타학습) 자산이라 보존만 한다.
load/save + calibration 병합. atomic write(임시파일 후 rename). 깨진 파일은 None.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pytz

KST = pytz.timezone("Asia/Seoul")
LESSONS = Path(__file__).resolve().parent.parent.parent / "data" / "lessons.json"
_MAX_CHANGELOG = 200


def _empty() -> dict:
    return {"calibration": None, "rules": [], "changelog": []}


def load(path: Path = LESSONS):
    """lessons.json 로드. 없음/깨짐 → None(브리핑 안 깸, stderr 경고)."""
    if not path.exists():
        return None
    try:
        with path.open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:  # noqa: BLE001
        print(f"[lessons] 로드 실패(무시): {e}", file=sys.stderr)
        return None


def update_calibration(cal: dict, path: Path = LESSONS) -> None:
    """calibration 교체 + rules 보존 + changelog append. atomic write."""
    data = load(path) or _empty()
    data["calibration"] = cal
    data.setdefault("rules", [])
    changelog = data.get("changelog") or []
    changelog.append({
        "ts": datetime.now(KST).isoformat(timespec="seconds"),
        "event": "calibration_updated",
        "note": f"N={cal.get('overall', {}).get('n')}",
    })
    data["changelog"] = changelog[-_MAX_CHANGELOG:]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
