#!/bin/bash

# Полный скрипт развертывания AI Analytics Bot из GitHub
# Используйте этот скрипт для первого развертывания на новом сервере

set -e

# Параметры
GITHUB_REPO=${1:-""}
DOMAIN=${2:-"yourdomain.kz"}
PROJECT_DIR="/opt/ai-analytics-bot"

if [ -z "$GITHUB_REPO" ]; then
    echo "❌ Не указан GitHub репозиторий"
    echo "Использование: $0 <github-repo-url> [domain]"
    echo "Пример: $0 https://github.com/username/ai-analytics-bot.git bot.mycompany.kz"
    exit 1
fi

echo "🚀 Развертывание AI Analytics Bot из GitHub"
echo "📦 Репозиторий: $GITHUB_REPO"
echo "🌐 Домен: $DOMAIN"
echo ""

# Проверка что скрипт запускается с правами sudo
if [ "$EUID" -eq 0 ]; then
    echo "❌ Не запускайте этот скрипт от root"
    echo "Запустите от обычного пользователя с sudo правами"
    exit 1
fi

# Обновление системы
echo "📦 Обновление системы..."
sudo apt update && sudo apt upgrade -y

# Установка необходимых пакетов
echo "📦 Установка необходимых пакетов..."
sudo apt install -y curl wget gnupg lsb-release apt-transport-https ca-certificates software-properties-common git ufw

# Установка Docker
echo "🐳 Установка Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io
    sudo usermod -aG docker $USER
    echo "✅ Docker установлен"
else
    echo "✅ Docker уже установлен"
fi

# Установка Docker Compose
echo "🐙 Установка Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep -Po '"tag_name": "\K.*?(?=")')
    sudo curl -L "https://github.com/docker/compose/releases/download/$DOCKER_COMPOSE_VERSION/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    echo "✅ Docker Compose установлен"
else
    echo "✅ Docker Compose уже установлен"
fi

# Установка Nginx
echo "🌐 Установка Nginx..."
if ! command -v nginx &> /dev/null; then
    sudo apt install -y nginx
    echo "✅ Nginx установлен"
else
    echo "✅ Nginx уже установлен"
fi

# Установка Certbot
echo "🔒 Установка Certbot..."
if ! command -v certbot &> /dev/null; then
    sudo apt install -y certbot python3-certbot-nginx
    echo "✅ Certbot установлен"
else
    echo "✅ Certbot уже установлен"
fi

# Настройка файрвола
echo "🔥 Настройка UFW..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# Клонирование репозитория
echo "📥 Клонирование репозитория..."
if [ -d "$PROJECT_DIR" ]; then
    echo "⚠️ Директория $PROJECT_DIR уже существует"
    read -p "Удалить и клонировать заново? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo rm -rf $PROJECT_DIR
    else
        echo "❌ Прервано пользователем"
        exit 1
    fi
fi

sudo git clone $GITHUB_REPO $PROJECT_DIR
sudo chown -R $USER:$USER $PROJECT_DIR
cd $PROJECT_DIR

# Создание .env файла
echo "⚙️ Создание .env файла..."
if [ ! -f ".env" ]; then
    if [ -f "env.template" ]; then
        cp env.template .env
        echo "✅ Создан .env файл из шаблона"
    else
        echo "❌ Шаблон env.template не найден"
        echo "Создайте .env файл вручную"
        exit 1
    fi
else
    echo "✅ Файл .env уже существует"
fi

# Установка исполняемых прав на скрипты
chmod +x deploy/*.sh

echo ""
echo "🎉 Базовая установка завершена!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Настройте .env файл:"
echo "   nano .env"
echo ""
echo "2. Обязательно заполните:"
echo "   - TELEGRAM_TOKEN (получить у @BotFather)"
echo "   - OPENAI_API_KEY (получить на https://platform.openai.com)"
echo "   - BASE_URL=https://$DOMAIN"
echo ""
echo "3. Запустите развертывание:"
echo "   ./deploy/deploy.sh $DOMAIN"
echo ""
echo "⚠️ ВАЖНО для Казахстана:"
echo "   Проверьте доступность OpenAI API: curl -s https://api.openai.com/v1/models"
echo "   Если недоступен, используйте VPN или прокси (см. ./deploy/proxy-setup.sh)"
echo ""
