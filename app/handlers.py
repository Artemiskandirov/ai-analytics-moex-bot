from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import os, re
from .storage import Session, User, Portfolio
from .texts import HELLO
from .moex import quotes_shares, candles
from .levels import atr, educational_levels
from .llm import render_trial_note

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

def get_main_keyboard():
    """Главное меню с кнопками"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Анализ акции", callback_data="analyze_stock")],
        [InlineKeyboardButton(text="💼 Мой портфель", callback_data="my_portfolio")],
        [InlineKeyboardButton(text="➕ Добавить в портфель", callback_data="add_to_portfolio")],
        [InlineKeyboardButton(text="📈 Динамика портфеля", callback_data="portfolio_dynamics")],
        [InlineKeyboardButton(text="🔍 Поиск акций", callback_data="search_stocks")],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")]
    ])

@router.message(Command("start"))
async def cmd_start(m: types.Message):
    get_or_create_user(m.from_user.id)
    welcome_text = """👋 Привет! Я MarketLens - твой AI-аналитик фондового рынка!

🚀 Что я умею:
• Анализировать акции с помощью ИИ
• Отслеживать твой портфель 
• Показывать динамику и прибыльность
• Давать образовательные рекомендации

Выбери действие:"""
    await m.answer(welcome_text, reply_markup=get_main_keyboard())

@router.message(Command("analyze"))
async def cmd_analyze(m: types.Message):
    # Получаем тикер из команды
    parts = (m.text or "").split()
    if len(parts) < 2:
        await m.answer("Использование: /analyze <ТИКЕР>\nПример: /analyze SBER", reply_markup=get_main_keyboard())
        return
        
    ticker = parts[1].upper()
    await analyze_stock(m, ticker)

async def analyze_stock(m: types.Message, ticker: str):
    """Анализ акции с помощью ИИ"""
    q = quotes_shares([ticker]).get(ticker, {})
    if not q or not q.get("last"):
        await m.answer(f"❌ Не удалось получить данные по тикеру {ticker}.\nПроверьте правильность тикера.", reply_markup=get_main_keyboard())
        return
        
    board = q.get("board","TQBR") if q else "TQBR"
    cs = candles(ticker, board, 24)
    atr14 = None
    if cs:
        series = [{"high":c["high"],"low":c["low"],"close":c["close"]} for c in cs][-50:]
        atr14 = atr(series, period=14)
    
    levels = educational_levels(q.get("last"), atr14 or 1.0, support=(q.get("low") or 0), resistance=(q.get("high") or 0), k=1.5)
    note = render_trial_note(ticker, q, levels)
    
    # Кнопки для дальнейших действий
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"➕ Добавить {ticker} в портфель", callback_data=f"add_{ticker}")],
        [InlineKeyboardButton(text="🔍 Анализ другой акции", callback_data="analyze_stock")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await m.answer(note, reply_markup=keyboard)

# Обработчики callback-кнопок
@router.callback_query(lambda c: c.data == "main_menu")
async def callback_main_menu(callback: types.CallbackQuery):
    welcome_text = """👋 MarketLens - твой AI-аналитик фондового рынка!

🚀 Что я умею:
• Анализировать акции с помощью ИИ
• Отслеживать твой портфель 
• Показывать динамику и прибыльность
• Давать образовательные рекомендации

Выбери действие:"""
    await callback.message.edit_text(welcome_text, reply_markup=get_main_keyboard())

@router.callback_query(lambda c: c.data == "analyze_stock")
async def callback_analyze_stock(callback: types.CallbackQuery):
    await callback.message.edit_text("📊 Введите тикер для анализа:\nПример: SBER, GAZP, LKOH\n\nИспользуйте команду: /analyze ТИКЕР")

@router.callback_query(lambda c: c.data == "my_portfolio")
async def callback_my_portfolio(callback: types.CallbackQuery):
    s = Session()
    u = s.query(User).filter_by(tg_id=str(callback.from_user.id)).first()
    portfolio = s.query(Portfolio).filter_by(user_id=u.id).first()
    
    if not portfolio.stocks:
        text = "💼 Ваш портфель пуст\n\nДобавьте акции для отслеживания динамики!"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить акции", callback_data="add_to_portfolio")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
    else:
        # Парсим акции из строки JSON
        import json
        try:
            stocks = json.loads(portfolio.stocks)
            text = "💼 Ваш портфель:\n\n"
            total_value = 0
            
            tickers = list(stocks.keys())
            quotes = quotes_shares(tickers)
            
            for ticker, quantity in stocks.items():
                quote = quotes.get(ticker, {})
                current_price = quote.get("last", 0)
                change_pct = quote.get("change_pct", 0)
                position_value = current_price * quantity
                total_value += position_value
                
                change_emoji = "📈" if change_pct > 0 else "📉" if change_pct < 0 else "➡️"
                text += f"{ticker}: {quantity} шт.\n"
                text += f"💰 {current_price:.2f} ₽ {change_emoji} {change_pct:+.2f}%\n"
                text += f"💵 Позиция: {position_value:,.0f} ₽\n\n"
            
            text += f"📊 Общая стоимость: {total_value:,.0f} ₽"
            
        except:
            text = "❌ Ошибка чтения портфеля"
            
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📈 Динамика", callback_data="portfolio_dynamics")],
            [InlineKeyboardButton(text="➕ Добавить", callback_data="add_to_portfolio")],
            [InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")]
        ])
    
    s.close()
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(lambda c: c.data == "add_to_portfolio")
async def callback_add_to_portfolio(callback: types.CallbackQuery):
    text = """➕ Добавление в портфель

Отправьте список ваших акций в формате:
ТИКЕР количество

Примеры:
• SBER 100
• GAZP 50 LKOH 20
• MOEX 30

Или загрузите скриншот брокерского приложения 📱"""

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(lambda c: c.data == "portfolio_dynamics")
async def callback_portfolio_dynamics(callback: types.CallbackQuery):
    s = Session()
    u = s.query(User).filter_by(tg_id=str(callback.from_user.id)).first()
    portfolio = s.query(Portfolio).filter_by(user_id=u.id).first()
    
    if not portfolio.stocks:
        text = "📈 Сначала добавьте акции в портфель для отслеживания динамики"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить акции", callback_data="add_to_portfolio")],
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
        ])
    else:
        try:
            import json
            stocks = json.loads(portfolio.stocks)
            text = "📈 Динамика портфеля:\n\n"
            
            tickers = list(stocks.keys())
            quotes = quotes_shares(tickers)
            
            total_gain = 0
            total_positions = 0
            
            for ticker, quantity in stocks.items():
                quote = quotes.get(ticker, {})
                current_price = quote.get("last", 0)
                change_pct = quote.get("change_pct", 0)
                day_change = current_price * change_pct / 100
                position_change = day_change * quantity
                
                total_gain += position_change
                total_positions += 1
                
                change_emoji = "🟢" if change_pct > 0 else "🔴" if change_pct < 0 else "⚪"
                text += f"{change_emoji} {ticker}: {change_pct:+.2f}% ({position_change:+.0f} ₽)\n"
            
            avg_change = (total_gain / sum(quotes.get(t, {}).get("last", 1) * stocks[t] for t in tickers)) * 100 if tickers else 0
            
            text += f"\n📊 Общее изменение: {total_gain:+.0f} ₽ ({avg_change:+.2f}%)"
            
            if total_gain > 0:
                text += "\n🎉 Портфель растет!"
            elif total_gain < 0:
                text += "\n📉 Портфель снижается"
            else:
                text += "\n➡️ Портфель без изменений"
                
        except Exception as e:
            text = f"❌ Ошибка расчета динамики: {e}"
            
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💼 Портфель", callback_data="my_portfolio")],
            [InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")]
        ])
    
    s.close()
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(lambda c: c.data == "search_stocks")
async def callback_search_stocks(callback: types.CallbackQuery):
    text = """🔍 Поиск акций

Популярные акции для анализа:

🏦 Банки: SBER, VTB, AFKS
⚡ Энергетика: GAZP, LKOH, ROSN, NVTK
💎 Металлы: NLMK, MAGN, GMKN
📱 IT: YNDX, OZON, SFTL
🏪 Ритейл: MGNT, FIVE, LNTA

Для анализа используйте: /analyze ТИКЕР"""

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Анализ акции", callback_data="analyze_stock")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(lambda c: c.data == "help")
async def callback_help(callback: types.CallbackQuery):
    text = """ℹ️ Помощь по MarketLens

🤖 Команды:
• /start - Главное меню
• /analyze ТИКЕР - Анализ акции

💼 Портфель:
• Добавляйте свои акции для отслеживания
• Смотрите динамику в реальном времени
• Получайте аналитику по позициям

📊 Анализ:
• ИИ анализирует техническую ситуацию
• Уровни поддержки и сопротивления
• Образовательные сценарии

⚠️ Дисклеймер:
Информация носит образовательный характер и не является инвестиционной рекомендацией."""

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard)

# Обработка добавления акций через callback
@router.callback_query(lambda c: c.data.startswith("add_"))
async def callback_add_specific_stock(callback: types.CallbackQuery):
    ticker = callback.data.split("_")[1]
    
    # Простое добавление с количеством по умолчанию
    s = Session()
    u = s.query(User).filter_by(tg_id=str(callback.from_user.id)).first()
    portfolio = s.query(Portfolio).filter_by(user_id=u.id).first()
    
    try:
        import json
        stocks = json.loads(portfolio.stocks) if portfolio.stocks else {}
        stocks[ticker] = stocks.get(ticker, 0) + 10  # Добавляем 10 акций по умолчанию
        portfolio.stocks = json.dumps(stocks)
        s.commit()
        
        text = f"✅ {ticker} добавлен в портфель (+10 шт.)\n\nТеперь вы можете отслеживать динамику этой позиции!"
        
    except Exception as e:
        text = f"❌ Ошибка добавления: {e}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💼 Мой портфель", callback_data="my_portfolio")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
    ])
    
    s.close()
    await callback.message.edit_text(text, reply_markup=keyboard)

# Обработка текстовых сообщений для добавления портфеля
@router.message()
async def handle_text_messages(m: types.Message):
    text = (m.text or "").strip()
    
    # Парсим сообщения вида "SBER 100 GAZP 50"
    pattern = r'([A-Z]{3,6})\s+(\d+)'
    matches = re.findall(pattern, text.upper())
    
    if matches:
        s = Session()
        u = s.query(User).filter_by(tg_id=str(m.from_user.id)).first()
        if not u:
            get_or_create_user(m.from_user.id)
            u = s.query(User).filter_by(tg_id=str(m.from_user.id)).first()
        
        portfolio = s.query(Portfolio).filter_by(user_id=u.id).first()
        
        try:
            import json
            stocks = json.loads(portfolio.stocks) if portfolio.stocks else {}
            
            added_stocks = []
            for ticker, quantity in matches:
                stocks[ticker] = int(quantity)
                added_stocks.append(f"{ticker}: {quantity} шт.")
            
            portfolio.stocks = json.dumps(stocks)
            s.commit()
            
            response = f"✅ Добавлено в портфель:\n\n" + "\n".join(added_stocks)
            response += f"\n\n💼 Всего в портфеле: {len(stocks)} позиций"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💼 Показать портфель", callback_data="my_portfolio")],
                [InlineKeyboardButton(text="📈 Динамика", callback_data="portfolio_dynamics")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
            ])
            
            await m.answer(response, reply_markup=keyboard)
            
        except Exception as e:
            await m.answer(f"❌ Ошибка добавления акций: {e}")
        
        s.close()
    else:
        # Если не распознали формат портфеля, показываем помощь
        await m.answer("❓ Не понял команду.\n\nДля добавления акций используйте формат:\nТИКЕР количество\n\nПример: SBER 100", 
                      reply_markup=get_main_keyboard())
