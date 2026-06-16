"""Gemini '비서+팀' 종합 자문 — 요약 + 다관점 토론 + 액션을 1콜 JSON으로.

핵심: 단순 텍스트 요약기가 아니라, 투자팀의 비서이자 다관점 애널리스트 팀의
입장에서 각 이슈를 토론하고 실행 가능한 안(action)을 제시하게 한다.
다관점(낙관/비관/중립)은 단일 프롬프트 안에서 생성 — 멀티콜 없이 토큰 절약.
"""

from __future__ import annotations

import json
import time

import requests

from src.config import Settings

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

_SCHEMA = (
    '{"briefing_type":"<pre|post>","topics":['
    '{"title":"주제명(짧게)",'
    '"headline":"한 줄 핵심(스캔용, 30자 내외, 무슨 일인지 한눈에)",'
    '"summary":"기사 핵심 내용(무슨 일이 일어났나) 2-3문장",'
    '"analysis":"왜 중요한지·배경·파급 효과를 짚는 분석 2-3문장",'
    '"priced_in":"<미반영|부분반영|이미반영>","priced_in_note":"반영 판단 근거 한 줄",'
    '"direction":"<상승|하락|중립|혼조>","direction_reason":"방향 예상 근거 1-2문장",'
    '"risk":"그 예상이 틀릴 수 있는 핵심 리스크 한 줄",'
    '"impacts":[{"name":"단일 상장 종목명(코드조회 가능) 또는 테마명","kind":"<종목|테마>","effect":"<수혜|타격|중립>","note":"이유 짧게"}],'
    '"action":"<관심|관찰|회피|무시>","confidence":0.0}],'
    '"noise_filtered_count":0}'
)

_PROMPT = """너는 한국 주식 투자팀의 비서이자 애널리스트다.
아래는 방금 수집한 국내 증시 관련 뉴스 기사 목록이다.
단순 요약이 아니라, 기사 내용 + 너의 시장 지식으로 각 이슈를 깊이 분석하고 명확한 결론을 내라.

작업 지침:
1. 기사들을 '지금 화제가 되는 이슈 주제'별로 묶어라. 단순 시황 중계·가십·중복은 노이즈로 제외하고 개수만 noise_filtered_count에.
2. 각 주제마다 다음을 충실히 작성하라:
   - title: 주제명 짧게. headline: 한 줄로 무슨 일인지 스캔되게(30자 내외).
   - summary: 기사의 핵심 내용. 무슨 일이 일어났는지 구체적으로.
   - analysis: 이 이슈가 왜 중요한지, 배경과 파급 효과. 표면 요약 말고 한 발 더 들어간 분석.
   - priced_in: 주가에 이미 반영됐는지 [미반영|부분반영|이미반영] + priced_in_note에 근거.
   - direction: 단기 주가 방향 예상 [상승|하락|중립|혼조]. 애매해도 반드시 하나 고르고 direction_reason에 근거.
   - risk: 그 방향 예상이 빗나갈 수 있는 핵심 리스크 한 줄.
   - impacts: 영향받는 대상. kind='종목'이면 name은 **코드 조회 가능한 단일 상장 종목명만**(예: 삼성전자, SK하이닉스). '반도체 대형주'·'소부장'·'소형주 및 비주도 섹터' 같은 묶음·서술은 개별 종목으로 쪼개거나 kind='테마'로. 괄호·복합명 금지. 각각 effect [수혜|타격|중립] + note. 명확한 것만(없으면 빈 배열).
   - action: [관심|관찰|회피|무시] 중 하나. 근거 없는 단정 금지, 확신 낮으면 관찰.
   - confidence: 0.0~1.0.
3. 주제는 영향도·화제성 순으로 최대 {max_topics}개.

출력은 아래 JSON 스키마 하나만. 설명·마크다운 없이 JSON만. briefing_type은 "{btype}".
스키마: {schema}

뉴스 목록:
{articles}
"""


_VALID_ACTIONS = {"관심", "관찰", "회피", "무시"}
_VALID_DIRECTIONS = {"상승", "하락", "중립", "혼조"}
_VALID_PRICED_IN = {"미반영", "부분반영", "이미반영"}
_VALID_EFFECTS = {"수혜", "타격", "중립"}
_VALID_KINDS = {"종목", "테마"}


class GeminiError(RuntimeError):
    pass


_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})


def _post_with_retry(
    url,
    *,
    params,
    headers,
    data,
    timeout,
    max_attempts=4,
    base_delay=2.0,
    sleep=time.sleep,
):
    """Gemini POST + 지수 백오프 재시도.

    무료 티어 Gemini는 수요 스파이크 때 429/503(UNAVAILABLE)·500을 흔히 던진다.
    재시도가 없으면 transient 한 방이 brief 전체를 죽여 그날 예측이 유실된다
    (2026-06-07~12 실패 클러스터). 일시 장애(429/5xx·네트워크 예외)에만 재시도하고,
    4xx(인증·요청 오류)는 결정적이라 그대로 반환해 호출부가 처리하게 둔다.
    재시도 소진 시 GeminiError로 가시화.
    """
    for attempt in range(max_attempts):
        try:
            r = requests.post(
                url, params=params, headers=headers, data=data, timeout=timeout
            )
        except requests.RequestException as e:
            last_desc = f"네트워크 오류: {e}"
        else:
            if r.status_code not in _RETRY_STATUS:
                return r
            last_desc = f"gemini {r.status_code}: {r.text[:200]}"
        if attempt == max_attempts - 1:
            raise GeminiError(f"{last_desc} (재시도 {max_attempts}회 소진)")
        sleep(base_delay * (2 ** attempt))
    raise GeminiError("unreachable")  # 루프가 항상 return/raise


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
    r = _post_with_retry(
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
    # 프롬프트 인젝션·스키마 일탈 방어: enum 강제, confidence clamp
    for t in result["topics"]:
        if t.get("action") not in _VALID_ACTIONS:
            t["action"] = "관찰"
        if t.get("direction") not in _VALID_DIRECTIONS:
            t["direction"] = "중립"
        if t.get("priced_in") not in _VALID_PRICED_IN:
            t["priced_in"] = "부분반영"
        impacts = t.get("impacts")
        if not isinstance(impacts, list):
            t["impacts"] = []
        else:
            for im in impacts:
                if not isinstance(im, dict):
                    continue
                if im.get("effect") not in _VALID_EFFECTS:
                    im["effect"] = "중립"
                if im.get("kind") not in _VALID_KINDS:
                    im["kind"] = "테마"  # 불명확하면 테마로(=P3 채점 제외, 안전)
        try:
            t["confidence"] = min(1.0, max(0.0, float(t.get("confidence", 0.0))))
        except (TypeError, ValueError):
            t["confidence"] = 0.0
    return result
