import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from .config import TIMEZONE, POLL_SEC
from .storage import Session, User, Portfolio, Position, EventLog
from .llm import render_digest
from .moex import quotes_shares
import json, quotes_etf, quotes_bonds
from collections import defaultdict

def start_scheduler(bot):
    tz = pytz.timezone(TIMEZONE)
    sch = AsyncIOScheduler(timezone=tz)

    async def morning():
        s=Session()
        for u in s.query(User).all():
            if u.plan!="premium": continue
            await bot.send_message(int(u.tg_id),
                render_digest("Утро", ["Ключевые события дня", "Уровни внимания по твоим бумагам"]))
        s.close()

    async def midday():
        s=Session()
        for u in s.query(User).all():
            if u.plan!="premium": continue
            await bot.send_message(int(u.tg_id),
                render_digest("Середина дня", ["Рынок остаётся волатильным"]))
        s.close()

    async def evening():
        s=Session()
        for u in s.query(User).all():
            if u.plan!="premium": continue
            await bot.send_message(int(u.tg_id),
                render_digest("Итоги дня", ["Лидеры/аутсайдеры по портфелю", "Что смотреть завтра"]))
        s.close()

    sch.add_job(morning, "cron", hour=8, minute=30)
    sch.add_job(midday,  "cron", hour=15, minute=0)
    sch.add_job(evening, "cron", hour=18, minute=30)

    async def triggers_job():
        s = Session()
        try:
            users = s.query(User).all()
            for u in users:
                if u.plan != "premium" or not u.plan_valid_to or u.plan_valid_to <= datetime.utcnow():
                    continue
                pf = s.query(Portfolio).filter_by(user_id=u.id).first()
                if not pf: continue
                positions = s.query(Position).filter_by(portfolio_id=pf.id).all()
                if not positions: continue
                boards = defaultdict(list)
                for p in positions:
                    if p.board in ("TQBR","TQTF","TQOB"):
                        boards[p.board].append(p.ticker)
                quotes = {}
                if boards.get("TQBR"):
                    quotes.update(quotes_shares(list(set(boards["TQBR"]))))
                if boards.get("TQTF"):
                    quotes.update(quotes_etf(list(set(boards["TQTF"]))))
                if boards.get("TQOB"):
                    quotes.update(quotes_bonds(list(set(boards["TQOB"]))))
                def daily_count(uid):
                    today = datetime.utcnow().date()
                    start = datetime(today.year, today.month, today.day)
                    return s.query(EventLog).filter(EventLog.user_id==uid, EventLog.sent_at>=start).count()
                def recent(uid,ticker,mins=20):
                    since = datetime.utcnow()- timedelta(minutes=mins)
                    return s.query(EventLog).filter(EventLog.user_id==uid, EventLog.ticker==ticker, EventLog.sent_at>=since).count()>0
                for p in positions:
                    t = p.ticker
                    q = quotes.get(t)
                    if not q: continue
                    ch = q.get("change_pct")
                    if ch is None: continue
                    try:
                        if abs(float(ch)) >= 5 and not recent(u.id,ticker=t) and daily_count(u.id) < 8:
                            text = f"⚡ Событие по {t}: значимое дневное изменение (цена {q.get('last')}, Δдень {ch}%).\n"                                    f"Некоторые трейдеры рассматривают такие движения как важные для сценария.\n"                                    f"ℹ️ Аналитика и обучение. Не является индивидуальной инвестрекомендацией."
                            await bot.send_message(int(u.tg_id), text)
                            ev = EventLog(user_id=u.id, ticker=t, event_type="trigger", payload={"change_pct":ch}, sent_at=datetime.utcnow())
                            s.add(ev); s.commit()
                    except Exception:
                        pass
        finally:
            s.close()

    sch.add_job(triggers_job, "interval", seconds=POLL_SEC)
    sch.start()
