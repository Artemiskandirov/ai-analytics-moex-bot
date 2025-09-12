#!/bin/bash

# Скрипт развертывания AI Analytics Bot
set -e

PROJECT_DIR="/opt/ai-analytics-bot"
DOMAIN=${1:-"yourdomain.kz"}

echo "🚀 Развертывание AI Analytics Bot на домене: $DOMAIN"

# Проверка существования директории проекта
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Директория проекта не найдена: $PROJECT_DIR"
    echo "Сначала клонируйте репозиторий из GitHub"
    exit 1
fi

# Проверка наличия .env файла
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "❌ Файл .env не найден в $PROJECT_DIR"
    echo "Скопируйте env.template в .env и настройте его"
    exit 1
fi

# Переход в директорию проекта
cd $PROJECT_DIR

# Обновление кода из GitHub
echo "📥 Обновление кода из GitHub..."
git pull origin main || git pull origin master || echo "⚠️ Не удалось обновить из Git"

# Остановка существующих контейнеров
echo "🛑 Остановка существующих контейнеров..."
docker-compose down 2>/dev/null || true

# Обновление Nginx конфигурации
echo "🌐 Настройка Nginx..."
sudo tee /etc/nginx/sites-available/ai-analytics-bot > /dev/null <<EOF
server {
    listen 80;
    server_name $DOMAIN;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        
        # Увеличиваем таймауты для AI запросов
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF

# Активация сайта
sudo ln -sf /etc/nginx/sites-available/ai-analytics-bot /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

# Сборка и запуск контейнеров
echo "🐳 Сборка и запуск контейнеров..."
docker-compose build
docker-compose up -d

# Ожидание запуска сервисов
echo "⏳ Ожидание запуска сервисов..."
sleep 10

# Проверка статуса
echo "📊 Проверка статуса сервисов..."
docker-compose ps

# Настройка SSL с Certbot
echo "🔒 Настройка SSL сертификата..."
if [ "$DOMAIN" != "yourdomain.kz" ]; then
    sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN
    echo "✅ SSL сертификат установлен"
else
    echo "⚠️  Замените yourdomain.kz на ваш реальный домен для получения SSL"
fi

echo ""
echo "🎉 Развертывание завершено!"
echo "🌐 Ваш бот доступен по адресу: https://$DOMAIN"
echo ""
echo "📋 Проверьте логи:"
echo "   docker-compose logs web"
echo "   docker-compose logs worker"
echo ""
echo "🔄 Для обновления запустите:"
echo "   git pull && ./deploy/deploy.sh $DOMAIN"
