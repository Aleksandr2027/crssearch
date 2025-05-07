"""
Модуль с реализациями экспортеров
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import json
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
import logging

class BaseExporter(ABC):
    """Базовый класс для всех экспортеров"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    @abstractmethod
    def export(self, data: List[Dict[str, Any]], output_path: Path) -> bool:
        """
        Экспорт данных в файл
        
        Args:
            data: Данные для экспорта
            output_path: Путь к файлу для сохранения
            
        Returns:
            True если экспорт успешен, False в противном случае
        """
        pass

class XMLExporter(BaseExporter):
    """Экспортер в XML формат"""
    
    def export(self, data: List[Dict[str, Any]], output_path: Path) -> bool:
        try:
            root = ET.Element("coordinate_systems")
            
            for item in data:
                system = ET.SubElement(root, "system")
                for key, value in item.items():
                    if value is not None:
                        field = ET.SubElement(system, key)
                        field.text = str(value)
            
            tree = ET.ElementTree(root)
            tree.write(output_path, encoding='utf-8', xml_declaration=True)
            self.logger.info(f"Данные успешно экспортированы в XML: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при экспорте в XML: {e}")
            return False

class JSONExporter(BaseExporter):
    """Экспортер в JSON формат"""
    
    def export(self, data: List[Dict[str, Any]], output_path: Path) -> bool:
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Данные успешно экспортированы в JSON: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при экспорте в JSON: {e}")
            return False

class CSVExporter(BaseExporter):
    """Экспортер в CSV формат"""
    
    def export(self, data: List[Dict[str, Any]], output_path: Path) -> bool:
        try:
            if not data:
                self.logger.warning("Нет данных для экспорта в CSV")
                return False
                
            fieldnames = data[0].keys()
            
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
                
            self.logger.info(f"Данные успешно экспортированы в CSV: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Ошибка при экспорте в CSV: {e}")
            return False 