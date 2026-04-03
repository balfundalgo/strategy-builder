"""
core/indicator_registry.py
───────────────────────────────────────────────────────────────────
Central registry of all indicators available in the Strategy Builder.

This file drives:
  - Dropdown menus in the Strategy Builder UI (what indicators exist)
  - Parameter forms (what settings each indicator has)
  - Condition operators (crosses above, is above, is below, etc.)
  - How to compute & compare each indicator pair

Structure per indicator:
  name        : Display name shown in UI dropdown
  key         : Internal key used in IndicatorEngine.snapshot()
  category    : Trend / Momentum / Volatility / Volume / Pattern / Price
  params      : List of user-configurable parameters with defaults
  outputs     : Sub-values available for comparison (e.g. MACD has macd, signal, histogram)
  operators   : Which condition operators apply
"""

from typing import List, Dict, Any

# ─────────────────────────────────────────────────────────────────────────────
# Operator definitions
# ─────────────────────────────────────────────────────────────────────────────

NUMERIC_OPERATORS = [
    "crosses above",
    "crosses below",
    "is above",
    "is below",
    "is equal to",
    "is greater than or equal to",
    "is less than or equal to",
]

BOOL_OPERATORS = [
    "is true",
    "is false",
]

SOURCE_OPTIONS = ["close", "open", "high", "low", "hl2", "hlc3", "ohlc4"]

# ─────────────────────────────────────────────────────────────────────────────
# Indicator definitions
# ─────────────────────────────────────────────────────────────────────────────

INDICATORS: List[Dict[str, Any]] = [

    # ══════════════════════════════════════
    # PRICE (built-in, no calculation)
    # ══════════════════════════════════════
    {
        "name":      "Price",
        "key":       "price",
        "category":  "Price",
        "params":    [
            {"name": "source", "type": "select", "options": SOURCE_OPTIONS, "default": "close", "label": "Source"},
        ],
        "outputs":   [{"key": "value", "label": "Price"}],
        "operators": NUMERIC_OPERATORS,
    },

    # ══════════════════════════════════════
    # TREND
    # ══════════════════════════════════════
    {
        "name":      "EMA",
        "key":       "ema",
        "category":  "Trend",
        "params":    [
            {"name": "period", "type": "int",    "default": 20,      "min": 1,   "max": 500, "label": "Period"},
            {"name": "source", "type": "select", "options": SOURCE_OPTIONS, "default": "close", "label": "Source"},
        ],
        "outputs":   [{"key": "value", "label": "EMA"}],
        "operators": NUMERIC_OPERATORS,
    },
    {
        "name":      "SMA",
        "key":       "sma",
        "category":  "Trend",
        "params":    [
            {"name": "period", "type": "int",    "default": 20,  "min": 1, "max": 500, "label": "Period"},
            {"name": "source", "type": "select", "options": SOURCE_OPTIONS, "default": "close", "label": "Source"},
        ],
        "outputs":   [{"key": "value", "label": "SMA"}],
        "operators": NUMERIC_OPERATORS,
    },
    {
        "name":      "WMA",
        "key":       "wma",
        "category":  "Trend",
        "params":    [
            {"name": "period", "type": "int",    "default": 20,  "min": 1, "max": 500, "label": "Period"},
            {"name": "source", "type": "select", "options": SOURCE_OPTIONS, "default": "close", "label": "Source"},
        ],
        "outputs":   [{"key": "value", "label": "WMA"}],
        "operators": NUMERIC_OPERATORS,
    },
    {
        "name":      "DEMA",
        "key":       "dema",
        "category":  "Trend",
        "params":    [
            {"name": "period", "type": "int", "default": 20, "min": 1, "max": 500, "label": "Period"},
        ],
        "outputs":   [{"key": "value", "label": "DEMA"}],
        "operators": NUMERIC_OPERATORS,
    },
    {
        "name":      "VWAP",
        "key":       "vwap",
        "category":  "Trend",
        "params":    [],   # no params — daily session reset
        "outputs":   [{"key": "VWAP", "label": "VWAP"}],
        "operators": NUMERIC_OPERATORS,
    },
    {
        "name":      "Supertrend",
        "key":       "supertrend",
        "category":  "Trend",
        "params":    [
            {"name": "period",     "type": "int",   "default": 7,   "min": 1, "max": 100, "label": "ATR Period"},
            {"name": "multiplier", "type": "float", "default": 3.0, "min": 0.1, "max": 10.0, "label": "Multiplier"},
        ],
        "outputs":   [
            {"key": "supertrend", "label": "Supertrend Line"},
            {"key": "direction",  "label": "Direction (+1 Bull / -1 Bear)"},
        ],
        "operators": NUMERIC_OPERATORS,
    },
    {
        "name":      "Ichimoku",
        "key":       "ichimoku",
        "category":  "Trend",
        "params":    [
            {"name": "tenkan_period",   "type": "int", "default": 9,  "min": 1, "max": 100, "label": "Tenkan Period"},
            {"name": "kijun_period",    "type": "int", "default": 26, "min": 1, "max": 200, "label": "Kijun Period"},
            {"name": "senkou_b_period", "type": "int", "default": 52, "min": 1, "max": 500, "label": "Senkou B Period"},
        ],
        "outputs":   [
            {"key": "tenkan",   "label": "Tenkan (Conversion)"},
            {"key": "kijun",    "label": "Kijun (Base)"},
            {"key": "senkou_a", "label": "Senkou A"},
            {"key": "senkou_b", "label": "Senkou B"},
        ],
        "operators": NUMERIC_OPERATORS,
    },

    # ══════════════════════════════════════
    # MOMENTUM
    # ══════════════════════════════════════
    {
        "name":      "RSI",
        "key":       "rsi",
        "category":  "Momentum",
        "params":    [
            {"name": "period", "type": "int",    "default": 14, "min": 1, "max": 100, "label": "Period"},
            {"name": "source", "type": "select", "options": SOURCE_OPTIONS, "default": "close", "label": "Source"},
        ],
        "outputs":   [{"key": "value", "label": "RSI"}],
        "operators": NUMERIC_OPERATORS,
    },
    {
        "name":      "MACD",
        "key":       "macd",
        "category":  "Momentum",
        "params":    [
            {"name": "fast",   "type": "int", "default": 12, "min": 1, "max": 200, "label": "Fast Period"},
            {"name": "slow",   "type": "int", "default": 26, "min": 1, "max": 200, "label": "Slow Period"},
            {"name": "signal", "type": "int", "default": 9,  "min": 1, "max": 100, "label": "Signal Period"},
        ],
        "outputs":   [
            {"key": "macd",      "label": "MACD Line"},
            {"key": "signal",    "label": "Signal Line"},
            {"key": "histogram", "label": "Histogram"},
        ],
        "operators": NUMERIC_OPERATORS,
    },
    {
        "name":      "Stochastic",
        "key":       "stochastic",
        "category":  "Momentum",
        "params":    [
            {"name": "k_period", "type": "int", "default": 14, "min": 1, "max": 100, "label": "%K Period"},
            {"name": "d_period", "type": "int", "default": 3,  "min": 1, "max": 50,  "label": "%D Period"},
            {"name": "smooth_k", "type": "int", "default": 3,  "min": 1, "max": 50,  "label": "Smooth K"},
        ],
        "outputs":   [
            {"key": "stoch_k", "label": "%K"},
            {"key": "stoch_d", "label": "%D"},
        ],
        "operators": NUMERIC_OPERATORS,
    },
    {
        "name":      "CCI",
        "key":       "cci",
        "category":  "Momentum",
        "params":    [
            {"name": "period", "type": "int", "default": 20, "min": 1, "max": 200, "label": "Period"},
        ],
        "outputs":   [{"key": "value", "label": "CCI"}],
        "operators": NUMERIC_OPERATORS,
    },
    {
        "name":      "ADX",
        "key":       "adx",
        "category":  "Momentum",
        "params":    [
            {"name": "period", "type": "int", "default": 14, "min": 1, "max": 100, "label": "Period"},
        ],
        "outputs":   [
            {"key": "adx",      "label": "ADX"},
            {"key": "plus_di",  "label": "+DI"},
            {"key": "minus_di", "label": "-DI"},
        ],
        "operators": NUMERIC_OPERATORS,
    },
    {
        "name":      "Williams %R",
        "key":       "williams_r",
        "category":  "Momentum",
        "params":    [
            {"name": "period", "type": "int", "default": 14, "min": 1, "max": 100, "label": "Period"},
        ],
        "outputs":   [{"key": "value", "label": "Williams %R"}],
        "operators": NUMERIC_OPERATORS,
    },
    {
        "name":      "ROC",
        "key":       "roc",
        "category":  "Momentum",
        "params":    [
            {"name": "period", "type": "int", "default": 9, "min": 1, "max": 200, "label": "Period"},
        ],
        "outputs":   [{"key": "value", "label": "ROC %"}],
        "operators": NUMERIC_OPERATORS,
    },

    # ══════════════════════════════════════
    # VOLATILITY
    # ══════════════════════════════════════
    {
        "name":      "ATR",
        "key":       "atr",
        "category":  "Volatility",
        "params":    [
            {"name": "period", "type": "int", "default": 14, "min": 1, "max": 100, "label": "Period"},
        ],
        "outputs":   [{"key": "value", "label": "ATR"}],
        "operators": NUMERIC_OPERATORS,
    },
    {
        "name":      "Bollinger Bands",
        "key":       "bollinger_bands",
        "category":  "Volatility",
        "params":    [
            {"name": "period",  "type": "int",   "default": 20,  "min": 1, "max": 200,  "label": "Period"},
            {"name": "std_dev", "type": "float", "default": 2.0, "min": 0.1, "max": 5.0, "label": "Std Dev"},
        ],
        "outputs":   [
            {"key": "bb_upper",  "label": "Upper Band"},
            {"key": "bb_middle", "label": "Middle Band"},
            {"key": "bb_lower",  "label": "Lower Band"},
            {"key": "bb_width",  "label": "Band Width"},
            {"key": "bb_pct_b",  "label": "%B"},
        ],
        "operators": NUMERIC_OPERATORS,
    },
    {
        "name":      "Keltner Channel",
        "key":       "keltner_channel",
        "category":  "Volatility",
        "params":    [
            {"name": "ema_period",  "type": "int",   "default": 20,  "min": 1, "max": 200,  "label": "EMA Period"},
            {"name": "atr_period",  "type": "int",   "default": 10,  "min": 1, "max": 100,  "label": "ATR Period"},
            {"name": "multiplier",  "type": "float", "default": 2.0, "min": 0.1, "max": 5.0, "label": "Multiplier"},
        ],
        "outputs":   [
            {"key": "kc_upper",  "label": "Upper"},
            {"key": "kc_middle", "label": "Middle"},
            {"key": "kc_lower",  "label": "Lower"},
        ],
        "operators": NUMERIC_OPERATORS,
    },
    {
        "name":      "Donchian Channel",
        "key":       "donchian_channel",
        "category":  "Volatility",
        "params":    [
            {"name": "period", "type": "int", "default": 20, "min": 1, "max": 500, "label": "Period"},
        ],
        "outputs":   [
            {"key": "dc_upper",  "label": "Upper"},
            {"key": "dc_middle", "label": "Middle"},
            {"key": "dc_lower",  "label": "Lower"},
        ],
        "operators": NUMERIC_OPERATORS,
    },

    # ══════════════════════════════════════
    # VOLUME
    # ══════════════════════════════════════
    {
        "name":      "OBV",
        "key":       "obv",
        "category":  "Volume",
        "params":    [],
        "outputs":   [{"key": "OBV", "label": "OBV"}],
        "operators": NUMERIC_OPERATORS,
    },
    {
        "name":      "MFI",
        "key":       "mfi",
        "category":  "Volume",
        "params":    [
            {"name": "period", "type": "int", "default": 14, "min": 1, "max": 100, "label": "Period"},
        ],
        "outputs":   [{"key": "value", "label": "MFI"}],
        "operators": NUMERIC_OPERATORS,
    },
    {
        "name":      "CMF",
        "key":       "cmf",
        "category":  "Volume",
        "params":    [
            {"name": "period", "type": "int", "default": 20, "min": 1, "max": 100, "label": "Period"},
        ],
        "outputs":   [{"key": "value", "label": "CMF"}],
        "operators": NUMERIC_OPERATORS,
    },

    # ══════════════════════════════════════
    # CANDLESTICK PATTERNS
    # ══════════════════════════════════════
    {
        "name":      "Doji",
        "key":       "pattern_doji",
        "category":  "Pattern",
        "params":    [
            {"name": "body_pct", "type": "float", "default": 0.1, "min": 0.01, "max": 0.5, "label": "Max Body %"},
        ],
        "outputs":   [{"key": "value", "label": "Doji Detected"}],
        "operators": BOOL_OPERATORS,
    },
    {
        "name":      "Hammer",
        "key":       "pattern_hammer",
        "category":  "Pattern",
        "params":    [],
        "outputs":   [{"key": "value", "label": "Hammer Detected"}],
        "operators": BOOL_OPERATORS,
    },
    {
        "name":      "Shooting Star",
        "key":       "pattern_shooting_star",
        "category":  "Pattern",
        "params":    [],
        "outputs":   [{"key": "value", "label": "Shooting Star Detected"}],
        "operators": BOOL_OPERATORS,
    },
    {
        "name":      "Bullish Engulfing",
        "key":       "pattern_bullish_engulfing",
        "category":  "Pattern",
        "params":    [],
        "outputs":   [{"key": "value", "label": "Pattern Detected"}],
        "operators": BOOL_OPERATORS,
    },
    {
        "name":      "Bearish Engulfing",
        "key":       "pattern_bearish_engulfing",
        "category":  "Pattern",
        "params":    [],
        "outputs":   [{"key": "value", "label": "Pattern Detected"}],
        "operators": BOOL_OPERATORS,
    },
    {
        "name":      "Morning Star",
        "key":       "pattern_morning_star",
        "category":  "Pattern",
        "params":    [],
        "outputs":   [{"key": "value", "label": "Pattern Detected"}],
        "operators": BOOL_OPERATORS,
    },
    {
        "name":      "Evening Star",
        "key":       "pattern_evening_star",
        "category":  "Pattern",
        "params":    [],
        "outputs":   [{"key": "value", "label": "Pattern Detected"}],
        "operators": BOOL_OPERATORS,
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# Lookup helpers used by Strategy Builder UI
# ─────────────────────────────────────────────────────────────────────────────

# All indicator names grouped by category (for dropdown menus)
def get_by_category() -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = {}
    for ind in INDICATORS:
        cat = ind["category"]
        result.setdefault(cat, []).append(ind["name"])
    return result

# Fast lookup by name
_BY_NAME = {ind["name"]: ind for ind in INDICATORS}
_BY_KEY  = {ind["key"]:  ind for ind in INDICATORS}

def get_by_name(name: str) -> Dict:
    return _BY_NAME.get(name, {})

def get_by_key(key: str) -> Dict:
    return _BY_KEY.get(key, {})

def all_names() -> List[str]:
    return [ind["name"] for ind in INDICATORS]

def all_categories() -> List[str]:
    seen = []
    for ind in INDICATORS:
        if ind["category"] not in seen:
            seen.append(ind["category"])
    return seen
