"""
Основной модуль приложения
"""

import os
import sys
import logging
from XML_search.bot.bot_manager import BotManager
from XML_search.bot.config import BotConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

if __name__ == "__main__":
    # Для Windows обязательно устанавливаем правильную политику event loop
    if sys.platform.startswith('win'):
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    try:
        config = BotConfig()
        config_path = os.getenv("XML_SEARCH_CONFIG", "XML_search/config/db_config.json")
        manager = BotManager(token=config.BOT_TOKEN, config_path=config_path)
        # Корректный запуск для PTB v20+ (run_polling сам управляет event loop)
        manager.run()
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем (Ctrl+C)") 