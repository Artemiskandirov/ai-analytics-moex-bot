# 🚀 Руководство по развертыванию AI Analytics Bot в Казахстане

Пошаговое руководство по развертыванию Telegram-бота для анализа акций MOEX на сервере в Казахстане.

## 📋 Предварительные требования

### 1. Сервер
- Ubuntu 20.04+ или CentOS 8+
- Минимум 2GB RAM, 2 CPU cores
- 20GB свободного места на диске
- Публичный IP-адрес
- Доменное имя (например: `bot.yourcompany.kz`)

### 2. Учетные записи
- Telegram Bot Token (получить у [@BotFather](https://t.me/botfather))
- OpenAI API Key (https://platform.openai.com/api-keys)
- Cloudflare/другой DNS провайдер для домена

## 🛠 Установка

### Шаг 1: Подготовка сервера

```bash
# Подключение к серверу
ssh user@your-server-ip

# Скачивание проекта
cd /opt
sudo git clone https://github.com/your-repo/ai-analytics-bot.git
sudo chown -R $USER:$USER ai-analytics-bot
cd ai-analytics-bot

# Запуск установки базовых компонентов
chmod +x deploy/install.sh
./deploy/install.sh
```

### Шаг 2: Настройка конфигурации

```bash
# Создание .env файла
cp env.template .env
nano .env
```

Заполните следующие обязательные параметры:

```env
# Получить у @BotFather в Telegram
TELEGRAM_TOKEN=1234567890:ABCdefGhIJklmnoPQRSTuvwXYZ

# Получить на https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Ваш домен
BASE_URL=https://bot.yourcompany.kz

# Секретный путь для webhook (измените на случайный)
WEBHOOK_SECRET_PATH=/tg/webhook_abc123def456

# Настройки для Казахстана
TIMEZONE=Asia/Almaty
PREMIUM_PRICE_MIN=5000
```

### Шаг 3: Проблема доступа к OpenAI API в Казахстане

⚠️ **ВАЖНО**: OpenAI API может быть недоступен из Казахстана. Проверьте доступность:

```bash
curl -s https://api.openai.com/v1/models
```

Если команда зависает или возвращает ошибку, используйте одно из решений:

#### Решение 1: VPN на сервере (рекомендуется)
```bash
# Установка WireGuard
sudo apt install wireguard

# Настройка конфига VPN (получите у провайдера VPN)
sudo nano /etc/wireguard/wg0.conf

# Запуск VPN
sudo wg-quick up wg0
sudo systemctl enable wg-quick@wg0
```

#### Решение 2: Прокси-сервер
```bash
# Настройка прокси
./deploy/proxy-setup.sh

# Добавьте в .env файл
echo "PROXY_URL=socks5://your-proxy-server:port" >> .env
```

#### Решение 3: Альтернативные API
Измените в `.env`:
```env
# Вместо OpenAI используйте совместимый сервис
OPENAI_BASE_URL=https://openrouter.ai/api/v1
OPENAI_API_KEY=sk-or-v1-xxxxxxxxxxxxxxxxxxxxxxxx
```

### Шаг 4: Развертывание

```bash
# Установка исполняемых прав
chmod +x deploy/deploy.sh

# Запуск развертывания
./deploy/deploy.sh bot.yourcompany.kz
```

Скрипт автоматически:
- Настроит Nginx
- Запустит Docker контейнеры  
- Установит SSL сертификат
- Проверит работоспособность

### Шаг 5: Проверка работы

```bash
# Проверка статуса сервисов
docker-compose ps

# Просмотр логов
docker-compose logs web
docker-compose logs worker

# Проверка webhook
curl https://bot.yourcompany.kz/health
```

## 🔧 Настройка Telegram бота

1. Откройте бота в Telegram: `@your_bot_username`
2. Отправьте команду `/start`
3. Протестируйте команды:
   - `/trial` - бесплатный анализ
   - `/chart SBER` - график акции
   - `/chart_ta GAZP` - технический анализ

## 🔄 Обновление

```bash
cd /opt/ai-analytics-bot
git pull
./deploy/deploy.sh bot.yourcompany.kz
```

## 📊 Мониторинг

### Логи
```bash
# Основное приложение
docker-compose logs -f web

# Фоновые задачи  
docker-compose logs -f worker

# Nginx
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Метрики системы
```bash
# Использование ресурсов
docker stats

# Дисковое пространство
df -h

# Память
free -h
```

## 🛡 Безопасность

### 1. Настройка файрвола
```bash
sudo ufw status
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp  
sudo ufw allow 443/tcp
sudo ufw deny 8000/tcp  # Закрыть прямой доступ к приложению
```

### 2. Регулярные обновления
```bash
# Настройка автообновлений безопасности
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```

### 3. Backup базы данных
```bash
# Создание backup скрипта
cat > /opt/ai-analytics-bot/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker exec ai-analytics-bot_web_1 sqlite3 /app/app.db ".backup /app/backup_$DATE.db"
docker cp ai-analytics-bot_web_1:/app/backup_$DATE.db ./backups/
find ./backups -name "backup_*.db" -mtime +7 -delete
EOF

chmod +x backup.sh

# Добавление в cron
echo "0 2 * * * /opt/ai-analytics-bot/backup.sh" | sudo crontab -
```

## 🚨 Устранение неполадок

### Проблема: Webhook не работает
```bash
# Проверьте настройки webhook в Telegram
curl -X POST "https://api.telegram.org/bot$TELEGRAM_TOKEN/getWebhookInfo"

# Перезапуск бота
docker-compose restart web
```

### Проблема: OpenAI API недоступен
```bash
# Тест подключения из контейнера
docker-compose exec web curl -s https://api.openai.com/v1/models

# Проверка прокси настроек
docker-compose exec web env | grep -i proxy
```

### Проблема: Высокое потребление ресурсов
```bash
# Анализ логов на ошибки
docker-compose logs web | grep -i error

# Мониторинг запросов
docker-compose logs web | grep "POST\|GET" | tail -20
```

## 📞 Поддержка

- **Документация**: README.md в корне проекта
- **Логи**: `/var/log/nginx/` и `docker-compose logs`
- **Конфигурация**: `.env` файл в корне проекта

## 💡 Рекомендации для продакшена

1. **База данных**: Используйте PostgreSQL вместо SQLite
2. **Monitoring**: Установите Grafana + Prometheus
3. **Backup**: Настройте регулярные бэкапы в облако
4. **Load Balancer**: При высокой нагрузке добавьте несколько инстансов
5. **CDN**: Используйте Cloudflare для кэширования статики

---

🇰🇿 **Особенности для Казахстана:**
- Используйте часовой пояс `Asia/Almaty`
- Цены в тенге (настройте `PREMIUM_PRICE_MIN`)
- Рассмотрите локальные платежные системы для premium подписок
- Убедитесь в соблюдении местного законодательства о финансовых рекомендациях
