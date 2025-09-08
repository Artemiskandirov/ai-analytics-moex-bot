import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_URL   = os.getenv("DATABASE_URL", "sqlite:///app.db")
TIMEZONE       = os.getenv("TIMEZONE", "Europe/Moscow")
PREMIUM_PRICE  = int(os.getenv("PREMIUM_PRICE_MIN", "2000"))
POLL_SEC       = int(os.getenv("PRICE_POLL_INTERVAL_SEC", "300"))
BASE_URL       = os.getenv("BASE_URL", "")
WEBHOOK_PATH   = os.getenv("WEBHOOK_SECRET_PATH", "/tg/hook")

BOARD_SHARES   = os.getenv("MARKET_BOARD_SHARES", "TQBR")
BOARD_ETF      = os.getenv("MARKET_BOARD_ETF", "TQTF")
BOARD_BONDS    = os.getenv("MARKET_BOARD_BONDS", "TQOB")
