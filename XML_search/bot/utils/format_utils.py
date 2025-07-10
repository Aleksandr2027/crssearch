"""
Утилиты для форматирования сообщений бота
"""

from typing import List, Dict, Any, Optional
from transliterate import translit
import logging
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.metrics_manager import MetricsManager
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

logger = LogManager().get_logger(__name__)
metrics = MetricsManager()

class MessageFormatter:
    """Класс для форматирования сообщений бота"""
    
    # Эмодзи для разных типов информации
    EMOJI = {
        'srid': '🔹',
        'name': '📝',
        'info': 'ℹ️',
        'reliability': '✅',
        'export': '📤',
        'error': '❌',
        'warning': '⚠️',
        'search': '🔍',
        'coordinates': '📍'
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.metrics = MetricsManager()
    
    @staticmethod
    def format_field(label: str, value: str, emoji: str = '') -> str:
        """
        Форматирование поля с поддержкой Markdown
        
        Args:
            label: Название поля
            value: Значение поля
            emoji: Эмодзи для поля
            
        Returns:
            Отформатированная строка
        """
        # Экранируем специальные символы Markdown
        value = value.replace('_', '\\_').replace('*', '\\*').replace('`', '\\`')
        return f"{emoji} *{label}:* `{value}`"
    
    @staticmethod
    def format_search_result(result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Форматирование результата поиска
        
        Args:
            result: Словарь с результатом поиска
            
        Returns:
            Словарь с отформатированным текстом и клавиатурой
        """
        # Форматируем основной текст
        text_parts = [
            MessageFormatter.format_field('SRID', str(result['srid']), MessageFormatter.EMOJI['srid']),
            MessageFormatter.format_field('Название', result['name'], MessageFormatter.EMOJI['name'])
        ]
        
        # Добавляем описание если есть
        if result.get('info'):
            text_parts.append(
                MessageFormatter.format_field('Описание', result['info'], MessageFormatter.EMOJI['info'])
            )
        
        # Определяем достоверность
        reliability = (
            "EPSG" if str(result['srid']).startswith('326')
            else "Уточнить у Администратора" if result.get('reliability') is None
            else result['reliability']
        )
        text_parts.append(
            MessageFormatter.format_field('Достоверность', reliability, MessageFormatter.EMOJI['reliability'])
        )
        
        # Добавляем форматы экспорта
        text_parts.append(
            MessageFormatter.format_field('Экспорт', 'xml_Civil3D, prj_GMv20, prj_GMv25', MessageFormatter.EMOJI['export'])
        )
        
        # Создаем клавиатуру с кнопками экспорта
        keyboard = [
            [
                InlineKeyboardButton("xml_Civil3D", callback_data=f"export_xml:{result['srid']}"),
                InlineKeyboardButton("prj_GMv20", callback_data=f"export_gmv20:{result['srid']}"),
                InlineKeyboardButton("prj_GMv25", callback_data=f"export_gmv25:{result['srid']}")
            ]
        ]
        
        return {
            'text': '\n'.join(text_parts),
            'keyboard': InlineKeyboardMarkup(keyboard)
        }
    
    @staticmethod
    def format_coordinates(lat: float, lon: float) -> str:
        """
        Форматирование координат
        
        Args:
            lat: Широта
            lon: Долгота
            
        Returns:
            Отформатированная строка с координатами
        """
        return f"{MessageFormatter.EMOJI['coordinates']} *Координаты:* `E: {round(lon, 3)}, N: {round(lat, 3)}`"
    
    @staticmethod
    def format_error(message: str) -> str:
        """
        Форматирование сообщения об ошибке
        
        Args:
            message: Текст ошибки
            
        Returns:
            Отформатированное сообщение об ошибке
        """
        return f"{MessageFormatter.EMOJI['error']} {message}"
    
    @staticmethod
    def format_warning(message: str) -> str:
        """
        Форматирование предупреждения
        
        Args:
            message: Текст предупреждения
            
        Returns:
            Отформатированное предупреждение
        """
        return f"{MessageFormatter.EMOJI['warning']} {message}"
    
    @staticmethod
    def format_too_many_results(count: int) -> str:
        """
        Форматирование сообщения о большом количестве результатов
        
        Args:
            count: Количество найденных результатов
            
        Returns:
            Отформатированное сообщение
        """
        return (
            f"{MessageFormatter.EMOJI['search']} Найдено {count} систем координат.\n\n"
            f"{MessageFormatter.EMOJI['warning']} Слишком много результатов для отображения.\n"
            "Попробуйте уточнить запрос, например:\n"
            "- Добавьте регион (например, 'мск москва')\n"
            "- Укажите зону (например, 'мск зона 1')\n"
            "- Используйте более точное название"
        )
    
    @staticmethod
    def format_export_message(srid: int, format_type: str) -> str:
        """
        Форматирование сообщения об экспорте
        
        Args:
            srid: SRID системы координат
            format_type: Тип формата экспорта
            
        Returns:
            Отформатированное сообщение
        """
        return f"{MessageFormatter.EMOJI['export']} Функционал экспорта в формат {format_type} для SRID {srid} находится в разработке"

def transliterate_text(text: str, direction: str = 'ru') -> str:
    """
    Транслитерация текста между кириллицей и латиницей
    
    Args:
        text: Исходный текст
        direction: Направление транслитерации ('ru' - в латиницу, 'en' - в кириллицу)
        
    Returns:
        Транслитерированный текст
    """
    try:
        if direction == 'ru':  # кириллица -> латиница
            return translit(text, 'ru', reversed=True)
        else:  # латиница -> кириллица
            return translit(text, 'ru')
    except Exception as e:
        logger.warning(f"Ошибка при транслитерации: {e}")
        return text

def format_search_instructions() -> str:
    """
    Форматирование инструкций по поиску
    
    Returns:
        Отформатированный текст инструкций
    """
    return (
        "🔍 Как пользоваться поиском:\n\n"
        "1. Поиск по SRID:\n"
        "   - Отправьте номер системы координат\n"
        "   - Пример: 100000\n\n"
        "2. Поиск по названию:\n"
        "   - Отправьте часть названия\n"
        "   - Пример: MSK01z1\n\n"
        "3. Поиск по описанию:\n"
        "   - Отправьте часть описания\n"
        "   - Пример: Московская, Moskovskaya\n\n"
        "Результаты будут отсортированы по релевантности:\n"
        "- Сначала точные совпадения\n"
        "- Затем частичные совпадения"
    )

def format_coord_instructions() -> str:
    """
    Форматирование инструкций по вводу координат
    
    Returns:
        Отформатированный текст инструкций
    """
    return (
        "📍 Введите координаты в формате 'latitude;longitude' или 'latitude$longitude' или 'latitude%longitude'\n\n"
        "Поддерживаемые форматы ввода:\n"
        "1. Десятичные градусы: 55.7558;37.6173 или 55.7558$37.6173 или 55.7558%37.6173\n"
        "2. Градусы и минуты: 55 45.348;37 37.038 или 55 45.348$37 37.038 или 55 45.348%37 37.038\n"
        "3. Градусы, минуты и секунды: 55 45 20.88;37 37 2.28 или 55 45 20.88$37 37 2.28 или 55 45 20.88%37 37 2.28\n"
        "4. С обозначениями: 55°45'20.88\";37°37'2.28\" или 55°45'20.88\"$37°37'2.28\" или 55°45'20.88\"%37°37'2.28\"\n\n"
        "Разделитель между широтой и долготой - точка с запятой (;) или знак доллара ($) или знак процента (%)"
    )

def format_coordinate_result(result: Dict[str, Any]) -> str:
    """
    Форматирование результата поиска по координатам
    
    Args:
        result: Словарь с результатом поиска
        
    Returns:
        Отформатированная строка с результатом
    """
    formatted = [
        f"🔹 *SRID:* `{result['srid']}`",
        f"📝 *Название:* `{result['name']}`"
    ]
    
    if result.get('info'):
        formatted.append(f"ℹ️ *Описание:* `{result['info']}`")
        
    if result.get('coordinates'):
        formatted.append(
            f"📍 *Координаты:* `E: {result['coordinates']['x']:.3f}, "
            f"N: {result['coordinates']['y']:.3f}`"
        )
        
    reliability = result.get('reliability', 'Уточнить у Администратора')
    formatted.append(f"✅ *Достоверность:* `{reliability}`")
    
    return '\n'.join(formatted)

def format_search_result(result: Dict[str, Any]) -> str:
    """
    Форматирование результата текстового поиска
    
    Args:
        result: Словарь с результатом поиска
        
    Returns:
        Отформатированная строка с результатом
    """
    formatted = [
        f"🔹 *SRID:* `{result['srid']}`",
        f"📝 *Название:* `{result['name']}`"
    ]
    
    if result.get('info'):
        formatted.append(f"ℹ️ *Описание:* `{result['info']}`")
        
    reliability = result.get('reliability', 'Уточнить у Администратора')
    formatted.append(f"✅ *Достоверность:* `{reliability}`")
    
    return '\n'.join(formatted)

def format_inline_result(result: dict) -> dict:
    """
    Форматирование результата для inline-режима
    
    Args:
        result: Словарь с данными результата
        
    Returns:
        Отформатированный результат для inline-режима
    """
    # Форматируем заголовок с ограничением длины
    title = f"SRID: {result['srid']} - {result['name']}"
    if len(title) > 50:
        title = title[:47] + "..."
    
    # Форматируем описание с ограничением длины
    description = result.get('info', '')
    if len(description) > 100:
        description = description[:97] + "..."
    
    # Формируем полный текст сообщения
    message_text = (
        f"🔹 *SRID:* `{result['srid']}`\n"
        f"📝 *Название:* `{result['name']}`"
    )
    if result.get('info'):
        message_text += f"\nℹ️ *Описание:* `{result['info']}`"
    
    # Добавляем информацию о достоверности
    reliability = result.get('reliability', 'Уточнить у Администратора')
    message_text += f"\n✅ *Достоверность:* `{reliability}`"
    
    return {
        'id': str(result['srid']),
        'title': title,
        'description': description,
        'message_text': message_text
    }

def format_error_message(error: str) -> str:
    """
    Форматирование сообщения об ошибке
    
    Args:
        error: Текст ошибки
        
    Returns:
        Отформатированное сообщение об ошибке
    """
    return f"❌ {error}"

def format_coord_result(result: Dict[str, Any]) -> Dict[str, str]:
    """
    Форматирование результата поиска по координатам
    
    Args:
        result: Словарь с результатом поиска
        
    Returns:
        Отформатированный результат
    """
    text = f"🔹 *SRID:* `{result['srid']}`\n"
    text += f"📝 *Название:* `{result['name']}`"
    
    if result.get('info'):
        text += f"\nℹ️ *Описание:* `{result['info']}`"
    
    if result.get('x') is not None and result.get('y') is not None:
        text += f"\n📍 *Координаты:* `E: {round(result['x'], 3)}, N: {round(result['y'], 3)}`"
    else:
        text += f"\n📍 *Координаты:* `E: -, N: -`"
    
    # Определяем значение достоверности
    if str(result['srid']).startswith('326'):
        p_value = "EPSG"
    elif result.get('reliability') is None:
        p_value = "Уточнить у Администратора"
    else:
        p_value = result['reliability']
    
    text += (
        f"\n✅ *Достоверность:* `{p_value}`\n"
        f"📤 *Экспорт:* `xml_Civil3D, prj_GMv20, prj_GMv25`"
    )
    
    return {
        'text': text,
        'parse_mode': 'Markdown'
    } 