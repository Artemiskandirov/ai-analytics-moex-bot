import os
from openai import OpenAI
from .config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)
MODEL = "gpt-4o-mini"
DISCLAIMER = ("ℹ️ Информация носит аналитический и образовательный характер "
              "и не является индивидуальной инвестиционной рекомендацией.")

def render_stock_analysis(ticker, q, levels=None):
    try:
        text = f"""
Сделай КРАТКИЙ инвестиционный анализ {ticker}. 

ДАННЫЕ:
Цена: {q.get('last')} ₽ ({q.get('change_pct'):+.1f}%)
Диапазон: {q.get('low')} - {q.get('high')} ₽
Поддержка: {(levels or {}).get('levels',{}).get('support','—')} ₽
Сопротивление: {(levels or {}).get('levels',{}).get('resistance','—')} ₽

ФОРМАТ ОТВЕТА:
🎯 Краткая оценка (1-2 предложения)
📈 Потенциал роста/падения
⚡ Ключевые факторы влияния
🔮 Прогноз на неделю

Пиши сжато, без воды. Макс 150 слов.
"""
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": text}],
            temperature=0.3,
            max_tokens=200
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
