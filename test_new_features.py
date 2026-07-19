"""
Тестовый скрипт для проверки новых фич Варианта А+
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Тестируем импорты
print("🔍 Проверка импортов...")
try:
    import streamlit as st
    print("✅ Streamlit импортирован")
except Exception as e:
    print(f"❌ Ошибка импорта Streamlit: {e}")

try:
    import pandas as pd
    print("✅ Pandas импортирован")
except Exception as e:
    print(f"❌ Ошибка импорта Pandas: {e}")

try:
    import plotly.express as px
    print("✅ Plotly импортирован")
except Exception as e:
    print(f"❌ Ошибка импорта Plotly: {e}")

# Тестируем модули проекта
print("\n🔍 Проверка модулей проекта...")

try:
    from calculator import (
        calculate_current_profit,
        calculate_recommended_price,
        calculate_break_even_price,
        get_status,
        get_commission_by_category,
        estimate_logistics
    )
    print("✅ Модуль calculator импортирован")
except Exception as e:
    print(f"❌ Ошибка импорта calculator: {e}")

try:
    from wb_api_prices import (
        get_all_cards,
        get_prices,
        update_prices,
        load_all_data_parallel
    )
    print("✅ Модуль wb_api_prices импортирован")
except Exception as e:
    print(f"❌ Ошибка импорта wb_api_prices: {e}")

# Тестируем создание тестовых данных
print("\n🔍 Проверка создания тестовых данных...")

try:
    # Создаём тестовый DataFrame
    test_data = {
        "article": [12345, 67890, 11111],
        "current_price_final": [1000, 2000, 1500],
        "current_profit": [200, 500, -50],
        "current_margin": [20.0, 25.0, -3.0],
        "break_even_price": [800, 1500, 1600],
        "recommended_final": [1100, 2100, 1600],
        "recommended_profit": [250, 550, 50],
    }
    
    df = pd.DataFrame(test_data)
    print(f"✅ Тестовый DataFrame создан: {len(df)} товаров")
    
    # Проверяем финансовые метрики
    total_revenue = df["current_price_final"].sum()
    total_profit = df["current_profit"].sum()
    avg_margin = df["current_margin"].mean()
    
    print(f"✅ Финансовая сводка:")
    print(f"   - Выручка: {total_revenue:,.0f} ₽")
    print(f"   - Прибыль: {total_profit:,.0f} ₽")
    print(f"   - Средняя маржа: {avg_margin:.1f}%")
    
    # Проверяем матрицу рисков
    losing_df = df[df["current_margin"] < 0]
    below_be = df[df["current_price_final"] < df["break_even_price"]]
    
    print(f"✅ Матрица рисков:")
    print(f"   - Убыточных: {len(losing_df)}")
    print(f"   - Ниже точки безубыточности: {len(below_be)}")
    
except Exception as e:
    print(f"❌ Ошибка создания тестовых данных: {e}")

# Тестируем экспорт в Excel
print("\n🔍 Проверка экспорта в Excel...")

try:
    import io
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Тест", index=False)
    
    print(f"✅ Excel-файл создан: {len(output.getvalue())} байт")
    
except Exception as e:
    print(f"❌ Ошибка экспорта в Excel: {e}")

print("\n" + "="*50)
print("✅ ВСЕ ПРОВЕРКИ ЗАВЕРШЕНЫ!")
print("="*50)
