"""Gemini '비서+팀' 종합 자문 — 요약 + 다관점 토론 + 액션을 1콜 JSON으로.

핵심: 단순 텍스트 요약기가 아니라, 투자팀의 비서이자 다관점 애널리스트 팀의
입장에서 각 이슈를 토론하고 실행 가능한 안(action)을 제시하게 한다.
다관점(낙관/비관/중립)은 단일 프롬프트 안에서 생성 — 멀티콜 없이 토큰 절약.
"""

from __future__ import annotations

import json

import requests

from src.config import Settings

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

_SCHEMA = (
    '{"briefing_type":"<pre|post>","topics":['
    '{"title":"주제명","summary":"2-3문장 핵심 요약",'
    '"debate":{"bull":"낙관 관점","bear":"비관 관점","neutral":"중립 관점"},'
    '"verdict":"팀 종합 판단 1-2문장","action":"<관심|관찰|회피|무시>",'
    '"confidence":0.0,"tickers":["관련 종목명"]}],'
    '"noise_filtered_count":0}'
)

_PROMPT = """너는 한국 주식 투자팀의 비서이자 다관점 애널리스트 팀이다.
아래는 방금 수집한 국내 증시 관련 뉴스 기사 목록이다.
너의 임무는 단순 요약이 아니라, 팀의 입장에서 판단하고 실행 가능한 안을 주는 것이다.

작업 지침:
1. 기사들을 '지금 화제가 되는 이슈 주제'별로 묶어라. 단순 시황·시세 중계·가십·중복 기사는 노이즈로 분류해 제외하고, 그 개수만 noise_filtered_count에 담아라.
2. 각 주제마다 다음을 작성하라:
   - summary: 무슨 일인지 핵심만.
   - debate: 낙관(bull)/비관(bear)/중립(neutral) 세 관점에서 팀원이 토론하듯 각각 한 줄.
   - verdict: 토론을 종합한 팀의 판단.
   - action: 반드시 [관심|관찰|회피|무시] 중 하나. 근거 없는 매수·단정 금지, 확신이 낮으면 '관찰'.
   - confidence: 0.0~1.0.
   - tickers: 명확히 관련된 종목명만(없으면 빈 배열).
3. 주제는 영향도·화제성 순으로 최대 {max_topics}개까지만.

출력은 아래 JSON 스키마 하나만. 설명·마크다운 없이 JSON만 출력하라. briefing_type은 "{btype}".
스키마: {schema}

뉴스 목록:
{articles}
"""


_VALID_ACTIONS = {"관심", "관찰", "회피", "무시"}


class GeminiError(RuntimeError):
    pass


def _build_prompt(articles: list[dict], max_topics: int, btype: str) -> str:
    lines = []
    for i, a in enumerate(articles, 1):
        stk = f" [{a['stock_name']}]" if a.get("stock_name") else ""
        extra = f" — {a['summary']}" if a.get("summary") else ""
        lines.append(f"{i}. {a.get('title', '')}{stk}{extra}")
    return _PROMPT.format(
        max_topics=max_topics,
        btype=btype,
        schema=_SCHEMA,
        articles="\n".join(lines),
    )


def _extract_json(text: str) -> dict:
    t = text.strip()
    if t.startswith("```"):
        # ```json ... ``` 펜스 제거
        t = t[3:]
        if t[:4].lower() == "json":
            t = t[4:]
        t = t.strip()
        if t.endswith("```"):
            t = t[:-3].strip()
    try:
        return json.loads(t)
    except Exception as e:  # noqa: BLE001
        raise GeminiError(f"JSON 파싱 실패: {e}; head={t[:200]!r}") from e


def advise(settings: Settings, articles: list[dict], btype: str) -> dict:
    """기사 목록 → 구조화된 종합 자문 dict. 실패 시 GeminiError(가시화)."""
    if not settings.GEMINI_API_KEY:
        raise GeminiError("GEMINI_API_KEY missing")
    prompt = _build_prompt(articles, settings.max_topics, btype)
    url = f"{API_BASE}/{settings.GEMINI_MODEL}:generateContent"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": settings.GEMINI_MAX_OUTPUT_TOKENS,
            "temperature": 0.4,
            "thinkingConfig": {"thinkingBudget": 0},
            "responseMimeType": "application/json",
        },
    }
    r = requests.post(
        url,
        params={"key": settings.GEMINI_API_KEY},
        headers={"Content-Type": "application/json"},
        data=json.dumps(body),
        timeout=45,
    )
    if r.status_code != 200:
        raise GeminiError(f"gemini {r.status_code}: {r.text[:300]}")
    data = r.json()
    candidates = data.get("candidates") or []
    if not candidates:
        raise GeminiError(f"empty candidates: {str(data)[:300]}")
    cand = candidates[0]
    finish = cand.get("finishReason")
    # MAX_TOKENS 등으로 잘리면 JSON이 깨진 채 와서 파싱이 cryptic하게 실패한다.
    # 미완료를 먼저 명시적 에러로 가시화한다.
    if finish and finish != "STOP":
        raise GeminiError(
            f"응답 미완료(finishReason={finish}) — maxOutputTokens 부족 또는 차단 가능. "
            f"max_topics/입력을 줄이거나 max_output_tokens를 올려라."
        )
    parts = cand.get("content", {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise GeminiError(f"empty text: {str(data)[:300]}")
    result = _extract_json(text)
    if "topics" not in result or not isinstance(result.get("topics"), list):
        raise GeminiError(f"스키마 위반(topics 없음): {str(result)[:200]}")
    # 프롬프트 인젝션·스키마 일탈 방어: action enum 강제, confidence clamp
    for t in result["topics"]:
        if t.get("action") not in _VALID_ACTIONS:
            t["action"] = "관찰"
        try:
            t["confidence"] = min(1.0, max(0.0, float(t.get("confidence", 0.0))))
        except (TypeError, ValueError):
            t["confidence"] = 0.0
    return result
