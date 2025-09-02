import pytz, asyncio, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .config import TIMEZONE, POLL_SEC
from .storage import Session, User, EventLog, Portfolio, Position
from .llm import render_digest
from .moex import quotes_shares, quotes_etf, quotes_bonds
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

_last_push = {}  # dict {user_id: {ticker: last_ts}}

def start_scheduler(bot):
    tz = pytz.timezone(TIMEZONE)
    sch = AsyncIOScheduler(timezone=tz)

    async def morning():
        """Утренний дайджест с анализом портфелей"""
        s = Session()
        try:
            users = s.query(User).filter(User.plan == "premium").all()
            for u in users:
                try:
                    digest = generate_morning_digest(u, s)
                    if digest:
                        await bot.send_message(int(u.tg_id), digest)
                except Exception as e:
                    logger.error(f"Error sending morning digest to user {u.tg_id}: {e}")
        finally:
            s.close()

    async def midday():
        """Дневной дайджест с текущими показателями"""
        s = Session()
        try:
            users = s.query(User).filter(User.plan == "premium").all()
            for u in users:
                try:
                    digest = generate_midday_digest(u, s)
                    if digest:
                        await bot.send_message(int(u.tg_id), digest)
                except Exception as e:
                    logger.error(f"Error sending midday digest to user {u.tg_id}: {e}")
        finally:
            s.close()

    async def evening():
        """Вечерний дайджест с итогами дня"""
        s = Session()
        try:
            users = s.query(User).filter(User.plan == "premium").all()
            for u in users:
                try:
                    digest = generate_evening_digest(u, s)
                    if digest:
                        await bot.send_message(int(u.tg_id), digest)
                except Exception as e:
                    logger.error(f"Error sending evening digest to user {u.tg_id}: {e}")
        finally:
            s.close()

    async def triggers_job():
        s=Session()
        for u in s.query(User).all():
            if u.plan!="premium" or not u.triggers_enabled: continue
            # Для MVP проверим GAZP
            tickers = ["GAZP"]
            q = quotes_shares(tickers)
            now = time.time()
            for t in tickers:
                info = q.get(t)
                if not info: continue
                change = info.get("change_pct") or 0
                # Используем пользовательские пороги триггеров
                user_positive_threshold = float(u.trigger_threshold_positive or 5.0)
                user_negative_threshold = float(u.trigger_threshold_negative or -5.0)
                
                if (change >= user_positive_threshold) or (change <= user_negative_threshold):
                    last_time = _last_push.get(u.id,{}).get(t,0)
                    if now - last_time > 1800:  # не чаще 30 мин
                        msg = render_digest(f"Триггер по {t}", [f"Движение {change:.2f}% за день"])
                        await bot.send_message(int(u.tg_id), msg)
                        _last_push.setdefault(u.id,{})[t] = now
        s.close()

    sch.add_job(morning, "cron", hour=8, minute=30)
    sch.add_job(midday,  "cron", hour=15, minute=0)
    sch.add_job(evening, "cron", hour=18, minute=30)
    sch.add_job(triggers_job, "interval", seconds=POLL_SEC)
    sch.start()


from .config import POLL_SEC
from .triggers import run_triggers

def _wrap_triggers(bot):
    async def job():
        # обёртка для асинхронной отправки: прогоним триггеры и сами отправим тексты
        # Перепишем run_triggers так, чтобы он возвращал список (user_id, text, ticker) — упростим тут:
        from .storage import Session, User, Portfolio, Position, WatchLevel, EventLog
        from .moex import quotes_shares, quotes_etf, quotes_bonds
        from datetime import datetime, timedelta
        from collections import defaultdict
        s = Session()
        try:
            users = s.query(User).all()
            for u in users:
                if u.plan != "premium" or not u.plan_valid_to or u.plan_valid_to <= datetime.utcnow():
                    continue
                # соберём тикеры
                pf = s.query(Portfolio).filter_by(user_id=u.id).first()
                if not pf: continue
                positions = s.query(Position).filter_by(portfolio_id=pf.id).all()
                if not positions: continue
                # Проверка изменения дня с пользовательскими порогами
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
                # простейшее правило и анти-спам
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
                        # Используем пользовательские пороги
                        user_positive_threshold = float(u.trigger_threshold_positive or 5.0)
                        user_negative_threshold = float(u.trigger_threshold_negative or -5.0)
                        
                        if ((float(ch) >= user_positive_threshold) or (float(ch) <= user_negative_threshold)) and not recent(u.id,ticker=t) and daily_count(u.id) < 8 and u.triggers_enabled:
                            text = f"⚡ Событие по {t}: значимое дневное изменение (цена {q.get('last')}, Δдень {ch}%).\n" \ 
                                   f"Некоторые трейдеры рассматривают такие движения как важные для сценария.\n" \ 
                                   f"ℹ️ Аналитика и обучение. Не является индивидуальной инвестрекомендацией."
                            await bot.send_message(int(u.tg_id), text)
                            ev = EventLog(user_id=u.id, ticker=t, event_type="trigger", payload={"change_pct":ch}, sent_at=datetime.utcnow())
                            s.add(ev); s.commit()
                    except Exception:
                        pass
        finally:
            s.close()
    return job


    # Периодический опрос цен и триггеры
    sch.add_job(_wrap_triggers(bot), "interval", seconds=POLL_SEC)

def get_user_portfolio_quotes(user, session):
    """Получает котировки по портфелю пользователя"""
    portfolio = session.query(Portfolio).filter_by(user_id=user.id).first()
    if not portfolio:
        return {}
    
    positions = session.query(Position).filter_by(portfolio_id=portfolio.id).all()
    if not positions:
        return {}
    
    # Группируем по доскам
    boards = defaultdict(list)
    for pos in positions:
        if pos.board in ("TQBR", "TQTF", "TQOB"):
            boards[pos.board].append(pos.ticker)
    
    # Получаем котировки
    quotes = {}
    try:
        if boards.get("TQBR"):
            quotes.update(quotes_shares(list(set(boards["TQBR"]))))
        if boards.get("TQTF"):
            quotes.update(quotes_etf(list(set(boards["TQTF"]))))
        if boards.get("TQOB"):
            quotes.update(quotes_bonds(list(set(boards["TQOB"]))))
    except Exception as e:
        logger.error(f"Error fetching quotes: {e}")
    
    return quotes, positions

def generate_morning_digest(user, session):
    """Генерирует утренний дайджест"""
    quotes, positions = get_user_portfolio_quotes(user, session)
    
    if not positions:
        return None
    
    bullets = []
    
    # Анализ предрыночных движений
    significant_moves = []
    for pos in positions:
        quote = quotes.get(pos.ticker, {})
        change_pct = quote.get('change_pct')
        if change_pct and abs(float(change_pct)) >= 2:
            direction = "рост" if float(change_pct) > 0 else "снижение"
            significant_moves.append(f"{pos.ticker}: {direction} {change_pct}%")
    
    if significant_moves:
        bullets.append(f"Предрыночные движения: {', '.join(significant_moves[:3])}")
    else:
        bullets.append("Спокойное открытие торгов по вашим бумагам")
    
    # Ключевые уровни внимания
    key_levels = []
    for pos in positions[:3]:  # Берем первые 3 позиции
        quote = quotes.get(pos.ticker, {})
        if quote.get('last'):
            price = quote['last']
            high = quote.get('high', price)
            low = quote.get('low', price)
            if high != low:
                key_levels.append(f"{pos.ticker}: поддержка {low:.2f}, сопротивление {high:.2f}")
    
    if key_levels:
        bullets.append(f"Уровни внимания: {key_levels[0]}")
    
    # Общие рыночные условия
    bullets.append("Следим за основными индексами и новостным фоном")
    
    return render_digest("🌅 Утренний обзор", bullets)

def generate_midday_digest(user, session):
    """Генерирует дневной дайджест"""
    quotes, positions = get_user_portfolio_quotes(user, session)
    
    if not positions:
        return None
    
    bullets = []
    
    # Текущая производительность портфеля
    total_value = 0
    positive_moves = 0
    negative_moves = 0
    
    for pos in positions:
        quote = quotes.get(pos.ticker, {})
        price = quote.get('last', 0)
        change_pct = quote.get('change_pct', 0)
        
        if price:
            total_value += price * float(pos.qty)
            
        if change_pct:
            if float(change_pct) > 0:
                positive_moves += 1
            elif float(change_pct) < 0:
                negative_moves += 1
    
    if positive_moves + negative_moves > 0:
        bullets.append(f"В портфеле: {positive_moves} бумаг растут, {negative_moves} снижаются")
    
    # Лидеры и аутсайдеры
    sorted_positions = []
    for pos in positions:
        quote = quotes.get(pos.ticker, {})
        change_pct = quote.get('change_pct')
        if change_pct:
            sorted_positions.append((pos.ticker, float(change_pct)))
    
    if sorted_positions:
        sorted_positions.sort(key=lambda x: x[1], reverse=True)
        if len(sorted_positions) >= 2:
            leader = sorted_positions[0]
            outsider = sorted_positions[-1]
            bullets.append(f"Лидер дня: {leader[0]} (+{leader[1]:.1f}%), аутсайдер: {outsider[0]} ({outsider[1]:+.1f}%)")
    
    bullets.append("Рынок продолжает движение, следим за развитием")
    
    return render_digest("📊 Середина дня", bullets)

def generate_evening_digest(user, session):
    """Генерирует вечерний дайджест"""
    quotes, positions = get_user_portfolio_quotes(user, session)
    
    if not positions:
        return None
    
    bullets = []
    
    # Итоги дня по портфелю
    portfolio_performance = []
    total_change = 0
    count = 0
    
    for pos in positions:
        quote = quotes.get(pos.ticker, {})
        change_pct = quote.get('change_pct')
        if change_pct:
            portfolio_performance.append((pos.ticker, float(change_pct)))
            total_change += float(change_pct)
            count += 1
    
    if count > 0:
        avg_change = total_change / count
        direction = "положительной" if avg_change > 0 else "отрицательной"
        bullets.append(f"Средняя динамика портфеля: {avg_change:+.2f}% ({direction} динамикой)")
    
    # Топ движения дня
    if portfolio_performance:
        portfolio_performance.sort(key=lambda x: abs(x[1]), reverse=True)
        top_moves = portfolio_performance[:2]
        moves_text = ", ".join([f"{ticker} {change:+.1f}%" for ticker, change in top_moves])
        bullets.append(f"Самые активные: {moves_text}")
    
    # Объемы торгов
    high_volume_tickers = []
    for pos in positions:
        quote = quotes.get(pos.ticker, {})
        volume = quote.get('volume', 0)
        if volume and volume > 1000000:  # Условный порог высокого объема
            high_volume_tickers.append(pos.ticker)
    
    if high_volume_tickers:
        bullets.append(f"Повышенные объемы: {', '.join(high_volume_tickers[:3])}")
    
    # Планы на завтра
    bullets.append("Завтра следим за корпоративными новостями и макроэкономической статистикой")
    
    return render_digest("🌆 Итоги дня", bullets)
