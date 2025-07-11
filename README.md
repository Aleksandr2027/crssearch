# 🚀 CrsSearchBot - Telegram Bot для поиска систем координат

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/downloads/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13%2B-blue)](https://www.postgresql.org/)

Полнофункциональный Telegram-бот для поиска и экспорта систем координат России. Поддерживает поиск по координатам, inline-поиск по описанию и экспорт в различные форматы.

## ✨ Основные возможности

### 🔍 Поиск систем координат
- **По координатам**: Введите широту и долготу, получите подходящие системы координат
- **Inline поиск**: Используйте `@CrsSearchBot описание` для поиска по названию/описанию
- **Интеллектуальная транслитерация**: Автоматическое преобразование кириллицы в латиницу

### 📄 Экспорт в форматы
- **GMv20**: PRJ-файлы для Global Mapper v20
- **GMv25**: PRJ-файлы для Global Mapper v25  
- **Civil3D**: Формат для Autodesk Civil3D (в разработке)
- **✅ Inline экспорт**: Кнопки экспорта работают прямо в результатах `@CrsSearchBot` поиска

### 🎯 Поддерживаемые системы координат
- **UTM зоны**: Универсальная поперечная проекция Меркатора
- **МСК**: Местные системы координат субъектов РФ
- **ГСК**: Государственные системы координат
- **СК42/СК95**: Зональные системы координат

## 📱 Использование

### Запуск бота
1. Найдите бота в Telegram: `@CrsSearchBot`
2. Нажмите `/start` для начала работы
3. Введите пароль (получите у администратора)

### Поиск по координатам
```
55.7558 37.6176
```
Введите широту и долготу через пробел

### Inline поиск
```
@CrsSearchBot Московская область
@CrsSearchBot UTM 37
@CrsSearchBot СК95 зона 2
```

### 🆕 Экспорт из inline результатов
После выбора системы координат из inline поиска, вы увидите кнопки:
- **📋 GMv20** - скачать PRJ-файл для Global Mapper v20
- **📋 GMv25** - скачать PRJ-файл для Global Mapper v25  
- **📄 Civil3D** - показывает статус "в разработке"

## 🛠 Техническая архитектура

### Стек технологий
- **Backend**: Python 3.11+
- **Bot Framework**: python-telegram-bot 
- **Database**: PostgreSQL 13+ с PostGIS
- **Cache**: In-memory кэширование
- **Logs**: Structured logging с ротацией

### Структура проекта
```
XML_search/
├── bot/                    # Telegram bot компоненты
│   ├── handlers/          # Обработчики команд и сообщений
│   ├── keyboards/         # Клавиатуры и кнопки
│   ├── states/           # Состояния диалогов
│   └── utils/            # Утилиты бота
├── core/                  # Основная логика поиска
│   └── search/           # Поисковые алгоритмы
├── enhanced/              # Расширенные компоненты
│   ├── export/           # Система экспорта
│   │   └── exporters/    # Экспортеры форматов
│   └── search/           # Улучшенный поиск
├── config/               # Конфигурационные файлы
└── spravka/             # Документация
```

## ⚙️ Установка и развертывание

### Требования
- Python 3.11+
- PostgreSQL 13+ с PostGIS
- Git
- Telegram Bot Token

### Быстрый старт

1. **Клонирование репозитория**
```bash
git clone https://github.com/Aleksandr2027/crssearch.git
cd crssearch/XML_search
```

2. **Создание виртуального окружения**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac  
source venv/bin/activate
```

3. **Установка зависимостей**
```bash
pip install -r requirements.txt
```

4. **Настройка базы данных**
```sql
-- Создание БД PostgreSQL
CREATE DATABASE crssearch;
\c crssearch
CREATE EXTENSION postgis;
```

5. **Конфигурация**
Создайте файл `.env`:
```env
BOT_TOKEN=ваш_telegram_bot_token
DB_HOST=localhost
DB_PORT=5432
DB_NAME=crssearch
DB_USER=postgres
DB_PASSWORD=ваш_пароль
BOT_PASSWORD=пароль_для_авторизации
```

6. **Запуск бота**
```bash
python main.py
```

## 🔧 Конфигурация

### Настройка базы данных
Файл `config/db_config.json`:
```json
{
  "host": "localhost",
  "port": 5432,
  "database": "crssearch",
  "pool_size": 10,
  "max_overflow": 20
}
```

### Настройка экспорта
Файл `enhanced/config/export_config.json`:
```json
{
  "output_directory": "output",
  "formats": {
    "gmv20": {"extension": ".prj"},
    "gmv25": {"extension": ".prj"}
  }
}
```

## 📊 Мониторинг и логирование

### Логи
- **Access logs**: `logs/access/`
- **Error logs**: `logs/errors/`
- **Debug logs**: `logs/debug/`
- **Metrics**: `logs/metrics/`

### Метрики
Система автоматически собирает:
- Количество запросов
- Время ответа
- Успешность операций
- Использование экспорта

## 🧪 Тестирование

### Запуск тестов
```bash
# Все тесты
python -m pytest tests/

# Конкретный модуль
python -m pytest tests/test_search_engine.py -v

# С покрытием
python -m pytest tests/ --cov=XML_search
```

### Создание простых тестов
Тесты не зависят от других модулей проекта:
```python
# Пример простого теста
def test_coordinate_parsing():
    from core.search.utils import parse_coordinates
    lat, lon = parse_coordinates("55.7558 37.6176")
    assert lat == 55.7558
    assert lon == 37.6176
```

## 🔒 Безопасность

### Авторизация
- Пароль-авторизация в боте
- Токены в переменных окружения
- Исключение секретов из репозитория

### Рекомендации
```env
# Используйте сильные пароли
BOT_PASSWORD=сложный_пароль!

# Ограничьте доступ к БД
DB_USER=crssearch_user  # не root/postgres
DB_PASSWORD=случайный_пароль
```

## 📚 API и интеграция

### Inline Query API
```python
# Формат inline запросов
@CrsSearchBot query_text

# Примеры:
@CrsSearchBot Московская       # Поиск по тексту
@CrsSearchBot 95 зона          # Поиск систем СК95
@CrsSearchBot UTM              # Поиск UTM систем
```

### Export API
```python
# Программный вызов экспорта
from enhanced.export.exporters.gmv20 import GMV20Exporter
exporter = GMV20Exporter(config)
result = exporter.export(srid=4326, output_path="output/")
```

## 🤝 Участие в разработке

### Архитектурные принципы
1. **Надежность**: Используйте стандартные решения
2. **Модульность**: Каждый компонент изолирован  
3. **Тестируемость**: Простые тесты без зависимостей
4. **Безопасность**: Исключение секретов из кода

### Workflow
1. Fork репозитория
2. Создайте feature branch
3. Внесите изменения с тестами
4. Создайте Pull Request

## 📄 Лицензия

MIT License - см. файл [LICENSE](LICENSE)

## 📞 Поддержка

- **Issues**: [GitHub Issues](https://github.com/Aleksandr2027/crssearch/issues)
- **Telegram**: `@CrsSearchBot` для тестирования
- **Документация**: Папка `spravka/`

## 🎯 Roadmap

### Ближайшие планы
- [ ] Полная поддержка Civil3D экспорта
- [ ] Веб-интерфейс для администрирования  
- [ ] REST API для интеграций
- [ ] Поддержка дополнительных форматов

### Долгосрочные цели
- [ ] Мобильное приложение
- [ ] Интеграция с ГИС-системами
- [ ] Машинное обучение для улучшения поиска

---

**CrsSearchBot** - Ваш надежный помощник в работе с системами координат! 🗺️ 