from aiogram import Router, types
from aiogram.filters import Command
from datetime import datetime, timedelta
import os
from .storage import Session, User, Portfolio
from .texts import HELLO, PAYWALL
from .config import PREMIUM_PRICE
from .moex import quotes_shares, candles
from .levels import atr, educational_levels
from .llm import render_trial_note
from .charts import render_price_chart

router = Router()
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "demo_code")

def get_or_create_user(tg_id):
    s=Session()
    u=s.query(User).filter_by(tg_id=str(tg_id)).first()
    if not u:
        u=User(tg_id=str(tg_id)); s.add(u); s.commit()
        p=Portfolio(user_id=u.id); s.add(p); s.commit()
    s.close()
    return u

@router.message(Command("start"))
async def cmd_start(m: types.Message):
    get_or_create_user(m.from_user.id)
    await m.answer(HELLO)

@router.message(Command("trial"))
async def cmd_trial(m: types.Message):
    s=Session(); u=s.query(User).filter_by(tg_id=str(m.from_user.id)).first()
    if u.free_trial_used:
        await m.answer(PAYWALL.format(price=PREMIUM_PRICE)); s.close(); return
    
    # Получаем тикер из команды или используем GAZP по умолчанию
    parts = (m.text or "").split()
    ticker = parts[1].upper() if len(parts) > 1 else "GAZP"
    
    q = quotes_shares([ticker]).get(ticker, {})
    if not q or not q.get("last"):
        await m.answer(f"Не удалось получить данные по тикеру {ticker}. Попробуйте другой тикер или используйте /trial без параметров для анализа GAZP.")
        s.close()
        return
        
    board = q.get("board","TQBR") if q else "TQBR"
    cs = candles(ticker, board, 24)
    atr14 = None
    if cs:
        series = [{"high":c["high"],"low":c["low"],"close":c["close"]} for c in cs][-50:]
        # простая оценка ATR как среднее истинных диапазонов последних 14 баров (см. levels.atr)
        atr14 = atr(series, period=14)
    levels = educational_levels(q.get("last"), atr14 or 1.0, support=(q.get("low") or 0), resistance=(q.get("high") or 0), k=1.5)
    note = render_trial_note(ticker, q, levels)
    await m.answer(note)
    u.free_trial_used=True; u.free_trial_used_at=datetime.utcnow(); u.trial_asset=ticker
    s.commit(); s.close()
    await m.answer(PAYWALL.format(price=PREMIUM_PRICE))

@router.message(Command("analyze"))
async def cmd_analyze(m: types.Message):
    s=Session(); u=s.query(User).filter_by(tg_id=str(m.from_user.id)).first()
    now=datetime.utcnow()
    if not (u.plan=="premium" and u.plan_valid_to and u.plan_valid_to>now):
        await m.answer(PAYWALL.format(price=PREMIUM_PRICE)); s.close(); return
    s.close()
    await m.answer("Твой аналитический дайджест по портфелю (demo).\n"
                   "Добавь позиции и уровни внимания — и я буду присылать обзоры.")

@router.message(Command("chart"))
async def cmd_chart(m: types.Message):
    parts = (m.text or "").split()
    if len(parts) < 2:
        await m.answer("Использование: /chart <ТИКЕР>, например: /chart GAZP")
        return
    ticker = parts[1].upper()
    q = quotes_shares([ticker]).get(ticker, {})
    board = q.get("board", "TQBR") or "TQBR"
    cs = candles(ticker, board, interval=24)
    sup = q.get("low")
    res = q.get("high")
    levels = {"levels":{"support": sup, "resistance": res}}
    try:
        path = render_price_chart(ticker, cs[-60:], levels=levels)
        with open(path, "rb") as ph:
            await m.bot.send_photo(chat_id=m.chat.id, photo=ph, caption=f"{ticker}: уровни внимания")
    except Exception as e:
        await m.answer(f"Не удалось построить график: {e}")

@router.message(Command("chart_ta"))
async def cmd_chart_ta(m: types.Message):
    parts = (m.text or "").split()
    if len(parts) < 2:
        await m.answer("Использование: /chart_ta <ТИКЕР>, например: /chart_ta MOEX")
        return
    ticker = parts[1].upper()
    q = quotes_shares([ticker]).get(ticker, {})
    board = q.get("board", "TQBR") or "TQBR"
    cs = candles(ticker, board, interval=24)
    try:
        from .charts import render_ta_chart
        path = render_ta_chart(ticker, cs[-200:])
        with open(path, "rb") as ph:
            await m.bot.send_photo(chat_id=m.chat.id, photo=ph, caption=f"{ticker}: TA график")
    except Exception as e:
        await m.answer(f"Не удалось построить TA-график: {e}")

@router.message(Command("verify"))
async def cmd_verify(m: types.Message):
    parts = (m.text or "").split()
    if len(parts) < 2:
        await m.answer("Введите код подтверждения оплаты: /verify <код>")
        return
    code = parts[1].strip()
    if code != VERIFY_TOKEN:
        await m.answer("Код не подошёл. Проверьте и повторите.")
        return
    s=Session(); u=s.query(User).filter_by(tg_id=str(m.from_user.id)).first()
    u.plan = "premium"
    u.plan_valid_to = (u.plan_valid_to or datetime.utcnow())
    if u.plan_valid_to < datetime.utcnow():
        u.plan_valid_to = datetime.utcnow()
    u.plan_valid_to += timedelta(days=30)
    s.commit(); s.close()
    await m.answer(f"Оплата подтверждена. Премиум активен до {u.plan_valid_to}. Спасибо!")
