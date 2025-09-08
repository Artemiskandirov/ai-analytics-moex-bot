import os
import asyncio
import logging
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Update
from .storage import init_db
from .handlers import router as tg_router
from .worker import start_scheduler
from .config import TELEGRAM_TOKEN, BASE_URL, WEBHOOK_PATH
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher()
dp.include_router(tg_router)
app = FastAPI()

@app.on_event("startup")
async def startup():
    init_db()
    if BASE_URL:
        logger.info(f"Starting webhook mode: {BASE_URL}{WEBHOOK_PATH}")
        await bot.set_webhook(url=f"{BASE_URL}{WEBHOOK_PATH}")
    else:
        logger.info("Starting polling mode")
        await bot.delete_webhook(drop_pending_updates=True)
        # Запускаем polling в фоновой задаче
        asyncio.create_task(start_polling())
    start_scheduler(bot)

async def start_polling():
    """Запуск polling режима"""
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Polling error: {e}")

@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.get("/health")
async def health_check():
    return {"status": "ok", "mode": "webhook" if BASE_URL else "polling"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
