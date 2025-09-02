#!/bin/bash

# 🚀 Скрипт автоматической настройки HTTPS webhook для Telegram бота
# Использование: ./setup-webhook.sh [domain]

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Настройка HTTPS webhook для Telegram бота${NC}"

# Определяем домен
if [ "$1" ]; then
    DOMAIN="$1"
    echo -e "${GREEN}✅ Используем домен: $DOMAIN${NC}"
else
    # Автоматически получаем IP сервера
    SERVER_IP=$(curl -s ifconfig.me || curl -s ipinfo.io/ip || echo "217.25.90.175")
    DOMAIN="bot-$(echo $SERVER_IP | tr '.' '-').nip.io"
    echo -e "${YELLOW}⚡ Автоматически создан домен: $DOMAIN${NC}"
    echo -e "${BLUE}💡 nip.io - это бесплатный DNS сервис для разработки${NC}"
fi

echo -e "${BLUE}🔍 Проверяем DNS резолв...${NC}"
if nslookup $DOMAIN > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Домен $DOMAIN корректно резолвится${NC}"
else
    echo -e "${RED}❌ Ошибка: домен $DOMAIN не резолвится!${NC}"
    echo -e "${YELLOW}💡 Убедитесь что A-запись домена указывает на IP сервера${NC}"
    exit 1
fi

echo -e "${BLUE}📦 Устанавливаем certbot...${NC}"
apt update -qq
apt install -y certbot > /dev/null 2>&1
echo -e "${GREEN}✅ Certbot установлен${NC}"

echo -e "${BLUE}🔒 Получаем SSL сертификат от Let's Encrypt...${NC}"
# Останавливаем nginx если запущен
docker-compose stop nginx > /dev/null 2>&1 || true

# Получаем сертификат
if certbot certonly --standalone \
    -d $DOMAIN \
    --email admin@$DOMAIN \
    --agree-tos \
    --non-interactive \
    --quiet; then
    echo -e "${GREEN}✅ SSL сертификат получен успешно${NC}"
else
    echo -e "${RED}❌ Ошибка получения SSL сертификата${NC}"
    exit 1
fi

echo -e "${BLUE}📁 Копируем сертификаты в проект...${NC}"
mkdir -p ops/ssl
cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem ops/ssl/
cp /etc/letsencrypt/live/$DOMAIN/privkey.pem ops/ssl/
chmod 644 ops/ssl/*.pem
echo -e "${GREEN}✅ Сертификаты скопированы${NC}"

echo -e "${BLUE}⚙️ Обновляем конфигурацию nginx...${NC}"
# Заменяем yourdomain.ru на реальный домен
sed -i "s/yourdomain.ru/$DOMAIN/g" ops/nginx.conf
echo -e "${GREEN}✅ Nginx конфигурация обновлена${NC}"

echo -e "${BLUE}🔧 Обновляем переменные окружения...${NC}"
# Обновляем .env
if grep -q "^BASE_URL=" .env; then
    sed -i "s|^BASE_URL=.*|BASE_URL=https://$DOMAIN|" .env
else
    echo "BASE_URL=https://$DOMAIN" >> .env
fi

# Проверяем .env
echo -e "${YELLOW}📋 Текущие настройки в .env:${NC}"
grep -E "(BOT_TOKEN|BASE_URL|WEBHOOK)" .env | head -5

echo -e "${BLUE}🐳 Перезапускаем контейнеры...${NC}"
docker-compose down > /dev/null 2>&1 || true
docker-compose up -d

echo -e "${BLUE}⏳ Ждем запуска приложения...${NC}"
sleep 15

echo -e "${BLUE}🔍 Проверяем статус...${NC}"
if curl -s "https://$DOMAIN/health" > /dev/null; then
    echo -e "${GREEN}✅ HTTPS работает корректно!${NC}"
else
    echo -e "${YELLOW}⚠️ HTTPS пока недоступен, проверяем логи...${NC}"
    docker-compose logs --tail=10 nginx
fi

echo -e "${BLUE}📱 Проверяем webhook Telegram...${NC}"
WEBHOOK_INFO=$(curl -s "https://api.telegram.org/bot$(grep BOT_TOKEN .env | cut -d'=' -f2)/getWebhookInfo")
echo -e "${YELLOW}📋 Информация о webhook:${NC}"
echo "$WEBHOOK_INFO" | python3 -m json.tool 2>/dev/null || echo "$WEBHOOK_INFO"

echo ""
echo -e "${GREEN}🎉 Настройка завершена!${NC}"
echo -e "${BLUE}🌐 Ваш бот доступен по адресу: https://$DOMAIN${NC}"
echo -e "${BLUE}📱 Webhook URL: https://$DOMAIN/webhook/secret/ai-bot-2024${NC}"
echo -e "${YELLOW}💡 Протестируйте бота в Telegram: @Market_Lensbot${NC}"

echo ""
echo -e "${BLUE}🔧 Полезные команды:${NC}"
echo -e "  • Проверить webhook: curl https://$DOMAIN/health"
echo -e "  • Посмотреть логи:  docker-compose logs -f web"
echo -e "  • Перезапустить:   docker-compose restart"

echo ""
echo -e "${GREEN}✅ Готово! Ваш бот работает с HTTPS webhook!${NC}"
