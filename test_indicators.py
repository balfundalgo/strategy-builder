"""
test_indicators.py
───────────────────────────────────────────────────────────────────
Milestone 2 — Indicator Engine Test Script

Run this locally on your Mac to verify all indicators calculate
correctly before pushing to GitHub.

Usage:
    python test_indicators.py               # synthetic data test
    python test_indicators.py --live        # fetch real NIFTY data from Dhan

Output: Prints a table of all indicator values at the last bar.
"""

import sys
import argparse
import numpy as np
import pandas as pd

# ─────────────────────────────────────────────────────────────────
# Make imports work from project root
# ─────────────────────────────────────────────────────────────────
sys.path.insert(0, ".")

from core.indicators import IndicatorEngine
from core.indicator_registry import INDICATORS, get_by_category, all_categories


# ─────────────────────────────────────────────────────────────────
# Synthetic OHLCV data generator (realistic random walk)
# ─────────────────────────────────────────────────────────────────

def make_synthetic_df(n: int = 500) -> pd.DataFrame:
    """Generate synthetic NIFTY-like OHLCV data."""
    np.random.seed(42)
    close = 22000 + np.cumsum(np.random.randn(n) * 30)
    close = np.maximum(close, 100)   # no negatives

    open_  = close + np.random.randn(n) * 10
    high   = np.maximum(close, open_) + np.abs(np.random.randn(n) * 15)
    low    = np.minimum(close, open_) - np.abs(np.random.randn(n) * 15)
    volume = np.abs(np.random.randn(n) * 500000 + 1000000).astype(int)

    idx = pd.date_range("2025-01-01 09:15", periods=n, freq="1min")
    return pd.DataFrame({
        "open":   open_,
        "high":   high,
        "low":    low,
        "close":  close,
        "volume": volume,
    }, index=idx)


# ─────────────────────────────────────────────────────────────────
# Real Dhan data fetch
# ─────────────────────────────────────────────────────────────────

def fetch_real_data():
    from core.dhan_client import load_credentials, fetch_intraday_ohlcv
    creds = load_credentials()
    if not creds.get("access_token"):
        print("❌  No access token found. Run the app and connect first.")
        sys.exit(1)

    print("📡  Fetching NIFTY 1-min intraday data from Dhan...")
    result = fetch_intraday_ohlcv(
        client_id        = creds["client_id"],
        access_token     = creds["access_token"],
        security_id      = "13",
        exchange_segment = "IDX_I",
        instrument       = "INDEX",
        interval         = "1",
    )
    if not result["success"]:
        print(f"❌  Fetch failed: {result['error']}")
        sys.exit(1)

    df = result["data"]
    print(f"✅  Got {len(df)} candles  ({df.index[0]}  →  {df.index[-1]})")
    return df


# ─────────────────────────────────────────────────────────────────
# Main test
# ─────────────────────────────────────────────────────────────────

def run_tests(df: pd.DataFrame):
    print(f"\n{'─'*65}")
    print(f"  Testing {len(df)} candles | Last close: {df['close'].iloc[-1]:.2f}")
    print(f"{'─'*65}\n")

    engine = IndicatorEngine(df)
    passed = 0
    failed = 0
    results = []

    # ── Individual indicator tests ────────────────────────────────
    tests = [
        ("SMA(20)",          lambda: engine.sma(20)),
        ("EMA(20)",          lambda: engine.ema(20)),
        ("EMA(50)",          lambda: engine.ema(50)),
        ("WMA(20)",          lambda: engine.wma(20)),
        ("DEMA(20)",         lambda: engine.dema(20)),
        ("TEMA(20)",         lambda: engine.tema(20)),
        ("VWAP",             lambda: engine.vwap()),
        ("RSI(14)",          lambda: engine.rsi(14)),
        ("ATR(14)",          lambda: engine.atr(14)),
        ("OBV",              lambda: engine.obv()),
        ("MFI(14)",          lambda: engine.mfi(14)),
        ("CMF(20)",          lambda: engine.cmf(20)),
        ("CCI(20)",          lambda: engine.cci(20)),
        ("WilliamsR(14)",    lambda: engine.williams_r(14)),
        ("ROC(9)",           lambda: engine.roc(9)),
    ]

    df_tests = [
        ("MACD(12,26,9)",    lambda: engine.macd()),
        ("Stochastic",       lambda: engine.stochastic()),
        ("ADX(14)",          lambda: engine.adx()),
        ("Supertrend(7,3)",  lambda: engine.supertrend()),
        ("BollingerBands",   lambda: engine.bollinger_bands()),
        ("KeltnerChannel",   lambda: engine.keltner_channel()),
        ("DonchianChannel",  lambda: engine.donchian_channel()),
        ("Ichimoku",         lambda: engine.ichimoku()),
    ]

    pattern_tests = [
        ("Doji",             lambda: engine.pattern_doji()),
        ("Hammer",           lambda: engine.pattern_hammer()),
        ("ShootingStar",     lambda: engine.pattern_shooting_star()),
        ("BullEngulfing",    lambda: engine.pattern_bullish_engulfing()),
        ("BearEngulfing",    lambda: engine.pattern_bearish_engulfing()),
        ("MorningStar",      lambda: engine.pattern_morning_star()),
        ("EveningStar",      lambda: engine.pattern_evening_star()),
    ]

    print("  📊  Series indicators (last value):")
    print(f"  {'Indicator':<25} {'Last Value':>14}  {'NaN Count':>10}  Status")
    print(f"  {'─'*60}")

    for name, fn in tests:
        try:
            series = fn()
            last   = series.dropna().iloc[-1] if len(series.dropna()) else float("nan")
            nans   = series.isna().sum()
            ok     = not np.isnan(last)
            status = "✅" if ok else "⚠️  all NaN"
            print(f"  {name:<25} {last:>14.4f}  {nans:>10}  {status}")
            if ok:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  {name:<25} {'ERROR':>14}  {'':>10}  ❌  {e}")
            failed += 1

    print(f"\n  📊  DataFrame indicators:")
    print(f"  {'─'*60}")

    for name, fn in df_tests:
        try:
            result_df = fn()
            cols      = list(result_df.columns)
            last_row  = result_df.dropna().iloc[-1] if len(result_df.dropna()) else None
            ok        = last_row is not None
            vals_str  = "  |  ".join([f"{c}={v:.2f}" for c, v in last_row.items()]) if ok else "all NaN"
            print(f"  {name:<25}  ✅  {vals_str}" if ok else f"  {name:<25}  ⚠️  {vals_str}")
            if ok:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  {name:<25}  ❌  {e}")
            failed += 1

    print(f"\n  🕯️  Candlestick patterns (last bar signal):")
    print(f"  {'─'*60}")

    for name, fn in pattern_tests:
        try:
            series    = fn()
            detected  = bool(series.iloc[-1])
            count     = series.sum()
            print(f"  {name:<25}  {'🟢 YES' if detected else '⬜ no':>8}  (detected {count}x in {len(df)} bars)")
            passed += 1
        except Exception as e:
            print(f"  {name:<25}  ❌  {e}")
            failed += 1

    # ── Full snapshot ─────────────────────────────────────────────
    print(f"\n  📋  Full snapshot() — all values at last bar:")
    print(f"  {'─'*60}")
    try:
        snap = engine.snapshot()
        for k, v in snap.items():
            if isinstance(v, float):
                print(f"  {k:<30}  {v:>14.4f}")
            else:
                print(f"  {k:<30}  {str(v):>14}")
        passed += 1
    except Exception as e:
        print(f"  ❌  snapshot() failed: {e}")
        failed += 1

    # ── Registry test ─────────────────────────────────────────────
    print(f"\n  📚  Indicator Registry:")
    print(f"  {'─'*60}")
    from core.indicator_registry import INDICATORS, get_by_category, all_categories
    cats = get_by_category()
    for cat in all_categories():
        names = cats.get(cat, [])
        print(f"  {cat:<15}  {len(names)} indicators: {', '.join(names)}")
    total_reg = len(INDICATORS)
    print(f"\n  Total registered: {total_reg} indicators")

    # ── Summary ───────────────────────────────────────────────────
    print(f"\n{'─'*65}")
    print(f"  Result: {passed} passed  |  {failed} failed")
    if failed == 0:
        print(f"  ✅  All indicators working correctly!")
    else:
        print(f"  ⚠️  {failed} indicator(s) need attention.")
    print(f"{'─'*65}\n")

    return failed == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Balfund indicator engine")
    parser.add_argument("--live", action="store_true", help="Use real NIFTY data from Dhan")
    args = parser.parse_args()

    if args.live:
        df = fetch_real_data()
    else:
        print("ℹ️  Using synthetic data (run with --live for real Dhan data)")
        df = make_synthetic_df(500)

    success = run_tests(df)
    sys.exit(0 if success else 1)
