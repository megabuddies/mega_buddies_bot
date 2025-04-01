#!/usr/bin/env python3
"""
Утилита для проверки загрузки переменных окружения.
Запустите этот скрипт, чтобы убедиться, что переменные окружения правильно загружаются.
"""

import os
import dotenv

# Загружаем переменные окружения
dotenv.load_dotenv()

# Получаем значения переменных
bot_token = os.getenv("BOT_TOKEN")
admin_ids_str = os.getenv("ADMIN_IDS", "")

# Проверяем токен бота
if bot_token:
    # Для безопасности показываем только первые и последние 4 символа
    masked_token = f"{bot_token[:4]}...{bot_token[-4:]}"
    print(f"✅ BOT_TOKEN загружен успешно: {masked_token}")
else:
    print("❌ BOT_TOKEN не найден в переменных окружения!")

# Проверяем ID администраторов
if admin_ids_str:
    try:
        admin_ids = [int(id.strip()) for id in admin_ids_str.split(",")]
        print(f"✅ ADMIN_IDS загружены успешно: {len(admin_ids)} администраторов")
        
        # Для безопасности показываем только часть каждого ID
        for i, admin_id in enumerate(admin_ids):
            masked_id = f"{str(admin_id)[:2]}...{str(admin_id)[-2:]}"
            print(f"  Админ #{i+1}: {masked_id}")
    except ValueError as e:
        print(f"❌ Ошибка при чтении ADMIN_IDS: {e}")
else:
    print("❌ ADMIN_IDS не найдены в переменных окружения!")

print("\nВНИМАНИЕ: Чувствительные данные маскируются для безопасности")
print("Если вы видите ошибки, проверьте формат данных в файле .env") 