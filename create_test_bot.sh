#!/bin/bash

# Скрипт для создания тестового бота
echo "🤖 Создание тестового бота для локальной разработки"

echo "📋 Инструкция по созданию тестового бота:"
echo ""
echo "1. Откройте Telegram и найдите @BotFather"
echo "2. Отправьте команду: /newbot"
echo "3. Введите имя бота: Expenses Bot Test"
echo "4. Введите username: your_test_bot_username_bot"
echo "5. Скопируйте полученный токен"
echo ""

read -p "Вставьте токен тестового бота: " test_token

if [ -z "$test_token" ]; then
    echo "❌ Токен не введен"
    exit 1
fi

# Создаем .env.test файл
echo "BOT_TOKEN=$test_token" > .env.test

echo "✅ Тестовый токен сохранен в .env.test"
echo ""
echo "🚀 Теперь можете запустить локальное тестирование:"
echo "./test_local.sh"
echo ""
echo "💡 Преимущества тестового бота:"
echo "   - Нет конфликтов с продакшен ботом"
echo "   - Отдельная база данных"
echo "   - Безопасное тестирование"
