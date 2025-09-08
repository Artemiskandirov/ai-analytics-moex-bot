import os
from typing import List, Dict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw

DISCLAIMER = ("Информация носит аналитический и образовательный характер "
              "и не является индивидуальной инвестиционной рекомендацией.")

def render_price_chart(ticker: str, candles: List[Dict], levels: Dict=None, out_dir: str="app/out") -> str:
    os.makedirs(out_dir, exist_ok=True)
    if not candles:
        raise ValueError("Нет данных свечей для построения графика")
    closes = [c["close"] for c in candles if c.get("close") is not None]
    xs = list(range(len(closes)))
    fig = plt.figure(figsize=(10, 4.5), dpi=150)
    ax = fig.add_subplot(111)
    ax.plot(xs, closes, linewidth=1.5)
    sup = res = None
    if levels and "levels" in levels:
        sup = levels["levels"].get("support")
        res = levels["levels"].get("resistance")
    if sup is not None:
        ax.axhline(sup, linestyle="--", linewidth=1)
        ax.text(xs[int(len(xs)*0.01)], sup, f" support ~{round(float(sup),2)}", va="bottom")
    if res is not None:
        ax.axhline(res, linestyle="--", linewidth=1)
        ax.text(xs[int(len(xs)*0.01)], res, f" resistance ~{round(float(res),2)}", va="bottom")
    ax.set_title(f"{ticker}: Price & Levels")
    ax.set_xlabel("bars")
    ax.set_ylabel("price")
    out_path = os.path.join(out_dir, f"chart_{ticker}.png")
    fig.tight_layout(); fig.savefig(out_path); plt.close(fig)

    try:
        im = Image.open(out_path).convert("RGBA")
        w, h = im.size
        overlay = Image.new("RGBA", im.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        pad = 12
        text = DISCLAIMER
        tw, th = draw.textbbox((0,0), text)[2:]
        box_h = th + pad*2
        draw.rectangle((0, h - box_h, w, h), fill=(255, 255, 255, 160))
        draw.text((pad, h - box_h + pad), text, fill=(0, 0, 0, 255))
        out_path2 = os.path.join(out_dir, f"chart_{ticker}_wm.png")
        Image.alpha_composite(im, overlay).convert("RGB").save(out_path2, "PNG", optimize=True)
        return out_path2
    except Exception:
        return out_path

def render_ta_chart(ticker: str, candles: List[Dict], out_dir: str="app/out") -> str:
    os.makedirs(out_dir, exist_ok=True)
    if not candles or len(candles) < 30:
        raise ValueError("Недостаточно данных для технического анализа")
    closes = [c["close"] for c in candles]
    highs  = [c["high"]  for c in candles]
    lows   = [c["low"]   for c in candles]

    from .ta import sma, atr_from_candles, recent_swing_levels, pivot_levels, breakout_signals
    sma20 = sma(closes, 20)
    sma50 = sma(closes, 50)
    sma200= sma(closes, 200)
    atr14 = atr_from_candles(candles, 14)

    swing_high, swing_low = recent_swing_levels(closes, highs, lows, 60)
    ph, pl, pc = highs[-2], lows[-2], closes[-2]
    piv = pivot_levels(ph, pl, pc)

    buys, sells = breakout_signals(closes, 20, 20)

    xs = list(range(len(closes)))
    fig = plt.figure(figsize=(11, 5), dpi=150)
    ax = fig.add_subplot(111)
    ax.plot(xs, closes, linewidth=1.3, label="Close")
    ax.plot(xs, sma20, linewidth=1.0, label="SMA20")
    ax.plot(xs, sma50, linewidth=1.0, label="SMA50")
    ax.plot(xs, sma200, linewidth=1.0, label="SMA200")
    if swing_high: ax.axhline(swing_high, linestyle="--", linewidth=1)
    if swing_low:  ax.axhline(swing_low,  linestyle="--", linewidth=1)
    ax.axhline(piv["P"],  linestyle=":", linewidth=1)
    ax.axhline(piv["R1"], linestyle=":", linewidth=1)
    ax.axhline(piv["S1"], linestyle=":", linewidth=1)
    if buys:
        ax.scatter(buys, [closes[i] for i in buys], s=25, marker="^")
    if sells:
        ax.scatter(sells,[closes[i] for i in sells], s=25, marker="v")
    ax.set_title(f"{ticker}: TA (Close, SMA20/50/200, Swing HL, Pivot, Breakouts)")
    ax.set_xlabel("bars")
    ax.set_ylabel("price")
    ax.legend(loc="best")
    out_path = os.path.join(out_dir, f"ta_{ticker}.png")
    fig.tight_layout(); fig.savefig(out_path); plt.close(fig)

    try:
        im = Image.open(out_path).convert("RGBA")
        w, h = im.size
        overlay = Image.new("RGBA", im.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        pad = 12
        text = DISCLAIMER
        tw, th = draw.textbbox((0,0), text)[2:]
        box_h = th + pad*2
        draw.rectangle((0, h - box_h, w, h), fill=(255, 255, 255, 160))
        draw.text((pad, h - box_h + pad), text, fill=(0, 0, 0, 255))
        out_path2 = os.path.join(out_dir, f"ta_{ticker}_wm.png")
        Image.alpha_composite(im, overlay).convert("RGB").save(out_path2, "PNG", optimize=True)
        return out_path2
    except Exception:
        return out_path
