import requests, datetime as dt
from .config import BOARD_SHARES, BOARD_ETF, BOARD_BONDS

UA = {"User-Agent": "ai-analytics-bot/1.0"}

def _get(url, params=None):
    r = requests.get(url, params=params, headers=UA, timeout=12)
    r.raise_for_status()
    return r.json()

def quotes_shares(tickers):
    base = f"https://iss.moex.com/iss/engines/stock/markets/shares/boards/{BOARD_SHARES}/securities.json"
    params={"securities":",".join(tickers),"iss.only":"marketdata,securities","iss.json":"extended"}
    return _normalize(_get(base, params))

def quotes_etf(tickers):
    base = f"https://iss.moex.com/iss/engines/stock/markets/shares/boards/{BOARD_ETF}/securities.json"
    params={"securities":",".join(tickers),"iss.only":"marketdata,securities","iss.json":"extended"}
    return _normalize(_get(base, params))

def quotes_bonds(isins):
    base = f"https://iss.moex.com/iss/engines/stock/markets/bonds/boards/{BOARD_BONDS}/securities.json"
    params={"securities":",".join(isins),"iss.only":"marketdata,securities","iss.json":"extended"}
    return _normalize(_get(base, params))

def candles(secid:str, board:str, interval:int=24, frm:str=None):
    if not frm:
        frm = (dt.date.today()-dt.timedelta(days=240)).isoformat()
    url = f"https://iss.moex.com/iss/engines/stock/markets/shares/boards/{board}/securities/{secid}/candles.json"
    params={"from": frm, "interval": interval, "iss.json":"extended"}
    try:
        data = _get(url, params)
        rows = data[1].get("candles", []) if len(data) > 1 else []
        out=[]
        for r in rows:
            out.append({
                "open": r.get("open"),
                "close": r.get("close"),
                "high": r.get("high"),
                "low":  r.get("low"),
                "value":r.get("value"),
                "volume": r.get("volume"),
                "begin": r.get("begin"),
                "end":   r.get("end"),
            })
        return out
    except Exception as e:
        print(f"Error getting candles for {secid}: {e}")
        return []

def _normalize(data):
    m={}
    try:
        # Безопасное получение данных с проверками
        if len(data) < 2:
            return m
        
        # MOEX возвращает структуру: [metadata, [actual_data]]
        md_block = data[1].get("marketdata", []) if len(data) > 1 else []
        sec_block = data[1].get("securities", []) if len(data) > 1 else []
        
        # Извлекаем фактические данные из второго элемента массива
        md = md_block[1] if len(md_block) > 1 and isinstance(md_block[1], list) else []
        sec = sec_block[1] if len(sec_block) > 1 and isinstance(sec_block[1], list) else []
        
        sec_by_id = {s.get("SECID"): s for s in sec if isinstance(s, dict) and s.get("SECID")}
        
        for row in md:
            if not isinstance(row, dict):
                continue
            sid = row.get("SECID")
            if not sid: 
                continue
            m[sid] = {
                "last": row.get("LAST"), 
                "open": row.get("OPEN"),
                "high": row.get("HIGH"), 
                "low": row.get("LOW"),
                "change_pct": row.get("LASTCHANGEPRCNT"),  # Исправил ключ
                "volume": row.get("VOLTODAY"),  # Исправил ключ
                "board": sec_by_id.get(sid, {}).get("BOARDID")
            }
    except Exception as e:
        print(f"Error normalizing MOEX data: {e}")
        print(f"Data structure keys: {list(data.keys()) if isinstance(data, dict) else 'not dict'}")
    return m
