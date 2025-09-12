#!/bin/bash

# 🚀 Быстрая установка AI Analytics Bot на сервер с Docker + Ubuntu
# Для серверов где Docker уже установлен

set -e

echo "🚀 Быстрая установка AI Analytics Bot"
echo "📋 Проверяем что Docker уже установлен..."

# Проверяем Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не найден! Установите Docker сначала."
    exit 1
fi

if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "📦 Устанавливаем Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

echo "✅ Docker готов: $(docker --version)"

# Устанавливаем только необходимые пакеты
echo "📦 Устанавливаем базовые пакеты..."
apt update
apt install -y git nginx certbot python3-certbot-nginx nano curl wget ufw

# Настройка файрвола
echo "🔥 Настройка файрвола..."
ufw allow 22/tcp
ufw allow 80/tcp  
ufw allow 443/tcp
ufw --force enable

# Запуск Nginx
echo "🌐 Запуск Nginx..."
systemctl start nginx
systemctl enable nginx

# Клонирование проекта
echo "📥 Клонирование проекта..."
cd /opt
if [ -d "ai-analytics-bot" ]; then
    echo "⚠️ Удаляем старую версию..."
    rm -rf ai-analytics-bot
fi

git clone https://github.com/Artemiskandirov/ai-analytics-moex-bot.git ai-analytics-bot
cd ai-analytics-bot

# Создание .env файла
echo "⚙️ Создание .env файла..."
if [ -f "env.template" ]; then
    cp env.template .env
    echo "✅ Создан .env файл из шаблона"
else
    echo "❌ Шаблон env.template не найден!"
    exit 1
fi

# Установка прав на скрипты
chmod +x deploy/*.sh

echo ""
echo "🎉 Установка завершена!"
echo ""
echo "📋 Что дальше:"
echo "1. Настройте .env файл:"
echo "   nano /opt/ai-analytics-bot/.env"
echo ""
echo "2. Обязательно заполните:"
echo "   - TELEGRAM_TOKEN (получить у @BotFather)"
echo "   - OPENAI_API_KEY (получить на platform.openai.com)"
echo "   - BASE_URL (ваш домен или IP)"
echo ""
echo "3. Запустите бота:"
echo "   cd /opt/ai-analytics-bot"
echo "   ./deploy/deploy.sh ваш-домен.com"
echo ""
echo "💡 Текущая директория: $(pwd)"
echo "📄 Файл конфигурации: /opt/ai-analytics-bot/.env"
echo ""
