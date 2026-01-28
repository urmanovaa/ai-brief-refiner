#!/usr/bin/env python3
"""
Скрипт для чистого перезапуска бота.
Удаляет webhook и все pending updates перед запуском.
"""

import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def clean_restart():
    """Очистка и перезапуск"""
    
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не установлен!")
        return False
    
    base_url = f"https://api.telegram.org/bot{BOT_TOKEN}"
    
    async with aiohttp.ClientSession() as session:
        # 1. Удаляем webhook
        print("🔄 Удаляю webhook...")
        async with session.post(f"{base_url}/deleteWebhook", json={"drop_pending_updates": True}) as resp:
            result = await resp.json()
            if result.get("ok"):
                print("✅ Webhook удалён, pending updates очищены")
            else:
                print(f"⚠️ Ответ: {result}")
        
        # 2. Проверяем статус
        print("🔍 Проверяю статус бота...")
        async with session.get(f"{base_url}/getMe") as resp:
            result = await resp.json()
            if result.get("ok"):
                bot_info = result["result"]
                print(f"✅ Бот: @{bot_info.get('username')} (ID: {bot_info.get('id')})")
            else:
                print(f"❌ Ошибка: {result}")
                return False
        
        # 3. Закрываем все сессии
        print("🔄 Закрываю активные соединения...")
        async with session.post(f"{base_url}/close") as resp:
            result = await resp.json()
            print(f"   close: {result}")
        
        # 4. Логаут (опционально, если долго не помогает)
        # print("🔄 Logout...")
        # async with session.post(f"{base_url}/logOut") as resp:
        #     result = await resp.json()
        #     print(f"   logOut: {result}")
    
    print("\n✅ Готово! Теперь можно запускать main.py")
    return True


if __name__ == "__main__":
    asyncio.run(clean_restart())

