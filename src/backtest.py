"""
백테스트 스크립트
과거 30일간의 DART 공시를 수집하여 전략별 성과를 시뮬레이션합니다.
"""

import json
import os
import sys
from datetime import datetime, timedelta
import time

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.collectors.dart_collector import DartCollector
from src.analyzers.keyword_scorer import KeywordScorer
from src.analyzers.stock_filter import StockFilter
from src.collectors.price_collector import PriceCollector

# 거래 비용 설정
TRADING_COSTS = {
    'buy_commission': 0.015,
    'buy_slippage': 0.1,
    'sell_commission': 0.015,
    'sell_slippage': 0.1,
    'sell_tax': 0.23,
}


def get_trading_days(start_date: datetime, end_date: datetime) -> list:
    """주말을 제외한 거래일 목록을 반환합니다."""
    trading_days = []
    current = start_date
    while current <= end_date:
        # 월~금만 (0=월, 4=금)
        if current.weekday() < 5:
            trading_days.append(current.strftime('%Y%m%d'))
        current += timedelta(days=1)
    return trading_days


def calculate_return_with_costs(buy_price: float, sell_price: float) -> dict:
    """거래 비용을 반영한 수익률을 계산합니다."""
    if buy_price <= 0:
        return {'gross_returns': 0, 'returns': 0, 'trading_costs': 0}

    gross_returns = ((sell_price - buy_price) / buy_price) * 100

    buy_cost = TRADING_COSTS['buy_commission'] + TRADING_COSTS['buy_slippage']
    sell_cost = TRADING_COSTS['sell_commission'] + TRADING_COSTS['sell_slippage'] + TRADING_COSTS['sell_tax']
    total_cost = buy_cost + sell_cost

    net_returns = gross_returns - total_cost

    return {
        'gross_returns': round(gross_returns, 2),
        'returns': round(net_returns, 2),
        'trading_costs': round(total_cost, 3)
    }


def run_backtest(days: int = 30):
    """백테스트를 실행합니다."""
    print(f"=" * 60)
    print(f"뉴스 트레이딩 봇 - 백테스트 ({days}일)")
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=" * 60)

    # 환경변수 확인
    dart_api_key = os.environ.get('DART_API_KEY')
    if not dart_api_key:
        print("오류: DART_API_KEY 환경변수가 설정되지 않았습니다.")
        return

    # 컬렉터/분석기 초기화
    dart = DartCollector(dart_api_key)
    scorer = KeywordScorer()
    stock_filter = StockFilter()
    price_collector = PriceCollector()

    # 거래일 목록 생성
    end_date = datetime.now() - timedelta(days=1)  # 어제까지
    start_date = end_date - timedelta(days=days + 10)  # 여유있게
    trading_days = get_trading_days(start_date, end_date)[-days:]

    print(f"\n분석 기간: {trading_days[0]} ~ {trading_days[-1]}")
    print(f"총 거래일: {len(trading_days)}일")

    # 결과 저장용
    all_signals = []

    # 각 거래일별로 처리
    for i, date in enumerate(trading_days):
        print(f"\n[{i+1}/{len(trading_days)}] {date} 처리 중...")

        try:
            # 전날 장 마감 후 ~ 당일 장 시작 전 공시 수집
            # 해당 날짜의 공시 조회
            disclosures = dart.get_disclosures(date, date)

            if disclosures.empty:
                print(f"  - 공시 없음")
                continue

            # 중요 공시 필터링
            important = dart.filter_important_disclosures(disclosures)
            if important.empty:
                print(f"  - 중요 공시 없음 (전체: {len(disclosures)}건)")
                continue

            signals = dart.to_signal_format(important)
            print(f"  - 중요 공시: {len(signals)}건")

            # 키워드 점수 계산
            scored_signals = scorer.score_signals(signals)

            # 5가지 전략 필터링
            results = stock_filter.apply_all_strategies(scored_signals)

            # 각 전략별 결과 처리
            for strategy_name, strategy_key in [
                ('A', 'strategy_a'),
                ('B', 'strategy_b'),
                ('C', 'strategy_c'),
                ('C+', 'strategy_c_plus'),
                ('D', 'strategy_d')
            ]:
                strategy_signals = results[strategy_key]

                if not strategy_signals:
                    continue

                # 다음 거래일 찾기 (매도일)
                date_idx = trading_days.index(date)
                if date_idx >= len(trading_days) - 1:
                    continue  # 마지막 날은 매도 불가

                sell_date = trading_days[date_idx + 1]

                # 각 종목별 수익률 계산
                trade_results = []
                for signal in strategy_signals:
                    stock_code = signal.get('stock_code')
                    if not stock_code:
                        continue

                    try:
                        # 매수일 시가
                        buy_df = price_collector.get_price(stock_code, date, date)
                        if buy_df.empty:
                            continue

                        # 매도일 종가
                        sell_df = price_collector.get_price(stock_code, sell_date, sell_date)
                        if sell_df.empty:
                            continue

                        buy_price = float(buy_df.iloc[0]['Open'])
                        sell_price = float(sell_df.iloc[0]['Close'])

                        returns_info = calculate_return_with_costs(buy_price, sell_price)

                        trade_results.append({
                            'stock_code': stock_code,
                            'buy_date': date,
                            'sell_date': sell_date,
                            'buy_price': buy_price,
                            'sell_price': sell_price,
                            'gross_returns': returns_info['gross_returns'],
                            'returns': returns_info['returns'],
                            'trading_costs': returns_info['trading_costs'],
                            'costs_applied': True,
                            'signal': signal
                        })

                    except Exception as e:
                        print(f"    - {stock_code} 오류: {e}")
                        continue

                if trade_results:
                    avg_return = sum(r['returns'] for r in trade_results) / len(trade_results)

                    record = {
                        'date': date,
                        'strategy': strategy_name,
                        'signals': strategy_signals,
                        'recorded_at': datetime.now().isoformat(),
                        'status': 'tracked',
                        'results': trade_results,
                        'tracked_at': datetime.now().isoformat(),
                        'avg_return': round(avg_return, 2)
                    }

                    all_signals.append(record)
                    print(f"  - 전략 {strategy_name}: {len(trade_results)}건, 평균 수익률: {avg_return:.2f}%")

            # API 호출 제한을 위한 딜레이
            time.sleep(0.5)

        except Exception as e:
            print(f"  - 오류: {e}")
            continue

    # 결과 저장
    print(f"\n{'=' * 60}")
    print("결과 저장 중...")

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    os.makedirs(data_dir, exist_ok=True)

    # signals.json에 저장 (기존 데이터와 병합)
    signals_path = os.path.join(data_dir, 'signals.json')

    # 기존 데이터 로드
    existing_signals = []
    try:
        with open(signals_path, 'r', encoding='utf-8') as f:
            existing_signals = json.load(f)
    except FileNotFoundError:
        pass

    # 백테스트 데이터와 병합 (중복 제거)
    existing_keys = set()
    for s in existing_signals:
        key = f"{s.get('date')}_{s.get('strategy')}"
        existing_keys.add(key)

    for s in all_signals:
        key = f"{s.get('date')}_{s.get('strategy')}"
        if key not in existing_keys:
            existing_signals.append(s)

    # 날짜순 정렬
    existing_signals.sort(key=lambda x: (x.get('date', ''), x.get('strategy', '')))

    with open(signals_path, 'w', encoding='utf-8') as f:
        json.dump(existing_signals, f, ensure_ascii=False, indent=2, default=str)

    print(f"  - signals.json 저장 완료: {len(existing_signals)}건")

    # 성과 요약 계산
    print(f"\n{'=' * 60}")
    print("전략별 성과 요약")
    print(f"{'=' * 60}")

    for strategy in ['A', 'B', 'C', 'C+', 'D']:
        strategy_records = [s for s in all_signals if s.get('strategy') == strategy]

        all_returns = []
        for record in strategy_records:
            for result in record.get('results', []):
                if 'returns' in result:
                    all_returns.append(result['returns'])

        if all_returns:
            wins = len([r for r in all_returns if r > 0])
            avg_return = sum(all_returns) / len(all_returns)
            win_rate = (wins / len(all_returns)) * 100

            print(f"\n[전략 {strategy}]")
            print(f"  - 거래 횟수: {len(all_returns)}건")
            print(f"  - 평균 수익률: {avg_return:.2f}%")
            print(f"  - 승률: {win_rate:.1f}%")
            print(f"  - 총 수익률: {sum(all_returns):.2f}%")
        else:
            print(f"\n[전략 {strategy}]")
            print(f"  - 거래 없음")

    # 대시보드 데이터 업데이트
    print(f"\n{'=' * 60}")
    print("대시보드 데이터 업데이트 중...")

    try:
        from src.analyzers.simulator import Simulator
        simulator = Simulator()
        simulator.signals_history = existing_signals

        # 대시보드 데이터 생성
        comparison = simulator.compare_strategies()
        cumulative = simulator.get_cumulative_returns()
        daily_returns = simulator.get_daily_returns(days=30)
        recent_signals = simulator.get_recent_signals(days=30)

        dashboard_data = {
            'updated_at': datetime.now().isoformat(),
            'performance': comparison,
            'cumulative_returns': cumulative,
            'daily_returns': daily_returns.to_dict(orient='records'),
            'recent_signals': recent_signals
        }

        # docs 폴더에 저장
        docs_dir = os.path.join(base_dir, 'docs')
        os.makedirs(docs_dir, exist_ok=True)

        dashboard_path = os.path.join(docs_dir, 'dashboard_data.json')
        with open(dashboard_path, 'w', encoding='utf-8') as f:
            json.dump(dashboard_data, f, ensure_ascii=False, indent=2, default=str)

        print(f"  - dashboard_data.json 업데이트 완료")

    except Exception as e:
        print(f"  - 대시보드 업데이트 오류: {e}")

    print(f"\n{'=' * 60}")
    print("백테스트 완료!")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='뉴스 트레이딩 봇 백테스트')
    parser.add_argument('--days', type=int, default=30, help='백테스트 기간 (일)')

    args = parser.parse_args()
    run_backtest(days=args.days)
