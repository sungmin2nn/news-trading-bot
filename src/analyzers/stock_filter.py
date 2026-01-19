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
    """종목 필터링 클래스 (A/B/C/C+/D 전략 지원)"""

    # 기본 필터 설정
    DEFAULT_SETTINGS = {
        # 공통 필터 (A, B, C, C+, D 모두 적용)
        'min_market_cap': 50_000_000_000,       # 최소 시가총액: 500억
        'max_market_cap': 10_000_000_000_000,   # 최대 시가총액: 10조
        'min_avg_volume': 100_000,              # 최소 평균 거래량: 10만주
        'min_score': 1,                         # 최소 키워드 점수

        # B 전략 전용 필터
        'max_price_change_5d': 15.0,            # 5일 수익률 상한: 15%
        'max_52week_high_ratio': 90.0,          # 52주 고가 대비 비율 상한: 90%
        'min_foreign_ratio': 1.0,               # 최소 외국인 보유 비율: 1%
        'min_contract_market_cap_ratio': 0.5,   # 계약금액/시총 비율: 0.5%

        # C 전략 전용 필터 (기술적 분석)
        'max_rsi': 70,                          # RSI 상한 (과매수 제외)
        'min_rsi': 20,                          # RSI 하한 (극단적 과매도 제외)
        'require_golden_cross': True,           # 골든크로스 필수 (5일선 > 20일선)
        'min_foreign_consecutive_days': 3,      # 최소 외국인 연속 순매수일

        # C+ 전략 전용 필터 (C 강화 - 거래량/볼린저 추가)
        'min_volume_ratio': 150,                # 최소 거래량 비율: 5일 평균 대비 150%
        'min_bb_position': 20,                  # 볼린저밴드 최소 위치: 20%
        'max_bb_position': 80,                  # 볼린저밴드 최대 위치: 80%

        # D 전략 전용 필터 (BNF/cis 하이브리드)
        'min_ma25_divergence': -5,              # 25일선 괴리율 하한: -5% (BNF식)
        'max_ma25_divergence': 15,              # 25일선 괴리율 상한: +15% (BNF식)
        'require_bullish_candle': True,         # 양봉 필수 (cis식)
        'd_min_volume_ratio': 120,              # D전략 최소 거래량 비율: 120%

        # E 전략 전용 필터 (Earnings Surprise - 실적 서프라이즈)
        'e_min_score': 3,                       # E전략 최소 점수 (실적 관련 키워드)
        'e_min_volume_ratio': 150,              # E전략 최소 거래량 비율: 150%
        'e_max_rsi': 75,                        # E전략 RSI 상한: 75
        'e_require_earnings_keyword': True,     # 실적 관련 키워드 필수

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

    def apply_strategy_c(self, signals: list) -> list:
        """
        전략 C (기술적 분석 결합) 적용.

        B 전략의 모든 필터 + 기술적 지표 필터:
        - RSI 70 미만 (과매수 제외)
        - 5일선 > 20일선 (상승 추세)
        - 외국인 3일 연속 순매수

        Args:
            signals: 시그널 리스트

        Returns:
            전략 C로 필터링된 시그널 리스트
        """
        # B 전략 필터 먼저 적용
        b_filtered = self.apply_strategy_b(signals)

        filtered = []

        for signal in b_filtered:
            stock_code = signal.get('stock_code')

            if stock_code:
                # 기술적 지표 가져오기
                tech = self.price_collector.get_technical_indicators(stock_code)

                # 1. RSI 필터 (과매수 제외)
                rsi = tech.get('rsi')
                if rsi is not None:
                    if rsi > self.settings.get('max_rsi', 70):
                        continue
                    if rsi < self.settings.get('min_rsi', 20):
                        continue
                    signal['rsi'] = round(rsi, 2)

                # 2. 골든크로스 필터 (상승 추세)
                if self.settings.get('require_golden_cross', True):
                    golden_cross = tech.get('golden_cross')
                    if golden_cross is False:  # None이면 통과
                        continue
                    signal['golden_cross'] = golden_cross
                    signal['ma_trend'] = tech.get('ma_trend')

                # 3. 외국인 연속 순매수 필터
                min_consecutive = self.settings.get('min_foreign_consecutive_days', 3)
                foreign_consecutive = tech.get('foreign_consecutive_days', 0)
                if foreign_consecutive < min_consecutive:
                    continue
                signal['foreign_consecutive_days'] = foreign_consecutive

                # 추가 정보 저장
                signal['ma5'] = tech.get('ma5')
                signal['ma20'] = tech.get('ma20')
                signal['bb_position'] = tech.get('bb_position')

            filtered.append(signal)

        # 점수 + RSI 가중치로 정렬 (RSI 낮을수록 좋음)
        def sort_key(x):
            score = x.get('score', 0)
            rsi = x.get('rsi', 50)
            # 점수는 높을수록, RSI는 낮을수록 좋음
            return (score * 2) - (rsi * 0.1)

        sorted_signals = sorted(filtered, key=sort_key, reverse=True)

        # 최대 종목 수 제한
        max_stocks = self.settings.get('max_stocks', 10)
        result = sorted_signals[:max_stocks]

        # 전략 표시
        for signal in result:
            signal['strategy'] = 'C'

        return result

    def apply_strategy_c_plus(self, signals: list) -> list:
        """
        전략 C+ (C 강화 버전) 적용.

        C 전략의 모든 필터 + 추가 필터:
        - 거래량 5일 평균 대비 150% 이상 (cis식 - 매수세 확인)
        - 볼린저밴드 위치 20~80% (극단 제외)

        Args:
            signals: 시그널 리스트

        Returns:
            전략 C+로 필터링된 시그널 리스트
        """
        # C 전략 필터 먼저 적용
        c_filtered = self.apply_strategy_c(signals)

        filtered = []

        for signal in c_filtered:
            stock_code = signal.get('stock_code')

            if stock_code:
                # 기술적 지표 가져오기 (이미 C에서 가져왔지만 추가 지표 필요)
                tech = self.price_collector.get_technical_indicators(stock_code)

                # 1. 거래량 모멘텀 필터 (cis식)
                volume_ratio = tech.get('volume_ratio')
                min_volume_ratio = self.settings.get('min_volume_ratio', 150)
                if volume_ratio is not None:
                    if volume_ratio < min_volume_ratio:
                        continue
                    signal['volume_ratio'] = volume_ratio
                    signal['volume_surge'] = tech.get('volume_surge', False)

                # 2. 볼린저밴드 위치 필터
                bb_position = signal.get('bb_position') or tech.get('bb_position')
                if bb_position is not None:
                    min_bb = self.settings.get('min_bb_position', 20)
                    max_bb = self.settings.get('max_bb_position', 80)
                    if bb_position < min_bb or bb_position > max_bb:
                        continue
                    signal['bb_position'] = round(bb_position, 2)

            filtered.append(signal)

        # 점수 + 거래량 가중치로 정렬
        def sort_key(x):
            score = x.get('score', 0)
            volume_ratio = x.get('volume_ratio', 100)
            rsi = x.get('rsi', 50)
            # 점수, 거래량 높을수록, RSI 낮을수록 좋음
            return (score * 2) + (volume_ratio * 0.01) - (rsi * 0.05)

        sorted_signals = sorted(filtered, key=sort_key, reverse=True)

        # 최대 종목 수 제한
        max_stocks = self.settings.get('max_stocks', 10)
        result = sorted_signals[:max_stocks]

        # 전략 표시
        for signal in result:
            signal['strategy'] = 'C+'

        return result

    def apply_strategy_d(self, signals: list) -> list:
        """
        전략 D (BNF/cis 하이브리드) 적용.

        B 전략 베이스 + BNF/cis 기법:
        - 25일선 괴리율 -5% ~ +15% (BNF식 - 급락/급등 제외)
        - 전일 양봉 (cis식 - 오르는 주식 매수)
        - 거래량 5일 평균 대비 120% 이상 (cis식)

        Args:
            signals: 시그널 리스트

        Returns:
            전략 D로 필터링된 시그널 리스트
        """
        # B 전략 필터 먼저 적용
        b_filtered = self.apply_strategy_b(signals)

        filtered = []

        for signal in b_filtered:
            stock_code = signal.get('stock_code')

            if stock_code:
                # 기술적 지표 가져오기
                tech = self.price_collector.get_technical_indicators(stock_code)

                # 1. 25일선 괴리율 필터 (BNF식)
                ma25_divergence = tech.get('ma25_divergence')
                if ma25_divergence is not None:
                    min_div = self.settings.get('min_ma25_divergence', -5)
                    max_div = self.settings.get('max_ma25_divergence', 15)
                    if ma25_divergence < min_div or ma25_divergence > max_div:
                        continue
                    signal['ma25'] = tech.get('ma25')
                    signal['ma25_divergence'] = ma25_divergence

                # 2. 양봉 필터 (cis식)
                if self.settings.get('require_bullish_candle', True):
                    is_bullish = tech.get('is_bullish')
                    if is_bullish is False:  # None이면 통과
                        continue
                    signal['is_bullish'] = is_bullish
                    signal['consecutive_bullish'] = tech.get('consecutive_bullish', 0)

                # 3. 거래량 모멘텀 필터 (cis식)
                volume_ratio = tech.get('volume_ratio')
                min_volume = self.settings.get('d_min_volume_ratio', 120)
                if volume_ratio is not None:
                    if volume_ratio < min_volume:
                        continue
                    signal['volume_ratio'] = volume_ratio

                # 추가 정보 저장
                signal['bb_position'] = tech.get('bb_position')
                signal['rsi'] = tech.get('rsi')
                signal['golden_cross'] = tech.get('golden_cross')

            filtered.append(signal)

        # BNF/cis 복합 점수로 정렬
        def sort_key(x):
            score = x.get('score', 0)
            # 괴리율: 0에 가까울수록 좋음 (너무 낮지도 높지도 않은 게 좋음)
            divergence = abs(x.get('ma25_divergence', 0))
            # 연속 양봉 많을수록 좋음 (cis식 모멘텀)
            consecutive = x.get('consecutive_bullish', 0)
            # 거래량 높을수록 좋음
            volume = x.get('volume_ratio', 100)

            return (score * 2) + (consecutive * 0.5) + (volume * 0.01) - (divergence * 0.1)

        sorted_signals = sorted(filtered, key=sort_key, reverse=True)

        # 최대 종목 수 제한
        max_stocks = self.settings.get('max_stocks', 10)
        result = sorted_signals[:max_stocks]

        # 전략 표시
        for signal in result:
            signal['strategy'] = 'D'

        return result

    def apply_strategy_e(self, signals: list) -> list:
        """
        전략 E (Earnings Surprise - 실적 서프라이즈) 적용.

        PEAD(Post-Earnings Announcement Drift) 효과 활용:
        - 실적 관련 호재 키워드 포함
        - 높은 키워드 점수 (실적 서프라이즈 강도)
        - 거래량 급증 (시장 반응)
        - RSI 과매수 아닌 구간

        Args:
            signals: 시그널 리스트

        Returns:
            전략 E로 필터링된 시그널 리스트
        """
        # 실적 관련 키워드
        EARNINGS_KEYWORDS = [
            '실적', '영업이익', '순이익', '매출', '흑자', '전환',
            '어닝', '서프라이즈', '호실적', '최대', '신기록',
            '분기', '반기', '연간', '잠정', '컨센서스', '상회',
            '증가', '성장', '개선', '회복'
        ]

        # 공통 필터 적용
        common_filtered = self.apply_common_filters(signals)

        filtered = []

        for signal in common_filtered:
            stock_code = signal.get('stock_code')
            title = signal.get('title', '').lower()

            # 1. 실적 관련 키워드 체크
            if self.settings.get('e_require_earnings_keyword', True):
                has_earnings_keyword = any(kw in title for kw in EARNINGS_KEYWORDS)
                if not has_earnings_keyword:
                    continue
                signal['has_earnings_keyword'] = True

            # 2. 최소 점수 체크 (실적 공시는 높은 점수 필요)
            min_score = self.settings.get('e_min_score', 3)
            if signal.get('score', 0) < min_score:
                continue

            if stock_code:
                # 기술적 지표 가져오기
                tech = self.price_collector.get_technical_indicators(stock_code)

                # 3. 거래량 급증 필터 (시장 반응 확인)
                volume_ratio = tech.get('volume_ratio')
                min_volume = self.settings.get('e_min_volume_ratio', 150)
                if volume_ratio is not None:
                    if volume_ratio < min_volume:
                        continue
                    signal['volume_ratio'] = volume_ratio

                # 4. RSI 필터 (과매수 제외)
                rsi = tech.get('rsi')
                max_rsi = self.settings.get('e_max_rsi', 75)
                if rsi is not None:
                    if rsi > max_rsi:
                        continue
                    signal['rsi'] = round(rsi, 2)

                # 추가 정보 저장
                signal['bb_position'] = tech.get('bb_position')
                signal['golden_cross'] = tech.get('golden_cross')
                signal['ma25_divergence'] = tech.get('ma25_divergence')

            filtered.append(signal)

        # 점수 + 거래량으로 정렬 (PEAD 강도 반영)
        def sort_key(x):
            score = x.get('score', 0)
            volume_ratio = x.get('volume_ratio', 100)
            # 점수와 거래량 높을수록 PEAD 효과 클 것으로 예상
            return (score * 3) + (volume_ratio * 0.02)

        sorted_signals = sorted(filtered, key=sort_key, reverse=True)

        # 최대 종목 수 제한
        max_stocks = self.settings.get('max_stocks', 10)
        result = sorted_signals[:max_stocks]

        # 전략 표시
        for signal in result:
            signal['strategy'] = 'E'

        return result

    def apply_all_strategies(self, signals: list) -> dict:
        """
        A/B/C/C+/D/E 전략 모두 적용하여 결과를 반환합니다.

        Args:
            signals: 시그널 리스트

        Returns:
            6개 전략 결과 딕셔너리
        """
        return {
            'strategy_a': self.apply_strategy_a(signals),
            'strategy_b': self.apply_strategy_b(signals),
            'strategy_c': self.apply_strategy_c(signals),
            'strategy_c_plus': self.apply_strategy_c_plus(signals),
            'strategy_d': self.apply_strategy_d(signals),
            'strategy_e': self.apply_strategy_e(signals)
        }

    def apply_both_strategies(self, signals: list) -> dict:
        """
        A/B 전략 모두 적용하여 결과를 반환합니다.
        (하위 호환성을 위해 유지)

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
