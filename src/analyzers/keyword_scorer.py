"""
키워드 점수 계산 모듈
뉴스/공시 제목에서 키워드를 분석하여 점수를 계산합니다.
"""

import os
from typing import Optional

import yaml
import pandas as pd


class KeywordScorer:
    """키워드 기반 점수 계산 클래스"""

    # 기본 점수
    STRONG_POSITIVE_SCORE = 3
    MEDIUM_POSITIVE_SCORE = 2  # 1 → 2로 상향 (차별화)
    NEGATIVE_SCORE = -10

    def __init__(self, config_path: Optional[str] = None):
        """
        Args:
            config_path: keywords.yaml 파일 경로
        """
        if config_path is None:
            # 기본 경로: 프로젝트 루트/config/keywords.yaml
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_path = os.path.join(base_dir, 'config', 'keywords.yaml')

        self.config_path = config_path
        self.keywords = self._load_keywords()

    def _load_keywords(self) -> dict:
        """키워드 설정을 로드합니다."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            return {
                'strong_positive': config.get('strong_positive', []),
                'medium_positive': config.get('medium_positive', []),
                'negative': config.get('negative', [])
            }

        except FileNotFoundError:
            print(f"키워드 설정 파일을 찾을 수 없습니다: {self.config_path}")
            return {'strong_positive': [], 'medium_positive': [], 'negative': []}

        except Exception as e:
            print(f"키워드 설정 로드 오류: {e}")
            return {'strong_positive': [], 'medium_positive': [], 'negative': []}

    def reload_keywords(self):
        """키워드 설정을 다시 로드합니다."""
        self.keywords = self._load_keywords()

    def calculate_score(self, text: str) -> dict:
        """
        텍스트에서 키워드를 분석하여 점수를 계산합니다.

        Args:
            text: 분석할 텍스트 (뉴스 제목, 공시 제목 등)

        Returns:
            점수 정보 딕셔너리:
            - total_score: 총 점수
            - strong_positive_count: 강한 호재 키워드 수
            - medium_positive_count: 중간 호재 키워드 수
            - negative_count: 악재 키워드 수
            - matched_keywords: 매칭된 키워드 목록
            - is_excluded: 악재로 인한 제외 여부
        """
        if not text:
            return {
                'total_score': 0,
                'strong_positive_count': 0,
                'medium_positive_count': 0,
                'negative_count': 0,
                'matched_keywords': [],
                'is_excluded': False
            }

        text = text.lower() if text else ''
        matched_keywords = []
        strong_count = 0
        medium_count = 0
        negative_count = 0

        # 강한 호재 키워드 체크
        for keyword in self.keywords.get('strong_positive', []):
            if keyword and keyword.lower() in text:
                strong_count += 1
                matched_keywords.append(f"+3: {keyword}")

        # 중간 호재 키워드 체크
        for keyword in self.keywords.get('medium_positive', []):
            if keyword and keyword.lower() in text:
                medium_count += 1
                matched_keywords.append(f"+1: {keyword}")

        # 악재 키워드 체크
        for keyword in self.keywords.get('negative', []):
            if keyword and keyword.lower() in text:
                negative_count += 1
                matched_keywords.append(f"-10: {keyword}")

        # 총 점수 계산
        total_score = (
            strong_count * self.STRONG_POSITIVE_SCORE +
            medium_count * self.MEDIUM_POSITIVE_SCORE +
            negative_count * self.NEGATIVE_SCORE
        )

        # 악재가 하나라도 있으면 제외 대상
        is_excluded = negative_count > 0

        return {
            'total_score': total_score,
            'strong_positive_count': strong_count,
            'medium_positive_count': medium_count,
            'negative_count': negative_count,
            'matched_keywords': matched_keywords,
            'is_excluded': is_excluded
        }

    def score_signals(self, signals: list) -> list:
        """
        시그널 목록에 점수를 계산하여 추가합니다.

        Args:
            signals: 시그널 딕셔너리 리스트

        Returns:
            점수가 추가된 시그널 리스트
        """
        scored_signals = []

        for signal in signals:
            title = signal.get('title', '')
            description = signal.get('description', '')

            # 제목과 설명 모두 분석
            combined_text = f"{title} {description}"
            score_info = self.calculate_score(combined_text)

            # 시그널에 점수 정보 추가
            scored_signal = signal.copy()
            scored_signal.update({
                'score': score_info['total_score'],
                'strong_positive_count': score_info['strong_positive_count'],
                'medium_positive_count': score_info['medium_positive_count'],
                'negative_count': score_info['negative_count'],
                'matched_keywords': score_info['matched_keywords'],
                'is_excluded': score_info['is_excluded']
            })

            scored_signals.append(scored_signal)

        return scored_signals

    def score_dataframe(self, df: pd.DataFrame, text_column: str = 'title') -> pd.DataFrame:
        """
        DataFrame의 텍스트 컬럼에 점수를 계산합니다.

        Args:
            df: 분석할 DataFrame
            text_column: 텍스트가 있는 컬럼명

        Returns:
            점수 컬럼이 추가된 DataFrame
        """
        if df.empty:
            return df

        result_df = df.copy()

        # 점수 계산
        scores = result_df[text_column].apply(self.calculate_score)

        # 결과를 개별 컬럼으로 분리
        result_df['score'] = scores.apply(lambda x: x['total_score'])
        result_df['strong_positive_count'] = scores.apply(lambda x: x['strong_positive_count'])
        result_df['medium_positive_count'] = scores.apply(lambda x: x['medium_positive_count'])
        result_df['negative_count'] = scores.apply(lambda x: x['negative_count'])
        result_df['matched_keywords'] = scores.apply(lambda x: x['matched_keywords'])
        result_df['is_excluded'] = scores.apply(lambda x: x['is_excluded'])

        return result_df

    def filter_positive_signals(self, signals: list, min_score: int = 1) -> list:
        """
        최소 점수 이상의 시그널만 필터링합니다.

        Args:
            signals: 점수가 계산된 시그널 리스트
            min_score: 최소 점수 (기본값: 1)

        Returns:
            필터링된 시그널 리스트
        """
        return [
            signal for signal in signals
            if signal.get('score', 0) >= min_score and not signal.get('is_excluded', False)
        ]

    def rank_signals(self, signals: list, top_n: Optional[int] = None) -> list:
        """
        시그널을 점수 순으로 정렬합니다.

        Args:
            signals: 점수가 계산된 시그널 리스트
            top_n: 상위 N개만 반환 (None이면 전체)

        Returns:
            정렬된 시그널 리스트
        """
        # 제외 대상 필터링
        valid_signals = [s for s in signals if not s.get('is_excluded', False)]

        # 점수 기준 내림차순 정렬
        sorted_signals = sorted(valid_signals, key=lambda x: x.get('score', 0), reverse=True)

        if top_n:
            return sorted_signals[:top_n]

        return sorted_signals

    def get_summary(self, signals: list) -> dict:
        """
        시그널 분석 요약을 생성합니다.

        Args:
            signals: 점수가 계산된 시그널 리스트

        Returns:
            요약 정보 딕셔너리
        """
        if not signals:
            return {
                'total_count': 0,
                'positive_count': 0,
                'negative_count': 0,
                'excluded_count': 0,
                'avg_score': 0,
                'max_score': 0,
                'top_keywords': []
            }

        scores = [s.get('score', 0) for s in signals]
        excluded = [s for s in signals if s.get('is_excluded', False)]
        positive = [s for s in signals if s.get('score', 0) > 0 and not s.get('is_excluded', False)]

        # 자주 등장하는 키워드 집계
        all_keywords = []
        for signal in signals:
            all_keywords.extend(signal.get('matched_keywords', []))

        keyword_counts = {}
        for kw in all_keywords:
            keyword_counts[kw] = keyword_counts.get(kw, 0) + 1

        top_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            'total_count': len(signals),
            'positive_count': len(positive),
            'negative_count': len([s for s in signals if s.get('score', 0) < 0]),
            'excluded_count': len(excluded),
            'avg_score': sum(scores) / len(scores) if scores else 0,
            'max_score': max(scores) if scores else 0,
            'top_keywords': top_keywords
        }
