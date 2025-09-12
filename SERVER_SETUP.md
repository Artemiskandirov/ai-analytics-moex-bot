# 🚀 Быстрая настройка сервера для AI Analytics Bot

Краткая инструкция для развертывания вашего AI Analytics Bot из GitHub на облачном сервере.

## 📋 Что нужно подготовить

### 1. Сервер
- **VPS/Облачный сервер** (DigitalOcean, Yandex Cloud, AWS EC2, и т.д.)
- **ОС**: Ubuntu 20.04+ 
- **Ресурсы**: минимум 2GB RAM, 2 CPU, 20GB диск
- **Доступ**: SSH ключ или пароль root/sudo пользователя

### 2. Домен (опционально, но рекомендуется)
- Купите домен (например: `bot.yourcompany.kz`)
- Настройте A-запись на IP вашего сервера

### 3. API ключи
- **Telegram Bot Token**: получите у [@BotFather](https://t.me/botfather)
- **OpenAI API Key**: получите на [platform.openai.com](https://platform.openai.com/api-keys)

## 🛠 Развертывание на сервере

### Шаг 1: Подключение к серверу
```bash
# Подключитесь к серверу по SSH
ssh root@YOUR_SERVER_IP
# или если у вас пользователь с sudo:
ssh username@YOUR_SERVER_IP
```

### Шаг 2: Одна команда для полного развертывания
```bash
# Скачайте и запустите скрипт развертывания
curl -fsSL https://raw.githubusercontent.com/Artemiskandirov/ai-analytics-moex-bot/main/deploy/github-deploy.sh | bash -s -- https://github.com/Artemiskandirov/ai-analytics-moex-bot.git bot.yourcompany.kz
```

**Замените `bot.yourcompany.kz` на ваш реальный домен или IP адрес!**

### Шаг 3: Настройка конфигурации
```bash
# Перейдите в директорию проекта
cd /opt/ai-analytics-bot

# Отредактируйте .env файл
nano .env
```

**Обязательно заполните:**
```env
TELEGRAM_TOKEN=ваш_токен_от_botfather
OPENAI_API_KEY=ваш_openai_ключ
BASE_URL=https://bot.yourcompany.kz
WEBHOOK_SECRET_PATH=/tg/secret_path_123
```

### Шаг 4: Запуск бота
```bash
# Запустите развертывание
./deploy/deploy.sh bot.yourcompany.kz
```

### Шаг 5: Проверка работы
```bash
# Проверьте статус сервисов
docker-compose ps

# Проверьте логи
docker-compose logs web

# Протестируйте бота в Telegram
```

## 🌍 Для Казахстана: решение проблем с OpenAI

Если OpenAI API заблокирован в вашем регионе:

### Вариант 1: Проверьте доступность
```bash
curl -s https://api.openai.com/v1/models
```

### Вариант 2: Настройте VPN на сервере
```bash
# Установите WireGuard VPN
sudo apt install wireguard

# Получите конфиг у VPN провайдера и поместите в /etc/wireguard/wg0.conf
sudo wg-quick up wg0
```

### Вариант 3: Используйте альтернативные API
В `.env` файле измените:
```env
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_API_KEY=sk-or-v1-ваш_ключ_openrouter
```

## 🔄 Обновление бота

```bash
cd /opt/ai-analytics-bot
./deploy/update.sh
```

## 📊 Полезные команды

```bash
# Логи в реальном времени
docker-compose logs -f web

# Перезапуск сервисов
docker-compose restart

# Статус системы
docker-compose ps
free -h
df -h

# Backup базы данных
docker exec ai-analytics-bot_web_1 sqlite3 /app/app.db ".backup /app/backup.db"
```

## 🆘 Быстрое решение проблем

### Бот не отвечает
```bash
# Проверьте webhook
curl https://api.telegram.org/bot$TELEGRAM_TOKEN/getWebhookInfo

# Перезапустите бота
docker-compose restart web
```

### OpenAI не работает
```bash
# Тест из контейнера
docker-compose exec web curl -s https://api.openai.com/v1/models

# Если не работает - настройте VPN или смените на OpenRouter
```

### Высокая нагрузка
```bash
# Проверьте логи на ошибки
docker-compose logs web | grep ERROR

# Мониторинг ресурсов
docker stats
```

## 💡 Рекомендации

1. **SSL сертификат**: автоматически устанавливается для доменов
2. **Monitoring**: настройте уведомления о падении сервиса
3. **Backup**: регулярно создавайте backup базы данных
4. **Security**: используйте ssh ключи, настройте fail2ban

---

## ⚡ Экспресс-развертывание (3 команды)

Если у вас уже есть сервер с Ubuntu и домен:

```bash
# 1. Подключитесь к серверу
ssh root@YOUR_SERVER_IP

# 2. Запустите развертывание одной командой
curl -fsSL https://raw.githubusercontent.com/Artemiskandirov/ai-analytics-moex-bot/main/deploy/github-deploy.sh | bash -s -- https://github.com/Artemiskandirov/ai-analytics-moex-bot.git bot.yourcompany.kz

# 3. Настройте .env и запустите
cd /opt/ai-analytics-bot && nano .env && ./deploy/deploy.sh bot.yourcompany.kz
```

🎉 **Готово!** Ваш бот должен работать по адресу `https://bot.yourcompany.kz`
