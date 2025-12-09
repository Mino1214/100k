"""전략 테스트"""

import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from strategy.base_strategy import Regime, SignalType
from strategy.regime_detector import RegimeDetector


@pytest.fixture
def sample_data_with_indicators():
    """지표가 포함된 샘플 데이터"""
    dates = pd.date_range("2024-01-01", periods=100, freq="1min")
    np.random.seed(42)
    prices = 50000 + np.cumsum(np.random.randn(100) * 100)
    
    df = pd.DataFrame({
        "open": prices,
        "high": prices * 1.01,
        "low": prices * 0.99,
        "close": prices,
        "volume": np.random.randint(100, 1000, 100),
    }, index=dates)
    
    # EMA 추가
    df["EMA_20"] = df["close"].ewm(span=20).mean()
    df["EMA_40"] = df["close"].ewm(span=40).mean()
    df["EMA_80"] = df["close"].ewm(span=80).mean()
    
    return df


def test_regime_detector(sample_data_with_indicators):
    """레짐 탐지기 테스트"""
    config = {
        "method": "ema_alignment",
        "ema_alignment": {
            "bull": {"min_separation_pct": 0.1},
            "bear": {"min_separation_pct": 0.1},
        },
    }
    
    detector = RegimeDetector(config)
    regime_series = detector.detect(sample_data_with_indicators)
    
    assert len(regime_series) == len(sample_data_with_indicators)
    assert all(r in [Regime.BULL, Regime.BEAR, Regime.SIDEWAYS] for r in regime_series.unique())

