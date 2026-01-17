# 뉴스 트레이딩 봇 - 프로젝트 가이드

> 이 문서는 프로젝트에 처음 참여하는 개발자가 전체 시스템을 이해하고 바로 작업할 수 있도록 작성되었습니다.

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [시스템 아키텍처](#2-시스템-아키텍처)
3. [디렉토리 구조](#3-디렉토리-구조)
4. [모듈 상세 설명](#4-모듈-상세-설명)
5. [설정 파일](#5-설정-파일)
6. [데이터 흐름](#6-데이터-흐름)
7. [환경 설정 및 실행](#7-환경-설정-및-실행)
8. [GitHub Actions 자동화](#8-github-actions-자동화)
9. [대시보드](#9-대시보드)
10. [개발 가이드](#10-개발-가이드)
11. [트러블슈팅](#11-트러블슈팅)

---

## 1. 프로젝트 개요

### 1.1 목적
장 마감 후 발표되는 **뉴스/공시**를 분석하여 다음 날 **시초가 매수** 종목을 자동 선정하는 시스템입니다.

### 1.2 핵심 기능
- **뉴스 수집**: DART 공시 + 네이버 금융 뉴스
- **키워드 분석**: 호재/악재 키워드 기반 점수 계산
- **A/B 전략 테스트**: 단순 로직 vs 고급 로직 비교
- **수익률 추적**: 일별 성과 기록 및 대시보드 시각화

### 1.3 운영 방식
| 시간 | 작업 | 스크립트 |
|------|------|----------|
| 08:30 | 아침 스캔 - 종목 선정 | `morning_scan.py` |
| 09:00 | 장 시작 - 시초가 매수 (수동) | - |
| 15:30 | 장 마감 | - |
| 15:40 | 저녁 추적 - 수익률 계산 | `evening_track.py` |

### 1.4 중요 면책사항
- **모의투자 전용**: 실제 매매 기능 없음
- **전략 검증 목적**: 백테스트 및 A/B 테스트용
- **투자 책임**: 모든 투자 결정은 사용자 본인 책임

---

## 2. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                        데이터 소스                               │
├──────────────────┬──────────────────┬──────────────────────────┤
│   DART API       │   네이버 금융     │   KRX (pykrx)           │
│   (공시 정보)     │   (뉴스 스크래핑)  │   (주가/시총/거래량)     │
└────────┬─────────┴────────┬─────────┴────────────┬─────────────┘
         │                  │                      │
         ▼                  ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                     수집 계층 (Collectors)                       │
├──────────────────┬──────────────────┬──────────────────────────┤
│ DartCollector    │ NaverCollector   │ PriceCollector           │
└────────┬─────────┴────────┬─────────┴────────────┬─────────────┘
         │                  │                      │
         └──────────────────┼──────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                     분석 계층 (Analyzers)                        │
├──────────────────┬──────────────────┬──────────────────────────┤
│ KeywordScorer    │ StockFilter      │ Simulator                │
│ (점수 계산)       │ (A/B 필터링)      │ (수익률 추적)            │
└────────┬─────────┴────────┬─────────┴────────────┬─────────────┘
         │                  │                      │
         ▼                  ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                     실행 계층 (Main Scripts)                     │
├─────────────────────────────┬───────────────────────────────────┤
│ morning_scan.py (08:30)     │ evening_track.py (15:40)          │
└─────────────────────────────┴───────────────────────────────────┘
         │                                        │
         ▼                                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                     저장소 (Storage)                             │
├─────────────────────────────┬───────────────────────────────────┤
│ data/signals.json           │ docs/dashboard_data.json          │
│ data/signals_YYYYMMDD.json  │ docs/index.html                   │
└─────────────────────────────┴───────────────────────────────────┘
```

---

## 3. 디렉토리 구조

```
news-trading-bot/
│
├── .github/
│   └── workflows/
│       ├── morning-scan.yml        # 아침 스캔 자동화 (08:30 KST)
│       └── evening-track.yml       # 저녁 추적 자동화 (15:40 KST)
│
├── config/
│   ├── keywords.yaml               # 키워드 점수 설정
│   └── settings.yaml               # 필터 및 시스템 설정
│
├── data/                           # [자동생성] 데이터 저장소
│   ├── signals.json                # 전체 시그널 히스토리
│   ├── signals_YYYYMMDD.json       # 일별 시그널
│   └── results.json                # 분석 결과
│
├── docs/                           # GitHub Pages 대시보드
│   ├── index.html                  # 대시보드 UI
│   └── dashboard_data.json         # [자동생성] 대시보드 데이터
│
├── src/
│   ├── __init__.py
│   │
│   ├── collectors/                 # 데이터 수집 모듈
│   │   ├── __init__.py
│   │   ├── dart_collector.py       # DART 공시 수집
│   │   ├── naver_collector.py      # 네이버 뉴스 수집
│   │   └── price_collector.py      # 주가/시총/거래량 수집
│   │
│   ├── analyzers/                  # 분석 모듈
│   │   ├── __init__.py
│   │   ├── keyword_scorer.py       # 키워드 점수 계산
│   │   ├── stock_filter.py         # A/B 전략 필터링
│   │   └── simulator.py            # 수익률 시뮬레이션
│   │
│   ├── utils/                      # 유틸리티 (확장용)
│   │   └── __init__.py
│   │
│   ├── morning_scan.py             # 아침 스캔 메인 스크립트
│   └── evening_track.py            # 저녁 추적 메인 스크립트
│
├── .gitignore
├── requirements.txt                # Python 의존성
├── README.md                       # 프로젝트 소개
└── PROJECT_STRUCTURE.md            # 이 문서
```

---

## 4. 모듈 상세 설명

### 4.1 수집 모듈 (src/collectors/)

#### dart_collector.py - DART 공시 수집

```python
from src.collectors import DartCollector

# 초기화 (API 키 필요)
dart = DartCollector(api_key="your_dart_api_key")
# 또는 환경변수 DART_API_KEY 자동 사용

# 주요 메서드
disclosures = dart.get_disclosures(start_date, end_date)  # 공시 목록 조회
overnight = dart.get_overnight_disclosures()               # 장 마감 후 공시
important = dart.filter_important_disclosures(disclosures) # 중요 공시 필터
signals = dart.to_signal_format(disclosures)               # 시그널 포맷 변환
```

**반환 데이터 형식:**
```python
{
    'source': 'dart',
    'corp_name': '삼성전자',
    'corp_code': '00126380',
    'stock_code': '005930',
    'title': '단일판매ㆍ공급계약체결',
    'date': '20240115',
    'rcept_no': '20240115000123',
    'url': 'https://dart.fss.or.kr/...'
}
```

#### naver_collector.py - 네이버 뉴스 수집

```python
from src.collectors import NaverCollector

naver = NaverCollector(delay=0.5)  # 요청 간 딜레이

# 주요 메서드
main_news = naver.get_main_news(page=1)           # 메인 뉴스
stock_news = naver.get_stock_news('005930')       # 종목별 뉴스
search_news = naver.search_news('수주')           # 키워드 검색
overnight = naver.get_overnight_news()            # 장 마감 후 뉴스
all_news = naver.collect_all_sources(codes, keywords)  # 통합 수집
```

**반환 데이터 형식:**
```python
{
    'source': 'naver_main',
    'title': '삼성전자, 대규모 수주 계약 체결',
    'url': 'https://finance.naver.com/...',
    'date': '2024.01.15 09:30',
    'stock_name': '삼성전자',
    'description': '...'
}
```

#### price_collector.py - 주가 데이터 수집

```python
from src.collectors import PriceCollector

price = PriceCollector()

# 주요 메서드
stock_list = price.get_stock_list('KOSPI')                    # 종목 목록
df = price.get_price('005930', start_date, end_date)          # OHLCV 데이터
market_cap = price.get_market_cap('005930')                   # 시가총액
avg_volume = price.get_trading_volume('005930', days=20)      # 평균 거래량
change = price.get_price_change('005930', days=5)             # 수익률 (%)
high_52w = price.get_52week_high('005930')                    # 52주 최고가
foreign = price.get_foreign_holding('005930')                 # 외국인 보유비율
info = price.get_stock_info('005930')                         # 종합 정보
```

**get_stock_info 반환 형식:**
```python
{
    'stock_code': '005930',
    'market_cap': 500000000000000,      # 시가총액
    'avg_volume': 15000000,             # 평균 거래량
    'price_change_5d': 3.5,             # 5일 수익률 (%)
    'price_change_20d': 8.2,            # 20일 수익률 (%)
    'high_52week': 85000,               # 52주 최고가
    'high_52week_ratio': 92.5,          # 52주 고가 대비 비율 (%)
    'foreign_ratio': 55.3               # 외국인 보유비율 (%)
}
```

---

### 4.2 분석 모듈 (src/analyzers/)

#### keyword_scorer.py - 키워드 점수 계산

```python
from src.analyzers import KeywordScorer

scorer = KeywordScorer(config_path='config/keywords.yaml')

# 단일 텍스트 점수 계산
result = scorer.calculate_score("삼성전자 대규모 수주 계약 체결")
# result = {
#     'total_score': 3,
#     'strong_positive_count': 1,
#     'medium_positive_count': 0,
#     'negative_count': 0,
#     'matched_keywords': ['+3: 수주'],
#     'is_excluded': False
# }

# 시그널 목록 점수 계산
scored_signals = scorer.score_signals(signals)

# 양호 시그널만 필터링
positive = scorer.filter_positive_signals(scored_signals, min_score=1)

# 점수순 정렬
ranked = scorer.rank_signals(scored_signals, top_n=10)

# 요약 통계
summary = scorer.get_summary(scored_signals)
```

**점수 체계:**
| 구분 | 점수 | 예시 키워드 |
|------|------|-------------|
| 강한 호재 | +3 | 흑자전환, 수주, FDA승인, 자사주매입 |
| 중간 호재 | +1 | 목표가상향, 신제품출시, 특허취득 |
| 악재 | -10 | 유상증자, CB발행, 횡령, 관리종목 |

**악재 키워드가 포함되면 `is_excluded=True`로 표시되어 매수 대상에서 제외됩니다.**

#### stock_filter.py - A/B 전략 필터링

```python
from src.analyzers import StockFilter

stock_filter = StockFilter(settings_path='config/settings.yaml')

# 공통 필터 적용 (A, B 모두)
filtered = stock_filter.apply_common_filters(scored_signals)

# 전략 A (단순 로직)
strategy_a = stock_filter.apply_strategy_a(scored_signals)

# 전략 B (고급 로직)
strategy_b = stock_filter.apply_strategy_b(scored_signals)

# A/B 동시 적용
results = stock_filter.apply_both_strategies(scored_signals)
# results = {'strategy_a': [...], 'strategy_b': [...]}

# 전략 비교
comparison = stock_filter.compare_strategies(strategy_a, strategy_b)
```

**A/B 전략 차이:**

| 필터 조건 | 전략 A (단순) | 전략 B (고급) |
|-----------|:-------------:|:-------------:|
| 키워드 점수 ≥ 1 | ✅ | ✅ |
| 시가총액 500억~10조 | ✅ | ✅ |
| 평균 거래량 ≥ 10만주 | ✅ | ✅ |
| 5일 급등주 제외 (15%) | ❌ | ✅ |
| 52주 신고가 근접 제외 (90%) | ❌ | ✅ |
| 외국인 보유비율 ≥ 1% | ❌ | ✅ |

#### simulator.py - 수익률 시뮬레이션

```python
from src.analyzers import Simulator

simulator = Simulator(data_path='data/signals.json')

# 시그널 기록
simulator.record_signals(signals, strategy='A', date='20240115')

# 수익률 추적 (전일 시그널)
simulator.track_signals(date='20240114')

# 개별 종목 수익률 계산
result = simulator.calculate_return(
    stock_code='005930',
    buy_date='20240115',
    sell_date='20240115'  # 당일 종가 매도
)
# result = {
#     'stock_code': '005930',
#     'buy_price': 75000,   # 시가 매수
#     'sell_price': 76500,  # 종가 매도
#     'returns': 2.0        # 수익률 (%)
# }

# 성과 요약
summary = simulator.get_performance_summary(strategy='A')
# summary = {
#     'total_days': 30,
#     'total_trades': 150,
#     'avg_return': 1.5,
#     'win_rate': 58.0,
#     'total_return': 45.0,
#     'best_return': 15.0,
#     'worst_return': -8.0
# }

# A/B 전략 비교
comparison = simulator.compare_strategies()

# 누적 수익률
cumulative = simulator.get_cumulative_returns()

# 결과 내보내기
simulator.export_results('data/results.json')
```

---

### 4.3 메인 스크립트 (src/)

#### morning_scan.py - 아침 스캔

**실행 시점:** 매일 08:30 KST (장 시작 전)

**실행 순서:**
1. DART 공시 수집 (장 마감 후 ~ 현재)
2. 네이버 뉴스 수집
3. 키워드 점수 계산
4. A/B 전략 필터링
5. 결과 저장 (`data/signals_YYYYMMDD.json`)

**실행 방법:**
```bash
export DART_API_KEY="your_api_key"
python src/morning_scan.py
```

**출력 예시:**
```
============================================================
뉴스 트레이딩 봇 - 아침 스캔
실행 시간: 2024-01-15 08:30:00
============================================================

[1/5] DART 공시 수집 중...
  - 수집된 공시: 45건
  - 중요 공시: 12건

[2/5] 네이버 뉴스 수집 중...
  - 수집된 뉴스: 78건

총 수집된 시그널: 90건

[3/5] 키워드 점수 계산 중...
  - 호재 시그널: 15건
  - 악재 시그널 (제외): 8건
  - 평균 점수: 1.85

[4/5] A/B 전략 필터링 중...

  [전략 A - 단순 로직]
  선정 종목: 10개
    1. 삼성전자 (점수: 6)
    2. SK하이닉스 (점수: 4)
    ...

  [전략 B - 고급 로직]
  선정 종목: 7개
    1. 삼성전자 (점수: 6)
    ...

[5/5] 결과 저장 중...
  - 저장 완료: data/signals_20240115.json

============================================================
아침 스캔 완료!
============================================================
```

#### evening_track.py - 저녁 추적

**실행 시점:** 매일 15:40 KST (장 마감 후)

**실행 순서:**
1. 당일 시그널 수익률 추적
2. 성과 분석 (A/B 비교)
3. 결과 저장 (`data/results.json`)
4. 대시보드 업데이트 (`docs/dashboard_data.json`)

**실행 방법:**
```bash
python src/evening_track.py
```

---

## 5. 설정 파일

### 5.1 config/keywords.yaml

키워드 점수 설정 파일입니다. 필요에 따라 키워드를 추가/수정할 수 있습니다.

```yaml
# 강한 호재 (+3점)
strong_positive:
  - 흑자전환
  - 사상최대
  - 수주
  - 계약 체결
  - 공급계약
  - 납품계약
  - FDA 승인
  - 식약처 승인
  - 임상 성공
  - 임상 통과
  - 자사주 매입
  - 자사주 취득
  - 기술수출
  - 라이선스 계약
  - 대규모 투자

# 중간 호재 (+1점)
medium_positive:
  - 목표가 상향
  - 투자의견 상향
  - 신제품 출시
  - 특허 취득
  - 투자 유치
  - 해외 진출
  - MOU 체결
  - 협력 계약

# 악재 (-10점) - 매수 제외
negative:
  - 유상증자
  - CB 발행
  - BW 발행
  - 전환사채
  - 신주인수권부사채
  - 최대주주 매각
  - 지분 매각
  - 횡령
  - 배임
  - 소송 패소
  - 행정처분
  - 감사의견 거절
  - 관리종목
  - 투자경고
```

### 5.2 config/settings.yaml

시스템 설정 파일입니다.

```yaml
# ===================
# 공통 필터 (A, B 전략 모두 적용)
# ===================

# 시가총액 필터 (원)
min_market_cap: 50000000000      # 최소: 500억
max_market_cap: 10000000000000   # 최대: 10조

# 거래량 필터
min_avg_volume: 100000           # 최소 평균 거래량: 10만주

# 키워드 점수 필터
min_score: 1                     # 최소 점수 (1점 이상)


# ===================
# B 전략 전용 필터 (고급 로직)
# ===================

# 급등주 제외
max_price_change_5d: 15.0        # 5일 수익률 상한: 15%

# 52주 고가 필터
max_52week_high_ratio: 90.0      # 52주 고가 대비 비율 상한: 90%

# 수급 필터
min_foreign_ratio: 1.0           # 최소 외국인 보유 비율: 1%


# ===================
# 결과 제한
# ===================

max_stocks: 10                   # 최대 선정 종목 수


# ===================
# 데이터 수집 설정
# ===================

news_max_pages: 10               # 네이버 뉴스 최대 페이지
news_delay: 0.5                  # 요청 간 딜레이 (초)
price_lookback_days: 30          # 주가 조회 기간 (일)


# ===================
# 실행 시간 (KST)
# ===================

morning_scan_time: "08:30"
evening_track_time: "15:40"
```

---

## 6. 데이터 흐름

### 6.1 전체 흐름도

```
┌─────────────────────────────────────────────────────────────────┐
│                      장 마감 (15:30)                            │
│                           │                                     │
│                           ▼                                     │
│              ┌────────────────────────┐                        │
│              │ 뉴스/공시 발표          │                        │
│              │ (15:30 ~ 다음날 08:30)  │                        │
│              └────────────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                 아침 스캔 (08:30)                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 1. 데이터 수집                                            │  │
│  │    ├─ DART API: 공시 조회                                │  │
│  │    ├─ 네이버: 뉴스 스크래핑                               │  │
│  │    └─ pykrx: 주가/시총/거래량                            │  │
│  │                                                          │  │
│  │ 2. 점수 계산                                             │  │
│  │    └─ keywords.yaml 기반 (+3, +1, -10)                  │  │
│  │                                                          │  │
│  │ 3. 필터링                                                │  │
│  │    ├─ 전략 A: 공통 필터만                                │  │
│  │    └─ 전략 B: 공통 + 급등/52주고가/외국인 필터           │  │
│  │                                                          │  │
│  │ 4. 저장                                                  │  │
│  │    └─ data/signals_YYYYMMDD.json                        │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   장 시작 (09:00)                                │
│                                                                 │
│            선정된 종목 시초가 매수 (사용자 수동)                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   장 마감 (15:30)                                │
│                                                                 │
│                    종가 확정                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                 저녁 추적 (15:40)                                │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ 1. 수익률 계산                                            │  │
│  │    └─ (종가 - 시가) / 시가 * 100                         │  │
│  │                                                          │  │
│  │ 2. 성과 분석                                             │  │
│  │    ├─ 전략 A 평균 수익률                                 │  │
│  │    ├─ 전략 B 평균 수익률                                 │  │
│  │    └─ 승률, 누적 수익률 계산                             │  │
│  │                                                          │  │
│  │ 3. 저장                                                  │  │
│  │    ├─ data/signals.json (히스토리 누적)                  │  │
│  │    └─ data/results.json (분석 결과)                      │  │
│  │                                                          │  │
│  │ 4. 대시보드 업데이트                                      │  │
│  │    └─ docs/dashboard_data.json                          │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Pages 대시보드                         │
│                                                                 │
│  ┌────────────────┐  ┌────────────────┐  ┌─────────────────┐   │
│  │ 전략 A 성과    │  │ 전략 B 성과    │  │ 누적 수익률 차트 │   │
│  │ - 평균 수익률  │  │ - 평균 수익률  │  │                 │   │
│  │ - 승률        │  │ - 승률        │  │                 │   │
│  │ - 누적 수익률  │  │ - 누적 수익률  │  │                 │   │
│  └────────────────┘  └────────────────┘  └─────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    최근 시그널 목록                       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 데이터 저장 형식

#### data/signals_YYYYMMDD.json
```json
{
  "date": "20240115",
  "generated_at": "2024-01-15T08:30:00",
  "summary": {
    "total_collected": 90,
    "strategy_a_count": 10,
    "strategy_b_count": 7
  },
  "strategy_a": [
    {
      "source": "dart",
      "corp_name": "삼성전자",
      "stock_code": "005930",
      "title": "단일판매ㆍ공급계약체결",
      "score": 6,
      "matched_keywords": ["+3: 수주", "+3: 계약 체결"],
      "market_cap": 500000000000000,
      "strategy": "A"
    }
  ],
  "strategy_b": [...]
}
```

#### data/signals.json (히스토리)
```json
[
  {
    "date": "20240115",
    "strategy": "A",
    "signals": [...],
    "recorded_at": "2024-01-15T08:30:00",
    "status": "tracked",
    "tracked_at": "2024-01-15T15:40:00",
    "results": [
      {
        "stock_code": "005930",
        "buy_price": 75000,
        "sell_price": 76500,
        "returns": 2.0,
        "signal": {...}
      }
    ],
    "avg_return": 1.85
  }
]
```

---

## 7. 환경 설정 및 실행

### 7.1 요구사항

- Python 3.9 이상
- DART API 키 (https://opendart.fss.or.kr 에서 발급)

### 7.2 설치

```bash
# 저장소 클론
git clone https://github.com/sungmin2nn/news-trading-bot.git
cd news-trading-bot

# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 7.3 환경변수 설정

```bash
# Linux/Mac
export DART_API_KEY="your_dart_api_key_here"

# Windows (PowerShell)
$env:DART_API_KEY="your_dart_api_key_here"

# Windows (CMD)
set DART_API_KEY=your_dart_api_key_here
```

### 7.4 실행

```bash
# 아침 스캔 (수동 테스트)
python src/morning_scan.py

# 저녁 추적 (수동 테스트)
python src/evening_track.py
```

### 7.5 의존성 목록 (requirements.txt)

```
pykrx>=1.0.0              # 한국 주식 데이터
finance-datareader>=0.9.0 # 금융 데이터
opendartreader>=0.2.0     # DART API
pandas>=2.0.0             # 데이터 처리
numpy>=1.24.0             # 수치 계산
beautifulsoup4>=4.12.0    # 웹 스크래핑
requests>=2.31.0          # HTTP 요청
lxml>=5.0.0               # HTML 파싱
pyyaml>=6.0.0             # YAML 파싱
python-dateutil>=2.8.0    # 날짜 처리
pytz>=2024.1              # 타임존
```

---

## 8. GitHub Actions 자동화

### 8.1 워크플로우 파일

#### .github/workflows/morning-scan.yml
```yaml
name: Morning Scan

on:
  schedule:
    - cron: '30 23 * * 0-4'  # UTC 23:30 = KST 08:30 (일~목)
  workflow_dispatch:          # 수동 실행

jobs:
  morning-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python src/morning_scan.py
        env:
          DART_API_KEY: ${{ secrets.DART_API_KEY }}
      - run: |
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git config user.name "github-actions[bot]"
          git add data/
          git diff --staged --quiet || git commit -m "Update signals"
          git push
```

#### .github/workflows/evening-track.yml
```yaml
name: Evening Track

on:
  schedule:
    - cron: '40 6 * * 1-5'   # UTC 06:40 = KST 15:40 (월~금)
  workflow_dispatch:

jobs:
  evening-track:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: python src/evening_track.py
        env:
          DART_API_KEY: ${{ secrets.DART_API_KEY }}
      - run: |
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git config user.name "github-actions[bot]"
          git add data/ docs/
          git diff --staged --quiet || git commit -m "Update tracking results"
          git push
```

### 8.2 GitHub 설정 방법

1. **DART API 키 등록**
   - Repository → Settings → Secrets and variables → Actions
   - "New repository secret" 클릭
   - Name: `DART_API_KEY`
   - Value: 발급받은 API 키 입력

2. **GitHub Pages 활성화**
   - Repository → Settings → Pages
   - Source: "Deploy from a branch"
   - Branch: `main`, Folder: `/docs`
   - Save

3. **워크플로우 권한 설정**
   - Repository → Settings → Actions → General
   - Workflow permissions: "Read and write permissions" 선택

4. **수동 테스트**
   - Repository → Actions
   - "Morning Scan" 또는 "Evening Track" 선택
   - "Run workflow" 클릭

---

## 9. 대시보드

### 9.1 접속 URL

GitHub Pages 활성화 후:
```
https://{username}.github.io/news-trading-bot/
```

### 9.2 대시보드 기능

1. **전략 A/B 성과 비교**
   - 평균 수익률
   - 승률
   - 누적 수익률
   - 거래일 수

2. **누적 수익률 차트**
   - 전략 A vs 전략 B 라인 차트

3. **일별 수익률 차트**
   - 막대 그래프로 일별 비교

4. **최근 시그널 목록**
   - 날짜, 전략, 종목 수, 수익률, 상태

### 9.3 데이터 갱신

- 저녁 추적(`evening_track.py`) 실행 시 자동 갱신
- `docs/dashboard_data.json` 파일 업데이트
- 브라우저에서 5분마다 자동 새로고침

---

## 10. 개발 가이드

### 10.1 새 키워드 추가

`config/keywords.yaml` 수정:
```yaml
strong_positive:
  - 기존키워드
  - 새로운키워드    # 추가
```

### 10.2 필터 조건 수정

`config/settings.yaml` 수정:
```yaml
min_market_cap: 100000000000  # 1000억으로 변경
max_price_change_5d: 20.0     # 20%로 변경
```

### 10.3 새 수집기 추가

1. `src/collectors/` 에 새 파일 생성
2. `src/collectors/__init__.py`에 import 추가
3. `src/morning_scan.py`에서 호출

예시 (트위터 수집기):
```python
# src/collectors/twitter_collector.py
class TwitterCollector:
    def collect(self):
        ...
        return signals
```

### 10.4 새 필터 조건 추가 (전략 C)

`src/analyzers/stock_filter.py` 수정:
```python
def apply_strategy_c(self, signals: list) -> list:
    """전략 C - 커스텀 로직"""
    filtered = self.apply_common_filters(signals)

    # 새로운 필터 조건 추가
    for signal in filtered:
        # ...

    return filtered
```

### 10.5 코드 스타일

- Python 3.9+ 타입 힌트 사용
- docstring 필수 (Google 스타일)
- 에러 처리 시 적절한 로깅

---

## 11. 트러블슈팅

### 11.1 DART API 오류

**증상:** `DART API 키가 필요합니다` 오류

**해결:**
```bash
# 환경변수 확인
echo $DART_API_KEY

# 없으면 설정
export DART_API_KEY="your_key"
```

### 11.2 pykrx 데이터 없음

**증상:** 주가 데이터가 빈 DataFrame 반환

**원인:**
- 휴장일 데이터 요청
- 잘못된 종목 코드

**해결:**
- 영업일 확인
- 종목 코드 6자리 확인 (예: `005930`)

### 11.3 네이버 스크래핑 차단

**증상:** 403 Forbidden 또는 빈 응답

**해결:**
- `news_delay` 값 증가 (기본 0.5초 → 1초)
- User-Agent 헤더 변경

### 11.4 GitHub Actions 실패

**증상:** 워크플로우 빨간색 X 표시

**확인 사항:**
1. Secrets에 `DART_API_KEY` 등록 확인
2. Actions 권한 "Read and write" 확인
3. Actions 로그에서 상세 오류 확인

### 11.5 대시보드 데이터 없음

**증상:** 대시보드에 "-" 표시

**원인:** `docs/dashboard_data.json` 파일 없음

**해결:**
```bash
python src/evening_track.py
```

---

## 부록: 주요 클래스/함수 요약

| 모듈 | 클래스/함수 | 용도 |
|------|-------------|------|
| dart_collector | DartCollector | DART 공시 수집 |
| dart_collector | get_overnight_disclosures() | 장 마감 후 공시 |
| naver_collector | NaverCollector | 네이버 뉴스 수집 |
| naver_collector | get_overnight_news() | 장 마감 후 뉴스 |
| price_collector | PriceCollector | 주가 데이터 수집 |
| price_collector | get_stock_info() | 종목 종합 정보 |
| keyword_scorer | KeywordScorer | 키워드 점수 계산 |
| keyword_scorer | score_signals() | 시그널 목록 점수화 |
| stock_filter | StockFilter | A/B 전략 필터링 |
| stock_filter | apply_both_strategies() | A/B 동시 적용 |
| simulator | Simulator | 수익률 시뮬레이션 |
| simulator | track_signals() | 수익률 추적 |
| simulator | compare_strategies() | A/B 성과 비교 |

---

**문서 버전:** 1.0
**최종 수정:** 2024-01-17
**작성자:** Claude AI Assistant
