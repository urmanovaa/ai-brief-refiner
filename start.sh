#!/bin/bash
# Безопасный запуск AI Brief Refiner Bot
# Автоматически убивает дублирующиеся процессы перед запуском

cd "$(dirname "$0")"

echo "🔄 Останавливаю предыдущие экземпляры бота..."
pkill -f "python.*main.py" 2>/dev/null
sleep 2

# Проверяем что все процессы убиты
if pgrep -f "python.*main.py" > /dev/null; then
    echo "⚠️  Не удалось остановить все процессы. Пробую принудительно..."
    pkill -9 -f "python.*main.py" 2>/dev/null
    sleep 2
fi

# Очищаем webhook
echo "🔄 Очищаю webhook и pending updates..."
python3 -c "
import asyncio
import aiohttp
import os
from dotenv import load_dotenv
load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
async def clean():
    async with aiohttp.ClientSession() as s:
        await s.post(f'https://api.telegram.org/bot{TOKEN}/deleteWebhook', json={'drop_pending_updates': True})
asyncio.run(clean())
" 2>/dev/null

echo "🚀 Запускаю бота..."
python3 main.py

