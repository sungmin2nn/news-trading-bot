"""
아침 스캔 메인 스크립트
장 시작 전(08:30) 뉴스/공시를 분석하여 매수 종목을 선정합니다.
"""

import json
import os
import sys
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.collectors.dart_collector import DartCollector
from src.collectors.naver_collector import NaverCollector
from src.analyzers.keyword_scorer import KeywordScorer
from src.analyzers.stock_filter import StockFilter
from src.analyzers.simulator import Simulator
from src.utils.notifier import EmailNotifier


def run_morning_scan():
    """아침 스캔을 실행합니다."""
    print(f"=" * 60)
    print(f"뉴스 트레이딩 봇 - 아침 스캔")
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=" * 60)

    all_signals = []

    # 1. DART 공시 수집
    print("\n[1/5] DART 공시 수집 중...")
    try:
        dart_api_key = os.environ.get('DART_API_KEY')
        if dart_api_key:
            dart = DartCollector(dart_api_key)
            disclosures = dart.get_overnight_disclosures()

            if not disclosures.empty:
                # 중요 공시 필터링
                important = dart.filter_important_disclosures(disclosures)
                dart_signals = dart.to_signal_format(important)
                all_signals.extend(dart_signals)
                print(f"  - 수집된 공시: {len(disclosures)}건")
                print(f"  - 중요 공시: {len(dart_signals)}건")
            else:
                print("  - 수집된 공시 없음")
        else:
            print("  - DART_API_KEY 환경변수가 설정되지 않음 (건너뜀)")
    except Exception as e:
        print(f"  - DART 수집 오류: {e}")

    # 2. 네이버 뉴스 수집
    print("\n[2/5] 네이버 뉴스 수집 중...")
    try:
        naver = NaverCollector()
        news_list = naver.get_overnight_news()

        if news_list:
            naver_signals = naver.to_signal_format(news_list)
            all_signals.extend(naver_signals)
            print(f"  - 수집된 뉴스: {len(naver_signals)}건")
        else:
            print("  - 수집된 뉴스 없음")
    except Exception as e:
        print(f"  - 네이버 수집 오류: {e}")

    if not all_signals:
        print("\n수집된 시그널이 없습니다. 스캔을 종료합니다.")
        return

    print(f"\n총 수집된 시그널: {len(all_signals)}건")

    # 3. 키워드 점수 계산
    print("\n[3/5] 키워드 점수 계산 중...")
    try:
        scorer = KeywordScorer()
        scored_signals = scorer.score_signals(all_signals)

        # 점수 요약
        summary = scorer.get_summary(scored_signals)
        print(f"  - 호재 시그널: {summary['positive_count']}건")
        print(f"  - 악재 시그널 (제외): {summary['excluded_count']}건")
        print(f"  - 평균 점수: {summary['avg_score']:.2f}")

        if summary['top_keywords']:
            print("  - 주요 키워드:")
            for kw, count in summary['top_keywords'][:5]:
                print(f"    * {kw}: {count}건")
    except Exception as e:
        print(f"  - 점수 계산 오류: {e}")
        scored_signals = all_signals

    # 4. 5가지 전략 필터링 (A/B/C/C+/D)
    print("\n[4/5] 5가지 전략 필터링 중...")
    try:
        stock_filter = StockFilter()
        results = stock_filter.apply_all_strategies(scored_signals)

        strategy_a = results['strategy_a']
        strategy_b = results['strategy_b']
        strategy_c = results['strategy_c']
        strategy_c_plus = results['strategy_c_plus']
        strategy_d = results['strategy_d']

        print(f"\n  [전략 A - 단순 로직]")
        print(f"  선정 종목: {len(strategy_a)}개")
        for i, signal in enumerate(strategy_a[:3], 1):
            print(f"    {i}. {signal.get('corp_name', signal.get('title', 'N/A'))} (점수: {signal.get('score', 0)})")

        print(f"\n  [전략 B - 고급 로직]")
        print(f"  선정 종목: {len(strategy_b)}개")
        for i, signal in enumerate(strategy_b[:3], 1):
            print(f"    {i}. {signal.get('corp_name', signal.get('title', 'N/A'))} (점수: {signal.get('score', 0)})")

        print(f"\n  [전략 C - 기술적 분석]")
        print(f"  선정 종목: {len(strategy_c)}개")
        for i, signal in enumerate(strategy_c[:3], 1):
            rsi = signal.get('rsi', 'N/A')
            foreign_days = signal.get('foreign_consecutive_days', 0)
            print(f"    {i}. {signal.get('corp_name', signal.get('title', 'N/A'))} (점수: {signal.get('score', 0)}, RSI: {rsi}, 외국인: {foreign_days}일)")

        print(f"\n  [전략 C+ - C 강화 (거래량/볼린저)]")
        print(f"  선정 종목: {len(strategy_c_plus)}개")
        for i, signal in enumerate(strategy_c_plus[:3], 1):
            vol_ratio = signal.get('volume_ratio', 'N/A')
            bb_pos = signal.get('bb_position', 'N/A')
            print(f"    {i}. {signal.get('corp_name', signal.get('title', 'N/A'))} (점수: {signal.get('score', 0)}, 거래량: {vol_ratio}%, BB: {bb_pos}%)")

        print(f"\n  [전략 D - BNF/cis 하이브리드]")
        print(f"  선정 종목: {len(strategy_d)}개")
        for i, signal in enumerate(strategy_d[:3], 1):
            divergence = signal.get('ma25_divergence', 'N/A')
            consecutive = signal.get('consecutive_bullish', 0)
            vol_ratio = signal.get('volume_ratio', 'N/A')
            print(f"    {i}. {signal.get('corp_name', signal.get('title', 'N/A'))} (점수: {signal.get('score', 0)}, 괴리율: {divergence}%, 연속양봉: {consecutive}일, 거래량: {vol_ratio}%)")

        # 전략 비교 요약
        print(f"\n  [전략 비교 요약]")
        print(f"  - A: {len(strategy_a)}개 | B: {len(strategy_b)}개 | C: {len(strategy_c)}개")
        print(f"  - C+: {len(strategy_c_plus)}개 | D: {len(strategy_d)}개")

    except Exception as e:
        print(f"  - 필터링 오류: {e}")
        strategy_a = []
        strategy_b = []
        strategy_c = []
        strategy_c_plus = []
        strategy_d = []

    # 5. 결과 저장
    print("\n[5/5] 결과 저장 중...")
    try:
        simulator = Simulator()
        today = datetime.now().strftime('%Y%m%d')

        # 5가지 전략 결과 각각 저장
        if strategy_a:
            simulator.record_signals(strategy_a, 'A', today)
        if strategy_b:
            simulator.record_signals(strategy_b, 'B', today)
        if strategy_c:
            simulator.record_signals(strategy_c, 'C', today)
        if strategy_c_plus:
            simulator.record_signals(strategy_c_plus, 'C+', today)
        if strategy_d:
            simulator.record_signals(strategy_d, 'D', today)

        # 결과 파일 생성
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_dir = os.path.join(base_dir, 'data')
        os.makedirs(output_dir, exist_ok=True)

        # 오늘의 시그널 저장
        today_signals = {
            'date': today,
            'generated_at': datetime.now().isoformat(),
            'summary': {
                'total_collected': len(all_signals),
                'strategy_a_count': len(strategy_a),
                'strategy_b_count': len(strategy_b),
                'strategy_c_count': len(strategy_c),
                'strategy_c_plus_count': len(strategy_c_plus),
                'strategy_d_count': len(strategy_d),
            },
            'strategy_a': strategy_a,
            'strategy_b': strategy_b,
            'strategy_c': strategy_c,
            'strategy_c_plus': strategy_c_plus,
            'strategy_d': strategy_d
        }

        output_path = os.path.join(output_dir, f'signals_{today}.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(today_signals, f, ensure_ascii=False, indent=2, default=str)

        print(f"  - 저장 완료: {output_path}")

    except Exception as e:
        print(f"  - 저장 오류: {e}")

    # 6. 이메일 알림 전송
    print("\n[6/6] 이메일 알림 전송 중...")
    try:
        notifier = EmailNotifier()
        if notifier.is_configured():
            signals_by_strategy = {
                'A': strategy_a,
                'B': strategy_b,
                'C': strategy_c,
                'C+': strategy_c_plus,
                'D': strategy_d
            }

            # 시그널이 하나라도 있으면 이메일 전송
            total_signals = sum(len(v) for v in signals_by_strategy.values())
            if total_signals > 0:
                success = notifier.send_signal_alert(signals_by_strategy, today)
                if success:
                    print(f"  - 이메일 전송 완료: {total_signals}개 시그널")
                else:
                    print("  - 이메일 전송 실패")
            else:
                print("  - 전송할 시그널 없음 (이메일 건너뜀)")
        else:
            print("  - 이메일 설정 미완료 (SMTP_EMAIL, SMTP_PASSWORD, RECIPIENT_EMAIL 환경변수 필요)")
    except Exception as e:
        print(f"  - 이메일 전송 오류: {e}")

    print(f"\n{'=' * 60}")
    print("아침 스캔 완료!")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    run_morning_scan()
