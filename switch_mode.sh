#!/bin/bash

# Скрипт для переключения между локальным и продакшен режимами
echo "🔄 Переключение режимов бота"

# Проверяем, что мы в правильной директории
if [ ! -f "main.py" ]; then
    echo "❌ Ошибка: main.py не найден. Убедитесь, что вы в корневой папке проекта."
    exit 1
fi

echo "Выберите режим:"
echo "1) 🧪 Локальное тестирование (с тестовым ботом)"
echo "2) 🚀 Продакшен (деплой на Railway)"
echo "3) 📊 Статус (проверить что запущено)"
echo "4) 🛑 Остановить локальный бот"
echo "5) 🤖 Создать тестовый бот"
echo ""
read -p "Введите номер (1-5): " choice

case $choice in
    1)
        echo "🧪 Переключаемся на локальное тестирование..."
        echo "⚠️  Останавливаем все локальные процессы бота..."
        pkill -f "python main.py" 2>/dev/null
        
        echo "🚀 Запускаем локальный бот с тестовым токеном..."
        ./test_local.sh
        ;;
    2)
        echo "🚀 Переключаемся на продакшен..."
        echo "⚠️  Останавливаем локальный бот..."
        pkill -f "python main.py" 2>/dev/null
        
        echo "📤 Деплоим на Railway..."
        ./deploy.sh
        ;;
    3)
        echo "📊 Проверяем статус..."
        local_processes=$(ps aux | grep "python main.py" | grep -v grep | wc -l)
        if [ $local_processes -gt 0 ]; then
            echo "✅ Локальный бот запущен ($local_processes процессов)"
        else
            echo "❌ Локальный бот не запущен"
        fi
        
        echo "🔍 Проверьте Railway Dashboard для статуса продакшен бота"
        echo "🌐 https://railway.app/dashboard"
        ;;
    4)
        echo "🛑 Останавливаем локальный бот..."
        pkill -f "python main.py" 2>/dev/null
        echo "✅ Локальный бот остановлен"
        echo "💡 Продакшен бот на Railway продолжает работать"
        ;;
    5)
        echo "🤖 Создание тестового бота..."
        ./create_test_bot.sh
        ;;
    *)
        echo "❌ Неверный выбор. Введите число от 1 до 5."
        exit 1
        ;;
esac
