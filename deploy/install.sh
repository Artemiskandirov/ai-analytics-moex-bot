#!/bin/bash

# Скрипт установки AI Analytics Bot на сервер в Казахстане
# Убедитесь, что запускаете от пользователя с sudo правами

set -e

echo "🚀 Установка AI Analytics Bot..."

# Обновление системы
echo "📦 Обновление системы..."
sudo apt update && sudo apt upgrade -y

# Установка Docker
echo "🐳 Установка Docker..."
if ! command -v docker &> /dev/null; then
    sudo apt install -y apt-transport-https ca-certificates curl gnupg lsb-release
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io
    sudo usermod -aG docker $USER
    echo "✅ Docker установлен. Перелогиньтесь для применения прав."
fi

# Установка Docker Compose
echo "🐙 Установка Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Установка Nginx для SSL
echo "🌐 Установка Nginx..."
sudo apt install -y nginx

# Установка Certbot для SSL
echo "🔒 Установка Certbot..."
sudo apt install -y certbot python3-certbot-nginx

# Настройка файрвола
echo "🔥 Настройка UFW..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# Установка Git (если не установлен)
echo "📦 Установка Git..."
sudo apt install -y git

echo "✅ Базовая установка завершена!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Клонируйте ваш репозиторий: git clone https://github.com/USERNAME/REPO.git /opt/ai-analytics-bot"
echo "2. Перейдите в директорию: cd /opt/ai-analytics-bot"
echo "3. Настройте .env файл: cp env.template .env && nano .env"
echo "4. Запустите развертывание: ./deploy/deploy.sh yourdomain.kz"
echo ""
