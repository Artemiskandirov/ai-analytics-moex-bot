# 🤖 AI Analytics Bot для MOEX

> Telegram-бот для аналитики российского фондового рынка с использованием MOEX ISS API и OpenAI

## 🎯 Основные возможности

### 🆓 Бесплатные функции
- **Пробный анализ** - один бесплатный разбор акции из вашего портфеля
- **Управление портфелем** - добавление и просмотр позиций
- **Актуальные котировки** - цены акций, ETF и облигаций с MOEX

### 💰 Премиум подписка (от 2000₽/мес)
- **Автоматические дайджесты** - 3 раза в день (8:30, 15:00, 18:30 МСК)
- **Настраиваемые триггеры** - пороги от -50% до +100% с шагом 1%
- **Полный анализ портфеля** - команда `/analyze` в любое время
- **Техническая аналитика** - уровни поддержки/сопротивления

## 🚀 Быстрый старт

### 1. Подготовка
```bash
git clone <repository>
cd ai-analytics-bot-with-triggers
cp env.example .env
```

### 2. Настройка переменных окружения

Отредактируйте файл `.env`:

```bash
# Обязательные параметры
TELEGRAM_TOKEN=your_bot_token_from_@BotFather
OPENAI_API_KEY=your_openai_api_key
BASE_URL=https://yourdomain.com
WEBHOOK_SECRET_PATH=/webhook/secret/path

# База данных (PostgreSQL рекомендуется для продакшена)
DATABASE_URL=postgresql://ai_bot_user:your_password@db:5432/ai_bot_db
DB_PASSWORD=secure_password_123

# Дополнительные настройки
PREMIUM_PRICE_MIN=2000
VERIFY_TOKEN=your_payment_verification_code
TIMEZONE=Europe/Moscow
LOG_LEVEL=INFO
```

### 3. Запуск с Docker

```bash
# Создание и запуск всех сервисов
docker compose up -d

# Проверка статуса
docker compose ps

# Просмотр логов
docker compose logs -f web
```

### 4. Настройка HTTPS

```bash
# Установка Certbot (Ubuntu/Debian)
sudo apt install certbot python3-certbot-nginx

# Получение SSL сертификата
sudo certbot --nginx -d yourdomain.com

# Перезапуск nginx
docker compose restart nginx
```

### 5. Настройка Telegram webhook

Бот автоматически установит webhook при запуске. Для проверки:

```bash
curl -X GET "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"
```

## 📱 Команды бота

### Пользовательские команды
- `/start` - приветствие и инструкции
- `/help` - справка по всем командам
- `/trial` - бесплатный анализ акции из вашего портфеля
- `/portfolio` - показать портфель с ценами
- `/analyze` - полный анализ (премиум)
- `/verify <код>` - активация премиум подписки
- `/features` - возможности премиум подписки

### Настройка триггеров
- `/settings` - текущие настройки пользователя
- `/trigger_set +15 -10` - установить пороги роста/падения  
- `/trigger_on` - включить уведомления
- `/trigger_off` - выключить уведомления

### Управление портфелем

Отправьте список тикеров для добавления:
```
GAZP 100
SBER 50
FXGD 200
```

Поддерживаются:
- **Акции**: GAZP, SBER, NVTK, YNDX и др.
- **ETF**: FXGD, FXIT, TECH, SBGB и др.
- **Облигации**: по ISIN коду

### Настройка персональных триггеров

**Для премиум пользователей:** настройте индивидуальные пороги срабатывания уведомлений

```bash
# Посмотреть текущие настройки
/settings

# Установить пороги: рост +15%, падение -10%
/trigger_set +15 -10

# Включить/выключить уведомления
/trigger_on    # включить
/trigger_off   # выключить
```

**Диапазоны:**
- Рост: от +1% до +100% 
- Падение: от -1% до -50%
- Шаг: 1% (только целые числа)

**Примеры настроек:**
- Консервативный: `/trigger_set +20 -15` 
- Средний: `/trigger_set +10 -8`
- Агрессивный: `/trigger_set +3 -3`

## 🏗 Архитектура

```
📦 ai-analytics-bot-with-triggers/
├── 🐍 app/                    # Основное приложение
│   ├── config.py             # Конфигурация
│   ├── main.py               # FastAPI приложение
│   ├── handlers.py           # Обработчики команд
│   ├── storage.py            # SQLAlchemy модели
│   ├── moex.py               # MOEX ISS API
│   ├── llm.py                # OpenAI интеграция
│   ├── worker.py             # Планировщик и дайджесты
│   ├── triggers.py           # Логика триггеров
│   ├── levels.py             # Технический анализ
│   ├── texts.py              # Тексты сообщений
│   └── logging_config.py     # Настройка логирования
├── 🐳 docker-compose.yml     # Оркестрация сервисов
├── 🐳 Dockerfile             # Образ приложения
├── 🌐 ops/
│   └── nginx.conf            # Конфигурация Nginx
├── 📋 requirements.txt       # Python зависимости
└── 📄 env.example           # Шаблон переменных окружения
```

## 🛠 Технический стек

- **Backend**: FastAPI + aiogram
- **Database**: PostgreSQL + SQLAlchemy
- **Scheduler**: APScheduler
- **AI**: OpenAI API
- **Market Data**: MOEX ISS API
- **Deployment**: Docker + Docker Compose
- **Proxy**: Nginx с SSL
- **Monitoring**: Dozzle (опционально)

## 📊 Схема базы данных

```sql
-- Пользователи
users (id, tg_id, plan, plan_valid_to, free_trial_used, tz, created_at)

-- Портфели
portfolios (id, user_id, updated_at)

-- Позиции в портфеле
positions (id, portfolio_id, ticker, board, qty, avg_price, currency)

-- Уровни для триггеров
watch_levels (id, user_id, ticker, level_type, value, note)

-- Лог событий
events_log (id, user_id, ticker, event_type, payload, sent_at)
```

## 🔧 Дополнительные команды

### Разработка

```bash
# Локальный запуск без Docker
pip install -r requirements.txt
export DATABASE_URL="sqlite:///app.db"
python -m app.main

# Запуск только базы данных
docker compose up -d db

# Просмотр логов
docker compose logs -f
```

### Мониторинг

```bash
# Включить веб-интерфейс для логов
docker compose --profile monitoring up -d

# Доступ к Dozzle: http://your-server:9999
```

### Бэкапы

```bash
# Создание бэкапа БД
docker compose exec db pg_dump -U ai_bot_user ai_bot_db > backup.sql

# Восстановление
docker compose exec -T db psql -U ai_bot_user ai_bot_db < backup.sql
```

## 🚨 Безопасность

### Обязательные меры:
1. **Смените все пароли** в `.env`
2. **Настройте firewall** (закройте порты кроме 80, 443, 22)
3. **Регулярно обновляйте** образы Docker
4. **Мониторьте логи** на подозрительную активность

### Nginx защита:
- ✅ Rate limiting на API endpoints
- ✅ SSL/TLS шифрование
- ✅ Скрытие версий сервера
- ✅ Защитные HTTP заголовки
- ✅ Ограничение размера запросов

## 📈 Производительность

- **Rate limits**: 10 запросов/мин на API, 60/мин на webhook
- **Кэширование**: статические ответы 1 минута
- **Connection pooling**: до 32 постоянных соединений
- **Health checks**: автоматическое восстановление сервисов

## ⚖️ Правовые аспекты

> ⚠️ **Важно**: Все сообщения содержат обязательный дисклеймер:
> 
> *"Информация носит аналитический и образовательный характер и не является индивидуальной инвестиционной рекомендацией."*

Бот предоставляет **образовательную аналитику**, а не инвестиционные советы.

## 🐛 Troubleshooting

### Частые проблемы:

**1. Бот не отвечает:**
```bash
# Проверить статус
docker compose ps
# Проверить логи
docker compose logs web
# Проверить webhook
curl https://yourdomain.com/health
```

**2. Ошибки базы данных:**
```bash
# Пересоздать БД
docker compose down -v
docker compose up -d
```

**3. Проблемы с SSL:**
```bash
# Проверить сертификат
sudo certbot certificates
# Обновить
sudo certbot renew
```

**4. OpenAI API ошибки:**
- Проверьте баланс аккаунта
- Убедитесь в правильности API ключа
- Проверьте лимиты запросов

## 📞 Поддержка

Для получения поддержки:
1. Проверьте логи: `docker compose logs`
2. Изучите этот README
3. Создайте issue с описанием проблемы

## 📜 Лицензия

Проект распространяется под лицензией MIT.
