"""
저녁 추적 메인 스크립트
장 마감 후(15:40) 당일 시그널의 수익률을 추적하고 대시보드를 업데이트합니다.
"""

import json
import os
import sys
from datetime import datetime, timedelta

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analyzers.simulator import Simulator


def run_evening_track():
    """저녁 추적을 실행합니다."""
    print(f"=" * 60)
    print(f"뉴스 트레이딩 봇 - 저녁 추적")
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=" * 60)

    simulator = Simulator()

    # 1. 오늘 시그널 수익률 추적
    print("\n[1/4] 오늘 시그널 수익률 추적 중...")
    try:
        today = datetime.now().strftime('%Y%m%d')
        simulator.track_signals(today)
        print(f"  - 추적 완료: {today}")
    except Exception as e:
        print(f"  - 추적 오류: {e}")

    # 2. 성과 요약 (5가지 전략)
    print("\n[2/4] 성과 분석 중...")
    try:
        comparison = simulator.compare_strategies()

        # 전략별 요약 출력 함수
        def print_strategy_summary(name, summary):
            print(f"\n  [{name}]")
            print(f"  - 총 거래일: {summary['total_days']}일 | 총 거래수: {summary.get('total_trades', 0)}건")
            print(f"  - 평균 수익률: {summary['avg_return']:.2f}% | 승률: {summary['win_rate']:.1f}%")
            print(f"  - 누적 수익률: {summary['total_return']:.2f}%")
            print(f"  - 최고/최저: {summary['best_return']:.2f}% / {summary['worst_return']:.2f}%")

        print_strategy_summary("전략 A - 단순 로직", comparison['strategy_a'])
        print_strategy_summary("전략 B - 고급 로직", comparison['strategy_b'])
        print_strategy_summary("전략 C - 기술적 분석", comparison['strategy_c'])
        print_strategy_summary("전략 C+ - C 강화", comparison['strategy_c_plus'])
        print_strategy_summary("전략 D - BNF/cis", comparison['strategy_d'])

        print(f"\n  [전략 비교 요약]")
        winner = comparison['winner']
        print(f"  - 현재 최고 성과 전략: {winner}")

        # 전략별 평균 수익률 비교
        strategies = {
            'A': comparison['strategy_a']['avg_return'],
            'B': comparison['strategy_b']['avg_return'],
            'C': comparison['strategy_c']['avg_return'],
            'C+': comparison['strategy_c_plus']['avg_return'],
            'D': comparison['strategy_d']['avg_return']
        }
        sorted_strategies = sorted(strategies.items(), key=lambda x: x[1], reverse=True)
        print(f"  - 평균 수익률 순위: ", end="")
        print(" > ".join([f"{k}({v:.2f}%)" for k, v in sorted_strategies]))

    except Exception as e:
        print(f"  - 성과 분석 오류: {e}")

    # 3. 결과 파일 저장
    print("\n[3/4] 결과 저장 중...")
    try:
        output_path = simulator.export_results()
        print(f"  - 저장 완료: {output_path}")
    except Exception as e:
        print(f"  - 저장 오류: {e}")

    # 4. 대시보드 업데이트
    print("\n[4/4] 대시보드 업데이트 중...")
    try:
        update_dashboard(simulator)
        print("  - 대시보드 업데이트 완료")
    except Exception as e:
        print(f"  - 대시보드 업데이트 오류: {e}")

    print(f"\n{'=' * 60}")
    print("저녁 추적 완료!")
    print(f"{'=' * 60}")


def update_dashboard(simulator: Simulator):
    """대시보드 데이터를 업데이트합니다."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, 'docs')
    os.makedirs(docs_dir, exist_ok=True)

    # 대시보드 데이터 생성 (5가지 전략)
    comparison = simulator.compare_strategies()
    cumulative = simulator.get_cumulative_returns()
    daily_returns = simulator.get_daily_returns(30)
    recent_signals = simulator.get_recent_signals(7)

    dashboard_data = {
        'updated_at': datetime.now().isoformat(),
        'performance': {
            'strategy_a': comparison['strategy_a'],
            'strategy_b': comparison['strategy_b'],
            'strategy_c': comparison['strategy_c'],
            'strategy_c_plus': comparison['strategy_c_plus'],
            'strategy_d': comparison['strategy_d'],
            'winner': comparison['winner']
        },
        'cumulative_returns': cumulative,
        'daily_returns': daily_returns.to_dict(orient='records') if not daily_returns.empty else [],
        'recent_signals': recent_signals
    }

    # JSON 데이터 저장
    data_path = os.path.join(docs_dir, 'dashboard_data.json')
    with open(data_path, 'w', encoding='utf-8') as f:
        json.dump(dashboard_data, f, ensure_ascii=False, indent=2, default=str)

    print(f"  - 데이터 저장: {data_path}")


if __name__ == '__main__':
    run_evening_track()
