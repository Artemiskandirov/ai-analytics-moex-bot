import logging
import sys
import os
from datetime import datetime

def setup_logging():
    """
    Настраивает систему логирования для приложения
    """
    # Получаем настройки из переменных окружения
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_file = os.getenv('LOG_FILE', '/app/logs/bot.log')
    
    # Создаем директорию для логов если её нет
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir, exist_ok=True)
        except Exception:
            # Если не можем создать директорию, используем текущую
            log_file = 'bot.log'
    
    # Формат логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Настраиваем root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # Удаляем существующие handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level, logging.INFO))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler (если удалось определить файл)
    try:
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # В файл пишем все
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        # Если не можем создать файловый handler, продолжаем только с консольным
        logging.warning(f"Cannot create file handler for {log_file}: {e}")
    
    # Настраиваем уровни для внешних библиотек
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('aiogram').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    
    # Логируем успешную инициализацию
    logging.info("Logging system initialized")
    logging.info(f"Log level: {log_level}")
    logging.info(f"Log file: {log_file}")

def log_user_action(user_id, action, details=None):
    """
    Логирует действия пользователей
    """
    logger = logging.getLogger('user_actions')
    message = f"User {user_id}: {action}"
    if details:
        message += f" - {details}"
    logger.info(message)

def log_api_call(api_name, endpoint, status_code=None, response_time=None, error=None):
    """
    Логирует вызовы внешних API
    """
    logger = logging.getLogger('api_calls')
    message = f"API call to {api_name} - {endpoint}"
    
    if status_code:
        message += f" - Status: {status_code}"
    if response_time:
        message += f" - Time: {response_time:.2f}s"
    
    if error:
        logger.error(f"{message} - Error: {error}")
    else:
        logger.info(message)

def log_notification_sent(user_id, notification_type, ticker=None):
    """
    Логирует отправленные уведомления
    """
    logger = logging.getLogger('notifications')
    message = f"Notification sent to user {user_id}: {notification_type}"
    if ticker:
        message += f" for {ticker}"
    logger.info(message)

class APICallLogger:
    """
    Декоратор для логирования API вызовов
    """
    def __init__(self, api_name):
        self.api_name = api_name
    
    def __call__(self, func):
        def wrapper(*args, **kwargs):
            import time
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                response_time = time.time() - start_time
                log_api_call(
                    self.api_name, 
                    func.__name__, 
                    status_code=200, 
                    response_time=response_time
                )
                return result
            except Exception as e:
                response_time = time.time() - start_time
                log_api_call(
                    self.api_name, 
                    func.__name__, 
                    response_time=response_time, 
                    error=str(e)
                )
                raise
        return wrapper
