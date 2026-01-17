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

    # 4. A/B 전략 필터링
    print("\n[4/5] A/B 전략 필터링 중...")
    try:
        stock_filter = StockFilter()
        results = stock_filter.apply_both_strategies(scored_signals)

        strategy_a = results['strategy_a']
        strategy_b = results['strategy_b']

        print(f"\n  [전략 A - 단순 로직]")
        print(f"  선정 종목: {len(strategy_a)}개")
        for i, signal in enumerate(strategy_a[:5], 1):
            print(f"    {i}. {signal.get('corp_name', signal.get('title', 'N/A'))} (점수: {signal.get('score', 0)})")

        print(f"\n  [전략 B - 고급 로직]")
        print(f"  선정 종목: {len(strategy_b)}개")
        for i, signal in enumerate(strategy_b[:5], 1):
            print(f"    {i}. {signal.get('corp_name', signal.get('title', 'N/A'))} (점수: {signal.get('score', 0)})")

        # 전략 비교
        comparison = stock_filter.compare_strategies(strategy_a, strategy_b)
        print(f"\n  [전략 비교]")
        print(f"  - 공통 종목: {comparison['common_count']}개")
        print(f"  - A 전용: {comparison['a_only_count']}개")
        print(f"  - B 전용: {comparison['b_only_count']}개")

    except Exception as e:
        print(f"  - 필터링 오류: {e}")
        strategy_a = []
        strategy_b = []

    # 5. 결과 저장
    print("\n[5/5] 결과 저장 중...")
    try:
        simulator = Simulator()
        today = datetime.now().strftime('%Y%m%d')

        # A/B 전략 결과 각각 저장
        if strategy_a:
            simulator.record_signals(strategy_a, 'A', today)
        if strategy_b:
            simulator.record_signals(strategy_b, 'B', today)

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
            },
            'strategy_a': strategy_a,
            'strategy_b': strategy_b
        }

        output_path = os.path.join(output_dir, f'signals_{today}.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(today_signals, f, ensure_ascii=False, indent=2, default=str)

        print(f"  - 저장 완료: {output_path}")

    except Exception as e:
        print(f"  - 저장 오류: {e}")

    print(f"\n{'=' * 60}")
    print("아침 스캔 완료!")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    run_morning_scan()
