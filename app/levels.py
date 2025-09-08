def atr(series, period=14):
    trs=[]
    prev_close=None
    for c in series:
        h,l,cl = c["high"], c["low"], c["close"]
        if prev_close is None:
            tr = h-l
        else:
            tr = max(h-l, abs(h-prev_close), abs(l-prev_close))
        trs.append(tr); prev_close=cl
    if len(trs) < period: return None
    return sum(trs[-period:])/period

def pivots_floor(prev_day):
    H,L,C = prev_day["high"], prev_day["low"], prev_day["close"]
    P = (H+L+C)/3
    R1 = 2*P - L; S1 = 2*P - H
    R2 = P + (H-L); S2 = P - (H-L)
    return {"P":P,"R1":R1,"S1":S1,"R2":R2,"S2":S2}

def educational_levels(close, atr_val, support, resistance, k=1.5):
    if atr_val is None or close is None: return None
    R = k*atr_val
    return {
        "risk_distance": R,
        "levels": {"support": support, "resistance": resistance},
        "long_case": {
            "note": "при закреплении выше сопротивления некоторые трейдеры рассматривают продолжение роста",
            "tp": [round(close+R,2), round(close+2*R,2), round(close+3*R,2)]
        },
        "short_case": {
            "note": "при уходе ниже поддержки некоторые трейдеры отмечают слабость",
            "tp": [round(close-R,2), round(close-2*R,2), round(close-3*R,2)]
        }
    }
