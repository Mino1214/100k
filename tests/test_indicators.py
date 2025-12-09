"""지표 테스트"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import pandas as pd
import numpy as np
from indicators.trend import EMA, SMA
from indicators.volatility import ATR, BollingerBands


@pytest.fixture
def sample_data():
    """샘플 데이터 생성"""
    dates = pd.date_range("2024-01-01", periods=100, freq="1min")
    np.random.seed(42)
    prices = 50000 + np.cumsum(np.random.randn(100) * 100)
    
    return pd.DataFrame({
        "open": prices,
        "high": prices * 1.01,
        "low": prices * 0.99,
        "close": prices,
        "volume": np.random.randint(100, 1000, 100),
    }, index=dates)


def test_ema(sample_data):
    """EMA 테스트"""
    ema = EMA(period=20)
    result = ema.calculate(sample_data)
    
    assert len(result) == len(sample_data)
    assert not result.isna().all()


def test_sma(sample_data):
    """SMA 테스트"""
    sma = SMA(period=20)
    result = sma.calculate(sample_data)
    
    assert len(result) == len(sample_data)
    assert result.iloc[19] is not None  # 20번째 값부터 유효


def test_atr(sample_data):
    """ATR 테스트"""
    atr = ATR(period=14)
    result = atr.calculate(sample_data)
    
    assert len(result) == len(sample_data)
    assert (result >= 0).all()  # ATR은 항상 양수


def test_bollinger_bands(sample_data):
    """Bollinger Bands 테스트"""
    bb = BollingerBands(period=20, std_dev=2.0)
    result = bb.calculate_full(sample_data)
    
    assert "bb_upper" in result.columns
    assert "bb_lower" in result.columns
    assert "bb_middle" in result.columns
    assert (result["bb_upper"] >= result["bb_lower"]).all()

