import streamlit as st
import pandas as pd
import io
import json
import gc
import time
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from calculator import (
    calculate_current_profit,
    calculate_recommended_price,
    get_status,
    get_commission_by_category,
    estimate_logistics,
    ACQUIRING,
)
from wb_api_prices import (
    get_all_cards,
    get_prices,
    get_commissions,
    get_stocks_by_warehouse,
    determine_model,
    get_available_models,
    update_prices,
    load_all_data_parallel,
)


st.set_page_config(
    page_title="Калькулятор цен WB",
    page_icon="🧮",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============ КАСТОМНЫЙ ДИЗАЙН (СВЕТЛАЯ ТЕМА + СКРЫТИЕ МЕНЮ STREAMLIT) ============

st.markdown("""
<style>
    /* ========== СКРЫВАЕМ МЕНЮ STREAMLIT ========== */
    
    /* Скрываем меню с 3 точками (справа сверху) */
    [data-testid="stMainMenu"] {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Скрываем "Made with Streamlit" внизу */
    footer {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Скрываем шапку Streamlit сверху */
    header[data-testid="stHeader"] {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Скрываем панель инструментов */
    [data-testid="stToolbar"] {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Скрываем кнопку Deploy */
    [data-testid="stDeployButton"] {
        display: none !important;
    }
    
    /* Убираем лишний отступ сверху */
    .block-container {
        padding-top: 2rem !important;
    }
    
    /* ========== ПРИНУДИТЕЛЬНО СВЕТЛАЯ ТЕМА ========== */
    
    @media (prefers-color-scheme: dark) {
        html, body, [class*="css"], [data-testid="stAppViewContainer"], 
        [data-testid="stMain"], [data-testid="stSidebar"], .stApp {
            background-color: #FFFFFF !important;
            color: #1F2937 !important;
        }
    }
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
    }
    
    .stApp {
        background-color: #FFFFFF !important;
    }
    
    [data-testid="stAppViewContainer"] {
        background-color: #FFFFFF !important;
    }
    
    input, textarea, select {
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
    }
    
    [data-testid="stTextInput"] input {
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
        border: 1px solid #D1D5DB !important;
    }
    
    [data-baseweb="select"] {
        background-color: #FFFFFF !important;
    }
    
    [data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
    }
    
    [data-testid="stRadio"] label {
        color: #1F2937 !important;
    }
    
    [data-testid="stCheckbox"] label {
        color: #1F2937 !important;
    }
    
    [data-testid="stSlider"] label {
        color: #1F2937 !important;
    }
    
    [data-testid="stFileUploader"] {
        background-color: #F9FAFB !important;
        border: 2px dashed #D1D5DB !important;
        border-radius: 10px !important;
        padding: 15px !important;
    }
    
    [data-testid="stFileUploader"] label {
        color: #1F2937 !important;
    }
    
    [data-testid="stFileUploader"] button {
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
        border: 1px solid #D1D5DB !important;
    }
    
    [data-testid="stSidebar"] button {
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
    }
    
    [data-testid="stSidebar"] * {
        color: #1F2937 !important;
    }
    
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 {
        color: #1E40AF !important;
    }
    
    [role="tooltip"] {
        background-color: #1F2937 !important;
        color: #FFFFFF !important;
    }
    
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: #F3F4F6;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #D1D5DB;
        border-radius: 5px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #9CA3AF;
    }
    
    /* ========== ЗАГОЛОВКИ ========== */
    
    h1 {
        color: #1E40AF !important;
        font-weight: 700 !important;
        border-bottom: 3px solid #3B82F6;
        padding-bottom: 10px;
        margin-bottom: 20px !important;
    }
    
    h2 {
        color: #1F2937 !important;
        font-weight: 600 !important;
        margin-top: 20px !important;
    }
    
    h3 {
        color: #374151 !important;
        font-weight: 600 !important;
    }
    
    /* ========== МЕТРИКИ ========== */
    
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #FFFFFF 0%, #F9FAFB 100%);
        padding: 20px;
        border-radius: 12px;
        border-left: 4px solid #3B82F6;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: transform 0.2s;
    }
    
    [data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    
    [data-testid="stMetricLabel"] {
        color: #6B7280 !important;
        font-size: 13px !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    [data-testid="stMetricValue"] {
        color: #111827 !important;
        font-size: 28px !important;
        font-weight: 700 !important;
    }
    
    /* ========== КНОПКИ ========== */
    
    .stButton > button {
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s !important;
        border: none !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    
    [data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%) !important;
        color: white !important;
    }
    
    /* ========== ALERTS ========== */
    
    [data-testid="stAlert"] {
        border-radius: 10px !important;
        border-left-width: 5px !important;
        padding: 15px 20px !important;
    }
    
    [data-testid="stAlert"][kind="success"] {
        background-color: #D1FAE5 !important;
        border-left-color: #10B981 !important;
    }
    
    [data-testid="stAlert"][kind="warning"] {
        background-color: #FEF3C7 !important;
        border-left-color: #F59E0B !important;
    }
    
    [data-testid="stAlert"][kind="error"] {
        background-color: #FEE2E2 !important;
        border-left-color: #EF4444 !important;
    }
    
    [data-testid="stAlert"][kind="info"] {
        background-color: #DBEAFE !important;
        border-left-color: #3B82F6 !important;
    }
    
    /* ========== ТАБЛИЦЫ ========== */
    
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
    /* ========== БОКОВАЯ ПАНЕЛЬ ========== */
    
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #F9FAFB 0%, #F3F4F6 100%) !important;
    }
    
    [data-testid="stSidebar"] h1 {
        color: #1E40AF !important;
        font-size: 22px !important;
        border-bottom: 2px solid #3B82F6;
    }
    
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
        color: #374151 !important;
        font-size: 16px !important;
    }
    
    /* ========== РАЗДЕЛИТЕЛИ ========== */
    
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(to right, transparent, #E5E7EB, transparent);
        margin: 20px 0;
    }
    
    /* ========== EXPANDER ========== */
    
    [data-testid="stExpander"] {
        border-radius: 10px !important;
        border: 1px solid #E5E7EB !important;
        background-color: white !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    
    [data-testid="stExpander"] summary {
        font-size: 16px !important;
        font-weight: 600 !important;
        color: #1E40AF !important;
        padding: 15px !important;
        background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%) !important;
        border-radius: 10px !important;
        border-left: 4px solid #3B82F6 !important;
    }
    
    [data-testid="stExpander"] summary:hover {
        background: linear-gradient(135deg, #DBEAFE 0%, #BFDBFE 100%) !important;
    }
    
    /* ========== ТАБЫ ========== */
    
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #F9FAFB;
        padding: 8px;
        border-radius: 10px;
    }
    
    [data-testid="stTabs"] [data-baseweb="tab"] {
        border-radius: 8px !important;
        padding: 10px 16px !important;
        font-weight: 500 !important;
        transition: all 0.2s !important;
        color: #374151 !important;
    }
    
    [data-testid="stTabs"] [data-baseweb="tab"]:hover {
        background-color: #EFF6FF !important;
    }
    
    [data-testid="stTabs"] [aria-selected="true"] {
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%) !important;
        color: white !important;
    }
    
    /* ========== КАСТОМНЫЕ БЛОКИ ========== */
    
    .loss-box {
        background: linear-gradient(135deg, #FEE2E2 0%, #FECACA 100%);
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #DC2626;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(220,38,38,0.1);
        color: #1F2937 !important;
    }
    
    .loss-box h4 {
        color: #991B1B !important;
        margin-top: 0 !important;
    }
    
    .success-box {
        background: linear-gradient(135deg, #D1FAE5 0%, #A7F3D0 100%);
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #059669;
        margin-bottom: 15px;
        color: #1F2937 !important;
    }
    
    .info-box {
        background: linear-gradient(135deg, #DBEAFE 0%, #BFDBFE 100%);
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #2563EB;
        margin-bottom: 15px;
        color: #1F2937 !important;
    }
    
    .disclaimer-box {
        background: linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%);
        padding: 15px 20px;
        border-radius: 10px;
        border-left: 4px solid #F59E0B;
        margin: 10px 0;
        font-size: 14px;
        color: #1F2937 !important;
    }
    
    /* ========== ГЛАВНЫЙ HEADER ========== */
    
    .main-header {
        background: linear-gradient(135deg, #3B82F6 0%, #1E40AF 100%);
        padding: 25px 30px;
        border-radius: 12px;
        color: white;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px rgba(59,130,246,0.2);
    }
    
    .main-header h1 {
        color: white !important;
        margin: 0 !important;
        border: none !important;
        padding: 0 !important;
        font-size: 32px !important;
    }
    
    .main-header p {
        color: #DBEAFE !important;
        margin: 5px 0 0 0 !important;
        font-size: 14px !important;
    }
    
    * {
        transition: background-color 0.15s ease;
    }
    
    /* ========== МОБИЛЬНАЯ АДАПТАЦИЯ ========== */
    
    @media (max-width: 768px) {
        .main-header {
            padding: 15px 20px !important;
        }
        
        .main-header h1 {
            font-size: 22px !important;
        }
        
        .main-header p {
            font-size: 12px !important;
        }
        
        h1 { font-size: 22px !important; }
        h2 { font-size: 18px !important; }
        h3 { font-size: 16px !important; }
        
        [data-testid="stMetric"] {
            padding: 12px !important;
        }
        
        [data-testid="stMetricValue"] {
            font-size: 20px !important;
        }
        
        [data-testid="stMetricLabel"] {
            font-size: 11px !important;
        }
        
        [data-testid="stDataFrame"] {
            font-size: 12px !important;
        }
        
        .stButton > button {
            padding: 12px 20px !important;
            font-size: 15px !important;
            min-height: 44px !important;
        }
        
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            padding-top: 1rem !important;
        }
        
        [data-testid="stTabs"] [data-baseweb="tab"] {
            padding: 8px 12px !important;
            font-size: 13px !important;
        }
    }
</style>
""", unsafe_allow_html=True)


# ============ SESSION STATE ============

if "calc_loaded" not in st.session_state: st.session_state["calc_loaded"] = False
if "df_results" not in st.session_state: st.session_state["df_results"] = None
if "cost_prices" not in st.session_state: st.session_state["cost_prices"] = {}
if "cost_models" not in st.session_state: st.session_state["cost_models"] = {}
if "show_confirm" not in st.session_state: st.session_state["show_confirm"] = None
if "to_update_data" not in st.session_state: st.session_state["to_update_data"] = None
if "update_result" not in st.session_state: st.session_state["update_result"] = None
if "skipped_no_stock" not in st.session_state: st.session_state["skipped_no_stock"] = 0
if "current_page" not in st.session_state: st.session_state["current_page"] = 1


# ============ SIDEBAR ============

with st.sidebar:
    st.title("⚙️ Настройки")

    api_key = st.text_input("🔑 API ключ WB", type="password", key="api_key_input")
    if api_key: st.success("✅ Ключ введён")
    st.markdown("---")

    st.subheader("💰 Себестоимость")
    st.caption("Формат: Артикул | Себестоимость | Модель (опционально)")
    cost_file = st.file_uploader("Excel файл", type=["xlsx", "xls", "csv"])

    if cost_file:
        try:
            cost_df = pd.read_csv(cost_file) if cost_file.name.endswith(".csv") else pd.read_excel(cost_file)
            cols = list(cost_df.columns)
            article_col, cost_col, model_col = None, None, None
            
            for c in cols:
                c_lower = str(c).lower().strip()
                if not article_col and any(k in c_lower for k in ["артикул", "article", "sku"]): 
                    article_col = c
                if not cost_col and any(k in c_lower for k in ["себест", "cost", "закуп"]): 
                    cost_col = c
                if not model_col and any(k in c_lower for k in ["модель", "model", "тип", "схема"]):
                    model_col = c

            if article_col and cost_col:
                new_costs = {}
                new_models = {}
                
                for _, row in cost_df.iterrows():
                    art = str(row[article_col]).strip()
                    try:
                        cost = float(str(row[cost_col]).replace(",", ".").replace(" ", ""))
                        if art and art.lower() != "nan" and cost > 0:
                            new_costs[art] = cost
                            
                            if model_col:
                                model_val = str(row[model_col]).strip().upper()
                                if model_val in ["FBS", "FBO", "DBS", "DBW"]:
                                    new_models[art] = model_val
                    except: pass
                
                if new_costs:
                    st.session_state["cost_prices"] = new_costs
                    st.session_state["cost_models"] = new_models
                    
                    st.success(f"✅ Загружено {len(new_costs)} товаров")
                    if new_models:
                        st.info(f"📋 Модели указаны для {len(new_models)} товаров")
            else: 
                st.error("❌ Не найдены колонки Артикул и Себестоимость")
        except Exception as e: 
            st.error(f"❌ Ошибка: {e}")

    saved_costs = st.session_state.get("cost_prices", {})
    saved_models = st.session_state.get("cost_models", {})
    if saved_costs: 
        info_text = f"💾 В памяти: {len(saved_costs)} товаров"
        if saved_models:
            info_text += f" | Моделей: {len(saved_models)}"
        st.info(info_text)
    st.markdown("---")

    st.subheader("🏬 Модель работы")
    work_model = st.radio(
        "По какой модели работаешь?",
        ["📦 FBS (Маркетплейс)", "🏬 FBO (Склад WB)", "🔀 Смешанная (авто)"],
        index=0
    )
    if work_model == "📦 FBS (Маркетплейс)": force_model = "FBS"
    elif work_model == "🏬 FBO (Склад WB)": force_model = "FBO"
    else: force_model = None
    
    if work_model != "🔀 Смешанная (авто)":
        load_stocks_option = st.checkbox(
            "📦 Загружать остатки WB", 
            value=False,
            help="Замедляет загрузку на 30-60 сек. Не нужно если работаешь только по FBS."
        )
    else:
        load_stocks_option = True
        st.info("💡 Для авто-режима остатки обязательны")

    st.markdown("---")

    st.subheader("🎯 Параметры расчёта")
    target_margin = st.slider("Целевая маржа, %", 10, 50, 20, 1)
    buyout_percent = st.slider("% выкупа", 30, 100, 90, 1)
    buyout_rate = buyout_percent / 100
    
    acceptance_fee = st.number_input(
        "Платная приёмка (₽ на ед.)", 
        min_value=0, max_value=500, value=0, step=5
    )

    with st.expander("🔄 Настройки возвратов (продвинуто)"):
        st.caption("💡 Полный учёт всех расходов на возврат товара")
        
        return_processing_fee = st.number_input(
            "Обработка возврата WB (₽)",
            min_value=0, max_value=200, value=30, step=5
        )
        
        damage_rate_percent = st.slider(
            "% порчи товара при возврате",
            min_value=0, max_value=50, value=10, step=1
        )
        damage_rate = damage_rate_percent / 100
        
        st.caption(f"""
        📊 **Расчёт одного возврата:**
        - Логистика обратно: как прямая
        - Обработка: {return_processing_fee}₽
        - Порча: {damage_rate_percent}% от себестоимости
        """)

    st.markdown("---")

    st.subheader("🏛️ Налог")
    tax_mode = st.selectbox(
        "Система налогообложения",
        ["УСН 6% (доходы)", "УСН 15% (доходы − расходы)", "Патент (0%)", "НПД / Самозанятый (6%)", "ОСНО (20%)", "Свой процент"]
    )
    if tax_mode == "УСН 6% (доходы)": tax_rate = 0.06
    elif tax_mode == "УСН 15% (доходы − расходы)": tax_rate = 0.15
    elif tax_mode == "Патент (0%)": tax_rate = 0.0
    elif tax_mode == "НПД / Самозанятый (6%)": tax_rate = 0.06
    elif tax_mode == "ОСНО (20%)": tax_rate = 0.20
    else:
        custom_tax = st.number_input("Свой % налога", 0.0, 50.0, 6.0, 0.5)
        tax_rate = custom_tax / 100

    st.markdown("---")

    st.subheader("🎁 Скидка")
    st.caption("💡 Ограничивает 'перечёркнутую цену' от завышения")
    
    discount_mode = st.radio(
        "Режим скидки:",
        ["🛡️ Плавно снижать", "🎯 Установить сразу", "🔒 Не менять"],
        index=0
    )
    
    if discount_mode == "🎯 Установить сразу":
        max_discount = st.slider("Разумная скидка, %", 0, 60, 30, 5)
        max_discount_change = 100
        keep_discount = False
        
        if max_discount > 0:
            multiplier = 1 / (1 - max_discount / 100)
            st.caption(f"📊 Цена до скидки будет максимум в {multiplier:.2f}x раз выше цены для покупателя")
        
    elif discount_mode == "🛡️ Плавно снижать":
        max_discount = st.slider("Целевая разумная скидка, %", 0, 60, 30, 5)
        max_discount_change = st.slider("Макс. снижение за раз, %", 1, 20, 5, 1)
        keep_discount = False
        
        st.caption(f"💡 Если сейчас скидка 60% — за 6 применений дойдёт до {max_discount}% (по {max_discount_change}%)")
        
    else:
        max_discount = 100
        max_discount_change = 0
        keep_discount = True
        st.info("🔒 Скидка не изменится.")
        st.warning("⚠️ Если текущая скидка > 50%, цена до скидки может быть завышенной!")

    st.markdown("---")
    if st.button("🗑️ Очистить кеш и данные", use_container_width=True):
        st.cache_data.clear()
        st.session_state["calc_loaded"] = False
        st.session_state["df_results"] = None
        st.session_state["show_confirm"] = None
        st.session_state["to_update_data"] = None
        st.session_state["skipped_no_stock"] = 0
        st.session_state["current_page"] = 1
        gc.collect()
        st.rerun()


# ============ ГЛАВНАЯ ============

st.markdown("""
<div class="main-header">
    <h1>🧮 Умный калькулятор цен WB</h1>
    <p>Автоматический расчёт оптимальных цен с учётом всех расходов</p>
</div>
""", unsafe_allow_html=True)


# ============ ИНСТРУКЦИЯ ============

with st.expander("📖 **Как пользоваться калькулятором** — нажми чтобы открыть инструкцию", expanded=False):
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "🚀 Быстрый старт", 
        "🔑 API ключ", 
        "💰 Себестоимость",
        "🏬 Модели работы",
        "🎁 Скидки",
        "📊 Что считает",
        "❓ FAQ"
    ])
    
    with tab1:
        st.markdown("""
        ### 🚀 Быстрый старт за 3 шага
        
        #### Шаг 1️⃣ — Введи API ключ WB
        В боковой панели слева введи свой **API ключ** от Wildberries.
        
        #### Шаг 2️⃣ — Загрузи файл с себестоимостью
        Excel файл с двумя колонками: **Артикул** и **Себестоимость**
        
        #### Шаг 3️⃣ — Настрой параметры и запусти
        - Выбери **модель работы** (FBS/FBO)
        - Установи **целевую маржу** (обычно 20-30%)
        - Укажи **% выкупа**
        - Нажми **"🚀 Загрузить и рассчитать"**
        
        ---
        
        #### ✨ Готово!
        
        Через 30-60 секунд ты увидишь:
        - 📊 Аналитику всех товаров
        - 📈 Графики
        - 📋 Таблицу с рекомендованными ценами
        - 💰 Кнопку обновления цен на WB
        """)
    
    with tab2:
        st.markdown("""
        ### 🔑 Как получить API ключ Wildberries
        
        1. Зайди в **личный кабинет продавца WB**: https://seller.wildberries.ru
        2. Профиль → **Настройки** → **Доступ к API**
        3. Нажми **"Создать новый токен"**
        4. Название: **"Калькулятор цен"**
        5. Отметь галочки:
           - ✅ **Контент** (обязательно)
           - ✅ **Цены и скидки** (обязательно!)
           - ✅ **Маркетплейс** (обязательно)
           - ✅ **Статистика** (для остатков)
        6. Создать → скопировать токен → вставить в наше поле
        
        ---
        
        #### ⚠️ Безопасность
        - 🔒 Мы **не храним** твой API ключ
        - 🔒 Можно **отозвать** в любой момент в кабинете WB
        - 🔒 Не давай ключ третьим лицам
        """)
    
    with tab3:
        st.markdown("""
        ### 💰 Файл с себестоимостью
        
        #### Формат — Excel (.xlsx) или CSV
        
        | Артикул | Себестоимость | Модель (опц.) |
        |---------|---------------|----------------|
        | A123-BLK | 500 | FBS |
        | B456-RED | 400 | FBS |
        | C789-BLU | 450 | DBS |
        
        ---
        
        #### 💡 Что включать в себестоимость
        
        ✅ **Включай:**
        - Закупочная цена товара
        - Доставка от поставщика
        - Упаковка
        - Комиссия посредника
        
        ❌ **НЕ включай:**
        - Комиссию WB (считаем сами)
        - Логистику WB (считаем сами)
        - Рекламу (не учитываем)
        - Налоги (считаем сами)
        """)
    
    with tab4:
        st.markdown("""
        ### 🏬 Модели работы на WB
        
        #### 📦 FBS — Маркетплейс
        - Товар на **твоём складе**
        - Ты собираешь, WB доставляет
        - Комиссия обычно 5-15%
        
        #### 🏬 FBO — Склад WB
        - Товар на **складе Wildberries**
        - WB всё делает сам
        - Комиссия 15-25%
        
        #### 🏪 DBS — Витрина
        - Ты сам доставляешь
        - Самая низкая комиссия
        
        #### 🎯 В калькуляторе:
        - Работаешь по FBS → выбирай "📦 FBS"
        - Работаешь по FBO → выбирай "🏬 FBO"
        - Разные товары → "🔀 Смешанная (авто)"
        """)
    
    with tab5:
        st.markdown("""
        ### 🎁 Работа со скидками
        
        #### ⚠️ Почему это важно
        
        Резкие изменения скидок → **карантин WB**:
        - Товар пропадает из поиска на 3-7 дней
        - Продажи падают до 0
        
        **Наш калькулятор защищает!**
        
        ---
        
        #### 3 режима
        
        **🛡️ Плавно снижать** (рекомендую)
        - Скидка 60% → 55% → 50% → 45%...
        - Безопасно
        
        **🎯 Установить сразу**
        - Сразу нужная скидка
        - Риск карантина
        
        **🔒 Не менять**
        - Оставляет как есть
        
        ---
        
        #### 💡 Оптимальная скидка на WB — 20-40%
        """)
    
    with tab6:
        st.markdown("""
        ### 📊 Что именно считает калькулятор
        
        #### ⚠️ ВАЖНО
        
        Калькулятор показывает **потенциальную прибыль С ОДНОЙ ПРОДАЖИ** (юнит-экономику), 
        а НЕ реальную прибыль магазина.
        
        ---
        
        #### 🔢 Что считаем
        
        Для каждого товара:
        - **Прибыль с 1 единицы** — сколько заработаешь если продашь одну штуку
        - **Маржу** — % прибыли от цены продажи
        - **Все расходы** — детально
        
        #### 📊 Учитываем всё:
        
        ✅ Комиссию WB  
        ✅ Логистику  
        ✅ Эквайринг 1.5%  
        ✅ Налоги  
        ✅ Себестоимость  
        ✅ Платную приёмку  
        ✅ **Возвраты** (полностью):
           - Логистика обратно
           - Обработка возврата WB
           - Порча товара
        """)
    
    with tab7:
        st.markdown("""
        ### ❓ FAQ
        
        **Q: Это моя реальная прибыль?**  
        A: **Нет!** Это прибыль с ОДНОЙ продажи. Реальная зависит от объёма продаж.
        
        **Q: Почему рекомендованная цена высокая?**  
        A: Учитываем **все расходы**. Если работал в убыток — цена вырастет.
        
        **Q: % выкупа — где посмотреть?**  
        A: Личный кабинет WB → Аналитика → Заказы и продажи.
        
        **Q: "WB ограничил запросы" — что делать?**  
        A: Подожди 1-2 минуты, попробуй снова.
        """)
    
    st.markdown("""
    <div style='text-align: center; margin-top: 20px; padding: 15px; background: linear-gradient(135deg, #DBEAFE 0%, #BFDBFE 100%); border-radius: 10px; color: #1F2937;'>
        <b>💡 Совет:</b> Начни с малого — попробуй на 10-20 товарах, потом масштабируй!
    </div>
    """, unsafe_allow_html=True)


# ============ ПРОВЕРКИ ============

if not api_key:
    st.warning("👈 Введи API ключ в боковой панели")
    st.stop()

if not st.session_state.get("cost_prices", {}):
    st.warning("👈 Загрузи Excel файл с себестоимостью в боковой панели")
    
    st.markdown("### 📋 Пример файла:")
    example_df = pd.DataFrame({
        "Артикул": ["A123-BLK", "B456-RED", "C789-BLU", "D012"],
        "Себестоимость": [500, 400, 450, 300],
        "Модель": ["FBS", "FBS", "DBS", "FBO"]
    })
    st.dataframe(example_df, use_container_width=False)
    st.caption("💡 Колонка 'Модель' опциональна")
    st.stop()

if st.session_state.get("update_result"):
    result = st.session_state["update_result"]
    st.success(f"✅ Отправлено на WB: **{result['success']}** товаров")
    if result.get("errors"):
        st.error("Ошибки:")
        for err in result["errors"]: st.text(err)
    if st.button("Скрыть уведомление"):
        st.session_state["update_result"] = None
        st.rerun()
    st.markdown("---")


col1, col2 = st.columns([1, 3])
with col1:
    load_button = st.button("🚀 Загрузить и рассчитать", type="primary", use_container_width=True)
with col2:
    st.info("⚡ Быстрая загрузка: 30-60 сек | Повторно: 1-2 сек (из кеша)")

if load_button:
    st.session_state["calc_loaded"] = True
    st.session_state["df_results"] = None
    st.session_state["current_page"] = 1

if not st.session_state["calc_loaded"]:
    st.stop()


# ============ РАСЧЁТ ============

if st.session_state["df_results"] is None:
    progress = st.progress(0, text="🚀 Запускаем параллельную загрузку...")
    
    start_time = time.time()
    
    progress.progress(10, text="📥 Загружаем карточки, цены и комиссии одновременно...")
    
    all_data = load_all_data_parallel(api_key, load_stocks=load_stocks_option)
    
    progress.progress(70, text="✅ Основные данные загружены!")
    
    cards_df = all_data["cards"]
    prices_df = all_data["prices"]
    commissions_df = all_data["commissions"]
    stocks_df = all_data["stocks"]
    
    if cards_df.empty:
        progress.empty()
        st.error("❌ Не удалось загрузить карточки")
        st.stop()
    
    if prices_df.empty:
        progress.empty()
        st.error("❌ Не удалось загрузить цены")
        st.stop()
    
    if load_stocks_option:
        progress.progress(90, text="📦 Остатки загружены")
    
    elapsed = time.time() - start_time
    progress.progress(100, text=f"⚡ Загружено за {elapsed:.1f} секунд!")
    time.sleep(1)
    progress.empty()
    
    st.success(f"✅ Данные загружены за **{elapsed:.1f} сек** ({len(cards_df)} товаров)")

    merged = cards_df.merge(prices_df[["nm_id", "price", "discount", "discounted_price"]], on="nm_id", how="left")
    merged["cost_price"] = merged["article"].astype(str).str.strip().map(st.session_state["cost_prices"]).fillna(0)

    merged["available_models"] = merged["article"].apply(lambda x: get_available_models(x, stocks_df))

    saved_models = st.session_state.get("cost_models", {})
    
    def determine_final_model(row):
        article = str(row["article"]).strip()
        if article in saved_models:
            return saved_models[article], "excel"
        available = row.get("available_models", set())
        if available and len(available) > 0:
            if force_model and force_model in available:
                return force_model, "wb_stocks"
            elif not force_model:
                for m in ["FBS", "FBO", "DBS"]:
                    if m in available:
                        return m, "wb_stocks"
        if force_model:
            return force_model, "default"
        else:
            return "FBO", "default"
    
    merged[["model", "model_source"]] = merged.apply(
        lambda row: pd.Series(determine_final_model(row)), axis=1
    )
    
    if force_model:
        def is_available(row):
            if row["model_source"] == "excel":
                return row["model"] == force_model
            elif row["model_source"] == "wb_stocks":
                return force_model in row.get("available_models", set())
            else:
                return True
        merged["model_available"] = merged.apply(is_available, axis=1)
    else:
        merged["model_available"] = True

    if not commissions_df.empty:
        merged = merged.merge(
            commissions_df[["subject_id", "commission_fbo", "commission_fbs", "commission_dbs", "commission_dbw"]],
            on="subject_id", how="left"
        )
        merged["commission_percent"] = merged.apply(
            lambda row: (
                row["commission_fbs"] if row["model"] == "FBS" and row.get("commission_fbs", 0) > 0
                else row["commission_fbo"] if row["model"] == "FBO" and row.get("commission_fbo", 0) > 0
                else get_commission_by_category(row["subject"], row["model"])
            ), axis=1
        )
    else:
        merged["commission_percent"] = merged.apply(lambda row: get_commission_by_category(row["subject"], row["model"]), axis=1)

    merged["logistics"] = merged.apply(lambda row: estimate_logistics(row["volume_liters"], row["model"]), axis=1)

    results = []
    skipped_no_stock = 0

    for _, row in merged.iterrows():
        if row["cost_price"] == 0 or row["price"] == 0: continue
        if not row.get("model_available", True):
            skipped_no_stock += 1
            continue

        current = calculate_current_profit(
            row["discounted_price"] or row["price"], row["commission_percent"],
            row["logistics"], row["cost_price"], buyout_rate, tax_rate, acceptance_fee,
            return_processing_fee, damage_rate
        )

        recommended = calculate_recommended_price(
            row["cost_price"], row["commission_percent"], row["logistics"], target_margin,
            row["discount"] or 0, max_discount, max_discount_change, keep_discount, 
            buyout_rate, tax_rate, acceptance_fee,
            return_processing_fee, damage_rate
        )

        if not recommended: continue

        status_icon, status_text = get_status(current["margin"], target_margin)
        cat = "убыточные" if current["margin"] < 0 else "ниже цели" if current["margin"] < target_margin - 2 else "в норме"

        results.append({
            "nm_id": row["nm_id"], "article": row["article"], "title": row["title"],
            "subject": row["subject"], "model": row["model"], 
            "model_source": row.get("model_source", "default"),
            "cost_price": row["cost_price"],
            "commission_percent": row["commission_percent"], "logistics": row["logistics"],
            "current_price": row["price"], "current_discount": row["discount"] or 0,
            "current_price_final": row["discounted_price"] or row["price"],
            "current_profit": current["profit"], "current_margin": current["margin"],
            "commission_rub": current["commission"],
            "logistics_rub": current["logistics"],
            "acquiring_rub": current["acquiring"],
            "returns_rub": current["returns_cost"],
            "return_logistics_rub": current.get("return_logistics", 0),
            "return_processing_rub": current.get("return_processing", 0),
            "return_damage_rub": current.get("return_damage", 0),
            "tax_rub": current["tax"],
            "recommended_price": recommended["price_without_discount"],
            "recommended_discount": recommended["discount_percent"],
            "recommended_final": recommended["price_with_discount"],
            "recommended_profit": recommended["profit"],
            "recommended_margin": recommended["margin"],
            "discount_change": recommended["discount_change"],
            "profit_diff": recommended["profit"] - current["profit"],
            "status_icon": status_icon, "status_text": status_text, "category": cat,
        })

    if not results:
        st.warning("⚠️ Нет товаров для расчёта.")
        st.session_state["calc_loaded"] = False
        st.stop()

    st.session_state["df_results"] = pd.DataFrame(results)
    st.session_state["skipped_no_stock"] = skipped_no_stock
    
    del cards_df, prices_df, commissions_df, stocks_df, merged, results
    gc.collect()


df_results = st.session_state["df_results"]


# ============ СВОДКА ============

st.markdown("---")
st.header("📊 Аналитика и сводка")

st.markdown("""
<div class="disclaimer-box">
    <b>💡 Важно:</b> Все расчёты показывают <b>потенциальную прибыль с одной продажи</b> (юнит-экономика), 
    а не твою реальную прибыль. Реальная зависит от количества продаж.
</div>
""", unsafe_allow_html=True)

total_products = len(df_results)
losing_df = df_results[df_results["category"] == "убыточные"]
below_target = df_results[df_results["category"] == "ниже цели"]
ok = df_results[df_results["category"] == "в норме"]
potential = df_results["profit_diff"].sum()

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1: st.metric("📦 Всего товаров", total_products)
with col_m2: st.metric("🔴 Убыточные", len(losing_df))
with col_m3: st.metric("🟡 Ниже цели", len(below_target))
with col_m4: st.metric("🟢 В норме", len(ok))


# ============ ГРАФИКИ ============

st.markdown("---")
st.subheader("📈 Визуальный анализ")

col_g1, col_g2 = st.columns(2)

with col_g1:
    st.markdown("##### 🎯 Распределение товаров по статусам")
    
    status_data = pd.DataFrame({
        "Статус": ["🔴 Убыточные", "🟡 Ниже цели", "🟢 В норме"],
        "Количество": [len(losing_df), len(below_target), len(ok)]
    })
    
    fig_donut = go.Figure(data=[go.Pie(
        labels=status_data["Статус"],
        values=status_data["Количество"],
        hole=0.55,
        marker=dict(colors=['#EF4444', '#F59E0B', '#10B981']),
        textinfo='label+percent',
        textfont=dict(size=13),
        hovertemplate='<b>%{label}</b><br>Товаров: %{value}<br>Доля: %{percent}<extra></extra>'
    )])
    
    fig_donut.update_layout(
        showlegend=False,
        height=350,
        margin=dict(t=20, b=20, l=20, r=20),
        paper_bgcolor='white',
        plot_bgcolor='white',
        annotations=[dict(
            text=f'<b>{total_products}</b><br>товаров',
            x=0.5, y=0.5,
            font=dict(size=20, color='#1F2937'),
            showarrow=False
        )]
    )
    
    st.plotly_chart(fig_donut, use_container_width=True)

with col_g2:
    st.markdown("##### 📊 Распределение маржи по товарам")
    
    margin_data = df_results["current_margin"].clip(-30, 60)
    
    fig_hist = px.histogram(
        x=margin_data,
        nbins=20,
        color_discrete_sequence=['#3B82F6']
    )
    
    fig_hist.add_vline(x=0, line_dash="dash", line_color="red", 
                       annotation_text="Убыток", annotation_position="top")
    fig_hist.add_vline(x=target_margin, line_dash="dash", line_color="green", 
                       annotation_text=f"Цель {target_margin}%", annotation_position="top")
    
    fig_hist.update_layout(
        xaxis_title="Маржа, %",
        yaxis_title="Количество товаров",
        height=350,
        margin=dict(t=20, b=40, l=40, r=20),
        showlegend=False,
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    fig_hist.update_xaxes(gridcolor='#F3F4F6', zerolinecolor='#E5E7EB')
    fig_hist.update_yaxes(gridcolor='#F3F4F6')
    
    st.plotly_chart(fig_hist, use_container_width=True)


col_g3, col_g4 = st.columns(2)

with col_g3:
    st.markdown("##### 🏆 ТОП-10 по прибыли с 1 продажи")
    st.caption("💡 Гипотетическая прибыль если продашь ОДНУ единицу")
    
    top_profitable = df_results.nlargest(10, "current_profit")[["article", "current_profit"]].copy()
    top_profitable["article_short"] = top_profitable["article"].astype(str).str[:25]
    top_profitable = top_profitable.sort_values("current_profit", ascending=True)
    
    fig_top = go.Figure(go.Bar(
        x=top_profitable["current_profit"],
        y=top_profitable["article_short"],
        orientation='h',
        marker=dict(
            color=top_profitable["current_profit"],
            colorscale='Greens',
            showscale=False
        ),
        text=top_profitable["current_profit"].apply(lambda x: f"{x:.0f} ₽"),
        textposition='outside'
    ))
    
    fig_top.update_layout(
        xaxis_title="Прибыль с 1 продажи, ₽",
        yaxis_title="",
        height=400,
        margin=dict(t=20, b=40, l=180, r=80),
        plot_bgcolor='white',
        paper_bgcolor='white',
        yaxis=dict(type='category', tickfont=dict(size=11))
    )
    
    fig_top.update_xaxes(gridcolor='#F3F4F6')
    
    st.plotly_chart(fig_top, use_container_width=True)


with col_g4:
    st.markdown("##### 🚨 ТОП-10 самых убыточных")
    st.caption("💡 Сколько теряешь на каждой ЕДИНИЦЕ")
    
    if len(losing_df) > 0:
        top_losing = losing_df.nsmallest(10, "current_profit")[["article", "current_profit"]].copy()
        top_losing["article_short"] = top_losing["article"].astype(str).str[:25]
        top_losing["loss"] = top_losing["current_profit"].abs()
        top_losing = top_losing.sort_values("loss", ascending=True)
        
        fig_loss = go.Figure(go.Bar(
            x=top_losing["loss"],
            y=top_losing["article_short"],
            orientation='h',
            marker=dict(
                color=top_losing["loss"],
                colorscale='Reds',
                showscale=False
            ),
            text=top_losing["current_profit"].apply(lambda x: f"{x:.0f} ₽"),
            textposition='outside'
        ))
        
        fig_loss.update_layout(
            xaxis_title="Убыток с 1 продажи, ₽",
            yaxis_title="",
            height=400,
            margin=dict(t=20, b=40, l=180, r=80),
            plot_bgcolor='white',
            paper_bgcolor='white',
            yaxis=dict(type='category', tickfont=dict(size=11))
        )
        
        fig_loss.update_xaxes(gridcolor='#F3F4F6')
        
        st.plotly_chart(fig_loss, use_container_width=True)
    else:
        st.success("🎉 Нет убыточных товаров!")


st.markdown("##### 🥧 Куда уходят деньги (в среднем на один товар)")

avg_commission = df_results["commission_rub"].mean()
avg_logistics = df_results["logistics_rub"].mean()
avg_acquiring = df_results["acquiring_rub"].mean()
avg_returns = df_results["returns_rub"].mean()
avg_tax = df_results["tax_rub"].mean()
avg_cost = df_results["cost_price"].mean()

expenses_data = pd.DataFrame({
    "Категория": ["💰 Комиссия WB", "🚚 Логистика", "💳 Эквайринг", "↩️ Возвраты", "🏛️ Налог", "📦 Себестоимость"],
    "Сумма": [avg_commission, avg_logistics, avg_acquiring, avg_returns, avg_tax, avg_cost]
})

fig_expenses = px.pie(
    expenses_data,
    values="Сумма",
    names="Категория",
    color_discrete_sequence=['#3B82F6', '#8B5CF6', '#EC4899', '#F59E0B', '#EF4444', '#10B981']
)

fig_expenses.update_traces(
    textinfo='label+percent',
    textfont=dict(size=13),
    hovertemplate='<b>%{label}</b><br>Средняя сумма: %{value:.0f} ₽<br>Доля: %{percent}<extra></extra>'
)

fig_expenses.update_layout(
    height=400,
    margin=dict(t=20, b=20, l=20, r=20),
    plot_bgcolor='white',
    paper_bgcolor='white',
    showlegend=True,
    legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05)
)

st.plotly_chart(fig_expenses, use_container_width=True)


with st.expander("🔄 Детализация расходов на возвраты"):
    if "return_logistics_rub" in df_results.columns:
        avg_ret_log = df_results["return_logistics_rub"].mean()
        avg_ret_proc = df_results["return_processing_rub"].mean()
        avg_ret_dmg = df_results["return_damage_rub"].mean()
        avg_ret_total = df_results["returns_rub"].mean()
        
        col_r1, col_r2, col_r3, col_r4 = st.columns(4)
        with col_r1:
            st.metric("🚚 Логистика обратно", f"{avg_ret_log:.1f} ₽")
        with col_r2:
            st.metric("📦 Обработка WB", f"{avg_ret_proc:.1f} ₽")
        with col_r3:
            st.metric("💔 Порча товара", f"{avg_ret_dmg:.1f} ₽")
        with col_r4:
            st.metric("💰 Всего на возвраты", f"{avg_ret_total:.1f} ₽")


# ============ УБЫТОЧНЫЕ ============

if len(losing_df) > 0:
    total_loss_per_unit = abs(losing_df["current_profit"].sum())
    
    st.markdown(f"""
    <div class="loss-box">
        <h4>🚨 Внимание! У тебя {len(losing_df)} убыточных товаров!</h4>
        <b>Суммарный убыток если продашь ПО 1 ШТ каждого: <span style='color:#DC2626; font-size:20px;'>− {total_loss_per_unit:,.0f} ₽</span></b><br>
        <i>Если продашь по 100 шт каждого = потеряешь {-total_loss_per_unit * 100:,.0f} ₽!</i>
    </div>
    """, unsafe_allow_html=True)


# ============ КАТЕГОРИИ ============

with st.expander("📁 Анализ по категориям товаров"):
    cat_analysis = df_results.groupby("subject").agg(
        Товаров=("article", "count"),
        Средняя_маржа=("current_margin", "mean"),
        Убыточных=("category", lambda x: (x == "убыточные").sum())
    ).reset_index()
    
    cat_analysis = cat_analysis.sort_values("Средняя_маржа")
    cat_analysis["Средняя_маржа"] = cat_analysis["Средняя_маржа"].round(1)
    
    def color_cat_margin(val):
        color = '#FEE2E2' if val < 0 else '#FEF3C7' if val < target_margin else '#D1FAE5'
        return f'background-color: {color}; color: black'

    st.dataframe(cat_analysis.style.map(color_cat_margin, subset=['Средняя_маржа']), use_container_width=True)

st.markdown(f"""
<div class="success-box">
    <h4 style='margin-top:0;'>💰 Потенциал роста прибыли (с одной продажи каждого товара)</h4>
    <div style='font-size: 28px; font-weight: 700; color: #059669;'>
        +{potential:,.0f} ₽
    </div>
    <div style='color: #6B7280; margin-top: 5px;'>
        суммарно если применить все рекомендованные цены и продать по 1 шт каждого товара
    </div>
</div>
""", unsafe_allow_html=True)


# ============ ФИЛЬТРЫ ============

st.markdown("---")
st.subheader("📋 Список товаров")

col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
with col_f1:
    filter_choice = st.radio("Фильтр:", ["🔴 Убыточные", "🟡 Ниже цели", "🟢 В норме", "📋 Все"], horizontal=True)
with col_f2:
    if not force_model:
        model_filter = st.radio("Модель:", ["Все", "FBO", "FBS"], horizontal=True)
    else:
        model_filter = "Все"
with col_f3:
    rows_per_page = st.selectbox("Показывать по:", [50, 100, 500, "Все"], index=0)

if filter_choice == "🔴 Убыточные": filtered = losing_df.copy(); filter_name = "убыточные"
elif filter_choice == "🟡 Ниже цели": filtered = below_target.copy(); filter_name = "ниже цели"
elif filter_choice == "🟢 В норме": filtered = ok.copy(); filter_name = "в норме"
else: filtered = df_results.copy(); filter_name = "все"

if model_filter != "Все":
    filtered = filtered[filtered["model"] == model_filter]

to_update_from_filter = filtered[
    (filtered["current_price"] != filtered["recommended_price"]) |
    (filtered["current_discount"] != filtered["recommended_discount"])
]

st.info(f"📊 Показано: **{len(filtered)}** товаров | Требуют обновления: **{len(to_update_from_filter)}**")


# ============ ТАБЛИЦА ============

if len(filtered) > 0:
    display_df = filtered[[
        "article", "subject", "model",
        "cost_price", "commission_percent", "logistics",
        "current_price", "current_discount", "current_price_final", "current_margin",
        "recommended_price", "recommended_discount", "recommended_final", "recommended_margin",
        "discount_change", "profit_diff"
    ]].copy()

    if force_model: display_df = display_df.drop(columns=["model"])

    cols = ["Артикул", "Категория"]
    if not force_model: cols.append("Модель")
    cols.extend([
        "Себест.", "Ком.%", "Лог.₽",
        "Цена до ск.", "Скид.%", "Покупателю", "Маржа %",
        "Реком. цена", "Реком. скид.%", "Реком. покуп.", "Реком. маржа %",
        "Δ Скид.%", "Δ Приб.₽"
    ])
    display_df.columns = cols

    total_items = len(display_df)
    if rows_per_page != "Все":
        total_pages = (total_items - 1) // rows_per_page + 1
        
        page_col1, page_col2, page_col3, page_col4 = st.columns([1, 1, 2, 6])
        with page_col1:
            if st.button("◀ Назад") and st.session_state["current_page"] > 1:
                st.session_state["current_page"] -= 1
                st.rerun()
        with page_col2:
            if st.button("Вперед ▶") and st.session_state["current_page"] < total_pages:
                st.session_state["current_page"] += 1
                st.rerun()
        with page_col3:
            st.write(f"Страница **{st.session_state['current_page']}** из {total_pages}")
            
        start_idx = (st.session_state["current_page"] - 1) * rows_per_page
        end_idx = start_idx + rows_per_page
        display_df_page = display_df.iloc[start_idx:end_idx]
    else:
        display_df_page = display_df

    def highlight_margins(val):
        try:
            v = float(val)
            if v < 0: return 'background-color: #FEE2E2; color: #991B1B; font-weight: 600'
            elif v < target_margin - 2: return 'background-color: #FEF3C7; color: #92400E; font-weight: 600'
            else: return 'background-color: #D1FAE5; color: #065F46; font-weight: 600'
        except: return ''

    styled_df = display_df_page.style.map(
        highlight_margins, 
        subset=['Маржа %', 'Реком. маржа %']
    ).format(precision=1)

    st.dataframe(styled_df, use_container_width=True, height=600)

else:
    st.info("Нет товаров в этой категории")


# ============ ЭКСПОРТ ============

st.markdown("---")
st.subheader("📤 Экспорт данных")

col_exp1, col_exp2, col_exp3 = st.columns(3)

with col_exp1:
    output_excel = io.BytesIO()
    with pd.ExcelWriter(output_excel, engine="openpyxl") as writer:
        df_results.to_excel(writer, sheet_name="Все товары", index=False)
        losing_df.to_excel(writer, sheet_name="Убыточные", index=False)
        below_target.to_excel(writer, sheet_name="Ниже цели", index=False)
        ok.to_excel(writer, sheet_name="В норме", index=False)
        prices_to_update = df_results[["nm_id", "recommended_price", "recommended_discount"]].copy()
        prices_to_update.columns = ["nmID", "price", "discount"]
        prices_to_update.to_excel(writer, sheet_name="Цены для загрузки", index=False)

    st.download_button(
        label="📊 Excel",
        data=output_excel.getvalue(),
        file_name=f"wb_prices_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

with col_exp2:
    csv_data = df_results.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📄 CSV",
        data=csv_data,
        file_name=f"wb_prices_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True
    )

with col_exp3:
    json_export = {
        "export_date": datetime.now().isoformat(),
        "total_products": len(df_results),
        "settings": {
            "model": force_model if force_model else "auto",
            "target_margin": target_margin,
            "buyout_percent": buyout_percent,
            "tax_rate": tax_rate,
            "acceptance_fee": acceptance_fee,
        },
        "summary": {
            "losing_count": len(losing_df),
            "below_target_count": len(below_target),
            "ok_count": len(ok),
            "potential_profit": float(potential),
        },
        "products": df_results.to_dict(orient="records"),
    }
    
    json_data = json.dumps(json_export, ensure_ascii=False, indent=2, default=str).encode('utf-8')
    
    st.download_button(
        label="🔧 JSON",
        data=json_data,
        file_name=f"wb_prices_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
        mime="application/json",
        use_container_width=True
    )


# ============ ОБНОВЛЕНИЕ ЦЕН ============

st.markdown("---")
st.subheader("💰 Обновление цен на WB")

if st.session_state["show_confirm"] is None:
    st.warning(f"Товаров к обновлению в текущем фильтре: **{len(to_update_from_filter)}**")

    col_upd1, col_upd2 = st.columns(2)
    with col_upd1:
        if st.button(
            f"💰 Обновить отфильтрованные ({len(to_update_from_filter)})",
            type="primary", use_container_width=True,
            disabled=(len(to_update_from_filter) == 0)
        ):
            st.session_state["show_confirm"] = "filtered"
            st.session_state["to_update_data"] = to_update_from_filter.copy()
            st.rerun()

    with col_upd2:
        all_to_update = df_results[
            (df_results["current_price"] != df_results["recommended_price"]) |
            (df_results["current_discount"] != df_results["recommended_discount"])
        ]
        if st.button(
            f"⚡ Обновить ВСЕ ({len(all_to_update)})",
            use_container_width=True, disabled=(len(all_to_update) == 0)
        ):
            st.session_state["show_confirm"] = "all"
            st.session_state["to_update_data"] = all_to_update.copy()
            st.rerun()

else:
    to_update = st.session_state["to_update_data"]
    st.error(f"## ⚠️ ПОДТВЕРЖДЕНИЕ\n\nБудет обновлено **{len(to_update)}** товаров.")

    preview = to_update[[
        "article", "subject", "current_price", "recommended_price",
        "current_discount", "recommended_discount", "current_margin", "recommended_margin"
    ]].copy()
    preview.columns = ["Артикул", "Категория", "Было цена", "Станет цена", "Было скид%", "Станет скид%", "Была маржа", "Станет маржа"]
    st.dataframe(preview, use_container_width=True, height=300)

    col_conf1, col_conf2 = st.columns(2)
    with col_conf1:
        if st.button("✅ ДА, обновить", type="primary", use_container_width=True):
            price_updates = [{"nmID": int(r["nm_id"]), "price": int(r["recommended_price"]), "discount": int(r["recommended_discount"])} for _, r in to_update.iterrows()]
            with st.spinner(f"💰 Обновляем {len(price_updates)} товаров..."):
                result = update_prices(api_key, price_updates)
            st.session_state["update_result"] = result
            st.session_state["show_confirm"] = None
            st.session_state["to_update_data"] = None
            st.rerun()

    with col_conf2:
        if st.button("❌ Отмена", use_container_width=True):
            st.session_state["show_confirm"] = None
            st.session_state["to_update_data"] = None
            st.rerun()
