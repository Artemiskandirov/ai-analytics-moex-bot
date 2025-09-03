import requests, datetime as dt
import logging
from .config import BOARD_SHARES, BOARD_ETF, BOARD_BONDS

logger = logging.getLogger(__name__)

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
        frm = (dt.date.today()-dt.timedelta(days=30)).isoformat()
    url = f"https://iss.moex.com/iss/engines/stock/markets/shares/boards/{board}/securities/{secid}/candles.json"
    params={"from": frm, "interval": interval, "iss.json":"extended"}
    data = _get(url, params)
    rows = data[1]["candles"]
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

def _normalize(data):
    m={}
    
    # Проверяем структуру ответа API
    if not data or len(data) < 2:
        logger.error(f"MOEX API: Unexpected data structure: {data}")
        return m
    
    # Проверяем наличие необходимых ключей
    securities_data = data[0].get("securities", []) if isinstance(data[0], dict) else []
    marketdata_data = data[1].get("marketdata", []) if isinstance(data[1], dict) else []
    
    if not securities_data or not marketdata_data:
        logger.error(f"MOEX API: Missing data - securities: {bool(securities_data)}, marketdata: {bool(marketdata_data)}")
        logger.error(f"MOEX API: data[0] keys: {list(data[0].keys()) if isinstance(data[0], dict) else 'not dict'}")
        logger.error(f"MOEX API: data[1] keys: {list(data[1].keys()) if isinstance(data[1], dict) else 'not dict'}")
        return m
    
    sec_by_id = {s["SECID"]: s for s in securities_data if isinstance(s, dict) and "SECID" in s}
    
    for row in marketdata_data:
        if not isinstance(row, dict):
            continue
        sid = row.get("SECID")
        if not sid: 
            continue
        m[sid] = {
            "last": row.get("LAST"), "open": row.get("OPEN"),
            "high": row.get("HIGH"), "low": row.get("LOW"),
            "change_pct": row.get("LASTCHANGEPRC"),
            "volume": row.get("VOLUME"),
            "board": sec_by_id.get(sid, {}).get("BOARDID")
        }
    return m
