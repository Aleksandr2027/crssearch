"""
Основной модуль приложения
"""

import os
import sys
import signal
import logging
import asyncio
from XML_search.bot.bot_manager import BotManager
from XML_search.bot.config import BotConfig
from typing import Optional

# Настройка лаконичного логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

# Отключаем избыточные логи от сторонних библиотек
logging.getLogger('telegram').setLevel(logging.WARNING)
logging.getLogger('telegram.ext').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

# Отключаем PTB предупреждения
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="telegram")

# Глобальная переменная для менеджера бота
bot_manager_instance: Optional[BotManager] = None

async def main_logic():
    """Основная асинхронная логика запуска и остановки бота."""
    global bot_manager_instance
    loop = asyncio.get_event_loop()

    config = BotConfig()
    config_path = os.getenv("XML_SEARCH_CONFIG", "XML_search/config/db_config.json")
    
    # Инициализируем bot_manager_instance здесь
    bot_manager_instance = BotManager(token=config.BOT_TOKEN, config_path=config_path)

    try:
        logging.info("🚀 Асинхронный запуск бота...")
        # Запускаем бота через его собственный асинхронный метод управления жизненным циклом
        await bot_manager_instance.run_bot_async_lifecycle()
        
    except (KeyboardInterrupt, SystemExit):
        logging.info("Получен сигнал KeyboardInterrupt/SystemExit в main_logic.")
    except Exception as e:
        logging.critical(f"Критическая ошибка в main_logic: {e}", exc_info=True)
    finally:
        logging.info("Блок finally в main_logic: начинаю остановку бота...")
        if bot_manager_instance:
            # Убедимся, что stop вызывается, даже если run_in_executor не завершился нормально
            # или если была отмена.
            if hasattr(bot_manager_instance, 'application') and hasattr(bot_manager_instance.application, 'running') and bot_manager_instance.application.running:
                 logging.info("Приложение Telegram все еще работает. Вызов await bot_manager_instance.stop()...")
            elif not (hasattr(bot_manager_instance, 'application') and hasattr(bot_manager_instance.application, 'running')):
                 logging.info("Экземпляр приложения или его статус 'running' не найден, но bot_manager существует. Вызов await bot_manager_instance.stop() для очистки.")
            else:
                 logging.info("Приложение Telegram не запущено, но bot_manager существует. Вызов await bot_manager_instance.stop() для очистки.")

            await bot_manager_instance.stop()
            logging.info("bot_manager_instance.stop() завершен.")
        else:
            logging.warning("Экземпляр bot_manager_instance не был инициализирован к моменту finally.")
        logging.info("Блок finally в main_logic завершен.")

if __name__ == "__main__":
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main_logic())
    except KeyboardInterrupt:
        # Этот блок обычно не достигается, если asyncio.run() обрабатывает SIGINT
        # и вызывает CancelledError в main_logic.
        # Оставляем как дополнительную страховку.
        logging.info("KeyboardInterrupt (Ctrl+C) пойман в __main__. "
                     "Остановка должна была быть обработана в блоке finally функции main_logic.")
    except Exception as e: 
        logging.critical(f"Критическая ошибка на уровне asyncio.run: {e}", exc_info=True)
    finally:
        logging.info("Программа завершена.") 