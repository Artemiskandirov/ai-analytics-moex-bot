#!/bin/bash

# Скрипт обновления AI Analytics Bot из GitHub
set -e

PROJECT_DIR="/opt/ai-analytics-bot"
DOMAIN=${1:-$(grep BASE_URL .env 2>/dev/null | cut -d'=' -f2 | sed 's|https://||' | sed 's|http://||' || echo "yourdomain.kz")}

echo "🔄 Обновление AI Analytics Bot"
echo "🌐 Домен: $DOMAIN"

# Проверка директории проекта
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Проект не найден в $PROJECT_DIR"
    echo "Сначала выполните полное развертывание с github-deploy.sh"
    exit 1
fi

cd $PROJECT_DIR

# Сохранение .env файла
echo "💾 Сохранение конфигурации..."
cp .env .env.backup

# Получение обновлений из GitHub
echo "📥 Получение обновлений из GitHub..."
git fetch origin
BEFORE=$(git rev-parse HEAD)
git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || {
    echo "❌ Ошибка при получении обновлений"
    exit 1
}
AFTER=$(git rev-parse HEAD)

# Проверка наличия изменений
if [ "$BEFORE" = "$AFTER" ]; then
    echo "✅ Обновлений нет. Текущая версия актуальна."
    exit 0
fi

echo "📊 Изменения:"
git log --oneline $BEFORE..$AFTER

# Восстановление .env файла
echo "🔧 Восстановление конфигурации..."
mv .env.backup .env

# Перезапуск сервисов
echo "🔄 Перезапуск сервисов..."
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Проверка статуса
echo "⏳ Ожидание запуска сервисов..."
sleep 10

echo "📊 Статус сервисов:"
docker-compose ps

# Проверка здоровья приложения
echo "🏥 Проверка работоспособности..."
if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Приложение работает корректно"
else
    echo "⚠️ Проблемы с работоспособностью приложения"
    echo "Проверьте логи: docker-compose logs"
fi

echo ""
echo "🎉 Обновление завершено!"
echo "🌐 Бот доступен: https://$DOMAIN"
echo ""
echo "📋 Полезные команды:"
echo "   docker-compose logs -f web    # Логи основного приложения"
echo "   docker-compose logs -f worker # Логи фоновых задач"
echo "   docker-compose ps             # Статус сервисов"
echo ""
