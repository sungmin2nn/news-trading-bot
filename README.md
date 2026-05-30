# 📰 주식 이슈 뉴스 브리핑 봇

한국 증시 관련 **지금 화제가 되는 뉴스**를 수집·주제화하고, **Gemini가 "비서 + 다관점 팀" 입장에서 종합 자문**(요약 + 낙관/비관/중립 토론 + 실행 제안)한 뒤 **텔레그램으로 하루 2회** 보내준다.

> Gemini는 텍스트 요약기가 아니라, 투자팀의 입장에서 판단하고 실행 가능한 안을 제시하는 역할.

## 🎯 개요

- **입력**: 네이버 금융 메인뉴스(코스피·코스닥 전반)
- **처리**: 중복제거·캡 → Gemini Flash 1콜(JSON) → 주제별 종합 자문
- **출력**: 텔레그램 메시지 (장전 08:00 / 장후 18:00 KST)
- **플랫폼**: GitHub Actions (무료) + Gemini Flash (무료 티어) + Telegram

## 📁 구조

```
news-trading-bot/
├── .github/workflows/
│   ├── brief-premarket.yml    # 08:00 KST 장전 브리핑
│   └── brief-postmarket.yml   # 18:00 KST 장후 브리핑
├── src/
│   ├── collectors/naver_news.py   # 네이버 메인뉴스 수집
│   ├── cluster/topic_grouper.py   # 중복제거 + 입력 캡
│   ├── gemini/advisor.py          # 비서+팀 종합 자문 (1콜 JSON)
│   ├── notify/telegram.py         # 4096자 분할 발송
│   ├── state/sent_store.py        # NEW/지속 판정
│   ├── config.py                  # env + settings.yaml
│   └── main_brief.py              # 파이프라인 엔트리
├── config/settings.yaml           # 주제·기사 캡 등 파라미터
└── data/sent_topics.json          # 발송 이력(자동 누적)
```

## ⚙️ 설정

### 1. 시크릿 등록 (GitHub Settings → Secrets and variables → Actions)

| 시크릿 | 발급처 |
|---|---|
| `GEMINI_API_KEY` | https://aistudio.google.com/apikey (무료) |
| `TELEGRAM_BOT_TOKEN` | 텔레그램 [@BotFather](https://t.me/BotFather) → `/newbot` |
| `TELEGRAM_CHAT_ID` | 봇과 대화 시작 후 `https://api.telegram.org/bot<TOKEN>/getUpdates`의 `chat.id` |

> 뉴스 브리핑 전용 **별도 봇** 권장(다른 알림과 섞이지 않게).

### 2. 로컬 실행 / 검증

```
pip install -r requirements.txt
cp .env.example .env   # 값 채우기 (선택)
python -m src.main_brief --mode post --dry-run   # 발송 없이 메시지 확인
```

`--dry-run`은 텔레그램 발송 없이 메시지를 콘솔에 출력한다. 시크릿 없이 수집·Gemini만 점검하려면 `GEMINI_API_KEY`만 env에 두면 된다.

### 3. 자동 실행

워크플로가 cron으로 자동 실행된다. 수동 테스트는 Actions 탭 → *Premarket/Postmarket Brief* → **Run workflow**.

## 🧩 동작 메모

- **다관점 토론**은 Gemini 단일 프롬프트 안에서 생성(멀티콜 없이 토큰 절약).
- **입력 캡**(주제 8·기사 40)으로 무료 티어 토큰 통제 — `config/settings.yaml`에서 조정.
- **NEW/지속** 태그는 발송 이력(`data/sent_topics.json`) 기준 — 장전/장후 중복 이슈 구분.
- **실패 가시화**: 수집·Gemini·텔레그램 실패는 조용히 넘기지 않고 stderr + 텔레그램 경보.

## ⚠️ 주의

- 자동 생성된 **참고용 자문**이며 투자 권유가 아니다. 투자 판단·책임은 본인.
- 구 버전(뉴스 기반 A~E 페이퍼 트레이딩)은 `legacy` 브랜치 / `archive/paper-ab-2026-05-30` 태그에 보존.

## 📝 라이선스

MIT License
