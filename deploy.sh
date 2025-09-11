
#!/bin/bash

# Скрипт для быстрого деплоя на Railway
echo "🚀 Быстрый деплой на Railway"

# Проверяем, что мы в правильной директории
if [ ! -f "main.py" ]; then
    echo "❌ Ошибка: main.py не найден. Убедитесь, что вы в корневой папке проекта."
    exit 1
fi

# Проверяем статус Git
if [ -z "$(git status --porcelain)" ]; then
    echo "✅ Нет изменений для коммита"
else
    echo "📝 Обнаружены изменения, коммитим..."
    
    # Добавляем все изменения
    git add .
    
    # Запрашиваем сообщение коммита
    echo "💬 Введите сообщение коммита:"
    read commit_message
    
    # Если сообщение пустое, используем стандартное
    if [ -z "$commit_message" ]; then
        commit_message="Обновление бота $(date '+%Y-%m-%d %H:%M')"
    fi
    
    # Коммитим изменения
    git commit -m "$commit_message"
    echo "✅ Изменения закоммичены: $commit_message"
fi

# Переключаемся на main ветку
echo "🔄 Переключаемся на main ветку..."
git checkout main

# Получаем последние изменения
echo "📥 Получаем последние изменения..."
git pull origin main

# Если были изменения в develop, мержим их
if git show-ref --verify --quiet refs/remotes/origin/develop; then
    echo "🔄 Мержим изменения из develop..."
    git merge origin/develop
fi

# Пушим изменения
echo "📤 Пушим изменения на GitHub..."
git push origin main

echo "✅ Деплой завершен! Railway автоматически обновит бота."
echo "⏳ Подождите 1-2 минуты, пока Railway перезапустит бота."
echo "🔍 Проверить статус можно в Railway Dashboard"
