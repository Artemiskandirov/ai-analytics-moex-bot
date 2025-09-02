import os
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Update
from .storage import init_db
from .handlers import router as tg_router
from .worker import start_scheduler
from .config import BOT_TOKEN, BASE_URL, WEBHOOK_PATH
from .logging_config import setup_logging, log_user_action, log_api_call
import uvicorn

# Инициализируем логирование
setup_logging()
logger = logging.getLogger(__name__)

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp  = Dispatcher()
dp.include_router(tg_router)
app = FastAPI()

@app.on_event("startup")
async def startup():
    """Инициализация приложения при запуске"""
    try:
        logger.info("Starting application initialization...")
        
        # Инициализация базы данных
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized successfully")
        
        # Настройка webhook
        if BASE_URL:
            webhook_url = f"{BASE_URL}{WEBHOOK_PATH}"
            logger.info(f"Setting webhook to: {webhook_url}")
            try:
                await bot.set_webhook(url=webhook_url)
                logger.info("Webhook set successfully")
            except Exception as e:
                logger.error(f"Failed to set webhook: {e}")
                raise
        else:
            logger.warning("BASE_URL not set, webhook will not be configured")
        
        # Запуск планировщика задач
        logger.info("Starting scheduler...")
        start_scheduler(bot)
        logger.info("Scheduler started successfully")
        
        logger.info("Application initialization completed")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise

@app.post(WEBHOOK_PATH)
async def telegram_webhook(request: Request):
    """Обработчик входящих обновлений от Telegram"""
    try:
        # Получаем данные
        data = await request.json()
        
        # Логируем входящее обновление (без полных данных для безопасности)
        update_type = "unknown"
        user_id = None
        
        if "message" in data:
            update_type = "message"
            user_id = data["message"].get("from", {}).get("id")
        elif "callback_query" in data:
            update_type = "callback_query"
            user_id = data["callback_query"].get("from", {}).get("id")
        
        if user_id:
            log_user_action(user_id, f"received_{update_type}")
        
        # Валидируем и обрабатываем обновление
        update = Update.model_validate(data)
        await dp.feed_update(bot, update)
        
        return {"ok": True}
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        logger.error(f"Request data keys: {list(data.keys()) if 'data' in locals() else 'No data'}")
        
        # Возвращаем ошибку, но не раскрываем детали
        raise HTTPException(status_code=500, detail="Internal server error")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Глобальный обработчик исключений"""
    logger.error(f"Unhandled exception: {exc}")
    logger.error(f"Request URL: {request.url}")
    
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

@app.get("/health")
async def health_check():
    """Проверка состояния сервиса"""
    try:
        # Проверяем доступность бота
        bot_info = await bot.get_me()
        
        return {
            "status": "healthy",
            "bot_username": bot_info.username,
            "timestamp": logging.Formatter().formatTime(logging.LogRecord(
                name="", level=0, pathname="", lineno=0, msg="", args=(), exc_info=None
            ))
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
