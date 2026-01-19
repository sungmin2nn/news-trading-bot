"""
알림 모듈
이메일, Slack 등 다양한 채널로 알림을 전송합니다.
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional


class EmailNotifier:
    """이메일 알림 클래스"""

    def __init__(
        self,
        smtp_email: Optional[str] = None,
        smtp_password: Optional[str] = None,
        recipient_email: Optional[str] = None
    ):
        """
        Args:
            smtp_email: 발송 이메일 (Gmail)
            smtp_password: Gmail 앱 비밀번호
            recipient_email: 수신 이메일
        """
        self.smtp_email = smtp_email or os.environ.get('SMTP_EMAIL')
        self.smtp_password = smtp_password or os.environ.get('SMTP_PASSWORD')
        self.recipient_email = recipient_email or os.environ.get('RECIPIENT_EMAIL')

        self.smtp_server = 'smtp.gmail.com'
        self.smtp_port = 587

    def is_configured(self) -> bool:
        """이메일 설정이 완료되었는지 확인합니다."""
        return all([self.smtp_email, self.smtp_password, self.recipient_email])

    def send_signal_alert(self, signals_by_strategy: dict, date: Optional[str] = None) -> bool:
        """
        시그널 알림 이메일을 전송합니다.

        Args:
            signals_by_strategy: 전략별 시그널 딕셔너리
                {'A': [...], 'B': [...], 'C': [...], 'C+': [...], 'D': [...]}
            date: 날짜 (기본: 오늘)

        Returns:
            전송 성공 여부
        """
        if not self.is_configured():
            print("이메일 설정이 완료되지 않았습니다.")
            return False

        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        # 이메일 제목
        total_count = sum(len(v) for v in signals_by_strategy.values())
        subject = f"[트레이딩 봇] {date} 아침 시그널 ({total_count}종목)"

        # 이메일 본문 생성
        html_body = self._generate_signal_html(signals_by_strategy, date)
        text_body = self._generate_signal_text(signals_by_strategy, date)

        return self._send_email(subject, text_body, html_body)

    def send_tracking_result(self, results: dict, date: Optional[str] = None) -> bool:
        """
        추적 결과 알림 이메일을 전송합니다.

        Args:
            results: 추적 결과 딕셔너리
            date: 날짜

        Returns:
            전송 성공 여부
        """
        if not self.is_configured():
            print("이메일 설정이 완료되지 않았습니다.")
            return False

        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        subject = f"[트레이딩 봇] {date} 저녁 추적 결과"

        html_body = self._generate_result_html(results, date)
        text_body = self._generate_result_text(results, date)

        return self._send_email(subject, text_body, html_body)

    def _generate_signal_html(self, signals_by_strategy: dict, date: str) -> str:
        """시그널 알림 HTML 본문을 생성합니다."""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; }}
                .strategy {{ margin: 15px 0; padding: 15px; background: #f5f7fa; border-radius: 8px; border-left: 4px solid; }}
                .strategy-a {{ border-color: #2196F3; }}
                .strategy-b {{ border-color: #FF9800; }}
                .strategy-c {{ border-color: #4CAF50; }}
                .strategy-c-plus {{ border-color: #9C27B0; }}
                .strategy-d {{ border-color: #E91E63; }}
                .stock {{ padding: 8px 0; border-bottom: 1px solid #eee; }}
                .stock:last-child {{ border-bottom: none; }}
                .score {{ background: #667eea; color: white; padding: 2px 8px; border-radius: 10px; font-size: 12px; }}
                .footer {{ margin-top: 20px; padding: 15px; background: #f0f0f0; border-radius: 8px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2 style="margin:0;">📈 아침 시그널 알림</h2>
                <p style="margin:5px 0 0 0;">{date}</p>
            </div>
        """

        strategy_names = {
            'A': ('전략 A - 단순 필터', 'strategy-a'),
            'B': ('전략 B - 고급 필터', 'strategy-b'),
            'C': ('전략 C - 기술적 분석', 'strategy-c'),
            'C+': ('전략 C+ - 거래량/볼린저', 'strategy-c-plus'),
            'D': ('전략 D - BNF/cis', 'strategy-d')
        }

        for strategy, signals in signals_by_strategy.items():
            if not signals:
                continue

            name, css_class = strategy_names.get(strategy, (f'전략 {strategy}', 'strategy-a'))

            html += f"""
            <div class="strategy {css_class}">
                <h3 style="margin:0 0 10px 0;">{name} ({len(signals)}종목)</h3>
            """

            for signal in signals[:5]:  # 최대 5개만 표시
                corp_name = signal.get('corp_name', 'N/A')
                stock_code = signal.get('stock_code', '')
                score = signal.get('score', 0)
                title = signal.get('title', '')[:30]

                html += f"""
                <div class="stock">
                    <strong>{corp_name}</strong> ({stock_code})
                    <span class="score">점수 {score}</span>
                    <br><small style="color:#666;">{title}</small>
                </div>
                """

            if len(signals) > 5:
                html += f'<p style="color:#666;margin:10px 0 0 0;">외 {len(signals)-5}종목...</p>'

            html += "</div>"

        html += """
            <div class="footer">
                <p>이 알림은 자동으로 생성되었습니다.</p>
                <p>대시보드: <a href="https://sungmin2nn.github.io/news-trading-bot/">바로가기</a></p>
            </div>
        </body>
        </html>
        """

        return html

    def _generate_signal_text(self, signals_by_strategy: dict, date: str) -> str:
        """시그널 알림 텍스트 본문을 생성합니다."""
        text = f"[아침 시그널 알림] {date}\n"
        text += "=" * 40 + "\n\n"

        strategy_names = {
            'A': '전략 A - 단순 필터',
            'B': '전략 B - 고급 필터',
            'C': '전략 C - 기술적 분석',
            'C+': '전략 C+ - 거래량/볼린저',
            'D': '전략 D - BNF/cis'
        }

        for strategy, signals in signals_by_strategy.items():
            if not signals:
                continue

            name = strategy_names.get(strategy, f'전략 {strategy}')
            text += f"[{name}] ({len(signals)}종목)\n"

            for signal in signals[:5]:
                corp_name = signal.get('corp_name', 'N/A')
                stock_code = signal.get('stock_code', '')
                score = signal.get('score', 0)
                text += f"  • {corp_name} ({stock_code}) - 점수 {score}\n"

            if len(signals) > 5:
                text += f"  외 {len(signals)-5}종목...\n"

            text += "\n"

        text += "-" * 40 + "\n"
        text += "대시보드: https://sungmin2nn.github.io/news-trading-bot/\n"

        return text

    def _generate_result_html(self, results: dict, date: str) -> str:
        """추적 결과 HTML 본문을 생성합니다."""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; }}
                .result {{ margin: 15px 0; padding: 15px; background: #f5f7fa; border-radius: 8px; }}
                .positive {{ color: #4CAF50; }}
                .negative {{ color: #f44336; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background: #f0f0f0; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2 style="margin:0;">📊 저녁 추적 결과</h2>
                <p style="margin:5px 0 0 0;">{date}</p>
            </div>
            <div class="result">
        """

        # 전략별 요약
        performance = results.get('performance', {})

        html += """
            <table>
                <tr>
                    <th>전략</th>
                    <th>거래</th>
                    <th>평균 수익률</th>
                    <th>승률</th>
                </tr>
        """

        for strategy in ['strategy_a', 'strategy_b', 'strategy_c', 'strategy_c_plus', 'strategy_d']:
            data = performance.get(strategy, {})
            name = strategy.replace('strategy_', '').upper().replace('_PLUS', '+')
            trades = data.get('total_trades', 0)
            avg_return = data.get('avg_return', 0)
            win_rate = data.get('win_rate', 0)

            return_class = 'positive' if avg_return >= 0 else 'negative'

            html += f"""
                <tr>
                    <td><strong>{name}</strong></td>
                    <td>{trades}건</td>
                    <td class="{return_class}">{avg_return:+.2f}%</td>
                    <td>{win_rate:.1f}%</td>
                </tr>
            """

        html += """
            </table>
            </div>
            <div style="margin-top: 20px; padding: 15px; background: #f0f0f0; border-radius: 8px; font-size: 12px; color: #666;">
                <p>대시보드에서 상세 내역을 확인하세요.</p>
                <p><a href="https://sungmin2nn.github.io/news-trading-bot/">대시보드 바로가기</a></p>
            </div>
        </body>
        </html>
        """

        return html

    def _generate_result_text(self, results: dict, date: str) -> str:
        """추적 결과 텍스트 본문을 생성합니다."""
        text = f"[저녁 추적 결과] {date}\n"
        text += "=" * 40 + "\n\n"

        performance = results.get('performance', {})

        for strategy in ['strategy_a', 'strategy_b', 'strategy_c', 'strategy_c_plus', 'strategy_d']:
            data = performance.get(strategy, {})
            name = strategy.replace('strategy_', '').upper().replace('_PLUS', '+')
            trades = data.get('total_trades', 0)
            avg_return = data.get('avg_return', 0)
            win_rate = data.get('win_rate', 0)

            text += f"[전략 {name}]\n"
            text += f"  거래: {trades}건\n"
            text += f"  평균 수익률: {avg_return:+.2f}%\n"
            text += f"  승률: {win_rate:.1f}%\n\n"

        text += "-" * 40 + "\n"
        text += "대시보드: https://sungmin2nn.github.io/news-trading-bot/\n"

        return text

    def _send_email(self, subject: str, text_body: str, html_body: str) -> bool:
        """이메일을 전송합니다."""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.smtp_email
            msg['To'] = self.recipient_email

            # 텍스트와 HTML 버전 모두 첨부
            part1 = MIMEText(text_body, 'plain', 'utf-8')
            part2 = MIMEText(html_body, 'html', 'utf-8')

            msg.attach(part1)
            msg.attach(part2)

            # SMTP 서버 연결 및 전송
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_email, self.smtp_password)
                server.sendmail(self.smtp_email, self.recipient_email, msg.as_string())

            print(f"이메일 전송 완료: {self.recipient_email}")
            return True

        except Exception as e:
            print(f"이메일 전송 오류: {e}")
            return False
