#!/bin/bash

# Скрипт для остановки Railway бота
echo "🛑 Остановка Railway бота"

# Проверяем, что мы в правильной директории
if [ ! -f "main.py" ]; then
    echo "❌ Ошибка: main.py не найден. Убедитесь, что вы в корневой папке проекта."
    exit 1
fi

echo "⚠️  ВНИМАНИЕ: Для остановки Railway бота нужно:"
echo "1. Зайти в Railway Dashboard: https://railway.app/dashboard"
echo "2. Найти ваш проект telegram-expenses-bot"
echo "3. Нажать на сервис бота"
echo "4. Нажать кнопку 'Stop' или переключить тумблер"
echo ""
echo "💡 Альтернативно, можете использовать Railway CLI:"
echo "railway service stop"
echo ""

read -p "Нажмите Enter после остановки Railway бота..."

echo "✅ Railway бот остановлен"
echo "🚀 Теперь можете запустить локальный бот:"
echo "./test_local.sh"
