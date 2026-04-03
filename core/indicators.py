"""
core/indicators.py
───────────────────────────────────────────────────────────────────
Balfund Strategy Builder — Indicator Engine (Milestone 2)

All indicators implemented from scratch using numpy + pandas only.
No pandas-ta or TA-Lib dependency. TradingView-accurate calculations.

Supported:
  Trend     : EMA, SMA, WMA, DEMA, TEMA, VWAP, Supertrend, Ichimoku
  Momentum  : RSI, MACD, Stochastic, CCI, ADX, Williams %R, ROC
  Volatility: Bollinger Bands, ATR, Keltner Channel, Donchian Channel
  Volume    : OBV, MFI, CMF
  Candles   : Engulfing, Doji, Hammer, Shooting Star, Morning/Evening Star

Usage:
    from core.indicators import IndicatorEngine
    engine = IndicatorEngine(df)          # df has columns: open,high,low,close,volume
    result = engine.ema(period=20)        # returns pd.Series
    result = engine.supertrend()          # returns pd.DataFrame
    result = engine.all_signals()         # returns dict of all indicator values at last bar
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict, Any, Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Indicator Engine
# ─────────────────────────────────────────────────────────────────────────────

class IndicatorEngine:
    """
    Takes an OHLCV DataFrame and computes any indicator on demand.

    DataFrame must have columns: open, high, low, close, volume
    Index should be DatetimeIndex (from Dhan API fetch).
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self._validate()

    def _validate(self):
        required = {"open", "high", "low", "close", "volume"}
        missing  = required - set(self.df.columns)
        if missing:
            raise ValueError(f"DataFrame missing columns: {missing}")
        # Ensure float
        for col in required:
            self.df[col] = self.df[col].astype(float)

    # ─────────────────────────────────────────────────────────────
    # Source helpers
    # ─────────────────────────────────────────────────────────────

    def _src(self, source: str = "close") -> pd.Series:
        """Return price series by source name."""
        src_map = {
            "close":  self.df["close"],
            "open":   self.df["open"],
            "high":   self.df["high"],
            "low":    self.df["low"],
            "hl2":    (self.df["high"] + self.df["low"]) / 2,
            "hlc3":   (self.df["high"] + self.df["low"] + self.df["close"]) / 3,
            "ohlc4":  (self.df["open"] + self.df["high"] + self.df["low"] + self.df["close"]) / 4,
            "hlcc4":  (self.df["high"] + self.df["low"] + self.df["close"] * 2) / 4,
        }
        if source not in src_map:
            raise ValueError(f"Unknown source '{source}'. Choose from: {list(src_map.keys())}")
        return src_map[source]

    # ══════════════════════════════════════════════════════════════
    # TREND INDICATORS
    # ══════════════════════════════════════════════════════════════

    def sma(self, period: int = 20, source: str = "close") -> pd.Series:
        """Simple Moving Average"""
        return self._src(source).rolling(window=period).mean().rename(f"SMA_{period}")

    def ema(self, period: int = 20, source: str = "close") -> pd.Series:
        """
        Exponential Moving Average — matches TradingView exactly.
        Uses adjust=False (recursive EMA, not Wilder's).
        """
        return self._src(source).ewm(span=period, adjust=False).mean().rename(f"EMA_{period}")

    def wma(self, period: int = 20, source: str = "close") -> pd.Series:
        """Weighted Moving Average — linearly weighted, most recent = highest weight."""
        src     = self._src(source)
        weights = np.arange(1, period + 1)

        def _wma(x):
            return np.dot(x, weights) / weights.sum()

        return src.rolling(window=period).apply(_wma, raw=True).rename(f"WMA_{period}")

    def dema(self, period: int = 20, source: str = "close") -> pd.Series:
        """Double EMA: 2*EMA(src) - EMA(EMA(src))"""
        e  = self.ema(period, source)
        ee = e.ewm(span=period, adjust=False).mean()
        return (2 * e - ee).rename(f"DEMA_{period}")

    def tema(self, period: int = 20, source: str = "close") -> pd.Series:
        """Triple EMA: 3*EMA - 3*EMA(EMA) + EMA(EMA(EMA))"""
        src = self._src(source)
        e1  = src.ewm(span=period, adjust=False).mean()
        e2  = e1.ewm(span=period, adjust=False).mean()
        e3  = e2.ewm(span=period, adjust=False).mean()
        return (3 * e1 - 3 * e2 + e3).rename(f"TEMA_{period}")

    def rma(self, period: int = 14, source: str = "close") -> pd.Series:
        """
        Wilder's Moving Average (RMA) — used inside RSI, ATR, ADX.
        Matches TradingView ta.rma() exactly.
        alpha = 1 / period
        """
        src   = self._src(source)
        alpha = 1.0 / period
        result = np.full(len(src), np.nan)
        values = src.values

        # Find first non-NaN
        first_valid = np.where(~np.isnan(values))[0]
        if len(first_valid) == 0:
            return pd.Series(result, index=src.index, name=f"RMA_{period}")

        start = first_valid[0] + period - 1
        if start >= len(values):
            return pd.Series(result, index=src.index, name=f"RMA_{period}")

        # Seed with SMA of first `period` bars
        result[start] = np.mean(values[first_valid[0]: first_valid[0] + period])

        for i in range(start + 1, len(values)):
            if not np.isnan(values[i]):
                result[i] = alpha * values[i] + (1 - alpha) * result[i - 1]

        return pd.Series(result, index=src.index, name=f"RMA_{period}")

    def vwap(self) -> pd.Series:
        """
        VWAP — Volume Weighted Average Price.
        Resets each session (day). Matches TradingView session VWAP.
        """
        df  = self.df
        hlc = (df["high"] + df["low"] + df["close"]) / 3
        pv  = hlc * df["volume"]

        # Group by date for daily reset
        if hasattr(df.index, "date"):
            date_key = pd.Series(df.index.date, index=df.index)
            cum_pv   = pv.groupby(date_key).cumsum()
            cum_vol  = df["volume"].groupby(date_key).cumsum()
        else:
            cum_pv  = pv.cumsum()
            cum_vol = df["volume"].cumsum()

        vwap = (cum_pv / cum_vol.replace(0, np.nan)).rename("VWAP")
        return vwap

    def supertrend(self, period: int = 7, multiplier: float = 3.0) -> pd.DataFrame:
        """
        Supertrend — matches TradingView exactly.
        Returns DataFrame with columns:
            supertrend  : float  (the line value)
            direction   : int    (+1 = bullish/green, -1 = bearish/red)
            upper_band  : float
            lower_band  : float
        """
        atr    = self._atr_raw(period)
        hl2    = (self.df["high"] + self.df["low"]) / 2
        close  = self.df["close"]

        upper_basic = hl2 + multiplier * atr
        lower_basic = hl2 - multiplier * atr

        upper = upper_basic.copy()
        lower = lower_basic.copy()
        direction = pd.Series(np.ones(len(close)), index=close.index, dtype=int)
        supertrend = pd.Series(np.nan, index=close.index)

        for i in range(1, len(close)):
            if np.isnan(upper.iloc[i - 1]):
                continue

            # Upper band
            upper.iloc[i] = (
                upper_basic.iloc[i]
                if upper_basic.iloc[i] < upper.iloc[i - 1] or close.iloc[i - 1] > upper.iloc[i - 1]
                else upper.iloc[i - 1]
            )

            # Lower band
            lower.iloc[i] = (
                lower_basic.iloc[i]
                if lower_basic.iloc[i] > lower.iloc[i - 1] or close.iloc[i - 1] < lower.iloc[i - 1]
                else lower.iloc[i - 1]
            )

            # Direction
            prev_st = supertrend.iloc[i - 1]
            if np.isnan(prev_st) or prev_st == upper.iloc[i - 1]:
                direction.iloc[i] = -1 if close.iloc[i] > upper.iloc[i] else 1
            else:
                direction.iloc[i] = 1 if close.iloc[i] < lower.iloc[i] else -1

            supertrend.iloc[i] = lower.iloc[i] if direction.iloc[i] == -1 else upper.iloc[i]

        return pd.DataFrame({
            "supertrend": supertrend,
            "direction":  direction,
            "upper_band": upper,
            "lower_band": lower,
        })

    def ichimoku(
        self,
        tenkan_period: int = 9,
        kijun_period: int  = 26,
        senkou_b_period: int = 52,
        displacement: int  = 26,
    ) -> pd.DataFrame:
        """Ichimoku Cloud — all 5 lines."""
        high  = self.df["high"]
        low   = self.df["low"]
        close = self.df["close"]

        def mid(h, l, p):
            return (h.rolling(p).max() + l.rolling(p).min()) / 2

        tenkan   = mid(high, low, tenkan_period)
        kijun    = mid(high, low, kijun_period)
        senkou_a = ((tenkan + kijun) / 2).shift(displacement)
        senkou_b = mid(high, low, senkou_b_period).shift(displacement)
        chikou   = close.shift(-displacement)

        return pd.DataFrame({
            "tenkan":   tenkan,
            "kijun":    kijun,
            "senkou_a": senkou_a,
            "senkou_b": senkou_b,
            "chikou":   chikou,
        })

    # ══════════════════════════════════════════════════════════════
    # MOMENTUM INDICATORS
    # ══════════════════════════════════════════════════════════════

    def rsi(self, period: int = 14, source: str = "close") -> pd.Series:
        """
        RSI — Relative Strength Index.
        Uses RMA (Wilder's smoothing) to match TradingView exactly.
        """
        src    = self._src(source)
        delta  = src.diff()
        gain   = delta.clip(lower=0)
        loss   = (-delta).clip(lower=0)

        avg_gain = self.rma(period, source="close")
        avg_loss = self.rma(period, source="close")

        # Re-compute correctly on gain/loss series
        alpha = 1.0 / period
        gain_vals = gain.values
        loss_vals = loss.values
        rsi_vals  = np.full(len(src), np.nan)

        # Seed from first full period
        seed = period  # first valid index
        if seed < len(gain_vals):
            avg_g = np.mean(gain_vals[1:seed + 1])
            avg_l = np.mean(loss_vals[1:seed + 1])
            if avg_l == 0:
                rsi_vals[seed] = 100.0
            else:
                rsi_vals[seed] = 100 - 100 / (1 + avg_g / avg_l)

            for i in range(seed + 1, len(gain_vals)):
                avg_g = alpha * gain_vals[i] + (1 - alpha) * avg_g
                avg_l = alpha * loss_vals[i] + (1 - alpha) * avg_l
                if avg_l == 0:
                    rsi_vals[i] = 100.0
                else:
                    rsi_vals[i] = 100 - 100 / (1 + avg_g / avg_l)

        return pd.Series(rsi_vals, index=src.index, name=f"RSI_{period}")

    def macd(
        self,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        source: str = "close",
    ) -> pd.DataFrame:
        """
        MACD — Moving Average Convergence Divergence.
        Returns DataFrame: macd, signal, histogram
        """
        src        = self._src(source)
        ema_fast   = src.ewm(span=fast,   adjust=False).mean()
        ema_slow   = src.ewm(span=slow,   adjust=False).mean()
        macd_line  = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram  = macd_line - signal_line

        return pd.DataFrame({
            "macd":      macd_line,
            "signal":    signal_line,
            "histogram": histogram,
        })

    def stochastic(
        self,
        k_period: int = 14,
        d_period: int = 3,
        smooth_k: int = 3,
    ) -> pd.DataFrame:
        """
        Stochastic Oscillator — %K and %D.
        Matches TradingView stoch().
        """
        high  = self.df["high"]
        low   = self.df["low"]
        close = self.df["close"]

        lowest_low   = low.rolling(k_period).min()
        highest_high = high.rolling(k_period).max()
        denom        = (highest_high - lowest_low).replace(0, np.nan)

        raw_k = 100 * (close - lowest_low) / denom
        k     = raw_k.rolling(smooth_k).mean()
        d     = k.rolling(d_period).mean()

        return pd.DataFrame({"stoch_k": k, "stoch_d": d})

    def cci(self, period: int = 20, source: str = "hlc3") -> pd.Series:
        """
        CCI — Commodity Channel Index.
        CCI = (Typical Price - SMA) / (0.015 * Mean Deviation)
        """
        tp      = self._src(source)
        sma     = tp.rolling(period).mean()
        mad     = tp.rolling(period).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True)
        cci_val = (tp - sma) / (0.015 * mad.replace(0, np.nan))
        return cci_val.rename(f"CCI_{period}")

    def adx(self, period: int = 14) -> pd.DataFrame:
        """
        ADX — Average Directional Index with +DI and -DI.
        Uses RMA (Wilder's smoothing) to match TradingView.
        Returns DataFrame: adx, plus_di, minus_di
        """
        high  = self.df["high"]
        low   = self.df["low"]
        close = self.df["close"]

        tr      = self._true_range()
        plus_dm = (high.diff()).clip(lower=0)
        minus_dm = (-low.diff()).clip(lower=0)

        # Where +DM > -DM, keep +DM else 0 (and vice versa)
        plus_dm  = plus_dm.where(plus_dm > minus_dm, 0)
        minus_dm = minus_dm.where(minus_dm > plus_dm.where(plus_dm > minus_dm, 0), 0)

        alpha    = 1.0 / period
        n        = len(tr)
        atr_vals = np.full(n, np.nan)
        pdm_vals = np.full(n, np.nan)
        mdm_vals = np.full(n, np.nan)

        tr_v  = tr.values
        pdm_v = plus_dm.values
        mdm_v = minus_dm.values

        start = period
        if start < n:
            atr_vals[start] = np.nanmean(tr_v[1:start + 1])
            pdm_vals[start] = np.nanmean(pdm_v[1:start + 1])
            mdm_vals[start] = np.nanmean(mdm_v[1:start + 1])

            for i in range(start + 1, n):
                atr_vals[i] = alpha * tr_v[i]  + (1 - alpha) * atr_vals[i - 1]
                pdm_vals[i] = alpha * pdm_v[i] + (1 - alpha) * pdm_vals[i - 1]
                mdm_vals[i] = alpha * mdm_v[i] + (1 - alpha) * mdm_vals[i - 1]

        atr_s  = pd.Series(atr_vals, index=tr.index)
        pdm_s  = pd.Series(pdm_vals, index=tr.index)
        mdm_s  = pd.Series(mdm_vals, index=tr.index)

        plus_di  = 100 * pdm_s / atr_s.replace(0, np.nan)
        minus_di = 100 * mdm_s / atr_s.replace(0, np.nan)
        dx       = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)

        # ADX = RMA of DX
        adx_vals = np.full(n, np.nan)
        dx_v     = dx.values
        adx_start = start + period - 1
        if adx_start < n:
            adx_vals[adx_start] = np.nanmean(dx_v[start:adx_start + 1])
            for i in range(adx_start + 1, n):
                if not np.isnan(dx_v[i]):
                    adx_vals[i] = alpha * dx_v[i] + (1 - alpha) * adx_vals[i - 1]

        return pd.DataFrame({
            "adx":      pd.Series(adx_vals, index=tr.index),
            "plus_di":  plus_di,
            "minus_di": minus_di,
        })

    def williams_r(self, period: int = 14) -> pd.Series:
        """Williams %R — oscillates between -100 and 0."""
        high  = self.df["high"].rolling(period).max()
        low   = self.df["low"].rolling(period).min()
        close = self.df["close"]
        wr    = -100 * (high - close) / (high - low).replace(0, np.nan)
        return wr.rename(f"WILLR_{period}")

    def roc(self, period: int = 9, source: str = "close") -> pd.Series:
        """Rate of Change — percentage change over N periods."""
        src = self._src(source)
        return (src.pct_change(period) * 100).rename(f"ROC_{period}")

    # ══════════════════════════════════════════════════════════════
    # VOLATILITY INDICATORS
    # ══════════════════════════════════════════════════════════════

    def _true_range(self) -> pd.Series:
        """True Range (internal helper)."""
        high  = self.df["high"]
        low   = self.df["low"]
        close = self.df["close"]
        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low  - prev_close).abs(),
        ], axis=1).max(axis=1)
        return tr.rename("TR")

    def _atr_raw(self, period: int = 14) -> pd.Series:
        """ATR computed via RMA — internal helper for Supertrend etc."""
        tr = self._true_range()
        # Feed TR series into rma-like computation
        alpha  = 1.0 / period
        values = tr.values
        result = np.full(len(values), np.nan)
        start  = period
        if start < len(values):
            result[start] = np.nanmean(values[1:start + 1])
            for i in range(start + 1, len(values)):
                if not np.isnan(values[i]):
                    result[i] = alpha * values[i] + (1 - alpha) * result[i - 1]
        return pd.Series(result, index=tr.index, name=f"ATR_{period}")

    def atr(self, period: int = 14) -> pd.Series:
        """ATR — Average True Range using Wilder's RMA."""
        return self._atr_raw(period).rename(f"ATR_{period}")

    def bollinger_bands(
        self,
        period: int = 20,
        std_dev: float = 2.0,
        source: str = "close",
    ) -> pd.DataFrame:
        """
        Bollinger Bands — upper, middle (SMA), lower.
        Matches TradingView bb().
        """
        src    = self._src(source)
        middle = src.rolling(period).mean()
        std    = src.rolling(period).std(ddof=0)   # population std, matches TV
        upper  = middle + std_dev * std
        lower  = middle - std_dev * std
        width  = (upper - lower) / middle.replace(0, np.nan) * 100
        pct_b  = (src - lower) / (upper - lower).replace(0, np.nan)

        return pd.DataFrame({
            "bb_upper":  upper,
            "bb_middle": middle,
            "bb_lower":  lower,
            "bb_width":  width,
            "bb_pct_b":  pct_b,
        })

    def keltner_channel(
        self,
        ema_period: int = 20,
        atr_period: int = 10,
        multiplier: float = 2.0,
        source: str = "close",
    ) -> pd.DataFrame:
        """Keltner Channel — EMA ± multiplier × ATR."""
        middle = self.ema(ema_period, source)
        atr_v  = self._atr_raw(atr_period)
        upper  = middle + multiplier * atr_v
        lower  = middle - multiplier * atr_v

        return pd.DataFrame({
            "kc_upper":  upper,
            "kc_middle": middle,
            "kc_lower":  lower,
        })

    def donchian_channel(self, period: int = 20) -> pd.DataFrame:
        """Donchian Channel — highest high / lowest low over N periods."""
        upper  = self.df["high"].rolling(period).max()
        lower  = self.df["low"].rolling(period).min()
        middle = (upper + lower) / 2

        return pd.DataFrame({
            "dc_upper":  upper,
            "dc_middle": middle,
            "dc_lower":  lower,
        })

    # ══════════════════════════════════════════════════════════════
    # VOLUME INDICATORS
    # ══════════════════════════════════════════════════════════════

    def obv(self) -> pd.Series:
        """On-Balance Volume."""
        close  = self.df["close"]
        volume = self.df["volume"]
        direction = np.sign(close.diff()).fillna(0)
        obv_vals  = (direction * volume).cumsum()
        return obv_vals.rename("OBV")

    def mfi(self, period: int = 14) -> pd.Series:
        """
        Money Flow Index — volume-weighted RSI.
        Range: 0–100. Overbought >80, Oversold <20.
        """
        tp     = (self.df["high"] + self.df["low"] + self.df["close"]) / 3
        volume = self.df["volume"]
        mf     = tp * volume
        delta  = tp.diff()

        pos_mf = mf.where(delta > 0, 0)
        neg_mf = mf.where(delta < 0, 0)

        pos_sum = pos_mf.rolling(period).sum()
        neg_sum = neg_mf.rolling(period).sum().abs()

        mfi_vals = 100 - 100 / (1 + pos_sum / neg_sum.replace(0, np.nan))
        return mfi_vals.rename(f"MFI_{period}")

    def cmf(self, period: int = 20) -> pd.Series:
        """
        Chaikin Money Flow.
        Range: -1 to +1. Positive = buying pressure.
        """
        high   = self.df["high"]
        low    = self.df["low"]
        close  = self.df["close"]
        volume = self.df["volume"]

        hl_diff = (high - low).replace(0, np.nan)
        clv     = ((close - low) - (high - close)) / hl_diff  # Money Flow Multiplier
        mf_vol  = clv * volume

        cmf_vals = mf_vol.rolling(period).sum() / volume.rolling(period).sum().replace(0, np.nan)
        return cmf_vals.rename(f"CMF_{period}")

    # ══════════════════════════════════════════════════════════════
    # CANDLESTICK PATTERNS
    # ══════════════════════════════════════════════════════════════

    def _body(self) -> pd.Series:
        return (self.df["close"] - self.df["open"]).abs()

    def _range(self) -> pd.Series:
        return self.df["high"] - self.df["low"]

    def _upper_wick(self) -> pd.Series:
        return self.df["high"] - self.df[["open", "close"]].max(axis=1)

    def _lower_wick(self) -> pd.Series:
        return self.df[["open", "close"]].min(axis=1) - self.df["low"]

    def pattern_doji(self, body_pct: float = 0.1) -> pd.Series:
        """
        Doji — body is very small relative to range.
        body_pct: max body/range ratio (default 10%).
        Returns bool Series — True where pattern detected.
        """
        body  = self._body()
        rng   = self._range().replace(0, np.nan)
        doji  = (body / rng) < body_pct
        return doji.rename("Doji")

    def pattern_hammer(self) -> pd.Series:
        """
        Hammer — small body at top, long lower wick, minimal upper wick.
        Bullish reversal at bottom of downtrend.
        Criteria:
          - lower wick >= 2 × body
          - upper wick <= 0.1 × range
          - body in upper third of candle
        """
        body  = self._body()
        rng   = self._range().replace(0, np.nan)
        lwick = self._lower_wick()
        uwick = self._upper_wick()

        hammer = (
            (lwick >= 2 * body) &
            (uwick <= 0.1 * rng) &
            (body > 0)
        )
        return hammer.rename("Hammer")

    def pattern_shooting_star(self) -> pd.Series:
        """
        Shooting Star — small body at bottom, long upper wick.
        Bearish reversal at top of uptrend.
        """
        body  = self._body()
        rng   = self._range().replace(0, np.nan)
        lwick = self._lower_wick()
        uwick = self._upper_wick()

        star = (
            (uwick >= 2 * body) &
            (lwick <= 0.1 * rng) &
            (body > 0)
        )
        return star.rename("ShootingStar")

    def pattern_bullish_engulfing(self) -> pd.Series:
        """
        Bullish Engulfing:
          - Previous candle is bearish (close < open)
          - Current candle is bullish (close > open)
          - Current body fully engulfs previous body
        """
        o = self.df["open"]
        c = self.df["close"]

        prev_bear  = c.shift(1) < o.shift(1)
        curr_bull  = c > o
        engulfs    = (c > o.shift(1)) & (o < c.shift(1))

        return (prev_bear & curr_bull & engulfs).rename("BullEngulfing")

    def pattern_bearish_engulfing(self) -> pd.Series:
        """
        Bearish Engulfing:
          - Previous candle is bullish
          - Current candle is bearish
          - Current body fully engulfs previous body
        """
        o = self.df["open"]
        c = self.df["close"]

        prev_bull  = c.shift(1) > o.shift(1)
        curr_bear  = c < o
        engulfs    = (c < o.shift(1)) & (o > c.shift(1))

        return (prev_bull & curr_bear & engulfs).rename("BearEngulfing")

    def pattern_morning_star(self) -> pd.Series:
        """
        Morning Star — 3-bar bullish reversal:
          Bar 1: large bearish candle
          Bar 2: small body (doji-like) gapping down
          Bar 3: large bullish candle closing > midpoint of bar 1
        """
        o = self.df["open"]
        c = self.df["close"]

        bar1_bear  = (c.shift(2) < o.shift(2)) & ((o.shift(2) - c.shift(2)) > 0.01 * o.shift(2))
        bar2_small = self._body() / self._range().replace(0, np.nan) < 0.35
        bar3_bull  = (c > o) & (c > (o.shift(2) + c.shift(2)) / 2)

        return (bar1_bear & bar2_small.shift(1) & bar3_bull).rename("MorningStar")

    def pattern_evening_star(self) -> pd.Series:
        """
        Evening Star — 3-bar bearish reversal:
          Bar 1: large bullish candle
          Bar 2: small body gapping up
          Bar 3: large bearish candle closing < midpoint of bar 1
        """
        o = self.df["open"]
        c = self.df["close"]

        bar1_bull  = (c.shift(2) > o.shift(2)) & ((c.shift(2) - o.shift(2)) > 0.01 * o.shift(2))
        bar2_small = self._body() / self._range().replace(0, np.nan) < 0.35
        bar3_bear  = (c < o) & (c < (o.shift(2) + c.shift(2)) / 2)

        return (bar1_bull & bar2_small.shift(1) & bar3_bear).rename("EveningStar")

    # ══════════════════════════════════════════════════════════════
    # CONVENIENCE — Get all latest values (for Strategy Builder)
    # ══════════════════════════════════════════════════════════════

    def latest(self, series_or_df) -> Any:
        """Return last non-NaN value(s) from a Series or DataFrame."""
        if isinstance(series_or_df, pd.Series):
            val = series_or_df.dropna()
            return float(val.iloc[-1]) if len(val) else np.nan
        elif isinstance(series_or_df, pd.DataFrame):
            return {col: self.latest(series_or_df[col]) for col in series_or_df.columns}

    def snapshot(self) -> Dict[str, Any]:
        """
        Compute and return the latest value of every standard indicator.
        Used by the Strategy Builder to evaluate conditions on the last bar.
        """
        result = {}

        # Trend
        for p in [9, 20, 50, 200]:
            result[f"SMA_{p}"]  = self.latest(self.sma(p))
            result[f"EMA_{p}"]  = self.latest(self.ema(p))
        result["WMA_20"]     = self.latest(self.wma(20))
        result["DEMA_20"]    = self.latest(self.dema(20))
        result["VWAP"]       = self.latest(self.vwap())

        st = self.supertrend()
        result["Supertrend"]           = self.latest(st["supertrend"])
        result["Supertrend_Direction"] = int(self.latest(st["direction"]))

        # Momentum
        result["RSI_14"]     = self.latest(self.rsi(14))
        result["RSI_9"]      = self.latest(self.rsi(9))

        macd_df = self.macd()
        result["MACD"]       = self.latest(macd_df["macd"])
        result["MACD_Signal"] = self.latest(macd_df["signal"])
        result["MACD_Hist"]  = self.latest(macd_df["histogram"])

        stoch = self.stochastic()
        result["Stoch_K"]    = self.latest(stoch["stoch_k"])
        result["Stoch_D"]    = self.latest(stoch["stoch_d"])

        result["CCI_20"]     = self.latest(self.cci(20))
        result["WilliamsR"]  = self.latest(self.williams_r(14))
        result["ROC_9"]      = self.latest(self.roc(9))

        adx_df = self.adx()
        result["ADX"]        = self.latest(adx_df["adx"])
        result["ADX_PlusDI"] = self.latest(adx_df["plus_di"])
        result["ADX_MinusDI"]= self.latest(adx_df["minus_di"])

        # Volatility
        result["ATR_14"]     = self.latest(self.atr(14))
        bb = self.bollinger_bands()
        result["BB_Upper"]   = self.latest(bb["bb_upper"])
        result["BB_Middle"]  = self.latest(bb["bb_middle"])
        result["BB_Lower"]   = self.latest(bb["bb_lower"])
        result["BB_Width"]   = self.latest(bb["bb_width"])

        kc = self.keltner_channel()
        result["KC_Upper"]   = self.latest(kc["kc_upper"])
        result["KC_Middle"]  = self.latest(kc["kc_middle"])
        result["KC_Lower"]   = self.latest(kc["kc_lower"])

        dc = self.donchian_channel()
        result["DC_Upper"]   = self.latest(dc["dc_upper"])
        result["DC_Lower"]   = self.latest(dc["dc_lower"])

        # Volume
        result["OBV"]        = self.latest(self.obv())
        result["MFI_14"]     = self.latest(self.mfi(14))
        result["CMF_20"]     = self.latest(self.cmf(20))

        # Candle patterns (last bar True/False)
        result["Pat_Doji"]          = bool(self.pattern_doji().iloc[-1])
        result["Pat_Hammer"]        = bool(self.pattern_hammer().iloc[-1])
        result["Pat_ShootingStar"]  = bool(self.pattern_shooting_star().iloc[-1])
        result["Pat_BullEngulf"]    = bool(self.pattern_bullish_engulfing().iloc[-1])
        result["Pat_BearEngulf"]    = bool(self.pattern_bearish_engulfing().iloc[-1])
        result["Pat_MorningStar"]   = bool(self.pattern_morning_star().iloc[-1])
        result["Pat_EveningStar"]   = bool(self.pattern_evening_star().iloc[-1])

        return result
