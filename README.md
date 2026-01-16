# 뉴스 기반 시초가 매매 시스템 기획서

## 문서 정보
- **작성일**: 2025-01-16
- **버전**: 1.0
- **목적**: AI에게 이 문서만 주면 코드 개발이 가능하도록 전체 시스템 명세 정리

---

## 1. 시스템 개요

### 1.1 목표
장 마감 후 발생한 호재 뉴스/공시를 분석하여 다음 날 장전 시간외 매수 종목을 자동 선정하고, 페이퍼 트레이딩으로 전략을 검증하는 시스템

### 1.2 운영 방식
- **Phase 1 (1~3개월)**: 실매매 없이 신호 수집 + 결과 추적 (페이퍼 트레이딩)
- **Phase 2**: 검증 완료 후 실매매 연동

### 1.3 플랫폼
- **실행 환경**: GitHub Actions (무료 티어)
- **데이터 저장**: GitHub Repository (JSON 파일)
- **대시보드**: GitHub Pages (React + Recharts)

---

## 2. 매매 전략

### 2.1 장전 시간외 매매란?
```
08:30 ~ 08:40  주문 가능 시간
08:40 이후     전일 종가로 체결

예시:
- 전일 종가: 10,000원
- 아침에 호재 뉴스 발생
- 08:35에 매수 주문
- 08:40에 10,000원으로 체결
- 09:00 시초가: 10,500원 (갭상승)
- → 시작부터 5% 수익 상태
```

### 2.2 전략 원리
```
1. 장 마감 후 호재 뉴스/공시 발생
2. 다음 날 아침 뉴스 분석 → 종목 선정
3. 장전 시간외로 전일 종가에 매수 (가정)
4. 시초가에 갭상승하면 수익
5. 장중 목표가/손절가 도달 시 매도
```

### 2.3 매매 규칙 (초기 설정값)
```yaml
진입:
  방식: 장전 시간외 매수
  가격: 전일 종가
  시간: 08:40 체결 가정

청산:
  익절_목표가: +5%      # 매수가 대비
  손절가: -3%           # 매수가 대비
  트레일링스탑: -2%     # 장중 고점 대비
  강제청산: 당일 15:30 종가

예시:
  매수가: 10,000원
  익절: 10,500원 이상 도달 시
  손절: 9,700원 이하 도달 시
  트레일링: 장중고점 10,800원 찍은 후 10,584원 이하 하락 시
```

---

## 3. 데이터 수집

### 3.1 수집 소스

#### 3.1.1 Open DART API (공시)
```yaml
용도: 공식 공시 정보 수집
URL: https://opendart.fss.or.kr
인증: API 키 필요 (무료 발급)
라이브러리: OpenDartReader

수집 대상:
  - 수주/계약 체결
  - 실적 공시 (영업이익, 매출)
  - 유상증자/CB/BW 발행
  - 자사주 취득/처분
  - 최대주주 변경
  - 합병/분할
```

#### 3.1.2 네이버 금융 (뉴스)
```yaml
용도: 뉴스 기사, 증권사 리포트
URL: https://finance.naver.com
인증: 불필요
방식: BeautifulSoup 크롤링

수집 대상:
  - 종목별 뉴스
  - 증권사 목표가 변경
  - 테마/이슈 뉴스
  - 시장 속보
```

### 3.2 수집 시간 범위
```
수집 대상 기간: 전일 15:30 ~ 당일 08:30
(장 마감 후 ~ 다음 날 아침까지 발생한 뉴스/공시)
```

---

## 4. 뉴스 분석 기준

### 4.1 키워드 점수표

#### 강한 호재 (+3점)
```yaml
실적_재무:
  - 흑자전환
  - 사상최대 실적
  - 영업이익 증가
  - 배당 확대
  - 자사주 매입
  - 자사주 취득

사업_확장:
  - 수주
  - 계약 체결
  - 공급계약
  - 납품계약
  - 신규 시장 진출
  - 대기업 공급
  - MOU 체결

바이오_제약:
  - 임상 성공
  - 임상 통과
  - FDA 승인
  - 식약처 승인
  - 기술수출
  - 라이선스 계약

기타:
  - 정부 정책 수혜
  - 보조금 지급
  - 규제 완화
```

#### 중간 호재 (+1점)
```yaml
  - 목표가 상향
  - 투자의견 상향
  - 신제품 출시
  - 투자 유치
  - 지분 투자
  - 특허 취득
  - 해외 진출
```

#### 제외 조건 (-10점) - 매수 금지
```yaml
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
  - 상장폐지
```

### 4.2 키워드 설정 파일 (config/keywords.yaml)
```yaml
strong_positive:  # +3점
  - 흑자전환
  - 사상최대
  - 수주
  - 계약 체결
  - 공급계약
  - FDA 승인
  - 임상 성공
  - 자사주 매입
  - 자사주 취득
  - 기술수출

medium_positive:  # +1점
  - 목표가 상향
  - 투자의견 상향
  - 신제품 출시
  - 특허 취득
  - 투자 유치

negative:  # -10점
  - 유상증자
  - CB 발행
  - BW 발행
  - 전환사채
  - 최대주주 매각
  - 횡령
  - 배임
  - 감사의견 거절
  - 관리종목
  - 상장폐지
```

---

## 5. 종목 필터링 조건

### 5.1 기본 필터 - A/B 공통 (1차)
```yaml
시가총액:
  최소: 500억원
  최대: 3조원

거래대금:
  전일_최소: 50억원

주가:
  최소: 1,000원

제외:
  - 관리종목
  - 투자경고
  - 투자위험
  - 정리매매
  - 스팩(SPAC)
  - ETF/ETN
```

### 5.2 거래량 필터 - A/B 공통 (2차)
```yaml
전일_거래량_증가율:
  최소: 50%  # 전일 대비

5일평균_대비_거래량:
  최소: 100%  # 5일 평균 대비
```

### 5.3 뉴스 점수 필터 - A/B 공통 (3차)
```yaml
최소_점수: 3점
```

### 5.4 B로직 추가 필터 (고도화)
```yaml
# A로직은 여기까지만, B로직은 아래 추가 적용

규모비율_필터:
  설명: 수주/계약 금액이 시총 대비 의미 있는지
  계산: 계약금액 ÷ 시가총액 × 100
  최소: 5%
  예시:
    - 시총 2000억, 수주 500억 → 25% → 통과
    - 시총 50조, 수주 100억 → 0.02% → 제외

선반영_필터:
  설명: 이미 급등한 종목 제외
  계산: 최근 5일 상승률
  최대: 15%
  예시:
    - 5일간 +8% → 통과
    - 5일간 +20% → 제외 (이미 반영됨)

수급_필터:
  설명: 외국인/기관이 사는 종목만
  조건: 최근 5일 외국인+기관 순매수 > 0
  예시:
    - 외국인 +100억, 기관 -50억 → 순매수 +50억 → 통과
    - 외국인 -200억, 기관 -100억 → 순매수 -300억 → 제외

차트위치_필터:
  설명: 52주 고점 부근 종목 제외
  계산: (현재가 - 52주저점) ÷ (52주고점 - 52주저점) × 100
  최대: 90%
  예시:
    - 52주 저점 10000, 고점 20000, 현재 12000 → 20% → 통과
    - 52주 저점 10000, 고점 20000, 현재 19000 → 90% → 제외
```

### 5.5 B로직 점수 조정 공식
```python
# A로직 점수
score_a = 키워드_점수_합계

# B로직 점수
score_b = score_a × 규모비율_가중치 × 수급_가중치 × 차트_가중치

# 가중치 계산
규모비율_가중치:
  - 계약금액/시총 > 10% → 1.5
  - 계약금액/시총 > 5%  → 1.2
  - 계약금액/시총 > 1%  → 1.0
  - 계약금액/시총 < 1%  → 0.5

수급_가중치:
  - 외국인+기관 순매수 > 100억 → 1.3
  - 외국인+기관 순매수 > 0     → 1.1
  - 외국인+기관 순매도         → 0.7

차트_가중치:
  - 52주 위치 < 30% (바닥권) → 1.2
  - 52주 위치 < 70% (중간)   → 1.0
  - 52주 위치 > 90% (고점권) → 0.7
```

---

## 6. 매도 시뮬레이션

### 6.1 시뮬레이션 로직
```python
# 의사코드

매수가 = 전일_종가
장중_고점 = 매수가

for 분봉 in 당일_분봉_데이터:
    현재가 = 분봉.종가
    
    # 장중 고점 갱신
    if 현재가 > 장중_고점:
        장중_고점 = 현재가
    
    # 익절 체크 (목표가 도달)
    if 현재가 >= 매수가 * 1.05:
        return 청산(가격=현재가, 사유="target_hit", 유형="익절")
    
    # 손절 체크
    if 현재가 <= 매수가 * 0.97:
        return 청산(가격=현재가, 사유="stop_loss", 유형="손절")
    
    # 트레일링 스탑 체크
    if 현재가 <= 장중_고점 * 0.98:
        return 청산(가격=현재가, 사유="trailing_stop", 유형="익절")

# 장 마감까지 조건 미충족 시
return 청산(가격=종가, 사유="eod_close", 유형="강제청산")
```

### 6.2 매도 사유 분류
```yaml
exit_reasons:
  target_hit:
    설명: 목표가 +5% 도달
    유형: 익절
  
  trailing_stop:
    설명: 장중 고점 대비 -2% 하락
    유형: 익절
  
  stop_loss:
    설명: 손절가 -3% 도달
    유형: 손절
  
  eod_close:
    설명: 당일 종가 강제 청산
    유형: 수익 또는 손실 (결과에 따라)
```

---

## 7. 실행 스케줄

### 7.1 GitHub Actions 스케줄
```yaml
# .github/workflows/morning-scan.yml
name: Morning Scan
on:
  schedule:
    - cron: '30 23 * * 0-4'  # UTC 23:30 = KST 08:30 (월~금)

# .github/workflows/evening-track.yml  
name: Evening Track
on:
  schedule:
    - cron: '40 6 * * 1-5'   # UTC 06:40 = KST 15:40 (월~금)
```

### 7.2 실행 흐름
```
[Morning Scan - 08:30 KST]
├── DART 공시 수집 (전일 15:30 ~ 당일 08:30)
├── 네이버 뉴스 수집 (전일 15:30 ~ 당일 08:30)
├── 키워드 분석 및 점수화
├── 종목 필터링
├── 매수 후보 저장 (signals.json)
└── 완료

[Evening Track - 15:40 KST]
├── 당일 분봉 데이터 수집
├── 매도 시뮬레이션 실행
├── 결과 기록 (익절/손절/강제청산)
├── 성과 지표 업데이트
├── signals.json 업데이트
└── 완료
```

---

## 8. 데이터 구조

### 8.1 A/B 테스트 방식
```
매일 아침 동일 종목 풀에서:

A 로직 (단순):
  - 키워드 매칭만으로 점수화
  - 기본 필터만 적용

B 로직 (고도화):
  - 키워드 + 규모비율 + 수급 + 차트
  - 선반영 체크, 출처 신뢰도 적용

→ 둘 다 시뮬레이션 → 결과 비교 → 어떤 로직이 나은지 데이터로 검증
```

### 8.2 메인 데이터 파일 (data/signals.json)
```json
{
  "updated_at": "2025-01-16T15:45:00+09:00",
  "config": {
    "target_pct": 5.0,
    "stop_loss_pct": 3.0,
    "trailing_pct": 2.0
  },
  "summary_a": {
    "total_signals": 150,
    "win_count": 82,
    "lose_count": 68,
    "win_rate": 54.7,
    "avg_return": 1.2,
    "total_return": 180.0
  },
  "summary_b": {
    "total_signals": 95,
    "win_count": 65,
    "lose_count": 30,
    "win_rate": 68.4,
    "avg_return": 2.8,
    "total_return": 266.0
  },
  "comparison": {
    "win_rate_diff": 13.7,
    "avg_return_diff": 1.6,
    "better_logic": "B"
  },
  "by_keyword": {
    "수주": {
      "a": {"count": 25, "win_rate": 60.0, "avg_return": 1.8},
      "b": {"count": 18, "win_rate": 77.8, "avg_return": 3.5}
    },
    "임상": {
      "a": {"count": 15, "win_rate": 53.3, "avg_return": 1.0},
      "b": {"count": 10, "win_rate": 70.0, "avg_return": 3.2}
    }
  },
  "daily": [
    {
      "date": "2025-01-16",
      "signals_a": [
        {
          "code": "005930",
          "name": "삼성전자",
          "news_title": "반도체 수주 10조 계약 체결",
          "news_source": "DART",
          "score": 6,
          "entry_price": 72000,
          "exit_price": 74300,
          "exit_reason": "trailing_stop",
          "pnl_percent": 3.2,
          "pnl_type": "익절"
        }
      ],
      "signals_b": [
        {
          "code": "005930",
          "name": "삼성전자",
          "news_title": "반도체 수주 10조 계약 체결",
          "news_source": "DART",
          "score": 6,
          "score_adjusted": 8.4,
          "adjustments": {
            "contract_ratio": 1.2,
            "no_prerun": 1.0,
            "institution_buy": 1.3,
            "chart_position": 0.9
          },
          "entry_price": 72000,
          "exit_price": 75600,
          "exit_reason": "target_hit",
          "pnl_percent": 5.0,
          "pnl_type": "익절"
        }
      ],
      "daily_summary": {
        "a": {"total": 5, "win": 3, "lose": 2, "daily_return": 1.8},
        "b": {"total": 3, "win": 2, "lose": 1, "daily_return": 3.5}
      }
    }
  ]
}
```

### 8.2 신호 상태값
```yaml
status:
  pending: 아침에 신호 생성됨, 아직 장중 결과 미반영
  closed: 매도 시뮬레이션 완료
  error: 데이터 수집 오류
```

---

## 9. 폴더 구조

```
news-trading-bot/
├── .github/
│   └── workflows/
│       ├── morning-scan.yml      # 08:30 뉴스 분석
│       └── evening-track.yml     # 15:40 결과 추적
│
├── src/
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── dart_collector.py     # DART 공시 수집
│   │   ├── naver_collector.py    # 네이버 뉴스 수집
│   │   └── price_collector.py    # 주가/분봉/수급 수집
│   │
│   ├── analyzers/
│   │   ├── __init__.py
│   │   ├── keyword_scorer.py     # 키워드 점수화 (A로직)
│   │   ├── advanced_scorer.py    # 고도화 점수화 (B로직)
│   │   ├── stock_filter.py       # 종목 필터링
│   │   └── simulator.py          # 매도 시뮬레이션
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── data_manager.py       # JSON 읽기/쓰기
│   │   └── date_utils.py         # 날짜 유틸리티
│   │
│   ├── morning_scan.py           # 아침 스캔 메인
│   └── evening_track.py          # 저녁 추적 메인
│
├── data/
│   ├── signals.json              # 누적 데이터 (A/B 비교 포함)
│   └── config.json               # 설정값 (대시보드에서 수정)
│
├── docs/                         # GitHub Pages 대시보드
│   ├── index.html
│   ├── app.jsx                   # React 앱
│   ├── pages/
│   │   ├── Home.jsx              # 메인 화면
│   │   ├── Analysis.jsx          # 분석 화면
│   │   └── Settings.jsx          # 설정 화면
│   └── style.css
│
├── requirements.txt
└── README.md
```

---

## 10. 대시보드 구성

### 10.1 메인 화면
```
┌─────────────────────────────────────────────────────────┐
│  📊 뉴스 트레이딩 대시보드      [홈] [분석] [설정]        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  [A/B 로직 비교 차트 - 라인 그래프]                       │
│  A로직(단순) ─── vs B로직(고도화) ───                    │
│                                                         │
├────────────┬────────────┬────────────┬─────────────────┤
│            │  A 로직    │  B 로직    │   차이          │
│  승률      │  55.0%     │  68.0%     │   +13%         │
│  평균수익   │  +1.2%     │  +2.8%     │   +1.6%        │
├────────────┴────────────┴────────────┴─────────────────┤
│                                                         │
│  [일별 손익 차트 - 바 그래프]                             │
│  X축: 날짜 / Y축: 일별 수익률(%)                         │
│  색상: A로직=회색, B로직=파랑                            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 10.2 분석 탭
```
┌─────────────────────────────────────────────────────────┐
│  [키워드별 성과]              [매도유형별 성과]           │
│                                                         │
│  수주/계약  ████████ 72%     목표도달 ████████ 38%      │
│  임상/승인  ██████ 67%       트레일링 ██████ 28%        │
│  실적      ████ 53%          손절    ████ 18%          │
│                              강제청산 ████ 16%          │
├─────────────────────────────────────────────────────────┤
│  [요일별 성과]                                           │
│                                                         │
│  월 ██████ 64%                                          │
│  화 ██████ 61%                                          │
│  수 ████████ 71%                                        │
│  목 ██████ 65%                                          │
│  금 ██████ 63%                                          │
└─────────────────────────────────────────────────────────┘
```

### 10.3 최근 신호 목록
```
┌─────────────────────────────────────────────────────────┐
│  최근 신호                                    [전체보기]  │
├─────────────────────────────────────────────────────────┤
│  01/16 삼성전자(005930)                                 │
│        A: +3.2% 익절  |  B: +5.0% 익절                  │
│        └ 반도체 수주 10조 계약 체결 (DART)              │
│                                                         │
│  01/16 셀트리온(068270)                                 │
│        A: -3.0% 손절  |  B: 미선정 (수급 불량)           │
│        └ FDA 바이오시밀러 승인 (네이버)                  │
│                                                         │
│  01/15 카카오(035720)                                   │
│        A: +1.5% 익절  |  B: +2.1% 익절                  │
│        └ AI 사업부 분사 검토 (네이버)                    │
└─────────────────────────────────────────────────────────┘
```

### 10.4 설정 페이지
```
┌─────────────────────────────────────────────────────────┐
│  📊 대시보드                    [홈] [분석] [설정]        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ⚙️ 설정                                                │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ API 설정                                        │   │
│  ├─────────────────────────────────────────────────┤   │
│  │ DART API Key: [••••••••••••••••] [저장]         │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 매매 파라미터                                    │   │
│  ├─────────────────────────────────────────────────┤   │
│  │ 익절 목표:     [5] %                            │   │
│  │ 손절 기준:     [3] %                            │   │
│  │ 트레일링:      [2] %                            │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 필터 조건                                        │   │
│  ├─────────────────────────────────────────────────┤   │
│  │ 최소 시총:     [500] 억                         │   │
│  │ 최대 시총:     [30000] 억                       │   │
│  │ 최소 거래대금: [50] 억                          │   │
│  │ 최소 점수:     [3] 점                           │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 키워드 설정                                      │   │
│  ├─────────────────────────────────────────────────┤   │
│  │ 강한 호재 (+3): [수주, 계약체결, FDA승인, ...]   │   │
│  │ 중간 호재 (+1): [목표가상향, 신제품, ...]        │   │
│  │ 제외 (-10):    [유상증자, CB발행, ...]          │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │ B로직 추가 설정 (고도화)                         │   │
│  ├─────────────────────────────────────────────────┤   │
│  │ 수주금액/시총 최소비율: [5] %                    │   │
│  │ 선반영 제외 (N일 상승률): [15] %                 │   │
│  │ 외국인+기관 순매수 필수: [✓]                    │   │
│  │ 52주 고점 제외 비율: [90] %                     │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│              [설정 저장] [기본값 복원]                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 10.5 설정 저장 방식
```yaml
저장_위치:
  API_Key: GitHub Secrets (보안) 또는 브라우저 localStorage
  기타_설정: data/config.json → GitHub 자동 커밋

config.json_구조:
  trading:
    target_pct: 5
    stop_loss_pct: 3
    trailing_pct: 2
  
  filters:
    min_market_cap: 50000000000
    max_market_cap: 3000000000000
    min_trading_value: 5000000000
    min_score: 3
  
  keywords:
    strong_positive: [수주, 계약체결, ...]
    medium_positive: [목표가상향, ...]
    negative: [유상증자, ...]
  
  logic_b:
    min_contract_ratio: 5
    max_recent_gain: 15
    require_institution_buy: true
    exclude_near_high_pct: 90
```

---

## 11. 사용 라이브러리

### 11.1 Python 패키지 (requirements.txt)
```
# 데이터 수집
pykrx>=1.0.0                # KRX 주가 데이터
finance-datareader>=0.9.0    # 종목 리스트, 시총
opendartreader>=0.2.0        # DART 공시
beautifulsoup4>=4.12.0       # 네이버 크롤링
requests>=2.31.0             # HTTP 요청
lxml>=5.0.0                  # HTML 파싱

# 데이터 처리
pandas>=2.0.0
numpy>=1.24.0
pyyaml>=6.0.0               # YAML 설정 파일

# 유틸리티
python-dateutil>=2.8.0
pytz>=2024.1
```

### 11.2 대시보드 (docs/)
```
React 18 (CDN)
Recharts (CDN) - 차트 라이브러리
Tailwind CSS (CDN) - 스타일링
```

---

## 12. 검증 기준

### 12.1 실매매 전환 조건
```yaml
최소_기간: 2개월 (약 40 거래일)
최소_신호_수: 100개 이상
승률: 60% 이상
평균_수익: 2% 이상
손익비: 1.5 이상  # 평균익절 / 평균손절
최대_단일_손실: -10% 이하
```

### 12.2 파라미터 조정 기준
```yaml
승률_50%_미만:
  - 키워드 점수 재검토
  - 필터 조건 강화

평균수익_1%_미만:
  - 목표가 상향 검토
  - 트레일링 비율 조정

손익비_1.0_미만:
  - 손절가 축소 검토
  - 진입 조건 강화
```

---

## 13. API 키 및 환경변수

### 13.1 필요한 API 키
```yaml
DART_API_KEY:
  용도: Open DART 공시 조회
  발급: https://opendart.fss.or.kr
  비용: 무료
  
# GitHub Secrets에 등록
# Settings > Secrets and variables > Actions > New repository secret
```

### 13.2 GitHub Actions 환경변수
```yaml
# .github/workflows/morning-scan.yml
env:
  DART_API_KEY: ${{ secrets.DART_API_KEY }}
  TZ: Asia/Seoul
```

---

## 14. 주의사항 및 제한

### 14.1 GitHub Actions 제한
```yaml
무료_티어:
  월간_실행시간: 2,000분
  일일_사용가능: 약 65분
  
예상_사용량:
  아침_스캔: 약 10분
  저녁_추적: 약 10분
  일일_합계: 약 20분
  월간_합계: 약 400분 (여유 있음)
```

### 14.2 크롤링 주의사항
```yaml
네이버_금융:
  - robots.txt 준수
  - 요청 간 딜레이 1초 이상
  - User-Agent 설정
  - 차단 시 대응 로직 필요

DART_API:
  - 일일 요청 한도 확인
  - 에러 처리 필수
```

### 14.3 데이터 정합성
```yaml
중복_제거:
  - DART + 네이버 동일 건 병합
  - 종목코드 기준으로 중복 체크
  
누락_처리:
  - 분봉 데이터 없을 시 일봉으로 대체
  - 시뮬레이션 불가 시 상태를 'error'로 표시
```

---

## 15. 향후 확장 계획

### 15.1 Phase 2 (실매매 연동)
```yaml
증권사: 키움증권 (OpenAPI+)
서버: Oracle Cloud 무료 티어 또는 집 PC
기능:
  - 실시간 장전 시간외 주문
  - 실시간 매도 모니터링
  - 텔레그램 알림 연동
```

### 15.2 고도화 기능
```yaml
ML_감성분석:
  - 뉴스 본문 긍정/부정 분류
  - 키워드 자동 추출

백테스트:
  - 과거 데이터로 전략 검증
  - 파라미터 최적화

멀티_전략:
  - 시초가 갭 매매
  - 장중 돌파 매매
  - 종가 베팅
```

---

## 16. 체크리스트

### 16.1 개발 전 준비
- [ ] GitHub 계정 생성
- [ ] Open DART API 키 발급
- [ ] GitHub Repository 생성
- [ ] GitHub Pages 활성화

### 16.2 개발 순서
1. [ ] 프로젝트 구조 생성
2. [ ] 설정 파일 작성 (keywords.yaml, filters.yaml)
3. [ ] DART 수집기 개발
4. [ ] 네이버 수집기 개발
5. [ ] 키워드 분석기 개발
6. [ ] 종목 필터 개발
7. [ ] 주가 수집기 개발
8. [ ] 매도 시뮬레이터 개발
9. [ ] 메인 스크립트 작성 (morning_scan.py, evening_track.py)
10. [ ] GitHub Actions 워크플로우 작성
11. [ ] 대시보드 개발
12. [ ] 테스트 및 배포

---

## 부록 A: 코드 예시

### A.1 DART 수집기 기본 구조
```python
# src/collectors/dart_collector.py

import OpenDartReader
from datetime import datetime, timedelta

class DartCollector:
    def __init__(self, api_key: str):
        self.dart = OpenDartReader(api_key)
    
    def get_disclosures(self, start_date: str, end_date: str) -> list:
        """
        기간 내 공시 목록 조회
        
        Args:
            start_date: 시작일 (YYYY-MM-DD)
            end_date: 종료일 (YYYY-MM-DD)
        
        Returns:
            공시 목록 리스트
        """
        # 구현 필요
        pass
    
    def filter_positive_disclosures(self, disclosures: list) -> list:
        """
        호재성 공시만 필터링
        """
        # 구현 필요
        pass
```

### A.2 네이버 수집기 기본 구조
```python
# src/collectors/naver_collector.py

import requests
from bs4 import BeautifulSoup
from typing import List, Dict

class NaverCollector:
    BASE_URL = "https://finance.naver.com"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_stock_news(self, stock_code: str) -> List[Dict]:
        """
        종목별 뉴스 수집
        
        Args:
            stock_code: 종목코드 (6자리)
        
        Returns:
            뉴스 리스트
        """
        # 구현 필요
        pass
    
    def get_market_news(self) -> List[Dict]:
        """
        시장 전체 뉴스 수집
        """
        # 구현 필요
        pass
```

### A.3 키워드 분석기 기본 구조
```python
# src/analyzers/keyword_scorer.py

import yaml
from typing import Dict, List, Tuple

class KeywordScorer:
    def __init__(self, config_path: str = "config/keywords.yaml"):
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        self.strong_positive = self.config.get('strong_positive', [])
        self.medium_positive = self.config.get('medium_positive', [])
        self.negative = self.config.get('negative', [])
    
    def score(self, text: str) -> Tuple[int, List[str]]:
        """
        텍스트 점수 계산
        
        Args:
            text: 분석할 텍스트 (뉴스 제목 등)
        
        Returns:
            (점수, 매칭된 키워드 리스트)
        """
        score = 0
        matched = []
        
        for keyword in self.strong_positive:
            if keyword in text:
                score += 3
                matched.append(keyword)
        
        for keyword in self.medium_positive:
            if keyword in text:
                score += 1
                matched.append(keyword)
        
        for keyword in self.negative:
            if keyword in text:
                score -= 10
                matched.append(keyword)
        
        return score, matched
```

---

## 부록 B: GitHub Actions 워크플로우 예시

### B.1 아침 스캔 워크플로우
```yaml
# .github/workflows/morning-scan.yml

name: Morning Scan

on:
  schedule:
    - cron: '30 23 * * 0-4'  # UTC 23:30 = KST 08:30
  workflow_dispatch:  # 수동 실행 허용

jobs:
  scan:
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run morning scan
        env:
          DART_API_KEY: ${{ secrets.DART_API_KEY }}
          TZ: Asia/Seoul
        run: python src/morning_scan.py
      
      - name: Commit results
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add data/signals.json
          git diff --staged --quiet || git commit -m "Update signals $(date +%Y-%m-%d)"
          git push
```

---

## 문서 끝

이 문서를 AI에게 제공하면 전체 시스템을 이해하고 코드를 개발할 수 있습니다.
