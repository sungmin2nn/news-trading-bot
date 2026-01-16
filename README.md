# 📊 뉴스 기반 시초가 매매 시스템

뉴스/공시를 분석하여 장전 시간외 매수 종목을 자동 선정하고, A/B 테스트로 전략을 검증하는 시스템입니다.

---

## 🎯 개요

| 항목 | 내용 |
|------|------|
| 목표 | 호재 뉴스/공시 분석 → 매수 종목 자동 선정 |
| 방식 | A/B 테스트 (단순 vs 고도화 로직 비교) |
| 플랫폼 | GitHub Actions (무료) |
| 대시보드 | GitHub Pages |

---

## 📁 프로젝트 구조

```
news-trading-bot/
├── .github/workflows/
│   ├── morning-scan.yml      # 08:30 뉴스 분석
│   └── evening-track.yml     # 15:40 결과 추적
│
├── src/
│   ├── collectors/
│   │   ├── naver_collector.py    # 네이버 뉴스 수집
│   │   ├── dart_collector.py     # DART 공시 수집
│   │   └── price_collector.py    # 주가 데이터 수집
│   │
│   ├── analyzers/
│   │   ├── keyword_scorer.py     # 키워드 점수화
│   │   ├── stock_filter.py       # A/B 필터 로직
│   │   └── simulator.py          # 매도 시뮬레이션
│   │
│   ├── utils/
│   │   ├── data_manager.py       # 데이터 관리
│   │   └── date_utils.py         # 날짜 유틸
│   │
│   ├── morning_scan.py           # 아침 스캔 메인
│   └── evening_track.py          # 저녁 추적 메인
│
├── config/
│   ├── keywords.yaml             # 키워드 설정
│   └── settings.yaml             # 필터/매매 설정
│
├── data/
│   └── signals.json              # 누적 데이터
│
├── docs/
│   └── index.html                # 대시보드
│
└── requirements.txt
```

---

## ⏰ 실행 스케줄

| 시간 (KST) | 작업 | 내용 |
|------------|------|------|
| 08:30 | Morning Scan | 뉴스 수집 → 분석 → 종목 선정 |
| 15:40 | Evening Track | 주가 수집 → 시뮬레이션 → 결과 기록 |

---

## 🔬 A/B 로직 비교

| 조건 | A로직 (단순) | B로직 (고도화) |
|------|:-----------:|:-------------:|
| 키워드 점수 | ✅ | ✅ |
| 시총/거래량 필터 | ✅ | ✅ |
| 수주금액/시총 비율 | ❌ | ✅ |
| 최근 5일 급등 제외 | ❌ | ✅ |
| 외국인/기관 수급 | ❌ | ✅ |
| 52주 고점 제외 | ❌ | ✅ |

---

## ⚙️ 설정 방법

### 1. GitHub Pages 활성화
```
Settings → Pages → Branch: main, /docs → Save
```

### 2. DART API 키 등록 (선택)
```
Settings → Secrets → New secret
Name: DART_API_KEY
Value: (https://opendart.fss.or.kr 에서 발급)
```

### 3. 테스트 실행
```
Actions → Morning Scan → Run workflow
```

---

## 📈 대시보드

**주소**: `https://[USERNAME].github.io/news-trading-bot/`

- 누적 수익률 차트
- A/B 로직 성과 비교
- 키워드별/요일별 분석
- 최근 신호 목록

---

## 📊 매매 규칙

| 항목 | 기본값 |
|------|--------|
| 진입 | 전일 종가 (장전 시간외) |
| 익절 | +5% |
| 손절 | -3% |
| 트레일링 | 고점 대비 -2% |
| 강제청산 | 당일 종가 |

`config/settings.yaml`에서 수정 가능

---

## ⚠️ 주의사항

- **페이퍼 트레이딩** (시뮬레이션) 시스템입니다
- 실제 매매는 하지 않습니다
- 투자 결정은 본인 책임입니다

---

## 📝 라이선스

MIT License
