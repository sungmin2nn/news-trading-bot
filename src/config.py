"""환경설정 — env(시크릿) + config/settings.yaml(파라미터)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH = ROOT / "config" / "settings.yaml"


@dataclass
class Settings:
    # 시크릿 (env / GitHub Secrets)
    GEMINI_API_KEY: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    # 파라미터 (settings.yaml)
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_MAX_OUTPUT_TOKENS: int = 8192
    naver_main_pages: int = 3
    max_articles: int = 40
    max_topics: int = 8
    max_article_title_len: int = 120
    telegram_max_len: int = 3800


def _load_dotenv(path: Path) -> None:
    """의존성 없는 최소 .env 로더. 이미 설정된 env는 덮지 않는다(setdefault)."""
    if not path.exists():
        return
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except Exception:  # noqa: BLE001 — .env 파싱 실패는 무시(env/Secrets가 진실)
        pass


def load_settings() -> Settings:
    _load_dotenv(ROOT / ".env")
    s = Settings()
    if SETTINGS_PATH.exists():
        data = yaml.safe_load(SETTINGS_PATH.read_text(encoding="utf-8")) or {}
        src = data.get("sources", {}) or {}
        caps = data.get("caps", {}) or {}
        gem = data.get("gemini", {}) or {}
        tg = data.get("telegram", {}) or {}
        s.naver_main_pages = int(src.get("naver_main_pages", s.naver_main_pages))
        s.max_articles = int(caps.get("max_articles", s.max_articles))
        s.max_topics = int(caps.get("max_topics", s.max_topics))
        s.max_article_title_len = int(
            caps.get("max_article_title_len", s.max_article_title_len)
        )
        s.GEMINI_MODEL = str(gem.get("model", s.GEMINI_MODEL))
        s.GEMINI_MAX_OUTPUT_TOKENS = int(
            gem.get("max_output_tokens", s.GEMINI_MAX_OUTPUT_TOKENS)
        )
        s.telegram_max_len = int(tg.get("max_message_len", s.telegram_max_len))
    # 시크릿은 env가 진실 (yaml에 두지 않는다)
    s.GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
    s.TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    s.TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
    s.GEMINI_MODEL = os.environ.get("GEMINI_MODEL", s.GEMINI_MODEL)
    return s
