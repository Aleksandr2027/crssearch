#!/usr/bin/env python3
"""
Простая проверка Telegram токена
"""
import asyncio
import os
import sys
from telegram import Bot
from telegram.error import InvalidToken, NetworkError

async def test_token():
    """Тестируем токен Telegram"""
    
    # Загружаем переменные окружения
    from dotenv import load_dotenv
    load_dotenv()
    
    token = os.getenv('TELEGRAM_TOKEN')
    
    if not token:
        print("❌ TELEGRAM_TOKEN не найден в переменных окружения")
        return False
        
    if token.count(':') != 1:
        print("❌ Неверный формат токена. Должен быть: БОТИД:ТОКЕН")
        return False
        
    print(f"🔍 Тестируем токен: {token[:10]}...{token[-10:]}")
    
    try:
        bot = Bot(token=token)
        me = await bot.get_me()
        print(f"✅ Токен работает!")
        print(f"   Имя бота: {me.first_name}")
        print(f"   Username: @{me.username}")
        print(f"   ID: {me.id}")
        return True
        
    except InvalidToken:
        print("❌ Недействительный токен")
        return False
        
    except NetworkError as e:
        print(f"❌ Ошибка сети: {e}")
        print("💡 Возможно, нужен прокси для доступа к Telegram API")
        return False
        
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_token())
    sys.exit(0 if result else 1) 