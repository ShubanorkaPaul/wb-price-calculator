"""
Модуль для экспорта данных в Google Sheets
Через публичную ссылку (без авторизации)
"""

import pandas as pd
import requests
import json
from typing import Optional


def export_to_google_sheets(
    df: pd.DataFrame,
    sheet_name: str = "WB Price Calculator",
    share_email: Optional[str] = None
) -> dict:
    """
    Экспортирует DataFrame в Google Sheets через Google Sheets API
    
    Args:
        df: DataFrame с данными
        sheet_name: Название листа
        share_email: Email для шаринга (опционально)
    
    Returns:
        dict: {"success": bool, "url": str, "message": str}
    """
    
    try:
        # Конвертируем DataFrame в список списков
        values = [df.columns.tolist()] + df.values.tolist()
        
        # Здесь должен быть код для работы с Google Sheets API
        # Пока что заглушка (возвращаем ссылку на инструкцию)
        
        return {
            "success": False,
            "url": None,
            "message": "⚠️ Функция в разработке. Используйте экспорт в Excel."
        }
        
    except Exception as e:
        return {
            "success": False,
            "url": None,
            "message": f"❌ Ошибка: {str(e)}"
        }


def create_google_sheets_link(df: pd.DataFrame) -> str:
    """
    Создаёт ссылку для импорта в Google Sheets
    (через CSV файл на публичном сервере)
    """
    
    # Конвертируем в CSV
    csv_data = df.to_csv(index=False, encoding='utf-8')
    
    # Здесь можно загрузить на публичный сервер (например, pastebin, transfer.sh)
    # Пока что возвращаем инструкцию
    
    instructions = """
    📋 **Инструкция по экспорту в Google Sheets:**
    
    1. Скачайте файл Excel (кнопка ниже)
    2. Зайдите в Google Таблицы
    3. Нажмите "Файл" → "Импорт" → "Загрузить" → выберите файл
    4. Настройте импорт и нажмите "Импортировать данные"
    
    ⚡ **Или используйте прямой импорт:**
    - Скопируйте данные из Excel
    - Вставьте в Google Таблицу (Ctrl+V)
    """
    
    return instructions


# Тестирование
if __name__ == "__main__":
    # Пример использования
    test_df = pd.DataFrame({
        "Артикул": [12345, 67890],
        "Цена": [1000, 2000],
        "Маржа": [20.5, 25.0]
    })
    
    result = export_to_google_sheets(test_df)
    print(result)
