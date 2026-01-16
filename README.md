# 📊 뉴스 기반 시초가 매매 시스템

뉴스/공시를 분석하여 장전 시간외 매수 종목을 자동 선정하고, A/B 테스트로 전략을 검증하는 시스템입니다.

## 🎯 시스템 개요

- **목표**: 장 마감 후 발생한 호재 뉴스/공시 분석 → 다음 날 매수 종목 자동 선정
- **방식**: A/B 테스트로 단순 로직 vs 고도화 로직 비교 검증
- **플랫폼**: GitHub Actions (무료) + GitHub Pages (대시보드)

## 📁 프로젝트 구조

```
news-trading-bot/
├── .github/workflows/       # GitHub Actions
│   ├── morning-scan.yml     # 08:30 뉴스 분석
│   └── evening-track.yml    # 15:40 결과 추적
├── src/
│   ├── collectors/          # 데이터 수집
│   │   ├── naver_collector.py
│   │   ├── dart_collector.py
│   │   └── price_collector.py
│   ├── analyzers/           # 분석 로직
│   │   ├── keyword_scorer.py
│   │   ├── stock_filter.py
│   │   └── simulator.py
│   ├── utils/               # 유틸리티
│   ├── morning_scan.py      # 아침 스캔 메인
│   └── evening_track.py     # 저녁 추적 메인
├── config/
│   ├── keywords.yaml        # 키워드 설정
│   └── settings.yaml        # 필터/매매 설정
├── data/
│   └── signals.json         # 누적 데이터
└── docs/
    └── index.html           # 대시보드
```

## ⚙️ 설정 방법

### 1. DART API 키 발급 (선택)

1. https://opendart.fss.or.kr 접속
2. 회원가입 후 API 키 발급
3. GitHub 저장소 Settings → Secrets → `DART_API_KEY` 등록

### 2. GitHub Pages 활성화

1. Settings → Pages
2. Source: Deploy from a branch
3. Branch: main, /docs
4. Save

### 3. 수동 실행 테스트

1. Actions 탭 → Morning Scan → Run workflow

## 📊 A/B 로직 비교

| 구분 | A로직 (단순) | B로직 (고도화) |
|------|-------------|---------------|
| 키워드 | ✅ | ✅ |
| 시총/거래량 필터 | ✅ | ✅ |
| 수주금액/시총 비율 | ❌ | ✅ |
| 최근 급등 제외 | ❌ | ✅ |
| 외국인/기관 수급 | ❌ | ✅ |
| 52주 고점 제외 | ❌ | ✅ |

## 📈 대시보드

GitHub Pages 주소: `https://[USERNAME].github.io/news-trading-bot/`

- 누적 수익률 차트
- A/B 로직 성과 비교
- 키워드별/요일별 분석
- 최근 신호 목록

## ⚠️ 주의사항

- 이 시스템은 **페이퍼 트레이딩**(시뮬레이션)입니다.
- 실제 매매는 하지 않으며, 전략 검증 목적입니다.
- 투자 결정은 본인 책임입니다.

## 📝 라이선스

MIT License
