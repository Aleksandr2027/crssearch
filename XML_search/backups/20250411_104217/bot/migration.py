"""
Скрипт для безопасной миграции на новую версию бота
"""

import os
import shutil
from pathlib import Path
import json
from datetime import datetime
import logging
from typing import Dict, Any, List
import asyncio
from .bot_manager import BotManager
from .utils.log_utils import bot_logger, log_debug, log_error

class BotMigration:
    """Класс для безопасной миграции на новую версию бота"""
    
    def __init__(self):
        self.logger = bot_logger
        self.base_dir = Path(__file__).resolve().parent.parent
        self.backup_dir = self.base_dir / "backups" / datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def create_backup(self) -> bool:
        """
        Создание резервной копии текущей версии
        
        Returns:
            True если бэкап создан успешно
        """
        try:
            # Создаем директорию для бэкапа
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Список файлов и директорий для бэкапа
            backup_items = [
                'bot',
                'config',
                'enhanced',
                'logs',
                'telegram_bot.py',
                'config.py',
                'requirements.txt',
                '.env'
            ]
            
            # Создаем бэкап каждого элемента
            for item in backup_items:
                src = self.base_dir / item
                dst = self.backup_dir / item
                
                if src.exists():
                    if src.is_dir():
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                        
            log_debug(
                "Создан бэкап текущей версии",
                {'backup_dir': str(self.backup_dir)}
            )
            return True
            
        except Exception as e:
            log_error(e, {'stage': 'backup_creation'})
            return False
            
    def verify_new_version(self) -> bool:
        """
        Проверка новой версии
        
        Returns:
            True если проверка прошла успешно
        """
        try:
            # Проверяем наличие всех необходимых файлов
            required_files = [
                'bot/bot_manager.py',
                'bot/handlers/base_handler.py',
                'bot/handlers/auth_handler.py',
                'bot/utils/log_utils.py',
                'bot/config.py'
            ]
            
            for file in required_files:
                if not (self.base_dir / file).exists():
                    raise FileNotFoundError(f"Отсутствует файл: {file}")
                    
            # Проверяем возможность импорта основных компонентов
            from .bot_manager import BotManager
            from .handlers.base_handler import BaseHandler
            from .utils.log_utils import bot_logger
            
            # Проверяем структуру логов
            log_dirs = ['logs', 'logs/errors', 'logs/access', 'logs/debug', 'logs/metrics']
            for dir in log_dirs:
                (self.base_dir / dir).mkdir(parents=True, exist_ok=True)
                
            log_debug("Проверка новой версии успешна")
            return True
            
        except Exception as e:
            log_error(e, {'stage': 'version_verification'})
            return False
            
    async def test_new_version(self) -> bool:
        """
        Тестирование новой версии
        
        Returns:
            True если тесты прошли успешно
        """
        try:
            # Создаем и инициализируем бота
            bot = BotManager()
            if not await bot.initialize():
                raise RuntimeError("Ошибка инициализации бота")
                
            # Проверяем работу логирования
            log_debug("Тестовое сообщение")
            
            # Останавливаем бота
            await bot.shutdown()
            
            log_debug("Тестирование новой версии успешно")
            return True
            
        except Exception as e:
            log_error(e, {'stage': 'version_testing'})
            return False
            
    def cleanup_old_version(self) -> bool:
        """
        Очистка файлов старой версии
        
        Returns:
            True если очистка прошла успешно
        """
        try:
            # Список файлов для удаления
            files_to_remove = [
                'telegram_bot.py'
            ]
            
            # Удаляем файлы
            for file in files_to_remove:
                path = self.base_dir / file
                if path.exists():
                    path.unlink()
                    
            log_debug(
                "Очистка старой версии успешна",
                {'removed_files': files_to_remove}
            )
            return True
            
        except Exception as e:
            log_error(e, {'stage': 'old_version_cleanup'})
            return False
            
    def restore_backup(self) -> bool:
        """
        Восстановление из бэкапа
        
        Returns:
            True если восстановление успешно
        """
        try:
            if not self.backup_dir.exists():
                raise FileNotFoundError("Бэкап не найден")
                
            # Восстанавливаем каждый элемент
            for item in self.backup_dir.iterdir():
                dst = self.base_dir / item.name
                if dst.exists():
                    if dst.is_dir():
                        shutil.rmtree(dst)
                    else:
                        dst.unlink()
                        
                if item.is_dir():
                    shutil.copytree(item, dst)
                else:
                    shutil.copy2(item, dst)
                    
            log_debug(
                "Восстановление из бэкапа успешно",
                {'backup_dir': str(self.backup_dir)}
            )
            return True
            
        except Exception as e:
            log_error(e, {'stage': 'backup_restoration'})
            return False
            
    async def migrate(self) -> bool:
        """
        Выполнение миграции
        
        Returns:
            True если миграция успешна
        """
        try:
            # Шаг 1: Создание бэкапа
            log_debug("Начало миграции: создание бэкапа")
            if not self.create_backup():
                raise RuntimeError("Ошибка создания бэкапа")
                
            # Шаг 2: Проверка новой версии
            log_debug("Проверка новой версии")
            if not self.verify_new_version():
                raise RuntimeError("Ошибка проверки новой версии")
                
            # Шаг 3: Тестирование
            log_debug("Тестирование новой версии")
            if not await self.test_new_version():
                raise RuntimeError("Ошибка тестирования новой версии")
                
            # Шаг 4: Очистка старой версии
            log_debug("Очистка старой версии")
            if not self.cleanup_old_version():
                raise RuntimeError("Ошибка очистки старой версии")
                
            log_debug("Миграция успешно завершена")
            return True
            
        except Exception as e:
            log_error(e, {'stage': 'migration'})
            # Пытаемся восстановить из бэкапа
            log_debug("Попытка восстановления из бэкапа")
            if not self.restore_backup():
                log_error(
                    Exception("Ошибка восстановления из бэкапа"),
                    {'stage': 'backup_restoration'}
                )
            return False

async def main():
    """Точка входа для миграции"""
    migration = BotMigration()
    if await migration.migrate():
        print("✅ Миграция успешно завершена")
    else:
        print("❌ Ошибка при миграции, проверьте логи")

if __name__ == '__main__':
    asyncio.run(main()) 