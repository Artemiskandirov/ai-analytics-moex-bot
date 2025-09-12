#!/bin/bash

# Скрипт настройки прокси для доступа к OpenAI API из Казахстана
# Используйте этот скрипт если OpenAI API заблокирован в вашем регионе

set -e

echo "🔄 Настройка прокси для OpenAI API..."

# Проверка доступности OpenAI API
echo "🌐 Проверка доступности OpenAI API..."
if curl -s --connect-timeout 5 https://api.openai.com/v1/models > /dev/null; then
    echo "✅ OpenAI API доступен напрямую"
    echo "Прокси не требуется"
    exit 0
else
    echo "❌ OpenAI API недоступен. Требуется настройка прокси."
fi

echo ""
echo "🔧 Варианты решения проблемы с доступом к OpenAI API:"
echo ""
echo "1. 🌍 VPN-сервер (рекомендуется)"
echo "   - Установите VPN (WireGuard, OpenVPN) на сервер"
echo "   - Используйте сервер в США/Европе как точку выхода"
echo ""
echo "2. 🔄 HTTP/SOCKS прокси"
echo "   - Купите приватный прокси в разрешенной стране"
echo "   - Настройте переменные окружения:"
echo "     export HTTPS_PROXY=socks5://proxy-server:port"
echo "     export HTTP_PROXY=http://proxy-server:port"
echo ""
echo "3. 🚪 Прокси-сервер с OpenAI API"
echo "   - Разверните прокси-сервер в разрешенной стране"
echo "   - Измените OPENAI_BASE_URL в .env файле"
echo ""
echo "4. 🤖 Альтернативные API"
echo "   - Используйте совместимые с OpenAI API сервисы:"
echo "   - OpenRouter (openrouter.ai)"
echo "   - Together AI (together.ai)"
echo "   - Groq (groq.com)"
echo ""

# Создание конфига для прокси через Docker
cat > docker-compose.proxy.yml <<EOF
version: "3.9"
services:
  web:
    build: .
    env_file: .env
    restart: always
    networks: [appnet]
    environment:
      - HTTPS_PROXY=\${PROXY_URL}
      - HTTP_PROXY=\${PROXY_URL}
  worker:
    build: .
    env_file: .env
    command: ["python","-m","app.worker"]
    restart: always
    networks: [appnet]
    environment:
      - HTTPS_PROXY=\${PROXY_URL}
      - HTTP_PROXY=\${PROXY_URL}
  nginx:
    image: nginx:stable
    volumes:
      - ./ops/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    ports: ["80:80","443:443"]
    depends_on: [web]
    restart: always
    networks: [appnet]
networks:
  appnet:
EOF

echo "📝 Создан docker-compose.proxy.yml для использования с прокси"
echo ""
echo "Для использования прокси:"
echo "1. Добавьте в .env: PROXY_URL=socks5://your-proxy:port"
echo "2. Запустите: docker-compose -f docker-compose.proxy.yml up -d"
echo ""
echo "🔗 Полезные ссылки:"
echo "   - Настройка WireGuard: https://www.wireguard.com/quickstart/"
echo "   - OpenRouter API: https://openrouter.ai/docs"
echo "   - Together AI: https://docs.together.ai/docs"
