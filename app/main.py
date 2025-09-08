import os
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

bot = Bot(TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher()
dp.include_router(tg_router)
app = FastAPI()

@app.on_event("startup")
async def startup():
    init_db()
    if BASE_URL:
        await bot.set_webhook(url=f"{BASE_URL}{WEBHOOK_PATH}")
    start_scheduler(bot)

@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
