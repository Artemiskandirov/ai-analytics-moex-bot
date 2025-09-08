from typing import List, Dict, Tuple

def sma(values: List[float], period: int) -> List[float]:
    out = []
    s = 0.0
    q = []
    for v in values:
        q.append(v)
        s += v
        if len(q) > period:
            s -= q.pop(0)
        out.append(s/len(q))
    return out

def atr_from_candles(candles: List[Dict], period: int = 14) -> List[float]:
    trs = []
    prev_close = None
    for c in candles:
        h, l, cl = c["high"], c["low"], c["close"]
        if prev_close is None:
            tr = h - l
        else:
            tr = max(h - l, abs(h - prev_close), abs(l - prev_close))
        trs.append(tr)
        prev_close = cl
    # simple moving average of TR to get ATR
    out = []
    s = 0.0
    q = []
    for tr in trs:
        q.append(tr)
        s += tr
        if len(q) > period:
            s -= q.pop(0)
        out.append(s/len(q))
    return out

def recent_swing_levels(closes: List[float], highs: List[float], lows: List[float], lookback: int = 60) -> Tuple[float, float]:
    if not closes:
        return None, None
    highs_win = highs[-lookback:] if len(highs) >= lookback else highs[:]
    lows_win  = lows[-lookback:]  if len(lows)  >= lookback else lows[:]
    swing_high = max(highs_win) if highs_win else None
    swing_low  = min(lows_win)  if lows_win else None
    return swing_high, swing_low

def pivot_levels(prev_high: float, prev_low: float, prev_close: float):
    P = (prev_high + prev_low + prev_close)/3.0
    R1 = 2*P - prev_low
    S1 = 2*P - prev_high
    R2 = P + (prev_high - prev_low)
    S2 = P - (prev_high - prev_low)
    return {"P":P, "R1":R1, "S1":S1, "R2":R2, "S2":S2}

def breakout_signals(closes: List[float], period_high: int = 20, period_low: int = 20):
    # Simple breakout signals:
    # BUY: close crosses above highest close over last N bars
    # SELL: close crosses below lowest close over last N bars
    buys, sells = [], []
    lookback = max(period_high, period_low)
    for i in range(lookback, len(closes)):
        hh = max(closes[i - period_high:i])
        ll = min(closes[i - period_low:i])
        if closes[i] > hh:
            buys.append(i)
        elif closes[i] < ll:
            sells.append(i)
    return buys, sells
