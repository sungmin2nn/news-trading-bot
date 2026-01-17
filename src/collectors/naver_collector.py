"""
네이버 뉴스 수집 모듈
네이버 금융 뉴스를 스크래핑하여 종목 관련 뉴스를 수집합니다.
"""

import re
import time
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
import pandas as pd


class NaverCollector:
    """네이버 금융 뉴스 수집 클래스"""

    BASE_URL = "https://finance.naver.com"
    NEWS_URL = "https://finance.naver.com/news/mainnews.naver"
    STOCK_NEWS_URL = "https://finance.naver.com/item/news.naver"

    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    }

    def __init__(self, delay: float = 0.5):
        """
        Args:
            delay: 요청 간 딜레이 (초)
        """
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update(self.HEADERS)

    def get_main_news(self, page: int = 1) -> list:
        """
        네이버 금융 메인 뉴스를 수집합니다.

        Args:
            page: 페이지 번호

        Returns:
            뉴스 목록
        """
        try:
            url = f"{self.NEWS_URL}?page={page}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'lxml')
            news_list = []

            # 뉴스 목록 파싱
            articles = soup.select('div.mainNewsList li')

            for article in articles:
                title_elem = article.select_one('a')
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                link = title_elem.get('href', '')

                if not link.startswith('http'):
                    link = self.BASE_URL + link

                # 날짜/시간 추출
                date_elem = article.select_one('span.wdate')
                date_str = date_elem.get_text(strip=True) if date_elem else ''

                # 연관 종목 추출
                stock_elem = article.select_one('span.stock')
                stock_name = stock_elem.get_text(strip=True) if stock_elem else ''

                news_list.append({
                    'title': title,
                    'url': link,
                    'date': date_str,
                    'stock_name': stock_name,
                    'source': 'naver_main'
                })

            time.sleep(self.delay)
            return news_list

        except Exception as e:
            print(f"네이버 메인 뉴스 수집 오류: {e}")
            return []

    def get_stock_news(self, stock_code: str, page: int = 1) -> list:
        """
        특정 종목의 뉴스를 수집합니다.

        Args:
            stock_code: 종목 코드 (6자리)
            page: 페이지 번호

        Returns:
            뉴스 목록
        """
        try:
            url = f"{self.STOCK_NEWS_URL}?code={stock_code}&page={page}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'lxml')
            news_list = []

            # 뉴스 테이블 파싱
            rows = soup.select('table.type5 tbody tr')

            for row in rows:
                title_elem = row.select_one('a.tit')
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                link = title_elem.get('href', '')

                if not link.startswith('http'):
                    link = self.BASE_URL + link

                # 날짜 추출
                date_elem = row.select_one('td.date')
                date_str = date_elem.get_text(strip=True) if date_elem else ''

                # 정보 제공처
                source_elem = row.select_one('td.info')
                source = source_elem.get_text(strip=True) if source_elem else ''

                news_list.append({
                    'title': title,
                    'url': link,
                    'date': date_str,
                    'stock_code': stock_code,
                    'info_source': source,
                    'source': 'naver_stock'
                })

            time.sleep(self.delay)
            return news_list

        except Exception as e:
            print(f"종목 뉴스 수집 오류 ({stock_code}): {e}")
            return []

    def search_news(self, keyword: str, page: int = 1) -> list:
        """
        키워드로 뉴스를 검색합니다.

        Args:
            keyword: 검색 키워드
            page: 페이지 번호

        Returns:
            뉴스 목록
        """
        try:
            encoded_keyword = quote(keyword)
            url = f"https://search.naver.com/search.naver?where=news&query={encoded_keyword}&start={((page-1)*10)+1}"

            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'lxml')
            news_list = []

            # 뉴스 검색 결과 파싱
            articles = soup.select('div.news_area')

            for article in articles:
                title_elem = article.select_one('a.news_tit')
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                link = title_elem.get('href', '')

                # 요약 내용
                desc_elem = article.select_one('div.news_dsc')
                description = desc_elem.get_text(strip=True) if desc_elem else ''

                # 정보 제공처
                source_elem = article.select_one('a.info.press')
                press = source_elem.get_text(strip=True) if source_elem else ''

                # 날짜
                date_elem = article.select_one('span.info')
                date_str = date_elem.get_text(strip=True) if date_elem else ''

                news_list.append({
                    'title': title,
                    'url': link,
                    'description': description,
                    'press': press,
                    'date': date_str,
                    'keyword': keyword,
                    'source': 'naver_search'
                })

            time.sleep(self.delay)
            return news_list

        except Exception as e:
            print(f"뉴스 검색 오류 ({keyword}): {e}")
            return []

    def get_recent_news(self, hours: int = 24, max_pages: int = 5) -> list:
        """
        최근 N시간 내 뉴스를 수집합니다.

        Args:
            hours: 수집할 시간 범위
            max_pages: 최대 페이지 수

        Returns:
            뉴스 목록
        """
        all_news = []
        cutoff_time = datetime.now() - timedelta(hours=hours)

        for page in range(1, max_pages + 1):
            news_list = self.get_main_news(page)

            if not news_list:
                break

            for news in news_list:
                # 날짜 파싱 시도
                try:
                    date_str = news.get('date', '')
                    if date_str:
                        # 다양한 날짜 형식 처리
                        news_date = self._parse_date(date_str)
                        if news_date and news_date >= cutoff_time:
                            all_news.append(news)
                        elif news_date and news_date < cutoff_time:
                            # 시간 범위 초과, 수집 중단
                            return all_news
                    else:
                        all_news.append(news)
                except Exception:
                    all_news.append(news)

        return all_news

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """날짜 문자열을 파싱합니다."""
        now = datetime.now()

        # "N분 전", "N시간 전" 형식
        if '분 전' in date_str:
            match = re.search(r'(\d+)분 전', date_str)
            if match:
                minutes = int(match.group(1))
                return now - timedelta(minutes=minutes)

        if '시간 전' in date_str:
            match = re.search(r'(\d+)시간 전', date_str)
            if match:
                hours = int(match.group(1))
                return now - timedelta(hours=hours)

        if '일 전' in date_str:
            match = re.search(r'(\d+)일 전', date_str)
            if match:
                days = int(match.group(1))
                return now - timedelta(days=days)

        # YYYY.MM.DD 형식
        try:
            return datetime.strptime(date_str, '%Y.%m.%d')
        except ValueError:
            pass

        # YYYY.MM.DD HH:MM 형식
        try:
            return datetime.strptime(date_str, '%Y.%m.%d %H:%M')
        except ValueError:
            pass

        return None

    def get_overnight_news(self) -> list:
        """
        장 마감 후(15:30) ~ 다음날 장 시작 전(09:00) 뉴스를 수집합니다.

        Returns:
            야간 뉴스 목록
        """
        now = datetime.now()

        # 오전 9시 이전: 어제 장 마감 후 ~ 현재
        if now.hour < 9:
            # 어제 15:30부터 현재까지
            hours_since_close = (24 - 15.5) + now.hour + (now.minute / 60)
        else:
            # 장중 또는 장 마감 후: 오늘 15:30부터 현재까지
            if now.hour >= 15 and now.minute >= 30:
                hours_since_close = (now.hour - 15) + ((now.minute - 30) / 60)
            else:
                hours_since_close = 24  # 장중에는 전일 뉴스 수집

        return self.get_recent_news(hours=int(hours_since_close) + 1, max_pages=10)

    def to_signal_format(self, news_list: list) -> list:
        """
        뉴스 데이터를 시그널 분석용 포맷으로 변환합니다.

        Args:
            news_list: 뉴스 목록

        Returns:
            시그널 분석용 딕셔너리 리스트
        """
        signals = []

        for news in news_list:
            signal = {
                'source': news.get('source', 'naver'),
                'title': news.get('title', ''),
                'url': news.get('url', ''),
                'date': news.get('date', ''),
                'stock_name': news.get('stock_name', ''),
                'stock_code': news.get('stock_code', ''),
                'description': news.get('description', ''),
            }
            signals.append(signal)

        return signals

    def collect_all_sources(self, stock_codes: list = None, keywords: list = None) -> pd.DataFrame:
        """
        모든 소스에서 뉴스를 수집합니다.

        Args:
            stock_codes: 수집할 종목 코드 목록
            keywords: 검색할 키워드 목록

        Returns:
            통합 뉴스 DataFrame
        """
        all_news = []

        # 메인 뉴스 수집
        main_news = self.get_overnight_news()
        all_news.extend(main_news)

        # 종목별 뉴스 수집
        if stock_codes:
            for code in stock_codes:
                stock_news = self.get_stock_news(code)
                all_news.extend(stock_news)

        # 키워드 검색
        if keywords:
            for keyword in keywords:
                search_news = self.search_news(keyword)
                all_news.extend(search_news)

        # DataFrame으로 변환
        if all_news:
            df = pd.DataFrame(all_news)
            # 중복 제거 (URL 기준)
            df = df.drop_duplicates(subset=['url'], keep='first')
            return df

        return pd.DataFrame()
