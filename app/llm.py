import os
from openai import OpenAI
from .config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)
MODEL = "gpt-4o-mini"
DISCLAIMER = ("ℹ️ Информация носит аналитический и образовательный характер "
              "и не является индивидуальной инвестиционной рекомендацией.")

def render_trial_note(ticker, q, levels=None):
    text = f"""
Сделай краткий учебный обзор по {ticker} в стиле аналитики.
Цена: {q.get('last')} (изм {q.get('change_pct')}%), HIGH {q.get('high')}, LOW {q.get('low')}.
Уровни внимания: поддержка ~{(levels or {}).get('levels',{}).get('support','—')}, сопротивление ~{(levels or {}).get('levels',{}).get('resistance','—')}.
Опиши 2 сценария в терминах "иногда рассматривают трейдеры", без слов купи/продай/стоп.
В конце поставь дисклеймер.
"""
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": text}],
        temperature=0.2,
        max_tokens=220
    )
    return resp.choices[0].message.content + "\n" + DISCLAIMER

def render_digest(title, bullets):
    body = f"{title}\n" + "\n".join([f"• {b}" for b in bullets]) + "\n" + DISCLAIMER
    return body
