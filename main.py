"""
Entry point for the household expenses bot
"""
import os
import logging
from bot import main

# Настройка логирования для продакшена
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

if __name__ == "__main__":
    # Получаем порт из переменных окружения (для Railway)
    PORT = int(os.environ.get('PORT', 8080))
    print(f"🚀 Запуск бота на порту {PORT}")
    main()
