from typing import List, Dict, Any, Optional
from transliterate import translit
import logging
from XML_search.enhanced.log_manager import LogManager
from XML_search.enhanced.metrics import MetricsCollector

logger = LogManager().get_logger(__name__)
metrics = MetricsCollector()

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

def format_search_result(result: Dict[str, Any]) -> Dict[str, str]:
    """
    Форматирование результата поиска
    
    Args:
        result: Словарь с результатом поиска
        
    Returns:
        Отформатированный результат
    """
    text = f"🔹 *SRID:* `{result['srid']}`\n"
    text += f"📝 *Название:* `{result['srtext']}`"
    
    if result.get('info'):
        text += f"\nℹ️ *Описание:* `{result['info']}`"
    
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