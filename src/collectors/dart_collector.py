"""
DART 공시 수집 모듈
OpenDartReader를 사용하여 기업 공시 정보를 수집합니다.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

try:
    import OpenDartReader
except ImportError:
    OpenDartReader = None


class DartCollector:
    """DART 공시 데이터 수집 클래스"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Args:
            api_key: DART API 키. 없으면 환경변수 DART_API_KEY 사용
        """
        self.api_key = api_key or os.environ.get('DART_API_KEY')

        if not self.api_key:
            raise ValueError("DART API 키가 필요합니다. DART_API_KEY 환경변수를 설정하거나 api_key 파라미터를 전달하세요.")

        if OpenDartReader is None:
            raise ImportError("OpenDartReader가 설치되지 않았습니다. pip install opendartreader")

        self.dart = OpenDartReader(self.api_key)

    def get_disclosures(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        corp_code: Optional[str] = None
    ) -> pd.DataFrame:
        """
        공시 목록을 조회합니다.

        Args:
            start_date: 시작일 (YYYYMMDD 형식). 기본값은 어제
            end_date: 종료일 (YYYYMMDD 형식). 기본값은 오늘
            corp_code: 특정 기업 코드 (선택사항)

        Returns:
            공시 목록 DataFrame
        """
        today = datetime.now()
        yesterday = today - timedelta(days=1)

        if start_date is None:
            start_date = yesterday.strftime('%Y%m%d')
        if end_date is None:
            end_date = today.strftime('%Y%m%d')

        try:
            if corp_code:
                disclosures = self.dart.list(corp_code, start=start_date, end=end_date)
            else:
                disclosures = self.dart.list(start=start_date, end=end_date)

            if disclosures is None or len(disclosures) == 0:
                return pd.DataFrame()

            return disclosures

        except Exception as e:
            print(f"DART 공시 조회 오류: {e}")
            return pd.DataFrame()

    def get_disclosure_detail(self, rcept_no: str) -> Optional[str]:
        """
        공시 상세 내용을 조회합니다.

        Args:
            rcept_no: 접수번호

        Returns:
            공시 본문 텍스트
        """
        try:
            document = self.dart.document(rcept_no)
            return document
        except Exception as e:
            print(f"공시 상세 조회 오류: {e}")
            return None

    def get_corp_code(self, corp_name: str) -> Optional[str]:
        """
        기업명으로 기업 코드를 조회합니다.

        Args:
            corp_name: 기업명

        Returns:
            기업 코드
        """
        try:
            corp_list = self.dart.corp_codes
            matched = corp_list[corp_list['corp_name'].str.contains(corp_name, na=False)]

            if len(matched) > 0:
                return matched.iloc[0]['corp_code']
            return None

        except Exception as e:
            print(f"기업 코드 조회 오류: {e}")
            return None

    def get_overnight_disclosures(self) -> pd.DataFrame:
        """
        장 마감 후(15:30) ~ 다음날 장 시작 전(09:00) 공시를 수집합니다.
        월요일에는 금요일 공시부터 수집합니다 (주말 공시 포함).
        주로 아침 스캔에서 사용됩니다.

        Returns:
            야간 공시 목록 DataFrame
        """
        now = datetime.now()
        weekday = now.weekday()  # 월=0, 화=1, ..., 일=6

        # 월요일 아침: 금요일 ~ 오늘 공시 수집
        if weekday == 0 and now.hour < 9:
            # 금요일부터 오늘까지 (3일간)
            start_date = (now - timedelta(days=3)).strftime('%Y%m%d')
            end_date = now.strftime('%Y%m%d')
        # 오늘 09:00 이전이면 어제 장 마감 후 ~ 오늘 아침 공시
        elif now.hour < 9:
            start_date = (now - timedelta(days=1)).strftime('%Y%m%d')
            end_date = now.strftime('%Y%m%d')
        else:
            # 09:00 이후면 오늘 장 마감 후 공시 (저녁 스캔용)
            start_date = now.strftime('%Y%m%d')
            end_date = now.strftime('%Y%m%d')

        disclosures = self.get_disclosures(start_date, end_date)

        if disclosures.empty:
            return disclosures

        # 시간 필터링 (rcept_dt 컬럼이 있는 경우)
        if 'rcept_dt' in disclosures.columns:
            disclosures['rcept_dt'] = pd.to_datetime(disclosures['rcept_dt'], format='%Y%m%d')

        return disclosures

    def filter_important_disclosures(self, disclosures: pd.DataFrame) -> pd.DataFrame:
        """
        중요 공시만 필터링합니다.

        Args:
            disclosures: 전체 공시 DataFrame

        Returns:
            필터링된 공시 DataFrame
        """
        if disclosures.empty:
            return disclosures

        # 중요 공시 유형 키워드
        important_keywords = [
            '수주', '계약', '공급', '납품',
            '유상증자', '무상증자', '전환사채', 'CB', 'BW',
            '자기주식', '자사주',
            '합병', '분할', '인수',
            '실적', '영업이익', '매출',
            '특허', '승인', 'FDA',
            '소송', '행정처분',
            '최대주주', '지분',
            '배당',
        ]

        if 'report_nm' not in disclosures.columns:
            return disclosures

        mask = disclosures['report_nm'].str.contains('|'.join(important_keywords), na=False)

        return disclosures[mask]

    def to_signal_format(self, disclosures: pd.DataFrame) -> list:
        """
        공시 데이터를 시그널 분석용 포맷으로 변환합니다.

        Args:
            disclosures: 공시 DataFrame

        Returns:
            시그널 분석용 딕셔너리 리스트
        """
        signals = []

        for _, row in disclosures.iterrows():
            signal = {
                'source': 'dart',
                'corp_name': row.get('corp_name', ''),
                'corp_code': row.get('corp_code', ''),
                'stock_code': row.get('stock_code', ''),
                'title': row.get('report_nm', ''),
                'date': row.get('rcept_dt', ''),
                'rcept_no': row.get('rcept_no', ''),
                'url': f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={row.get('rcept_no', '')}"
            }
            signals.append(signal)

        return signals
