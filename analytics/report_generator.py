"""리포트 생성 모듈"""

from pathlib import Path
from typing import Dict, Any, Optional
import pandas as pd
from jinja2 import Template, Environment
from analytics.metrics import PerformanceMetrics
from utils.logger import get_logger

logger = get_logger(__name__)


class ReportGenerator:
    """리포트 생성 클래스"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        리포트 생성기 초기화
        
        Args:
            config: 리포트 설정
        """
        self.config = config
        self.output_path = Path(config.get("output_path", "./reports/"))
        self.output_path.mkdir(parents=True, exist_ok=True)
        self.formats = config.get("format", ["console"])
        self.include_charts = config.get("include_charts", True)
        self.include_trade_log = config.get("include_trade_log", True)
        logger.info("리포트 생성기 초기화 완료")
    
    def generate(
        self,
        metrics: PerformanceMetrics,
        trades_df: pd.DataFrame,
        equity_curve_df: pd.DataFrame,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """
        리포트 생성
        
        Args:
            metrics: 성능 지표
            trades_df: 거래 기록
            equity_curve_df: 자산 곡선
            additional_data: 추가 데이터
            
        Returns:
            생성된 리포트 파일 경로
        """
        results = {}
        
        if "console" in self.formats:
            self._print_console_report(metrics)
        
        if "html" in self.formats:
            html_path = self._generate_html_report(metrics, trades_df, equity_curve_df, additional_data)
            results["html"] = str(html_path)
        
        if "pdf" in self.formats:
            pdf_path = self._generate_pdf_report(metrics, trades_df, equity_curve_df, additional_data)
            results["pdf"] = str(pdf_path)
        
        return results
    
    def _print_console_report(self, metrics: PerformanceMetrics):
        """콘솔 리포트 출력"""
        print("\n" + "=" * 60)
        print("백테스트 성능 리포트")
        print("=" * 60)
        print(f"\n수익률 지표:")
        print(f"  총 수익률: {metrics.total_return:.2%}")
        print(f"  연환산 수익률: {metrics.annualized_return:.2%}")
        print(f"\n리스크 조정 수익률:")
        print(f"  Sharpe 비율: {metrics.sharpe_ratio:.2f}")
        print(f"  Sortino 비율: {metrics.sortino_ratio:.2f}")
        print(f"  Calmar 비율: {metrics.calmar_ratio:.2f}")
        print(f"\n드로다운:")
        print(f"  최대 드로다운: {metrics.max_drawdown:.2%}")
        print(f"  최대 드로다운 기간: {metrics.max_drawdown_duration} bars")
        print(f"\n거래 통계:")
        print(f"  총 거래 수: {metrics.total_trades}")
        print(f"  승률: {metrics.win_rate:.2%}")
        print(f"  Profit Factor: {metrics.profit_factor:.2f}")
        print(f"  기대값: {metrics.expectancy:.2f}")
        print("=" * 60 + "\n")
    
    def _generate_html_report(
        self,
        metrics: PerformanceMetrics,
        trades_df: pd.DataFrame,
        equity_curve_df: pd.DataFrame,
        additional_data: Optional[Dict[str, Any]],
    ) -> Path:
        """HTML 리포트 생성"""
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <title>백테스트 리포트</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        tr:nth-child(even) { background-color: #f2f2f2; }
    </style>
</head>
<body>
    <h1>백테스트 성능 리포트</h1>
    
    <h2>수익률 지표</h2>
    <table>
        <tr><th>지표</th><th>값</th></tr>
        <tr><td>총 수익률</td><td>{{ (metrics.total_return * 100) | round(2) }}%</td></tr>
        <tr><td>연환산 수익률</td><td>{{ (metrics.annualized_return * 100) | round(2) }}%</td></tr>
    </table>
    
    <h2>리스크 조정 수익률</h2>
    <table>
        <tr><th>지표</th><th>값</th></tr>
        <tr><td>Sharpe 비율</td><td>{{ metrics.sharpe_ratio | round(2) }}</td></tr>
        <tr><td>Sortino 비율</td><td>{{ metrics.sortino_ratio | round(2) }}</td></tr>
        <tr><td>Calmar 비율</td><td>{{ metrics.calmar_ratio | round(2) }}</td></tr>
    </table>
    
    <h2>드로다운</h2>
    <table>
        <tr><th>지표</th><th>값</th></tr>
        <tr><td>최대 드로다운</td><td>{{ (metrics.max_drawdown * 100) | round(2) }}%</td></tr>
        <tr><td>최대 드로다운 기간</td><td>{{ metrics.max_drawdown_duration }} bars</td></tr>
    </table>
    
    <h2>거래 통계</h2>
    <table>
        <tr><th>지표</th><th>값</th></tr>
        <tr><td>총 거래 수</td><td>{{ metrics.total_trades }}</td></tr>
        <tr><td>승률</td><td>{{ (metrics.win_rate * 100) | round(2) }}%</td></tr>
        <tr><td>Profit Factor</td><td>{{ metrics.profit_factor | round(2) }}</td></tr>
        <tr><td>기대값</td><td>{{ metrics.expectancy | round(2) }}</td></tr>
    </table>
</body>
</html>
        """
        
        # Jinja2 Environment 생성 및 필터 등록
        env = Environment()
        
        # multiply 필터 정의 (100을 곱하는 필터)
        def multiply_by_100(value):
            """값에 100을 곱하는 필터"""
            if value is None:
                return 0
            return float(value) * 100
        
        env.filters['multiply'] = multiply_by_100
        
        # 템플릿 생성
        template = env.from_string(html_template)
        
        html_content = template.render(
            metrics=metrics,
            trades_df=trades_df,
            equity_curve_df=equity_curve_df,
        )
        
        # 파일 저장
        html_path = self.output_path / "report.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        logger.info(f"HTML 리포트 생성: {html_path}")
        return html_path
    
    def _generate_pdf_report(
        self,
        metrics: PerformanceMetrics,
        trades_df: pd.DataFrame,
        equity_curve_df: pd.DataFrame,
        additional_data: Optional[Dict[str, Any]],
    ) -> Path:
        """PDF 리포트 생성 (WeasyPrint 사용)"""
        try:
            from weasyprint import HTML
            
            # HTML 리포트 먼저 생성
            html_path = self._generate_html_report(metrics, trades_df, equity_curve_df, additional_data)
            
            # PDF 변환
            pdf_path = self.output_path / "report.pdf"
            HTML(filename=str(html_path)).write_pdf(str(pdf_path))
            
            logger.info(f"PDF 리포트 생성: {pdf_path}")
            return pdf_path
        except ImportError:
            logger.warning("WeasyPrint이 설치되지 않아 PDF 리포트를 생성할 수 없습니다.")
            return None
        except Exception as e:
            logger.error(f"PDF 리포트 생성 실패: {e}")
            return None

