"""
종목 필터링 모듈
A/B 전략에 따라 종목을 필터링합니다.
"""

import os
from typing import Optional

import yaml
import pandas as pd

from ..collectors.price_collector import PriceCollector


class StockFilter:
    """종목 필터링 클래스 (A/B 전략 지원)"""

    # 기본 필터 설정
    DEFAULT_SETTINGS = {
        # 공통 필터 (A, B 모두 적용)
        'min_market_cap': 50_000_000_000,       # 최소 시가총액: 500억
        'max_market_cap': 10_000_000_000_000,   # 최대 시가총액: 10조
        'min_avg_volume': 100_000,              # 최소 평균 거래량: 10만주
        'min_score': 1,                         # 최소 키워드 점수

        # B 전략 전용 필터
        'max_price_change_5d': 15.0,            # 5일 수익률 상한: 15%
        'max_52week_high_ratio': 90.0,          # 52주 고가 대비 비율 상한: 90%
        'min_foreign_ratio': 1.0,               # 최소 외국인 보유 비율: 1%
        'min_contract_market_cap_ratio': 0.5,   # 계약금액/시총 비율: 0.5%

        # 결과 제한
        'max_stocks': 10,                       # 최대 선정 종목 수
    }

    def __init__(self, settings_path: Optional[str] = None):
        """
        Args:
            settings_path: settings.yaml 파일 경로
        """
        self.settings = self._load_settings(settings_path)
        self.price_collector = PriceCollector()

    def _load_settings(self, settings_path: Optional[str]) -> dict:
        """설정을 로드합니다."""
        settings = self.DEFAULT_SETTINGS.copy()

        if settings_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            settings_path = os.path.join(base_dir, 'config', 'settings.yaml')

        try:
            with open(settings_path, 'r', encoding='utf-8') as f:
                file_settings = yaml.safe_load(f)
                if file_settings:
                    settings.update(file_settings)
        except FileNotFoundError:
            pass  # 기본 설정 사용
        except Exception as e:
            print(f"설정 파일 로드 오류: {e}")

        return settings

    def apply_common_filters(self, signals: list) -> list:
        """
        공통 필터를 적용합니다 (A, B 전략 모두).

        필터 조건:
        - 최소 키워드 점수
        - 악재 제외
        - 시가총액 범위
        - 최소 거래량

        Args:
            signals: 점수가 계산된 시그널 리스트

        Returns:
            필터링된 시그널 리스트
        """
        filtered = []

        for signal in signals:
            # 1. 악재 제외
            if signal.get('is_excluded', False):
                continue

            # 2. 최소 점수 체크
            if signal.get('score', 0) < self.settings['min_score']:
                continue

            # 종목 코드가 있는 경우만 주가 정보 체크
            stock_code = signal.get('stock_code')
            if stock_code:
                # 3. 시가총액 체크
                market_cap = self.price_collector.get_market_cap(stock_code)
                if market_cap:
                    if market_cap < self.settings['min_market_cap']:
                        continue
                    if market_cap > self.settings['max_market_cap']:
                        continue
                    signal['market_cap'] = market_cap

                # 4. 거래량 체크
                avg_volume = self.price_collector.get_trading_volume(stock_code)
                if avg_volume:
                    if avg_volume < self.settings['min_avg_volume']:
                        continue
                    signal['avg_volume'] = avg_volume

            filtered.append(signal)

        return filtered

    def apply_strategy_a(self, signals: list) -> list:
        """
        전략 A (단순 로직) 적용.

        필터 조건:
        - 공통 필터만 적용
        - 점수 순 정렬

        Args:
            signals: 시그널 리스트

        Returns:
            전략 A로 필터링된 시그널 리스트
        """
        # 공통 필터 적용
        filtered = self.apply_common_filters(signals)

        # 점수 순 정렬
        sorted_signals = sorted(filtered, key=lambda x: x.get('score', 0), reverse=True)

        # 최대 종목 수 제한
        max_stocks = self.settings.get('max_stocks', 10)

        result = sorted_signals[:max_stocks]

        # 전략 표시
        for signal in result:
            signal['strategy'] = 'A'

        return result

    def apply_strategy_b(self, signals: list) -> list:
        """
        전략 B (고급 로직) 적용.

        추가 필터 조건:
        - 최근 5일 급등주 제외
        - 52주 신고가 근접 종목 제외
        - 외국인 보유 비율 체크
        - (계약 공시의 경우) 계약금액/시총 비율 체크

        Args:
            signals: 시그널 리스트

        Returns:
            전략 B로 필터링된 시그널 리스트
        """
        # 공통 필터 먼저 적용
        common_filtered = self.apply_common_filters(signals)

        filtered = []

        for signal in common_filtered:
            stock_code = signal.get('stock_code')

            if stock_code:
                # 1. 5일 급등주 제외
                price_change = self.price_collector.get_price_change(stock_code, days=5)
                if price_change is not None:
                    if price_change > self.settings['max_price_change_5d']:
                        continue
                    signal['price_change_5d'] = price_change

                # 2. 52주 신고가 근접 제외
                high_52week = self.price_collector.get_52week_high(stock_code)
                current_price = self.price_collector.get_today_close_price(stock_code)

                if high_52week and current_price:
                    ratio = (current_price / high_52week) * 100
                    if ratio > self.settings['max_52week_high_ratio']:
                        continue
                    signal['high_52week_ratio'] = ratio

                # 3. 외국인 보유 비율 체크
                foreign_ratio = self.price_collector.get_foreign_holding(stock_code)
                if foreign_ratio is not None:
                    if foreign_ratio < self.settings['min_foreign_ratio']:
                        continue
                    signal['foreign_ratio'] = foreign_ratio

            filtered.append(signal)

        # 점수 순 정렬
        sorted_signals = sorted(filtered, key=lambda x: x.get('score', 0), reverse=True)

        # 최대 종목 수 제한
        max_stocks = self.settings.get('max_stocks', 10)

        result = sorted_signals[:max_stocks]

        # 전략 표시
        for signal in result:
            signal['strategy'] = 'B'

        return result

    def apply_both_strategies(self, signals: list) -> dict:
        """
        A/B 전략 모두 적용하여 결과를 반환합니다.

        Args:
            signals: 시그널 리스트

        Returns:
            {'strategy_a': [...], 'strategy_b': [...]} 형태의 딕셔너리
        """
        return {
            'strategy_a': self.apply_strategy_a(signals),
            'strategy_b': self.apply_strategy_b(signals)
        }

    def get_stock_details(self, stock_code: str) -> dict:
        """
        종목의 상세 정보를 수집합니다.

        Args:
            stock_code: 종목 코드

        Returns:
            종목 상세 정보 딕셔너리
        """
        return self.price_collector.get_stock_info(stock_code)

    def enrich_signals(self, signals: list) -> list:
        """
        시그널에 주가 정보를 추가합니다.

        Args:
            signals: 시그널 리스트

        Returns:
            주가 정보가 추가된 시그널 리스트
        """
        enriched = []

        for signal in signals:
            stock_code = signal.get('stock_code')

            if stock_code:
                stock_info = self.get_stock_details(stock_code)
                signal.update(stock_info)

            enriched.append(signal)

        return enriched

    def to_dataframe(self, signals: list) -> pd.DataFrame:
        """
        시그널 리스트를 DataFrame으로 변환합니다.

        Args:
            signals: 시그널 리스트

        Returns:
            DataFrame
        """
        if not signals:
            return pd.DataFrame()

        return pd.DataFrame(signals)

    def compare_strategies(self, strategy_a: list, strategy_b: list) -> dict:
        """
        A/B 전략 결과를 비교합니다.

        Args:
            strategy_a: 전략 A 결과
            strategy_b: 전략 B 결과

        Returns:
            비교 결과 딕셔너리
        """
        a_codes = set(s.get('stock_code') for s in strategy_a if s.get('stock_code'))
        b_codes = set(s.get('stock_code') for s in strategy_b if s.get('stock_code'))

        return {
            'strategy_a_count': len(strategy_a),
            'strategy_b_count': len(strategy_b),
            'common_count': len(a_codes & b_codes),
            'a_only_count': len(a_codes - b_codes),
            'b_only_count': len(b_codes - a_codes),
            'common_stocks': list(a_codes & b_codes),
            'a_only_stocks': list(a_codes - b_codes),
            'b_only_stocks': list(b_codes - a_codes),
            'strategy_a_avg_score': sum(s.get('score', 0) for s in strategy_a) / len(strategy_a) if strategy_a else 0,
            'strategy_b_avg_score': sum(s.get('score', 0) for s in strategy_b) / len(strategy_b) if strategy_b else 0,
        }
