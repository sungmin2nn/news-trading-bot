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
