import os
from openai import OpenAI
from .config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)
MODEL = "gpt-4o-mini"
DISCLAIMER = ("ℹ️ Информация носит аналитический и образовательный характер "
              "и не является индивидуальной инвестиционной рекомендацией.")

def render_stock_analysis(ticker, q, levels=None):
    try:
        support = (levels or {}).get('levels', {}).get('support', q.get('low', 0))
        resistance = (levels or {}).get('levels', {}).get('resistance', q.get('high', 0))
        current_price = q.get('last', 0)
        
        # Рассчитываем уровни стоп-лосса и тейк-профита
        stop_loss_tight = round(current_price * 0.97, 2)  # 3% стоп
        stop_loss_wide = round(current_price * 0.94, 2)   # 6% стоп
        take_profit_1 = round(current_price * 1.05, 2)    # 5% тейк
        take_profit_2 = round(current_price * 1.12, 2)    # 12% тейк
        
        text = f"""
Ты - приватный аналитик крупного российского банка для VIP-клиентов. 
Анализируй {ticker} с учетом АКТУАЛЬНЫХ НОВОСТЕЙ и рыночной ситуации.

ТЕКУЩИЕ ДАННЫЕ:
• Цена: {current_price} ₽ ({q.get('change_pct', 0):+.1f}% за день)
• Дневной диапазон: {q.get('low', 0)} - {q.get('high', 0)} ₽
• Техническая поддержка: ~{support} ₽
• Техническое сопротивление: ~{resistance} ₽

ТРЕБОВАНИЯ К АНАЛИЗУ:
1. 💼 ИНВЕСТИЦИОННОЕ МНЕНИЕ: четкая рекомендация (покупать/держать/продавать)
2. 📰 НОВОСТНОЙ ФОН: влияние актуальных новостей на бумагу
3. 📊 ТЕХНИЧЕСКИЙ АНАЛИЗ: ключевые уровни и паттерны
4. 🎯 ТОРГОВЫЕ УРОВНИ:
   - Stop-Loss консервативный: {stop_loss_wide} ₽ (-6%)
   - Stop-Loss агрессивный: {stop_loss_tight} ₽ (-3%)
   - Take-Profit первый: {take_profit_1} ₽ (+5%)
   - Take-Profit основной: {take_profit_2} ₽ (+12%)
5. ⚡ КАТАЛИЗАТОРЫ: что может двинуть цену в ближайшее время
6. ⏰ ГОРИЗОНТ: рекомендации на 1-4 недели

СТИЛЬ: Как приватный банкир - профессионально, конкретно, без воды. 
Учитывай свежие новости по эмитенту и рынку в целом.
"""
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": text}],
            temperature=0.2,
            max_tokens=800
        )
        return resp.choices[0].message.content + f"\n\n{DISCLAIMER}"
    except Exception as e:
        print(f"OpenAI API error: {e}")
        # Fallback - простой анализ без AI
        last = q.get('last') or 0
        change_pct = q.get('change_pct') or 0
        high = q.get('high') or 0
        low = q.get('low') or 0
        
        support = (levels or {}).get('levels', {}).get('support', '—')
        resistance = (levels or {}).get('levels', {}).get('resistance', '—')
        
        return f"""📊 {ticker}: {last} ₽ ({change_pct:+.1f}%)

🎯 Диапазон: {low} - {high} ₽
📍 Поддержка: ~{support} ₽ | Сопротивление: ~{resistance} ₽

📈 Технический анализ недоступен (ошибка API)
🔮 Рекомендация: следите за пробоем ключевых уровней

{DISCLAIMER}"""

def render_portfolio_analysis(stocks_data, market_trend=None):
    """Анализ всего портфеля с рекомендациями"""
    try:
        total_value = sum(data.get('position_value', 0) for data in stocks_data.values())
        gainers = [(t, d) for t, d in stocks_data.items() if d.get('change_pct', 0) > 0]
        losers = [(t, d) for t, d in stocks_data.items() if d.get('change_pct', 0) < 0]
        
        stocks_info = "\n".join([
            f"{ticker}: {data.get('current_price', 0):.1f} ₽ ({data.get('change_pct', 0):+.1f}%)"
            for ticker, data in stocks_data.items()
        ])
        
        text = f"""
АНАЛИЗИРУЙ ПОРТФЕЛЬ как профессиональный аналитик.

ПОРТФЕЛЬ:
{stocks_info}
Общая стоимость: {total_value:,.0f} ₽
Растут: {len(gainers)} позиций | Падают: {len(losers)} позиций

ЗАДАЧА:
1. 💼 Общая оценка портфеля (диверсификация, риски)
2. ⚡ Текущие рыночные факторы влияния
3. 🎯 Конкретные действия (перебалансировка, фиксация прибыли)
4. 📅 Стратегия на неделю

Ответ до 200 слов, конкретно и по делу.
"""
        
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": text}],
            temperature=0.4,
            max_tokens=250
        )
        return resp.choices[0].message.content + f"\n\n{DISCLAIMER}"
    except Exception as e:
        print(f"Portfolio analysis error: {e}")
        return f"💼 Портфель: {total_value:,.0f} ₽\n\n📈 Растут: {len(gainers)} позиций\n📉 Падают: {len(losers)} позиций\n\n{DISCLAIMER}"

def render_market_strategy(market_data):
    """Стратегия работы с портфелем на основе рынка"""
    try:
        text = f"""
Ты - стратег инвестиционного фонда. Дай КРАТКИЕ рекомендации по портфелю.

РЫНОЧНАЯ СИТУАЦИЯ:
- Индекс MOEX: движение и тренды
- Настроения инвесторов
- Ключевые риски и возможности

СТРАТЕГИЧЕСКИЕ РЕКОМЕНДАЦИИ:
🎯 Сейчас фокус на: (сектора/стратегии)
⚡ Избегать: (риски)
💰 Управление капиталом: (размер позиций)
📅 Горизонт: (краткосрочно/долгосрочно)

Макс 150 слов, конкретные действия.
"""
        
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": text}],
            temperature=0.5,
            max_tokens=200
        )
        return resp.choices[0].message.content + f"\n\n{DISCLAIMER}"
    except Exception as e:
        print(f"Strategy error: {e}")
        return f"📊 Рыночная стратегия временно недоступна\n\n🎯 Базовая рекомендация: держите диверсифицированный портфель\n\n{DISCLAIMER}"

def render_digest(title, bullets):
    body = f"{title}\n" + "\n".join([f"• {b}" for b in bullets]) + "\n" + DISCLAIMER
    return body
