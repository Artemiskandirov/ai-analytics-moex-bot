from aiogram import Router, types
from aiogram.filters import Command
from datetime import datetime, timedelta
from .storage import Session, User, Portfolio, Position
from .texts import HELLO, PAYWALL, HELP_TEXT, TRIAL_USED_TEXT, PREMIUM_FEATURES_TEXT
from .config import PREMIUM_PRICE, BOARD_SHARES, BOARD_ETF, BOARD_BONDS
from .moex import quotes_shares, quotes_etf, quotes_bonds
from .levels import educational_levels
from .llm import render_trial_note, render_digest
import re
import logging

logger = logging.getLogger(__name__)

router = Router()

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
    """Бесплатный пробный разбор акции из портфеля пользователя"""
    s = Session()
    try:
        user = get_or_create_user(m.from_user.id)
        u = s.query(User).filter_by(tg_id=str(m.from_user.id)).first()
        
    if u.free_trial_used:
            await m.answer(TRIAL_USED_TEXT.format(price=PREMIUM_PRICE))
            return
        
        # Получаем портфель пользователя
        portfolio = s.query(Portfolio).filter_by(user_id=u.id).first()
        if not portfolio:
            await m.answer("❌ Сначала добавьте портфель!\n\n"
                          "Отправьте список тикеров в формате:\n"
                          "GAZP 100\nSBER 50\nFXGD 200\n\n"
                          "После добавления портфеля команда /trial проанализирует одну из ваших позиций.")
            return
        
        positions = s.query(Position).filter_by(portfolio_id=portfolio.id).all()
        if not positions:
            await m.answer("❌ Ваш портфель пуст!\n\n"
                          "Добавьте позиции, отправив список тикеров:\n"
                          "GAZP 100\nSBER 50\nFXGD 200")
            return
        
        # Выбираем акцию для анализа (приоритет - акции с TQBR)
        selected_position = None
        
        # Сначала ищем акции
        for pos in positions:
            if pos.board == BOARD_SHARES:  # TQBR
                selected_position = pos
                break
        
        # Если акций нет, берем ETF
        if not selected_position:
            for pos in positions:
                if pos.board == BOARD_ETF:  # TQTF
                    selected_position = pos
                    break
        
        # В крайнем случае берем любую позицию
        if not selected_position:
            selected_position = positions[0]
        
        ticker = selected_position.ticker
        board = selected_position.board
        
        # Получаем котировки в зависимости от типа инструмента
        try:
            quotes = {}
            if board == BOARD_SHARES:
                quotes = quotes_shares([ticker])
            elif board == BOARD_ETF:
                quotes = quotes_etf([ticker])
            elif board == BOARD_BONDS:
                quotes = quotes_bonds([ticker])
            
            quote = quotes.get(ticker, {})
            if not quote:
                await m.answer(f"❌ Временно не удается получить данные по {ticker}. Попробуйте позже.")
                return
            
            # Вычисляем технические уровни
            levels = educational_levels(
                quote.get("last"), 
                1.0, 
                support=(quote.get("low") or 0), 
                resistance=(quote.get("high") or 0), 
                k=1.5
            )
            
            # Генерируем анализ
            note = render_trial_note(ticker, quote, levels)
    await m.answer(note)
            
            # Отмечаем что trial использован
            u.free_trial_used = True
            u.free_trial_used_at = datetime.utcnow()
            u.trial_asset = ticker
            s.commit()
            
            # Показываем информацию о премиуме
    await m.answer(PAYWALL.format(price=PREMIUM_PRICE))
            
        except Exception as e:
            logger.error(f"Error in trial analysis for {ticker}: {e}")
            await m.answer(f"❌ Произошла ошибка при анализе {ticker}. Попробуйте позже.")
            
    finally:
        s.close()

@router.message(Command("help"))
async def cmd_help(m: types.Message):
    """Справка по командам"""
    await m.answer(HELP_TEXT)

@router.message(Command("analyze"))
async def cmd_analyze(m: types.Message):
    """Полный анализ портфеля (премиум функция)"""
    s = Session()
    try:
        user = get_or_create_user(m.from_user.id)
        u = s.query(User).filter_by(tg_id=str(m.from_user.id)).first()
        now = datetime.utcnow()
        
        # Проверяем премиум подписку
        if not (u.plan == "premium" and u.plan_valid_to and u.plan_valid_to > now):
            await m.answer(PAYWALL.format(price=PREMIUM_PRICE))
            return
        
        # Получаем портфель
        portfolio = s.query(Portfolio).filter_by(user_id=u.id).first()
        if not portfolio:
            await m.answer("❌ Портфель не настроен. Отправьте список тикеров для добавления.")
            return
        
        positions = s.query(Position).filter_by(portfolio_id=portfolio.id).all()
        if not positions:
            await m.answer("❌ Портфель пуст. Добавьте позиции, отправив список тикеров.")
            return
        
        # Генерируем полный анализ
        try:
            from .worker import generate_evening_digest
            analysis = generate_evening_digest(u, s)
            
            if analysis:
                await m.answer(f"📊 Аналитический разбор вашего портфеля:\n\n{analysis}")
            else:
                await m.answer("❌ Не удалось получить данные для анализа. Попробуйте позже.")
                
        except Exception as e:
            logger.error(f"Error in portfolio analysis: {e}")
            await m.answer("❌ Произошла ошибка при анализе портфеля. Попробуйте позже.")
            
    finally:
        s.close()

@router.message(Command("features"))
async def cmd_features(m: types.Message):
    """Показывает возможности премиум подписки"""
    await m.answer(PREMIUM_FEATURES_TEXT)

@router.message(Command("settings"))
async def cmd_settings(m: types.Message):
    """Показывает текущие настройки пользователя"""
    s = Session()
    try:
        user = get_or_create_user(m.from_user.id)
        u = s.query(User).filter_by(tg_id=str(m.from_user.id)).first()
        
        triggers_status = "🟢 Включены" if u.triggers_enabled else "🔴 Выключены"
        positive_threshold = float(u.trigger_threshold_positive or 5.0)
        negative_threshold = float(u.trigger_threshold_negative or -5.0)
        
        settings_text = f"""⚙️ Ваши настройки:

📊 Триггеры уведомлений: {triggers_status}
📈 Порог для роста: +{positive_threshold:.0f}%
📉 Порог для падения: {negative_threshold:.0f}%

🔧 Команды для настройки:
/trigger_set +10 -7  - установить пороги +10% и -7%
/trigger_on  - включить уведомления
/trigger_off - выключить уведомления

💡 Доступные пороги: от -50% до +100% с шагом 1%
Например: /trigger_set +15 -10
"""
        
        await m.answer(settings_text)
        
    finally:
        s.close()

@router.message(Command("trigger_set"))
async def cmd_trigger_set(m: types.Message):
    """Устанавливает пороги срабатывания триггеров"""
    s = Session()
    try:
        user = get_or_create_user(m.from_user.id)
        u = s.query(User).filter_by(tg_id=str(m.from_user.id)).first()
        
        # Парсим аргументы команды
        parts = (m.text or "").split()
        if len(parts) != 3:
            await m.answer("❌ Неверный формат команды!\n\n"
                          "Используйте: /trigger_set +10 -7\n"
                          "Где +10 - порог роста, -7 - порог падения\n\n"
                          "Диапазоны: от -50% до +100%")
            return
        
        try:
            positive_str = parts[1]
            negative_str = parts[2]
            
            # Убираем знак + если есть и парсим числа
            positive_val = float(positive_str.replace('+', ''))
            negative_val = float(negative_str)
            
            # Валидация диапазонов
            if positive_val < 1 or positive_val > 100:
                await m.answer("❌ Порог роста должен быть от +1% до +100%")
                return
                
            if negative_val > -1 or negative_val < -50:
                await m.answer("❌ Порог падения должен быть от -1% до -50%")
                return
            
            # Проверяем что это целые числа (шаг 1%)
            if positive_val != int(positive_val) or negative_val != int(negative_val):
                await m.answer("❌ Используйте целые числа с шагом 1%\n"
                              "Например: /trigger_set +15 -10")
                return
            
            # Сохраняем настройки
            u.trigger_threshold_positive = positive_val
            u.trigger_threshold_negative = negative_val
            s.commit()
            
            await m.answer(f"✅ Пороги триггеров обновлены!\n\n"
                          f"📈 Рост: +{positive_val:.0f}%\n"
                          f"📉 Падение: {negative_val:.0f}%\n\n"
                          f"Теперь вы будете получать уведомления при изменениях цен на эти значения или больше.")
            
        except ValueError:
            await m.answer("❌ Неверный формат чисел!\n\n"
                          "Используйте: /trigger_set +15 -10\n"
                          "Числа должны быть целыми")
            
    finally:
        s.close()

@router.message(Command("trigger_on"))
async def cmd_trigger_on(m: types.Message):
    """Включает триггеры уведомлений"""
    s = Session()
    try:
        user = get_or_create_user(m.from_user.id)
        u = s.query(User).filter_by(tg_id=str(m.from_user.id)).first()
        
        u.triggers_enabled = True
        s.commit()
        
        positive = float(u.trigger_threshold_positive or 5.0)
        negative = float(u.trigger_threshold_negative or -5.0)
        
        await m.answer(f"🟢 Триггеры уведомлений включены!\n\n"
                      f"Вы будете получать уведомления при изменениях:\n"
                      f"📈 Рост: +{positive:.0f}% и больше\n"
                      f"📉 Падение: {negative:.0f}% и больше\n\n"
                      f"Изменить пороги: /trigger_set +10 -7")
        
    finally:
    s.close()

@router.message(Command("trigger_off"))
async def cmd_trigger_off(m: types.Message):
    """Выключает триггеры уведомлений"""
    s = Session()
    try:
        user = get_or_create_user(m.from_user.id)
        u = s.query(User).filter_by(tg_id=str(m.from_user.id)).first()
        
        u.triggers_enabled = False
        s.commit()
        
        await m.answer("🔴 Триггеры уведомлений выключены.\n\n"
                      "Дайджесты будут приходить по расписанию, но уведомления о значимых изменениях цен отключены.\n\n"
                      "Включить обратно: /trigger_on")
        
    finally:
        s.close()

@router.message(Command("paycheck"))
async def cmd_paycheck(m: types.Message):
    s=Session(); u=s.query(User).filter_by(tg_id=str(m.from_user.id)).first()
    # MVP: просто включаем premium на 30 дней
    u.plan="premium"; u.plan_valid_to=datetime.utcnow()+timedelta(days=30)
    s.commit(); s.close()
    await m.answer("✅ Оплата подтверждена. Доступ premium активирован на 30 дней.")


from .config import PREMIUM_PRICE
import os
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "demo_code")

@router.message(Command("verify"))
async def cmd_verify(m: types.Message):
    # /verify <code>
    parts = (m.text or "").split()
    if len(parts) < 2:
        await m.answer("Введите код подтверждения оплаты: /verify <код>")
        return
    code = parts[1].strip()
    if code != VERIFY_TOKEN:
        await m.answer("Код не подошёл. Проверьте и повторите.")
        return
    # Выдать премиум на 30 дней
    s=Session(); u=s.query(User).filter_by(tg_id=str(m.from_user.id)).first()
    from datetime import datetime, timedelta
    u.plan = "premium"
    u.plan_valid_to = (u.plan_valid_to or datetime.utcnow())
    if u.plan_valid_to < datetime.utcnow():
        u.plan_valid_to = datetime.utcnow()
    u.plan_valid_to += timedelta(days=30)
    s.commit(); s.close()
    await m.answer(f"Оплата подтверждена. Премиум активен до {u.plan_valid_to}. Спасибо!")

def parse_portfolio_message(text):
    """
    Парсит сообщение с портфелем в формате:
    GAZP 100
    SBER 50
    FXGD 200
    Или просто список тикеров: GAZP, SBER, FXGD
    """
    positions = []
    
    # Убираем лишние символы и разбиваем на строки
    lines = [line.strip() for line in text.upper().split('\n') if line.strip()]
    
    for line in lines:
        # Пытаемся найти тикер и количество
        # Формат: GAZP 100 или GAZP,100 или GAZP:100
        match = re.match(r'^([A-Z]{3,5})[,:\s]+(\d+(?:\.\d+)?)$', line)
        if match:
            ticker, qty = match.groups()
            positions.append({
                'ticker': ticker,
                'qty': float(qty),
                'board': detect_board(ticker)
            })
        else:
            # Пытаемся найти просто тикер
            match = re.match(r'^([A-Z]{3,5})$', line)
            if match:
                ticker = match.group(1)
                positions.append({
                    'ticker': ticker,
                    'qty': 1.0,  # Дефолтное количество
                    'board': detect_board(ticker)
                })
    
    return positions

def detect_board(ticker):
    """
    Определяет биржевую доску по тикеру (упрощенная логика)
    """
    # ETF обычно начинаются с определенных префиксов
    etf_prefixes = ['FX', 'TECH', 'RUSI', 'SBGB', 'SBCB']
    
    if any(ticker.startswith(prefix) for prefix in etf_prefixes):
        return BOARD_ETF
    
    # Остальные считаем акциями
    return BOARD_SHARES

def update_user_portfolio(user_id, positions):
    """
    Обновляет портфель пользователя
    """
    s = Session()
    try:
        # Получаем портфель пользователя
        portfolio = s.query(Portfolio).filter_by(user_id=user_id).first()
        if not portfolio:
            return False
        
        # Удаляем старые позиции
        s.query(Position).filter_by(portfolio_id=portfolio.id).delete()
        
        # Добавляем новые позиции
        for pos_data in positions:
            position = Position(
                portfolio_id=portfolio.id,
                ticker=pos_data['ticker'],
                board=pos_data['board'],
                qty=pos_data['qty'],
                currency='RUB'
            )
            s.add(position)
        
        # Обновляем время изменения портфеля
        portfolio.updated_at = datetime.utcnow()
        
        s.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating portfolio: {e}")
        s.rollback()
        return False
    finally:
        s.close()

@router.message(Command("portfolio"))
async def cmd_portfolio(m: types.Message):
    """Показывает текущий портфель пользователя"""
    s = Session()
    try:
        user = s.query(User).filter_by(tg_id=str(m.from_user.id)).first()
        if not user:
            await m.answer("Сначала выполните команду /start")
            return
        
        portfolio = s.query(Portfolio).filter_by(user_id=user.id).first()
        if not portfolio:
            await m.answer("Портфель не найден")
            return
        
        positions = s.query(Position).filter_by(portfolio_id=portfolio.id).all()
        if not positions:
            await m.answer("Ваш портфель пуст. Отправьте список тикеров для добавления:\n\nПример:\nGAZP 100\nSBER 50\nFXGD 200")
            return
        
        # Группируем по биржевым доскам для получения котировок
        boards = {'TQBR': [], 'TQTF': [], 'TQOB': []}
        for pos in positions:
            if pos.board in boards:
                boards[pos.board].append(pos.ticker)
        
        # Получаем котировки
        quotes = {}
        try:
            if boards['TQBR']:
                quotes.update(quotes_shares(boards['TQBR']))
            if boards['TQTF']:
                quotes.update(quotes_etf(boards['TQTF']))
            if boards['TQOB']:
                quotes.update(quotes_bonds(boards['TQOB']))
        except Exception as e:
            logger.error(f"Error fetching quotes: {e}")
        
        # Формируем сообщение
        portfolio_text = "📊 Ваш портфель:\n\n"
        total_value = 0
        
        for pos in positions:
            quote = quotes.get(pos.ticker, {})
            price = quote.get('last', 0) or 0
            change_pct = quote.get('change_pct', 0) or 0
            
            position_value = price * float(pos.qty) if price else 0
            total_value += position_value
            
            change_emoji = "🔴" if change_pct < 0 else "🟢" if change_pct > 0 else "⚪"
            
            portfolio_text += f"{change_emoji} {pos.ticker}: {pos.qty} шт.\n"
            if price:
                portfolio_text += f"    Цена: {price:.2f} ₽ ({change_pct:+.2f}%)\n"
                portfolio_text += f"    Стоимость: {position_value:,.0f} ₽\n\n"
            else:
                portfolio_text += f"    Цена: нет данных\n\n"
        
        if total_value > 0:
            portfolio_text += f"💼 Общая стоимость: {total_value:,.0f} ₽"
        
        portfolio_text += "\n\nℹ️ Информация носит аналитический и образовательный характер и не является индивидуальной инвестиционной рекомендацией."
        
        await m.answer(portfolio_text)
        
    finally:
        s.close()

@router.message()
async def handle_text_message(m: types.Message):
    """Обрабатывает текстовые сообщения (потенциально портфель)"""
    if not m.text or m.text.startswith('/'):
        return
    
    # Проверяем, похоже ли сообщение на список тикеров
    if not re.search(r'[A-Z]{3,5}', m.text.upper()):
        await m.answer("Не понимаю сообщение. Используйте команды:\n"
                      "/start - начать\n"
                      "/trial - бесплатный разбор\n"
                      "/portfolio - показать портфель\n"
                      "/analyze - анализ (премиум)\n\n"
                      "Или отправьте список тикеров в формате:\nGAZP 100\nSBER 50")
        return
    
    # Парсим портфель
    positions = parse_portfolio_message(m.text)
    
    if not positions:
        await m.answer("Не удалось распознать тикеры. Используйте формат:\n\n"
                      "GAZP 100\n"
                      "SBER 50\n"
                      "FXGD 200\n\n"
                      "Или просто список тикеров через запятую: GAZP, SBER, FXGD")
        return
    
    # Получаем/создаем пользователя
    user = get_or_create_user(m.from_user.id)
    
    # Обновляем портфель
    if update_user_portfolio(user.id, positions):
        tickers_list = [f"{pos['ticker']} ({pos['qty']} шт.)" for pos in positions]
        await m.answer(f"✅ Портфель обновлен!\n\n"
                      f"Добавлено {len(positions)} позиций:\n" + 
                      "\n".join(tickers_list) + 
                      "\n\nИспользуйте /portfolio для просмотра с ценами")
    else:
        await m.answer("❌ Ошибка при обновлении портфеля. Попробуйте позже.")
