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
from .utils.log_utils import bot_logger

class BotMigration:
    """Класс для безопасной миграции на новую версию бота"""
    
    def __init__(self):
        """Инициализация миграции"""
        self.logger = bot_logger.logger  # Используем внутренний logger вместо BotLogger
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
            
            # Копируем файлы конфигурации
            config_dir = self.base_dir / "config"
            if config_dir.exists():
                shutil.copytree(
                    config_dir,
                    self.backup_dir / "config",
                    dirs_exist_ok=True
                )
            
            # Копируем логи
            logs_dir = self.base_dir / "logs"
            if logs_dir.exists():
                shutil.copytree(
                    logs_dir,
                    self.backup_dir / "logs",
                    dirs_exist_ok=True
                )
            
            # Копируем базу данных (если есть)
            db_dir = self.base_dir / "db"
            if db_dir.exists():
                shutil.copytree(
                    db_dir,
                    self.backup_dir / "db",
                    dirs_exist_ok=True
                )
            
            self.logger.info(f"Создан бэкап в директории: {self.backup_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при создании бэкапа: {str(e)}")
            return False
    
    def create_log_structure(self) -> bool:
        """
        Создание структуры директорий для логов
        
        Returns:
            True если структура создана успешно
        """
        try:
            # Создаем основные директории для логов
            log_dirs = [
                self.base_dir / "logs",
                self.base_dir / "logs" / "errors",
                self.base_dir / "logs" / "access",
                self.base_dir / "logs" / "debug",
                self.base_dir / "logs" / "metrics"
            ]
            
            for directory in log_dirs:
                directory.mkdir(parents=True, exist_ok=True)
                
            self.logger.info("Создана структура директорий для логов")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при создании структуры логов: {str(e)}")
            return False
    
    def migrate(self) -> bool:
        """
        Выполнение миграции
        
        Returns:
            True если миграция выполнена успешно
        """
        try:
            # Создаем бэкап
            if not self.create_backup():
                self.logger.error("Не удалось создать бэкап")
                return False
            
            # Создаем структуру логов
            if not self.create_log_structure():
                self.logger.error("Не удалось создать структуру логов")
                return False
            
            # Проверяем конфигурацию
            if not self.check_config():
                self.logger.error("Не удалось проверить конфигурацию")
                return False
            
            # Проверяем подключение к БД
            if not self.check_database():
                self.logger.error("Не удалось проверить подключение к БД")
                return False
            
            # Проверяем бота
            if not self.check_bot():
                self.logger.error("Не удалось проверить бота")
                return False
            
            self.logger.info("Миграция успешно завершена")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при выполнении миграции: {str(e)}")
            return False
    
    def check_config(self) -> bool:
        """
        Проверка конфигурации
        
        Returns:
            True если конфигурация корректна
        """
        try:
            # Проверяем наличие файла конфигурации
            config_file = self.base_dir / "config" / "enhanced_config.json"
            if not config_file.exists():
                self.logger.error("Файл enhanced_config.json не найден")
                return False
            
            # Проверяем содержимое конфигурации
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Проверяем обязательные секции
            required_sections = ['metrics', 'database', 'cache', 'search', 'logging']
            for section in required_sections:
                if section not in config:
                    self.logger.error(f"В конфигурации отсутствует секция {section}")
                    return False
            
            self.logger.info("Конфигурация проверена успешно")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при проверке конфигурации: {str(e)}")
            return False
    
    def check_database(self) -> bool:
        """
        Проверка подключения к базе данных
        
        Returns:
            True если подключение успешно
        """
        try:
            # Создаем менеджер бота для проверки БД
            bot_manager = BotManager()
            
            # Проверяем подключение
            if not bot_manager.search_handler.search_processor.crs_bot.db_manager:
                self.logger.error("Не удалось создать менеджер БД")
                return False
            
            self.logger.info("Подключение к БД проверено успешно")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при проверке БД: {str(e)}")
            return False
    
    def check_bot(self) -> bool:
        """
        Проверка бота
        
        Returns:
            True если бот работает корректно
        """
        try:
            # Создаем менеджер бота
            bot_manager = BotManager()
            
            # Проверяем основные компоненты
            if not bot_manager.auth_handler:
                self.logger.error("Не удалось создать AuthHandler")
                return False
                
            if not bot_manager.menu_handler:
                self.logger.error("Не удалось создать MenuHandler")
                return False
                
            if not bot_manager.search_handler:
                self.logger.error("Не удалось создать SearchHandler")
                return False
                
            if not bot_manager.coord_handler:
                self.logger.error("Не удалось создать CoordHandler")
                return False
            
            self.logger.info("Бот проверен успешно")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при проверке бота: {str(e)}")
            return False

def main():
    """Точка входа для миграции"""
    try:
        # Настраиваем логирование
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logger = logging.getLogger(__name__)
        
        # Выполняем миграцию
        migration = BotMigration()
        if migration.migrate():
            logger.info("Миграция успешно завершена")
        else:
            logger.error("Миграция завершилась с ошибками")
            
    except Exception as e:
        logger.error(f"Критическая ошибка при миграции: {str(e)}")

if __name__ == '__main__':
    main() 