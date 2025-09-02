import time
from datetime import datetime, timedelta
from collections import defaultdict
from .storage import Session, User, Portfolio, Position, WatchLevel, EventLog
from .moex import quotes_shares, quotes_etf, quotes_bonds
from .llm import render_digest
import logging

logger = logging.getLogger(__name__)

# Кэш для предотвращения спама уведомлений
_last_notification = {}  # {user_id: {ticker: timestamp}}

def run_triggers(bot=None):
    """
    Проверяет триггеры для всех премиум пользователей и отправляет уведомления
    """
    s = Session()
    notifications = []
    
    try:
        users = s.query(User).filter(User.plan == "premium").all()
        
        for user in users:
            # Проверяем что подписка активна
            if not user.plan_valid_to or user.plan_valid_to <= datetime.utcnow():
                continue
                
            # Получаем портфель пользователя
            portfolio = s.query(Portfolio).filter_by(user_id=user.id).first()
            if not portfolio:
                continue
                
            positions = s.query(Position).filter_by(portfolio_id=portfolio.id).all()
            if not positions:
                continue
                
            # Группируем тикеры по биржевым доскам
            boards = defaultdict(list)
            for pos in positions:
                if pos.board in ("TQBR", "TQTF", "TQOB"):
                    boards[pos.board].append(pos.ticker)
                    
            # Получаем котировки
            all_quotes = {}
            if boards.get("TQBR"):
                try:
                    all_quotes.update(quotes_shares(list(set(boards["TQBR"]))))
                except Exception as e:
                    logger.error(f"Error fetching shares quotes: {e}")
                    
            if boards.get("TQTF"):
                try:
                    all_quotes.update(quotes_etf(list(set(boards["TQTF"]))))
                except Exception as e:
                    logger.error(f"Error fetching ETF quotes: {e}")
                    
            if boards.get("TQOB"):
                try:
                    all_quotes.update(quotes_bonds(list(set(boards["TQOB"]))))
                except Exception as e:
                    logger.error(f"Error fetching bonds quotes: {e}")
            
            # Проверяем триггеры
            user_notifications = check_user_triggers(user, positions, all_quotes, s)
            notifications.extend(user_notifications)
            
    except Exception as e:
        logger.error(f"Error in run_triggers: {e}")
    finally:
        s.close()
        
    return notifications

def check_user_triggers(user, positions, quotes, session):
    """
    Проверяет триггеры для конкретного пользователя
    """
    notifications = []
    current_time = time.time()
    
    # Проверяем включены ли триггеры у пользователя
    if not user.triggers_enabled:
        return notifications
    
    # Ограничение: не более 10 уведомлений в день
    today_notifications = get_daily_notification_count(user.id, session)
    if today_notifications >= 10:
        return notifications
    
    for position in positions:
        ticker = position.ticker
        quote = quotes.get(ticker)
        
        if not quote:
            continue
            
        # Проверяем различные типы триггеров
        triggers = []
        
        # 1. Значительное изменение цены за день (пользовательские пороги)
        change_pct = quote.get("change_pct")
        if change_pct:
            change_val = float(change_pct)
            user_positive_threshold = float(user.trigger_threshold_positive or 5.0)
            user_negative_threshold = float(user.trigger_threshold_negative or -5.0)
            
            # Проверяем пороги для роста и падения отдельно
            if (change_val >= user_positive_threshold) or (change_val <= user_negative_threshold):
                triggers.append({
                    "type": "daily_change",
                    "message": f"⚡ Значительное движение по {ticker}: {change_pct}% за день\nЦена: {quote.get('last')} ₽",
                    "payload": {"change_pct": change_pct, "price": quote.get('last')}
                })
        
        # 2. Пробитие уровней поддержки/сопротивления
        watch_levels = session.query(WatchLevel).filter_by(user_id=user.id, ticker=ticker).all()
        current_price = quote.get("last")
        
        if current_price and watch_levels:
            for level in watch_levels:
                level_value = float(level.value)
                price_diff = abs(current_price - level_value) / level_value * 100
                
                # Если цена близко к уровню (в пределах 1%)
                if price_diff <= 1.0:
                    triggers.append({
                        "type": "level_approach",
                        "message": f"🎯 {ticker} приближается к уровню {level.level_type}: {level_value} ₽\nТекущая цена: {current_price} ₽\n{level.note or ''}",
                        "payload": {"level_type": level.level_type, "level_value": level_value, "current_price": current_price}
                    })
        
        # 3. Высокий объем торгов (в 2+ раза выше среднего)
        volume = quote.get("volume")
        if volume and volume > 0:
            # Простая эвристика: если объем очень большой
            avg_volume = get_average_volume(ticker)  # Заглушка
            if avg_volume and volume >= avg_volume * 2:
                triggers.append({
                    "type": "high_volume",
                    "message": f"📊 Повышенный объем торгов по {ticker}\nТекущий объем: {volume:,.0f}\nЦена: {quote.get('last')} ₽",
                    "payload": {"volume": volume, "avg_volume": avg_volume}
                })
        
        # Отправляем уведомления с учетом анти-спама
        for trigger in triggers:
            if should_send_notification(user.id, ticker, trigger["type"], current_time):
                notifications.append({
                    "user_id": user.id,
                    "ticker": ticker,
                    "message": trigger["message"] + "\n\nℹ️ Информация носит аналитический и образовательный характер и не является индивидуальной инвестиционной рекомендацией.",
                    "event_type": "trigger",
                    "payload": trigger["payload"]
                })
                
                # Записываем в лог и обновляем кэш
                log_notification(user.id, ticker, trigger["type"], trigger["payload"], session)
                update_notification_cache(user.id, ticker, trigger["type"], current_time)
    
    return notifications

def should_send_notification(user_id, ticker, trigger_type, current_time):
    """
    Проверяет можно ли отправить уведомление (анти-спам)
    """
    key = f"{user_id}_{ticker}_{trigger_type}"
    last_time = _last_notification.get(key, 0)
    
    # Минимальный интервал между уведомлениями одного типа - 30 минут
    min_interval = 30 * 60  # 30 минут в секундах
    
    return (current_time - last_time) >= min_interval

def update_notification_cache(user_id, ticker, trigger_type, timestamp):
    """
    Обновляет кэш последних уведомлений
    """
    key = f"{user_id}_{ticker}_{trigger_type}"
    _last_notification[key] = timestamp

def get_daily_notification_count(user_id, session):
    """
    Получает количество уведомлений за сегодня
    """
    today = datetime.utcnow().date()
    start_of_day = datetime(today.year, today.month, today.day)
    
    count = session.query(EventLog).filter(
        EventLog.user_id == user_id,
        EventLog.event_type == "trigger",
        EventLog.sent_at >= start_of_day
    ).count()
    
    return count

def log_notification(user_id, ticker, trigger_type, payload, session):
    """
    Записывает уведомление в лог
    """
    event = EventLog(
        user_id=user_id,
        ticker=ticker,
        event_type="trigger",
        payload={
            "trigger_type": trigger_type,
            **payload
        },
        sent_at=datetime.utcnow()
    )
    session.add(event)
    session.commit()

def get_average_volume(ticker):
    """
    Заглушка для получения среднего объема торгов
    В реальной реализации здесь был бы запрос исторических данных
    """
    # Можно реализовать через MOEX API для получения исторических данных
    return None
