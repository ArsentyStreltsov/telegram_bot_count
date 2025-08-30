#!/bin/bash

# Скрипт для локального тестирования бота
echo "🧪 Локальное тестирование бота"

# Проверяем, что мы в правильной директории
if [ ! -f "main.py" ]; then
    echo "❌ Ошибка: main.py не найден. Убедитесь, что вы в корневой папке проекта."
    exit 1
fi

# Проверяем наличие токена
if [ -f ".env.test" ]; then
    echo "✅ Найден тестовый токен (.env.test)"
    export BOT_TOKEN=$(grep BOT_TOKEN .env.test | cut -d '=' -f2)
elif [ -f ".env" ]; then
    echo "✅ Найден основной токен (.env)"
    # Проверяем есть ли тестовый токен в .env
    if grep -q "BOT_TOKEN_TEST" .env; then
        echo "🔄 Используем тестовый токен из .env"
        export BOT_TOKEN=$(grep BOT_TOKEN_TEST .env | cut -d '=' -f2)
    else
        echo "⚠️  Используем основной токен (может быть конфликт с Railway)"
        echo "💡 Рекомендуется создать тестовый бот (см. setup_test_bot.md)"
        export BOT_TOKEN=$(grep BOT_TOKEN .env | cut -d '=' -f2)
    fi
else
    echo "❌ Ошибка: .env или .env.test файл не найден."
    echo "📝 Создайте .env файл с BOT_TOKEN=ваш_токен"
    echo "💡 Или создайте .env.test с тестовым токеном"
    echo "📖 См. setup_test_bot.md для инструкций"
    exit 1
fi

# Проверяем зависимости
echo "📦 Проверяем зависимости..."
if ! python -c "import telegram" 2>/dev/null; then
    echo "⚠️  Устанавливаем зависимости..."
    pip install -r requirements.txt
fi

# Останавливаем предыдущий процесс бота, если он запущен
echo "🛑 Останавливаем предыдущий процесс бота..."
pkill -f "python main.py" 2>/dev/null

# Проверяем, не запущен ли бот на Railway
echo "🔍 Проверяем статус продакшен бота..."
echo "⚠️  ВНИМАНИЕ: Если бот запущен на Railway, могут быть конфликты!"
echo "💡 Для полного тестирования рекомендуется остановить бота на Railway"
echo ""

# Запускаем бота
echo "🚀 Запускаем бота локально..."
echo "📱 Теперь можете тестировать бота в Telegram"
echo "🛑 Для остановки нажмите Ctrl+C"
echo ""

python main.py
