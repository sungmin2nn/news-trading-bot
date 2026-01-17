"""
시뮬레이션 모듈
모의 투자 수익률을 계산하고 추적합니다.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

from ..collectors.price_collector import PriceCollector


class Simulator:
    """모의 투자 시뮬레이터 클래스"""

    def __init__(self, data_path: Optional[str] = None):
        """
        Args:
            data_path: signals.json 파일 경로
        """
        if data_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            data_path = os.path.join(base_dir, 'data', 'signals.json')

        self.data_path = data_path
        self.price_collector = PriceCollector()
        self.signals_history = self._load_signals()

    def _load_signals(self) -> list:
        """저장된 시그널 히스토리를 로드합니다."""
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
        except Exception as e:
            print(f"시그널 히스토리 로드 오류: {e}")
            return []

    def _save_signals(self):
        """시그널 히스토리를 저장합니다."""
        try:
            os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump(self.signals_history, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            print(f"시그널 히스토리 저장 오류: {e}")

    def record_signals(self, signals: list, strategy: str, date: Optional[str] = None):
        """
        시그널을 기록합니다.

        Args:
            signals: 선정된 시그널 리스트
            strategy: 전략 ('A' 또는 'B')
            date: 기록 날짜 (YYYYMMDD)
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')

        record = {
            'date': date,
            'strategy': strategy,
            'signals': signals,
            'recorded_at': datetime.now().isoformat(),
            'status': 'pending'  # pending -> tracked
        }

        self.signals_history.append(record)
        self._save_signals()

    def calculate_return(
        self,
        stock_code: str,
        buy_date: str,
        sell_date: Optional[str] = None,
        buy_price: Optional[float] = None
    ) -> dict:
        """
        종목의 수익률을 계산합니다.

        Args:
            stock_code: 종목 코드
            buy_date: 매수일 (YYYYMMDD)
            sell_date: 매도일 (기본: 당일)
            buy_price: 매수가 (기본: 시가)

        Returns:
            수익률 정보 딕셔너리
        """
        if sell_date is None:
            sell_date = datetime.now().strftime('%Y%m%d')

        try:
            # 매수일 주가
            buy_df = self.price_collector.get_price(stock_code, buy_date, buy_date)
            if buy_df.empty:
                return {'error': '매수일 주가 데이터 없음'}

            # 시가 매수 가정
            if buy_price is None:
                buy_price = float(buy_df.iloc[0]['Open'])

            # 매도일 주가
            sell_df = self.price_collector.get_price(stock_code, sell_date, sell_date)
            if sell_df.empty:
                return {'error': '매도일 주가 데이터 없음'}

            # 종가 매도 가정
            sell_price = float(sell_df.iloc[0]['Close'])

            # 수익률 계산
            returns = ((sell_price - buy_price) / buy_price) * 100

            return {
                'stock_code': stock_code,
                'buy_date': buy_date,
                'sell_date': sell_date,
                'buy_price': buy_price,
                'sell_price': sell_price,
                'returns': round(returns, 2),
                'profit': sell_price - buy_price
            }

        except Exception as e:
            return {'error': str(e)}

    def track_signals(self, date: Optional[str] = None):
        """
        기록된 시그널의 수익률을 추적합니다.

        Args:
            date: 추적할 날짜 (해당 날짜에 기록된 시그널)
        """
        if date is None:
            # 어제 기록된 시그널 추적
            yesterday = datetime.now() - timedelta(days=1)
            date = yesterday.strftime('%Y%m%d')

        updated = False

        for record in self.signals_history:
            if record.get('date') == date and record.get('status') == 'pending':
                signals = record.get('signals', [])
                results = []

                for signal in signals:
                    stock_code = signal.get('stock_code')
                    if stock_code:
                        result = self.calculate_return(
                            stock_code,
                            date,
                            datetime.now().strftime('%Y%m%d')
                        )
                        result['signal'] = signal
                        results.append(result)

                record['results'] = results
                record['status'] = 'tracked'
                record['tracked_at'] = datetime.now().isoformat()

                # 전략별 평균 수익률 계산
                valid_results = [r for r in results if 'returns' in r]
                if valid_results:
                    avg_return = sum(r['returns'] for r in valid_results) / len(valid_results)
                    record['avg_return'] = round(avg_return, 2)

                updated = True

        if updated:
            self._save_signals()

    def get_performance_summary(self, strategy: Optional[str] = None) -> dict:
        """
        전략별 성과 요약을 생성합니다.

        Args:
            strategy: 전략 ('A', 'B', 또는 None=전체)

        Returns:
            성과 요약 딕셔너리
        """
        tracked = [r for r in self.signals_history if r.get('status') == 'tracked']

        if strategy:
            tracked = [r for r in tracked if r.get('strategy') == strategy]

        if not tracked:
            return {
                'total_days': 0,
                'avg_return': 0,
                'win_rate': 0,
                'total_return': 0,
                'best_return': 0,
                'worst_return': 0
            }

        all_returns = []
        for record in tracked:
            for result in record.get('results', []):
                if 'returns' in result:
                    all_returns.append(result['returns'])

        if not all_returns:
            return {
                'total_days': len(tracked),
                'avg_return': 0,
                'win_rate': 0,
                'total_return': 0,
                'best_return': 0,
                'worst_return': 0
            }

        wins = len([r for r in all_returns if r > 0])

        return {
            'total_days': len(tracked),
            'total_trades': len(all_returns),
            'avg_return': round(sum(all_returns) / len(all_returns), 2),
            'win_rate': round((wins / len(all_returns)) * 100, 1),
            'total_return': round(sum(all_returns), 2),
            'best_return': round(max(all_returns), 2),
            'worst_return': round(min(all_returns), 2),
            'strategy': strategy or 'ALL'
        }

    def compare_strategies(self) -> dict:
        """
        A/B 전략 성과를 비교합니다.

        Returns:
            비교 결과 딕셔너리
        """
        a_summary = self.get_performance_summary('A')
        b_summary = self.get_performance_summary('B')

        return {
            'strategy_a': a_summary,
            'strategy_b': b_summary,
            'difference': {
                'avg_return': round(b_summary['avg_return'] - a_summary['avg_return'], 2),
                'win_rate': round(b_summary['win_rate'] - a_summary['win_rate'], 1),
                'total_return': round(b_summary['total_return'] - a_summary['total_return'], 2)
            },
            'winner': 'B' if b_summary['avg_return'] > a_summary['avg_return'] else 'A'
        }

    def get_daily_returns(self, days: int = 30) -> pd.DataFrame:
        """
        일별 수익률 데이터를 생성합니다.

        Args:
            days: 조회 기간 (일)

        Returns:
            일별 수익률 DataFrame
        """
        tracked = [r for r in self.signals_history if r.get('status') == 'tracked']

        # 날짜순 정렬
        tracked = sorted(tracked, key=lambda x: x.get('date', ''))

        # 최근 N일만
        if len(tracked) > days:
            tracked = tracked[-days:]

        data = []
        for record in tracked:
            data.append({
                'date': record.get('date'),
                'strategy': record.get('strategy'),
                'avg_return': record.get('avg_return', 0),
                'trade_count': len(record.get('results', []))
            })

        return pd.DataFrame(data)

    def get_cumulative_returns(self) -> dict:
        """
        누적 수익률을 계산합니다.

        Returns:
            누적 수익률 딕셔너리
        """
        a_returns = []
        b_returns = []

        for record in sorted(self.signals_history, key=lambda x: x.get('date', '')):
            if record.get('status') != 'tracked':
                continue

            avg_return = record.get('avg_return', 0)

            if record.get('strategy') == 'A':
                a_returns.append(avg_return)
            else:
                b_returns.append(avg_return)

        # 누적 수익률 계산 (복리)
        def calculate_cumulative(returns_list):
            cumulative = 100  # 시작 금액
            history = [100]
            for r in returns_list:
                cumulative *= (1 + r / 100)
                history.append(round(cumulative, 2))
            return {
                'final': round(cumulative - 100, 2),
                'history': history
            }

        return {
            'strategy_a': calculate_cumulative(a_returns),
            'strategy_b': calculate_cumulative(b_returns)
        }

    def export_results(self, output_path: Optional[str] = None) -> str:
        """
        결과를 JSON 파일로 내보냅니다.

        Args:
            output_path: 출력 파일 경로

        Returns:
            출력 파일 경로
        """
        if output_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            output_path = os.path.join(base_dir, 'data', 'results.json')

        results = {
            'generated_at': datetime.now().isoformat(),
            'performance': {
                'strategy_a': self.get_performance_summary('A'),
                'strategy_b': self.get_performance_summary('B'),
                'comparison': self.compare_strategies()
            },
            'cumulative_returns': self.get_cumulative_returns(),
            'daily_returns': self.get_daily_returns().to_dict(orient='records')
        }

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        return output_path

    def get_recent_signals(self, days: int = 7) -> list:
        """
        최근 시그널 목록을 가져옵니다.

        Args:
            days: 조회 기간

        Returns:
            최근 시그널 리스트
        """
        cutoff = (datetime.now() - timedelta(days=days)).strftime('%Y%m%d')

        recent = [
            r for r in self.signals_history
            if r.get('date', '') >= cutoff
        ]

        return sorted(recent, key=lambda x: x.get('date', ''), reverse=True)
