"""
주가 데이터 수집 모듈
pykrx와 FinanceDataReader를 사용하여 주가 및 시장 데이터를 수집합니다.
"""

from datetime import datetime, timedelta
from typing import Optional, Union

import pandas as pd

try:
    from pykrx import stock as pykrx_stock
except ImportError:
    pykrx_stock = None

try:
    import FinanceDataReader as fdr
except ImportError:
    fdr = None


class PriceCollector:
    """주가 데이터 수집 클래스"""

    def __init__(self):
        """PriceCollector 초기화"""
        if pykrx_stock is None and fdr is None:
            raise ImportError("pykrx 또는 FinanceDataReader가 필요합니다.")

    def get_stock_list(self, market: str = 'ALL') -> pd.DataFrame:
        """
        상장 종목 목록을 가져옵니다.

        Args:
            market: 시장 구분 ('KOSPI', 'KOSDAQ', 'ALL')

        Returns:
            종목 목록 DataFrame
        """
        try:
            if fdr:
                if market == 'ALL':
                    kospi = fdr.StockListing('KOSPI')
                    kosdaq = fdr.StockListing('KOSDAQ')
                    return pd.concat([kospi, kosdaq], ignore_index=True)
                else:
                    return fdr.StockListing(market)

            elif pykrx_stock:
                today = datetime.now().strftime('%Y%m%d')
                if market == 'ALL':
                    tickers = pykrx_stock.get_market_ticker_list(today, market='ALL')
                else:
                    tickers = pykrx_stock.get_market_ticker_list(today, market=market)

                stocks = []
                for ticker in tickers:
                    name = pykrx_stock.get_market_ticker_name(ticker)
                    stocks.append({'Code': ticker, 'Name': name})

                return pd.DataFrame(stocks)

        except Exception as e:
            print(f"종목 목록 조회 오류: {e}")
            return pd.DataFrame()

    def get_price(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        종목의 주가 데이터를 가져옵니다.

        Args:
            stock_code: 종목 코드
            start_date: 시작일 (YYYYMMDD 또는 YYYY-MM-DD)
            end_date: 종료일

        Returns:
            주가 DataFrame (시가, 고가, 저가, 종가, 거래량)
        """
        today = datetime.now()

        if end_date is None:
            end_date = today.strftime('%Y%m%d')
        if start_date is None:
            start_date = (today - timedelta(days=30)).strftime('%Y%m%d')

        # 날짜 형식 통일
        start_date = start_date.replace('-', '')
        end_date = end_date.replace('-', '')

        try:
            if pykrx_stock:
                df = pykrx_stock.get_market_ohlcv_by_date(start_date, end_date, stock_code)
                if not df.empty:
                    # pykrx 버전에 따라 컬럼 수가 다름 (5개 또는 6개)
                    if len(df.columns) == 6:
                        df.columns = ['Open', 'High', 'Low', 'Close', 'Volume', 'Change']
                    elif len(df.columns) == 5:
                        df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                return df

            elif fdr:
                start_fmt = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:]}"
                end_fmt = f"{end_date[:4]}-{end_date[4:6]}-{end_date[6:]}"
                return fdr.DataReader(stock_code, start_fmt, end_fmt)

        except Exception as e:
            print(f"주가 조회 오류 ({stock_code}): {e}")
            return pd.DataFrame()

    def get_market_cap(self, stock_code: str, date: Optional[str] = None) -> Optional[int]:
        """
        종목의 시가총액을 가져옵니다.

        Args:
            stock_code: 종목 코드
            date: 조회일 (YYYYMMDD)

        Returns:
            시가총액 (원)
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')

        try:
            if pykrx_stock:
                df = pykrx_stock.get_market_cap_by_date(date, date, stock_code)
                if not df.empty:
                    return int(df.iloc[0]['시가총액'])

        except Exception as e:
            print(f"시가총액 조회 오류 ({stock_code}): {e}")

        return None

    def get_market_cap_all(self, date: Optional[str] = None, market: str = 'ALL') -> pd.DataFrame:
        """
        전체 종목의 시가총액을 가져옵니다.

        Args:
            date: 조회일 (YYYYMMDD)
            market: 시장 구분

        Returns:
            시가총액 DataFrame
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')

        try:
            if pykrx_stock:
                df = pykrx_stock.get_market_cap_by_ticker(date, market=market)
                return df

        except Exception as e:
            print(f"전체 시가총액 조회 오류: {e}")
            return pd.DataFrame()

    def get_trading_volume(self, stock_code: str, days: int = 20) -> Optional[float]:
        """
        종목의 평균 거래량을 계산합니다.

        Args:
            stock_code: 종목 코드
            days: 평균 계산 기간 (일)

        Returns:
            평균 거래량
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days * 2)  # 휴장일 고려

        try:
            df = self.get_price(
                stock_code,
                start_date.strftime('%Y%m%d'),
                end_date.strftime('%Y%m%d')
            )

            if not df.empty and 'Volume' in df.columns:
                return df['Volume'].tail(days).mean()

        except Exception as e:
            print(f"거래량 조회 오류 ({stock_code}): {e}")

        return None

    def get_price_change(self, stock_code: str, days: int = 5) -> Optional[float]:
        """
        종목의 기간 수익률을 계산합니다.

        Args:
            stock_code: 종목 코드
            days: 기간 (일)

        Returns:
            수익률 (%)
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days * 2)

        try:
            df = self.get_price(
                stock_code,
                start_date.strftime('%Y%m%d'),
                end_date.strftime('%Y%m%d')
            )

            if not df.empty and 'Close' in df.columns and len(df) >= 2:
                df = df.tail(days + 1)
                if len(df) >= 2:
                    start_price = df.iloc[0]['Close']
                    end_price = df.iloc[-1]['Close']
                    return ((end_price - start_price) / start_price) * 100

        except Exception as e:
            print(f"수익률 계산 오류 ({stock_code}): {e}")

        return None

    def get_52week_high(self, stock_code: str) -> Optional[float]:
        """
        종목의 52주 최고가를 가져옵니다.

        Args:
            stock_code: 종목 코드

        Returns:
            52주 최고가
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)

        try:
            df = self.get_price(
                stock_code,
                start_date.strftime('%Y%m%d'),
                end_date.strftime('%Y%m%d')
            )

            if not df.empty and 'High' in df.columns:
                return float(df['High'].max())

        except Exception as e:
            print(f"52주 최고가 조회 오류 ({stock_code}): {e}")

        return None

    def get_investor_trading(
        self,
        stock_code: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        투자자별 매매동향을 가져옵니다.

        Args:
            stock_code: 종목 코드
            start_date: 시작일
            end_date: 종료일

        Returns:
            투자자별 매매동향 DataFrame
        """
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')

        try:
            if pykrx_stock:
                df = pykrx_stock.get_market_trading_value_by_date(
                    start_date, end_date, stock_code
                )
                return df

        except Exception as e:
            print(f"투자자별 매매동향 조회 오류 ({stock_code}): {e}")
            return pd.DataFrame()

    def get_foreign_holding(self, stock_code: str, date: Optional[str] = None) -> Optional[float]:
        """
        외국인 보유 비율을 가져옵니다.

        Args:
            stock_code: 종목 코드
            date: 조회일

        Returns:
            외국인 보유 비율 (%)
        """
        if date is None:
            date = datetime.now().strftime('%Y%m%d')

        try:
            if pykrx_stock:
                df = pykrx_stock.get_exhaustion_rates_by_ticker(date)
                if stock_code in df.index:
                    return float(df.loc[stock_code, '외국인보유비율'])

        except Exception as e:
            print(f"외국인 보유비율 조회 오류 ({stock_code}): {e}")

        return None

    def get_today_open_price(self, stock_code: str) -> Optional[float]:
        """
        당일 시가를 가져옵니다.

        Args:
            stock_code: 종목 코드

        Returns:
            시가
        """
        today = datetime.now().strftime('%Y%m%d')

        try:
            df = self.get_price(stock_code, today, today)
            if not df.empty and 'Open' in df.columns:
                return float(df.iloc[0]['Open'])

        except Exception as e:
            print(f"시가 조회 오류 ({stock_code}): {e}")

        return None

    def get_today_close_price(self, stock_code: str) -> Optional[float]:
        """
        당일 종가를 가져옵니다.

        Args:
            stock_code: 종목 코드

        Returns:
            종가
        """
        today = datetime.now().strftime('%Y%m%d')

        try:
            df = self.get_price(stock_code, today, today)
            if not df.empty and 'Close' in df.columns:
                return float(df.iloc[0]['Close'])

        except Exception as e:
            print(f"종가 조회 오류 ({stock_code}): {e}")

        return None

    def get_rsi(self, stock_code: str, period: int = 14) -> Optional[float]:
        """
        RSI (상대강도지수)를 계산합니다.

        Args:
            stock_code: 종목 코드
            period: RSI 계산 기간 (기본 14일)

        Returns:
            RSI 값 (0~100)
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period * 3)  # 충분한 데이터 확보

        try:
            df = self.get_price(
                stock_code,
                start_date.strftime('%Y%m%d'),
                end_date.strftime('%Y%m%d')
            )

            if df.empty or 'Close' not in df.columns or len(df) < period + 1:
                return None

            # 가격 변화 계산
            delta = df['Close'].diff()

            # 상승/하락 분리
            gain = delta.where(delta > 0, 0)
            loss = (-delta).where(delta < 0, 0)

            # 평균 상승/하락 계산 (EMA 방식)
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()

            # RS 및 RSI 계산
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

            return float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None

        except Exception as e:
            print(f"RSI 계산 오류 ({stock_code}): {e}")
            return None

    def get_moving_averages(self, stock_code: str) -> dict:
        """
        이동평균선을 계산합니다.

        Args:
            stock_code: 종목 코드

        Returns:
            이동평균 정보 딕셔너리
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)  # 충분한 데이터 확보

        try:
            df = self.get_price(
                stock_code,
                start_date.strftime('%Y%m%d'),
                end_date.strftime('%Y%m%d')
            )

            if df.empty or 'Close' not in df.columns:
                return {'ma5': None, 'ma20': None, 'ma_trend': None, 'golden_cross': None}

            close = df['Close']
            current_price = float(close.iloc[-1])

            # 이동평균 계산
            ma5 = float(close.rolling(window=5).mean().iloc[-1]) if len(close) >= 5 else None
            ma20 = float(close.rolling(window=20).mean().iloc[-1]) if len(close) >= 20 else None

            # 추세 판단
            ma_trend = None
            golden_cross = None

            if ma5 and ma20:
                if ma5 > ma20:
                    ma_trend = 'uptrend'  # 상승 추세
                    golden_cross = True
                else:
                    ma_trend = 'downtrend'  # 하락 추세
                    golden_cross = False

            return {
                'current_price': current_price,
                'ma5': ma5,
                'ma20': ma20,
                'ma_trend': ma_trend,
                'golden_cross': golden_cross  # 5일선 > 20일선
            }

        except Exception as e:
            print(f"이동평균 계산 오류 ({stock_code}): {e}")
            return {'ma5': None, 'ma20': None, 'ma_trend': None, 'golden_cross': None}

    def get_foreign_consecutive_buy_days(self, stock_code: str, days: int = 10) -> int:
        """
        외국인 연속 순매수 일수를 계산합니다.

        Args:
            stock_code: 종목 코드
            days: 조회 기간

        Returns:
            연속 순매수 일수 (음수면 연속 순매도)
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days * 2)

        try:
            df = self.get_investor_trading(
                stock_code,
                start_date.strftime('%Y%m%d'),
                end_date.strftime('%Y%m%d')
            )

            if df.empty:
                return 0

            # 외국인 순매수 컬럼 확인
            foreign_col = None
            for col in df.columns:
                if '외국인' in str(col):
                    foreign_col = col
                    break

            if foreign_col is None:
                return 0

            # 최근 데이터부터 연속 순매수/순매도 일수 계산
            foreign_data = df[foreign_col].tail(days)
            consecutive = 0

            if len(foreign_data) == 0:
                return 0

            # 가장 최근 날의 방향 확인
            last_value = foreign_data.iloc[-1]
            if last_value > 0:
                direction = 1  # 순매수
            elif last_value < 0:
                direction = -1  # 순매도
            else:
                return 0

            # 연속 일수 계산
            for value in reversed(foreign_data.values):
                if direction == 1 and value > 0:
                    consecutive += 1
                elif direction == -1 and value < 0:
                    consecutive -= 1
                else:
                    break

            return consecutive

        except Exception as e:
            print(f"외국인 연속 매수일 계산 오류 ({stock_code}): {e}")
            return 0

    def get_bollinger_bands(self, stock_code: str, period: int = 20, std_dev: float = 2.0) -> dict:
        """
        볼린저 밴드를 계산합니다.

        Args:
            stock_code: 종목 코드
            period: 이동평균 기간
            std_dev: 표준편차 배수

        Returns:
            볼린저 밴드 정보 딕셔너리
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period * 3)

        try:
            df = self.get_price(
                stock_code,
                start_date.strftime('%Y%m%d'),
                end_date.strftime('%Y%m%d')
            )

            if df.empty or 'Close' not in df.columns or len(df) < period:
                return {'upper': None, 'middle': None, 'lower': None, 'position': None}

            close = df['Close']
            current_price = float(close.iloc[-1])

            # 볼린저 밴드 계산
            middle = close.rolling(window=period).mean()
            std = close.rolling(window=period).std()

            upper = middle + (std * std_dev)
            lower = middle - (std * std_dev)

            upper_val = float(upper.iloc[-1])
            middle_val = float(middle.iloc[-1])
            lower_val = float(lower.iloc[-1])

            # 현재 위치 (0~100, 0=하단, 100=상단)
            if upper_val != lower_val:
                position = ((current_price - lower_val) / (upper_val - lower_val)) * 100
            else:
                position = 50

            return {
                'upper': upper_val,
                'middle': middle_val,
                'lower': lower_val,
                'current_price': current_price,
                'position': position  # 0에 가까우면 하단, 100에 가까우면 상단
            }

        except Exception as e:
            print(f"볼린저 밴드 계산 오류 ({stock_code}): {e}")
            return {'upper': None, 'middle': None, 'lower': None, 'position': None}

    def get_stock_info(self, stock_code: str) -> dict:
        """
        종목의 종합 정보를 수집합니다.

        Args:
            stock_code: 종목 코드

        Returns:
            종목 정보 딕셔너리
        """
        info = {
            'stock_code': stock_code,
            'market_cap': self.get_market_cap(stock_code),
            'avg_volume': self.get_trading_volume(stock_code),
            'price_change_5d': self.get_price_change(stock_code, 5),
            'price_change_20d': self.get_price_change(stock_code, 20),
            'high_52week': self.get_52week_high(stock_code),
            'foreign_ratio': self.get_foreign_holding(stock_code),
        }

        # 현재가 대비 52주 고가 비율
        today_price = self.get_today_close_price(stock_code)
        if today_price and info['high_52week']:
            info['high_52week_ratio'] = (today_price / info['high_52week']) * 100
        else:
            info['high_52week_ratio'] = None

        return info

    def get_volume_momentum(self, stock_code: str, days: int = 5) -> dict:
        """
        거래량 모멘텀을 계산합니다. (cis식 분석)

        Args:
            stock_code: 종목 코드
            days: 평균 거래량 계산 기간

        Returns:
            거래량 모멘텀 정보 딕셔너리
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days * 3)

        try:
            df = self.get_price(
                stock_code,
                start_date.strftime('%Y%m%d'),
                end_date.strftime('%Y%m%d')
            )

            if df.empty or 'Volume' not in df.columns or len(df) < days + 1:
                return {'volume_ratio': None, 'volume_surge': False}

            # 최근 거래량
            today_volume = float(df['Volume'].iloc[-1])

            # N일 평균 거래량 (오늘 제외)
            avg_volume = float(df['Volume'].iloc[-(days+1):-1].mean())

            if avg_volume > 0:
                volume_ratio = (today_volume / avg_volume) * 100
            else:
                volume_ratio = None

            return {
                'today_volume': today_volume,
                'avg_volume': avg_volume,
                'volume_ratio': round(volume_ratio, 2) if volume_ratio else None,
                'volume_surge': volume_ratio >= 150 if volume_ratio else False  # 150% 이상이면 급증
            }

        except Exception as e:
            print(f"거래량 모멘텀 계산 오류 ({stock_code}): {e}")
            return {'volume_ratio': None, 'volume_surge': False}

    def get_ma25_divergence(self, stock_code: str) -> dict:
        """
        25일 이동평균선 괴리율을 계산합니다. (BNF식 분석)

        Args:
            stock_code: 종목 코드

        Returns:
            괴리율 정보 딕셔너리
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)

        try:
            df = self.get_price(
                stock_code,
                start_date.strftime('%Y%m%d'),
                end_date.strftime('%Y%m%d')
            )

            if df.empty or 'Close' not in df.columns or len(df) < 25:
                return {'ma25': None, 'divergence': None}

            close = df['Close']
            current_price = float(close.iloc[-1])
            ma25 = float(close.rolling(window=25).mean().iloc[-1])

            # 괴리율 계산: (현재가 - 25일선) / 25일선 * 100
            divergence = ((current_price - ma25) / ma25) * 100

            return {
                'current_price': current_price,
                'ma25': round(ma25, 2),
                'divergence': round(divergence, 2),
                'above_ma25': divergence > 0,
                'oversold': divergence < -10,     # 10% 이상 하락 (BNF 매수 신호)
                'overbought': divergence > 15     # 15% 이상 상승 (과열)
            }

        except Exception as e:
            print(f"25일선 괴리율 계산 오류 ({stock_code}): {e}")
            return {'ma25': None, 'divergence': None}

    def is_bullish_candle(self, stock_code: str) -> dict:
        """
        전일 양봉 여부를 확인합니다. (cis식 - 오르는 주식 매수)

        Args:
            stock_code: 종목 코드

        Returns:
            양봉 정보 딕셔너리
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=10)

        try:
            df = self.get_price(
                stock_code,
                start_date.strftime('%Y%m%d'),
                end_date.strftime('%Y%m%d')
            )

            if df.empty or len(df) < 2:
                return {'is_bullish': None, 'candle_body': None}

            # 최근 봉 (전일 또는 당일)
            latest = df.iloc[-1]
            open_price = float(latest['Open'])
            close_price = float(latest['Close'])

            is_bullish = close_price > open_price
            candle_body = ((close_price - open_price) / open_price) * 100 if open_price > 0 else 0

            # 연속 양봉 확인
            consecutive_bullish = 0
            for i in range(len(df) - 1, -1, -1):
                if df.iloc[i]['Close'] > df.iloc[i]['Open']:
                    consecutive_bullish += 1
                else:
                    break

            return {
                'is_bullish': is_bullish,
                'candle_body': round(candle_body, 2),
                'consecutive_bullish': consecutive_bullish,
                'strong_bullish': is_bullish and candle_body > 1.0  # 1% 이상 양봉
            }

        except Exception as e:
            print(f"양봉 확인 오류 ({stock_code}): {e}")
            return {'is_bullish': None, 'candle_body': None}

    def get_technical_indicators(self, stock_code: str) -> dict:
        """
        종목의 기술적 지표를 종합 수집합니다.

        Args:
            stock_code: 종목 코드

        Returns:
            기술적 지표 딕셔너리
        """
        # RSI
        rsi = self.get_rsi(stock_code)

        # 이동평균선
        ma_info = self.get_moving_averages(stock_code)

        # 외국인 연속 매수일
        foreign_consecutive = self.get_foreign_consecutive_buy_days(stock_code)

        # 볼린저 밴드
        bb_info = self.get_bollinger_bands(stock_code)

        # 거래량 모멘텀 (C+, D 전략용)
        volume_info = self.get_volume_momentum(stock_code)

        # 25일선 괴리율 (D 전략용 - BNF식)
        ma25_info = self.get_ma25_divergence(stock_code)

        # 양봉 확인 (D 전략용 - cis식)
        candle_info = self.is_bullish_candle(stock_code)

        return {
            'rsi': rsi,
            'rsi_oversold': rsi < 30 if rsi else None,      # 과매도
            'rsi_overbought': rsi > 70 if rsi else None,    # 과매수
            'ma5': ma_info.get('ma5'),
            'ma20': ma_info.get('ma20'),
            'ma_trend': ma_info.get('ma_trend'),
            'golden_cross': ma_info.get('golden_cross'),
            'foreign_consecutive_days': foreign_consecutive,
            'bb_upper': bb_info.get('upper'),
            'bb_lower': bb_info.get('lower'),
            'bb_position': bb_info.get('position'),
            # C+, D 전략용 추가 지표
            'volume_ratio': volume_info.get('volume_ratio'),
            'volume_surge': volume_info.get('volume_surge'),
            'ma25': ma25_info.get('ma25'),
            'ma25_divergence': ma25_info.get('divergence'),
            'is_bullish': candle_info.get('is_bullish'),
            'consecutive_bullish': candle_info.get('consecutive_bullish'),
            'strong_bullish': candle_info.get('strong_bullish'),
        }
