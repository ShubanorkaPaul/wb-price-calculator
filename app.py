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
    calculate_break_even_price,
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
    parse_action_file,
)


st.set_page_config(
    page_title="Калькулятор цен WB",
    page_icon="🧮",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============ КАСТОМНЫЙ ДИЗАЙН ============

st.markdown("""
<style>
    [data-testid="stMainMenu"] { display: none !important; }
    footer { display: none !important; }
    header[data-testid="stHeader"] { display: none !important; }
    [data-testid="stToolbar"] { display: none !important; }
    [data-testid="stDeployButton"] { display: none !important; }
    .block-container { padding-top: 2rem !important; }
    
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
    
    .stApp { background-color: #FFFFFF !important; }
    [data-testid="stAppViewContainer"] { background-color: #FFFFFF !important; }
    
    input, textarea, select {
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
    }
    
    [data-testid="stTextInput"] input {
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
        border: 1px solid #D1D5DB !important;
    }
    
    [data-baseweb="select"] { background-color: #FFFFFF !important; }
    [data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
    }
    
    [data-testid="stRadio"] label { color: #1F2937 !important; }
    [data-testid="stCheckbox"] label { color: #1F2937 !important; }
    [data-testid="stSlider"] label { color: #1F2937 !important; }
    
    [data-testid="stFileUploader"] {
        background-color: #F9FAFB !important;
        border: 2px dashed #D1D5DB !important;
        border-radius: 10px !important;
        padding: 15px !important;
    }
    
    [data-testid="stFileUploader"] label { color: #1F2937 !important; }
    [data-testid="stFileUploader"] button {
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
        border: 1px solid #D1D5DB !important;
    }
    
    [data-testid="stSidebar"] button {
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
    }
    
    [data-testid="stSidebar"] * { color: #1F2937 !important; }
    
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 {
        color: #1E40AF !important;
    }
    
    [role="tooltip"] {
        background-color: #1F2937 !important;
        color: #FFFFFF !important;
    }
    
    ::-webkit-scrollbar { width: 10px; height: 10px; }
    ::-webkit-scrollbar-track { background: #F3F4F6; }
    ::-webkit-scrollbar-thumb { background: #D1D5DB; border-radius: 5px; }
    ::-webkit-scrollbar-thumb:hover { background: #9CA3AF; }
    
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
    
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    
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
    
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(to right, transparent, #E5E7EB, transparent);
        margin: 20px 0;
    }
    
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
    
    .loss-box {
        background: linear-gradient(135deg, #FEE2E2 0%, #FECACA 100%);
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #DC2626;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(220,38,38,0.1);
        color: #1F2937 !important;
    }
    
    .loss-box h4 { color: #991B1B !important; margin-top: 0 !important; }
    
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
    
    * { transition: background-color 0.15s ease; }
    
    @media (max-width: 768px) {
        .main-header { padding: 15px 20px !important; }
        .main-header h1 { font-size: 22px !important; }
        .main-header p { font-size: 12px !important; }
        h1 { font-size: 22px !important; }
        h2 { font-size: 18px !important; }
        h3 { font-size: 16px !important; }
        [data-testid="stMetric"] { padding: 12px !important; }
        [data-testid="stMetricValue"] { font-size: 20px !important; }
        [data-testid="stMetricLabel"] { font-size: 11px !important; }
        [data-testid="stDataFrame"] { font-size: 12px !important; }
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


# ============ ФУНКЦИЯ ВАЛИДАЦИИ ============

def validate_price_updates(to_update):
    critical_errors = []
    warnings = []
    info = []
    
    for _, row in to_update.iterrows():
        article = row["article"]
        current_price = row["current_price"]
        new_price = row["recommended_price"]
        new_final = row["recommended_final"]
        new_margin = row["recommended_margin"]
        cost_price = row["cost_price"]
        current_discount = row["current_discount"]
        new_discount = row["recommended_discount"]
        break_even = row.get("break_even_price", 0)
        
        if break_even > 0 and new_final < break_even:
            loss = break_even - new_final
            critical_errors.append({
                "type": "below_break_even",
                "article": article,
                "message": f"Цена покупателю ({new_final:.0f}₽) НИЖЕ точки безубыточности ({break_even:.0f}₽). Убыток {loss:.0f}₽/шт"
            })
        elif new_final < cost_price:
            critical_errors.append({
                "type": "below_cost",
                "article": article,
                "message": f"Цена покупателю ({new_final:.0f}₽) НИЖЕ себестоимости ({cost_price:.0f}₽)!"
            })
        elif new_margin < 0:
            critical_errors.append({
                "type": "negative_margin",
                "article": article,
                "message": f"Отрицательная маржа {new_margin:.1f}%"
            })
        else:
            if current_price > 0:
                price_change_percent = abs(new_price - current_price) / current_price * 100
                if price_change_percent > 30:
                    direction = "выше" if new_price > current_price else "ниже"
                    warnings.append({
                        "type": "big_price_change",
                        "article": article,
                        "message": f"Цена меняется на {price_change_percent:.0f}% ({direction}). Риск карантина WB!"
                    })
            
            discount_change = abs(new_discount - current_discount)
            if discount_change > 10:
                direction = "выше" if new_discount > current_discount else "ниже"
                warnings.append({
                    "type": "big_discount_change",
                    "article": article,
                    "message": f"Скидка меняется на {discount_change}% ({direction}). Риск карантина!"
                })
            
            if 0 <= new_margin < 5:
                warnings.append({
                    "type": "low_margin",
                    "article": article,
                    "message": f"Очень низкая маржа {new_margin:.1f}% — почти в ноль"
                })
            
            if new_discount > 50:
                warnings.append({
                    "type": "huge_discount",
                    "article": article,
                    "message": f"Скидка {new_discount}% — покупатели могут заподозрить накрутку цены"
                })
        
        safety_pct = row.get("safety_margin_percent", 100)
        if 0 < safety_pct < 10:
            info.append({
                "type": "low_safety",
                "article": article,
                "message": f"Малый запас прочности ({safety_pct:.1f}%)"
            })
        
        if new_price > 10000:
            info.append({
                "type": "high_price",
                "article": article,
                "message": f"Цена {new_price:.0f}₽ — проверь что не опечатка"
            })
    
    return critical_errors, warnings, info


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
if "action_data" not in st.session_state: st.session_state["action_data"] = None


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
        load_stocks_option = st.checkbox("📦 Загружать остатки WB", value=False)
    else:
        load_stocks_option = True
        st.info("💡 Для авто-режима остатки обязательны")

    st.markdown("---")
    st.markdown("---")

    st.subheader("💰 Комиссии WB")

    st.caption("Если комиссия в калькуляторе не совпадает с кабинетом WB — выбери правильное поле вручную.")

    fbs_commission_field = st.selectbox(
        "Для FBS / Маркетплейс использовать:",
        [
            "kgvpMarketplace",
            "paidStorageKgvp",
            "kgvpSupplier",
            "kgvpSupplierExpress",
        ],
        index=0,
        help="Обычно для FBS используется kgvpMarketplace"
    )

    fbo_commission_field = st.selectbox(
        "Для FBO / Склад WB использовать:",
        [
            "paidStorageKgvp",
            "kgvpMarketplace",
            "kgvpSupplier",
            "kgvpSupplierExpress",
        ],
        index=0,
        help="Обычно для FBO используется paidStorageKgvp"
    )

    dbs_commission_field = st.selectbox(
        "Для DBS / Витрина использовать:",
        [
            "kgvpSupplier",
            "kgvpMarketplace",
            "paidStorageKgvp",
            "kgvpSupplierExpress",
        ],
        index=0,
        help="Обычно для DBS используется kgvpSupplier"
    )
    st.subheader("🎯 Параметры расчёта")
    target_margin = st.slider("Целевая маржа, %", 10, 50, 20, 1)
    buyout_percent = st.slider("% выкупа", 30, 100, 90, 1)
    buyout_rate = buyout_percent / 100
    
    acceptance_fee = st.number_input("Платная приёмка (₽ на ед.)", 0, 500, 0, 5)

    with st.expander("🔄 Настройки возвратов"):
        return_processing_fee = st.number_input("Обработка возврата WB (₽)", 0, 200, 30, 5)
        damage_rate_percent = st.slider("% порчи товара при возврате", 0, 50, 10, 1)
        damage_rate = damage_rate_percent / 100

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
    discount_mode = st.radio(
        "Режим скидки:",
        ["🛡️ Плавно снижать", "🎯 Установить сразу", "🔒 Не менять"],
        index=0
    )
    
    if discount_mode == "🎯 Установить сразу":
        max_discount = st.slider("Разумная скидка, %", 0, 60, 30, 5)
        max_discount_change = 100
        keep_discount = False
    elif discount_mode == "🛡️ Плавно снижать":
        max_discount = st.slider("Целевая разумная скидка, %", 0, 60, 30, 5)
        max_discount_change = st.slider("Макс. снижение за раз, %", 1, 20, 5, 1)
        keep_discount = False
    else:
        max_discount = 100
        max_discount_change = 0
        keep_discount = True

    st.markdown("---")
    if st.button("🗑️ Очистить кеш и данные", use_container_width=True):
        st.cache_data.clear()
        st.session_state["calc_loaded"] = False
        st.session_state["df_results"] = None
        st.session_state["show_confirm"] = None
        st.session_state["to_update_data"] = None
        st.session_state["skipped_no_stock"] = 0
        st.session_state["current_page"] = 1
        st.session_state["action_data"] = None
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
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🚀 Быстрый старт", 
        "🔑 API ключ", 
        "💰 Себестоимость",
        "🎉 Акции WB",
        "❓ FAQ"
    ])
    
    with tab1:
        st.markdown("""
        ### 🚀 Быстрый старт за 3 шага
        1. Введи API ключ WB
        2. Загрузи файл с себестоимостью
        3. Нажми "🚀 Загрузить и рассчитать"
        
        Через 30-60 секунд увидишь:
        - Аналитику всех товаров
        - Точку безубыточности
        - Графики и метрики
        - Возможность анализа акций WB
        """)
    
    with tab2:
        st.markdown("""
        ### 🔑 Как получить API ключ
        1. WB Seller → Настройки → Доступ к API
        2. Создать новый токен
        3. Отметить: Контент, Цены и скидки, Маркетплейс
        4. Скопировать → вставить в поле
        """)
    
    with tab3:
        st.markdown("""
        ### 💰 Формат файла себестоимости
        Excel с колонками:
        - Артикул
        - Себестоимость
        - Модель (опц.)
        """)
    
    with tab4:
        st.markdown("""
        ### 🎉 Как анализировать акции WB
        
        1. Получи Excel-файл акции от WB
        2. Перейди на вкладку "🎉 Акции WB"
        3. Загрузи файл
        4. Калькулятор покажет:
           - Какие товары ВЫГОДНО добавить
           - Какие УБЫТОЧНЫЕ (не участвовать!)
           - Сколько доп. прибыли получишь
        5. Скачай готовый файл-исключение для WB
        """)
    
    with tab5:
        st.markdown("""
        ### ❓ FAQ
        
        **Q: Это моя реальная прибыль?**  
        A: Нет, это прибыль с ОДНОЙ продажи.
        
        **Q: Что такое точка безубыточности?**  
        A: Минимальная цена без убытка.
        
        **Q: Как считаются акции?**  
        A: Берётся плановая цена от WB, применяются все расходы, показывается результат.
        """)


# ============ ПРОВЕРКИ ============

if not api_key:
    st.warning("👈 Введи API ключ в боковой панели")
    st.stop()

if not st.session_state.get("cost_prices", {}):
    st.warning("👈 Загрузи Excel файл с себестоимостью в боковой панели")
    st.stop()

if st.session_state.get("update_result"):
    result = st.session_state["update_result"]
    st.success(f"✅ Отправлено на WB: **{result['success']}** товаров")
    if result.get("errors"):
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
    progress.progress(10, text="📥 Загружаем данные...")
    
    all_data = load_all_data_parallel(api_key, load_stocks=load_stocks_option)
    
    progress.progress(70, text="✅ Обрабатываем...")
    
    cards_df = all_data["cards"]
    prices_df = all_data["prices"]
    commissions_df = all_data["commissions"]
    stocks_df = all_data["stocks"]
    
    if cards_df.empty or prices_df.empty:
        progress.empty()
        st.error("❌ Не удалось загрузить данные")
        st.stop()
    
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
    
    merged[["model", "model_source"]] = merged.apply(lambda row: pd.Series(determine_final_model(row)), axis=1)
    
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
            commissions_df[
                [
                    "subject_id",
                    "subject_name",
                    "kgvpMarketplace",
                    "paidStorageKgvp",
                    "kgvpSupplier",
                    "kgvpSupplierExpress",
                ]
            ],
            on="subject_id",
            how="left"
        )

        def pick_commission(row):
            """
            Выбирает комиссию по модели товара и выбранным в боковой панели полям.
            Если API не дал значение — используем fallback по категории.
            """

            model = str(row.get("model", "")).upper()

            if model == "FBS":
                field = fbs_commission_field
            elif model == "FBO":
                field = fbo_commission_field
            elif model == "DBS":
                field = dbs_commission_field
            else:
                field = fbs_commission_field

            value = row.get(field, 0)

            try:
                value = float(value)
            except:
                value = 0

            if value > 0:
                return value, f"API: {field}"

            fallback = get_commission_by_category(row.get("subject", ""), model)
            return fallback, "Fallback"

        commission_result = merged.apply(lambda row: pick_commission(row), axis=1)

        merged["commission_percent"] = commission_result.apply(lambda x: x[0])
        merged["commission_source"] = commission_result.apply(lambda x: x[1])

    else:
        merged["commission_percent"] = merged.apply(
            lambda row: get_commission_by_category(row["subject"], row["model"]),
            axis=1
        )
        merged["commission_source"] = "Fallback"
        merged["kgvpMarketplace"] = 0
        merged["paidStorageKgvp"] = 0
        merged["kgvpSupplier"] = 0
        merged["kgvpSupplierExpress"] = 0
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
        
        break_even_price = calculate_break_even_price(
            row["cost_price"], row["commission_percent"], row["logistics"],
            buyout_rate, tax_rate, acceptance_fee,
            return_processing_fee, damage_rate
        )
        
        current_final_price = row["discounted_price"] or row["price"]
        safety_margin_rub = current_final_price - (break_even_price or 0)
        safety_margin_percent = (safety_margin_rub / current_final_price * 100) if current_final_price > 0 else 0

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
            "break_even_price": break_even_price or 0,
            "safety_margin_rub": round(safety_margin_rub, 2),
            "safety_margin_percent": round(safety_margin_percent, 1),
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

total_products = len(df_results)
losing_df = df_results[df_results["category"] == "убыточные"]
below_target = df_results[df_results["category"] == "ниже цели"]
ok = df_results[df_results["category"] == "в норме"]
potential = df_results["profit_diff"].sum()


# ============ ВКЛАДКИ ============

st.markdown("---")

tab_analytics, tab_products, tab_actions = st.tabs([
    "📊 Аналитика",
    "💰 Управление ценами",
    "🎉 Акции WB"
])


# ============ ВКЛАДКА 1: АНАЛИТИКА ============

with tab_analytics:
    st.header("📊 Аналитика и сводка")

    st.markdown("""
    <div class="disclaimer-box">
        <b>💡 Важно:</b> Все расчёты показывают <b>потенциальную прибыль с одной продажи</b> (юнит-экономика), 
        а не твою реальную прибыль. Реальная зависит от количества продаж.
    </div>
    """, unsafe_allow_html=True)

    with st.expander("🎯 Что такое 'Точка безубыточности' и 'Запас прочности'"):
        st.markdown("""
        ### 🎯 Точка безубыточности (Мин. цена)
        Это минимальная цена, при которой ты не в убытке (прибыль = 0).
        
        ### 🛡️ Запас прочности
        Насколько твоя цена выше точки безубыточности.
        
        ### 💡 Зачем это знать?
        - Планировать акции WB
        - Оценивать риски
        - Защита от убытков
        """)

    st.subheader("💰 Финансовая сводка (потенциальная)")
    total_revenue = df_results["current_price_final"].sum()
    total_profit_sum = df_results["current_profit"].sum()
    total_cost_sum = df_results["cost_price"].sum()
    roi_percent = (total_profit_sum / total_cost_sum * 100) if total_cost_sum > 0 else 0
    
    col_fin1, col_fin2, col_fin3, col_fin4 = st.columns(4)
    with col_fin1:
        st.metric("💰 Выручка (текущая)", f"{total_revenue:,.0f} ₽")
    with col_fin2:
        margin_avg = df_results["current_margin"].mean()
        st.metric("📈 Прибыль (текущая)", f"{total_profit_sum:,.0f} ₽", delta=f"{margin_avg:.1f}% маржа")
    with col_fin3:
        st.metric("📊 ROI", f"{roi_percent:.1f}%")
    with col_fin4:
        st.metric("🚀 Потенциал роста", f"+{potential:,.0f} ₽", delta=f"+{potential:,.0f} ₽ от цен")

    st.markdown("---")

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1: st.metric("📦 Всего товаров", total_products)
    with col_m2: st.metric("🔴 Убыточные", len(losing_df))
    with col_m3: st.metric("🟡 Ниже цели", len(below_target))
    with col_m4: st.metric("🟢 В норме", len(ok))

    if "break_even_price" in df_results.columns:
        below_break_even = df_results[df_results["current_price_final"] < df_results["break_even_price"]]
        close_to_break_even = df_results[
            (df_results["current_price_final"] >= df_results["break_even_price"]) &
            (df_results["safety_margin_percent"] < 10)
        ]
        
        st.markdown("##### 🎯 Точка безубыточности:")
        
        col_be1, col_be2, col_be3 = st.columns(3)
        with col_be1:
            st.metric("🚨 Ниже точки безубыточности", len(below_break_even))
        with col_be2:
            st.metric("⚠️ На грани (запас < 10%)", len(close_to_break_even))
        with col_be3:
            avg_safety = df_results["safety_margin_percent"].mean()
            st.metric("📊 Средний запас прочности", f"{avg_safety:.1f}%")

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
        )])
        fig_donut.update_layout(
            showlegend=False, height=350,
            margin=dict(t=20, b=20, l=20, r=20),
            paper_bgcolor='white', plot_bgcolor='white',
            annotations=[dict(text=f'<b>{total_products}</b><br>товаров', x=0.5, y=0.5,
                font=dict(size=20, color='#1F2937'), showarrow=False)]
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with col_g2:
        st.markdown("##### 📊 Распределение маржи по товарам")
        margin_data = df_results["current_margin"].clip(-30, 60)
        fig_hist = px.histogram(x=margin_data, nbins=20, color_discrete_sequence=['#3B82F6'])
        fig_hist.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="Убыток")
        fig_hist.add_vline(x=target_margin, line_dash="dash", line_color="green", annotation_text=f"Цель {target_margin}%")
        fig_hist.update_layout(
            xaxis_title="Маржа, %", yaxis_title="Количество товаров",
            height=350, margin=dict(t=20, b=40, l=40, r=20),
            showlegend=False, plot_bgcolor='white', paper_bgcolor='white'
        )
        fig_hist.update_xaxes(gridcolor='#F3F4F6', zerolinecolor='#E5E7EB')
        fig_hist.update_yaxes(gridcolor='#F3F4F6')
        st.plotly_chart(fig_hist, use_container_width=True)

    col_g3, col_g4 = st.columns(2)
    
    with col_g3:
        st.markdown("##### 🏆 ТОП-10 по прибыли с 1 продажи")
        top_profitable = df_results.nlargest(10, "current_profit")[["article", "current_profit"]].copy()
        top_profitable["article_short"] = top_profitable["article"].astype(str).str[:25]
        top_profitable = top_profitable.sort_values("current_profit", ascending=True)
        
        fig_top = go.Figure(go.Bar(
            x=top_profitable["current_profit"],
            y=top_profitable["article_short"],
            orientation='h',
            marker=dict(color=top_profitable["current_profit"], colorscale='Greens', showscale=False),
            text=top_profitable["current_profit"].apply(lambda x: f"{x:.0f} ₽"),
            textposition='outside'
        ))
        fig_top.update_layout(
            xaxis_title="Прибыль с 1 продажи, ₽", yaxis_title="",
            height=400, margin=dict(t=20, b=40, l=180, r=80),
            plot_bgcolor='white', paper_bgcolor='white',
            yaxis=dict(type='category', tickfont=dict(size=11))
        )
        fig_top.update_xaxes(gridcolor='#F3F4F6')
        st.plotly_chart(fig_top, use_container_width=True)

    with col_g4:
        st.markdown("##### 🚨 ТОП-10 самых убыточных")
        if len(losing_df) > 0:
            top_losing = losing_df.nsmallest(10, "current_profit")[["article", "current_profit"]].copy()
            top_losing["article_short"] = top_losing["article"].astype(str).str[:25]
            top_losing["loss"] = top_losing["current_profit"].abs()
            top_losing = top_losing.sort_values("loss", ascending=True)
            
            fig_loss = go.Figure(go.Bar(
                x=top_losing["loss"],
                y=top_losing["article_short"],
                orientation='h',
                marker=dict(color=top_losing["loss"], colorscale='Reds', showscale=False),
                text=top_losing["current_profit"].apply(lambda x: f"{x:.0f} ₽"),
                textposition='outside'
            ))
            fig_loss.update_layout(
                xaxis_title="Убыток с 1 продажи, ₽", yaxis_title="",
                height=400, margin=dict(t=20, b=40, l=180, r=80),
                plot_bgcolor='white', paper_bgcolor='white',
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
        expenses_data, values="Сумма", names="Категория",
        color_discrete_sequence=['#3B82F6', '#8B5CF6', '#EC4899', '#F59E0B', '#EF4444', '#10B981']
    )
    fig_expenses.update_traces(textinfo='label+percent', textfont=dict(size=13))
    fig_expenses.update_layout(
        height=400, margin=dict(t=20, b=20, l=20, r=20),
        plot_bgcolor='white', paper_bgcolor='white',
        showlegend=True, legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05)
    )
    st.plotly_chart(fig_expenses, use_container_width=True)

    if len(losing_df) > 0:
        total_loss_per_unit = abs(losing_df["current_profit"].sum())
        st.markdown(f"""
        <div class="loss-box">
            <h4>🚨 Внимание! У тебя {len(losing_df)} убыточных товаров!</h4>
            <b>Суммарный убыток с продажи по 1 шт каждого: <span style='color:#DC2626; font-size:20px;'>− {total_loss_per_unit:,.0f} ₽</span></b><br>
            <i>Если продашь по 100 шт каждого = потеряешь {-total_loss_per_unit * 100:,.0f} ₽!</i>
        </div>
        """, unsafe_allow_html=True)

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
        <h4 style='margin-top:0;'>💰 Потенциал роста прибыли</h4>
        <div style='font-size: 28px; font-weight: 700; color: #059669;'>
            +{potential:,.0f} ₽
        </div>
        <div style='color: #6B7280; margin-top: 5px;'>
            суммарно если применить все рекомендованные цены
        </div>
    </div>
    """, unsafe_allow_html=True)


# ============ ВКЛАДКА 2: УПРАВЛЕНИЕ ЦЕНАМИ ============

with tab_products:
    st.header("💰 Управление ценами")

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

    if len(filtered) > 0:
        display_df = filtered[[
            "article", "subject", "model",
            "cost_price", "commission_percent", "logistics",
            "current_price", "current_discount", "current_price_final", "current_margin",
            "break_even_price", "safety_margin_rub",
            "recommended_price", "recommended_discount", "recommended_final", "recommended_margin",
            "discount_change", "profit_diff"
        ]].copy()

        if force_model: display_df = display_df.drop(columns=["model"])

        cols = ["Артикул", "Категория"]
        if not force_model: cols.append("Модель")
        cols.extend([
            "Себест.", "Ком.%", "Лог.₽",
            "Цена до ск.", "Скид.%", "Покупателю", "Маржа %",
            "🎯 Мин. цена", "🛡️ Запас ₽",
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
        
        def highlight_safety(val):
            try:
                v = float(val)
                if v < 0: return 'background-color: #FEE2E2; color: #991B1B; font-weight: 600'
                elif v < 100: return 'background-color: #FEF3C7; color: #92400E; font-weight: 600'
                else: return 'background-color: #D1FAE5; color: #065F46; font-weight: 600'
            except: return ''

        styled_df = display_df_page.style.map(
            highlight_margins, subset=['Маржа %', 'Реком. маржа %']
        ).map(highlight_safety, subset=['🛡️ Запас ₽']).format(precision=1)

        st.dataframe(styled_df, use_container_width=True, height=600)
    else:
        st.info("Нет товаров в этой категории")

    # ЭКСПОРТ
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
            "📊 Excel",
            data=output_excel.getvalue(),
            file_name=f"wb_prices_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    with col_exp2:
        csv_data = df_results.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            "📄 CSV",
            data=csv_data,
            file_name=f"wb_prices_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    with col_exp3:
        json_export = {
            "export_date": datetime.now().isoformat(),
            "total_products": len(df_results),
            "products": df_results.to_dict(orient="records"),
        }
        json_data = json.dumps(json_export, ensure_ascii=False, indent=2, default=str).encode('utf-8')
        st.download_button(
            "🔧 JSON",
            data=json_data,
            file_name=f"wb_prices_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",
            use_container_width=True
        )

    # ОБНОВЛЕНИЕ ЦЕН С ВАЛИДАЦИЕЙ
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
        critical_errors, warnings, info = validate_price_updates(to_update)
        
        st.error(f"## ⚠️ ПОДТВЕРЖДЕНИЕ ОБНОВЛЕНИЯ ЦЕН")
        
        total = len(to_update)
        
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        with col_stat1: st.metric("📊 Всего", total)
        with col_stat2: st.metric("🚨 Критичных", len(critical_errors))
        with col_stat3: st.metric("⚠️ Предупреждений", len(warnings))
        with col_stat4: st.metric("💡 Заметок", len(info))
        
        if critical_errors:
            st.markdown(f"""
            <div class="loss-box">
                <h4>🚨 КРИТИЧНЫЕ ПРОБЛЕМЫ! ({len(critical_errors)} шт)</h4>
                <b>Эти товары будут УБЫТОЧНЫМИ после обновления!</b>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander(f"🔴 Показать проблемы ({len(critical_errors)} шт)", expanded=True):
                for err in critical_errors[:20]:
                    st.error(f"**{err['article']}** — {err['message']}")
                if len(critical_errors) > 20:
                    st.caption(f"...и ещё {len(critical_errors) - 20}")
        
        if warnings:
            with st.expander(f"⚠️ Предупреждения ({len(warnings)})", expanded=False):
                for warn in warnings[:30]:
                    st.warning(f"**{warn['article']}** — {warn['message']}")
        
        if info:
            with st.expander(f"💡 Заметки ({len(info)})", expanded=False):
                for i in info[:30]:
                    st.info(f"**{i['article']}** — {i['message']}")
        
        if not critical_errors and not warnings:
            st.success("✅ Всё проверено — проблем не обнаружено!")
        
        st.markdown("---")
        st.markdown("### 📋 Что будет изменено:")
        
        preview = to_update[[
            "article", "subject", "current_price", "recommended_price",
            "current_discount", "recommended_discount", "current_margin", "recommended_margin"
        ]].copy()
        preview.columns = ["Артикул", "Категория", "Было цена", "Станет цена", "Было скид%", "Станет скид%", "Была маржа", "Станет маржа"]
        st.dataframe(preview, use_container_width=True, height=300)

        st.markdown("---")
        
        if critical_errors:
            safe_update = to_update[~to_update["article"].isin([e["article"] for e in critical_errors])]
            
            col_conf1, col_conf2, col_conf3 = st.columns(3)
            
            with col_conf1:
                if st.button(f"✅ Только безопасные ({len(safe_update)})", type="primary", use_container_width=True):
                    price_updates = [{"nmID": int(r["nm_id"]), "price": int(r["recommended_price"]), "discount": int(r["recommended_discount"])} for _, r in safe_update.iterrows()]
                    with st.spinner(f"💰 Обновляем {len(price_updates)} товаров..."):
                        result = update_prices(api_key, price_updates)
                    st.session_state["update_result"] = result
                    st.session_state["show_confirm"] = None
                    st.session_state["to_update_data"] = None
                    st.rerun()
            
            with col_conf2:
                if st.button("🚨 Обновить ВСЕ, включая убыточные", use_container_width=True):
                    price_updates = [{"nmID": int(r["nm_id"]), "price": int(r["recommended_price"]), "discount": int(r["recommended_discount"])} for _, r in to_update.iterrows()]
                    with st.spinner(f"💰 Обновляем {len(price_updates)} товаров..."):
                        result = update_prices(api_key, price_updates)
                    st.session_state["update_result"] = result
                    st.session_state["show_confirm"] = None
                    st.session_state["to_update_data"] = None
                    st.rerun()
            
            with col_conf3:
                if st.button("❌ Отмена", use_container_width=True):
                    st.session_state["show_confirm"] = None
                    st.session_state["to_update_data"] = None
                    st.rerun()
        else:
            col_conf1, col_conf2 = st.columns(2)
            with col_conf1:
                if st.button(f"✅ ДА, обновить {total} товаров", type="primary", use_container_width=True):
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


# ============ ВКЛАДКА 3: АКЦИИ WB ============

with tab_actions:
    st.header("🎉 Калькулятор акций WB")
    
    st.markdown("""
    <div class="info-box">
        <b>💡 Как это работает:</b><br>
        1. Получи от WB Excel-файл акции<br>
        2. Загрузи его сюда<br>
        3. Мы посчитаем прибыль по КАЖДОМУ товару с точной скидкой WB<br>
        4. Покажем какие товары ВЫГОДНЫ, а какие УБЫТОЧНЫ<br>
        5. Сформируем готовый файл-исключение для WB
    </div>
    """, unsafe_allow_html=True)
    
    action_file = st.file_uploader(
        "📎 Загрузи файл акции от WB (Excel)",
        type=["xlsx", "xls", "csv"],
        key="action_file_uploader"
    )
    
    if action_file:
        with st.spinner("📊 Анализируем файл акции..."):
            action_df, error = parse_action_file(action_file)
        
        if error:
            st.error(f"❌ {error}")
        elif action_df is None or action_df.empty:
            st.warning("⚠️ Не удалось прочитать данные из файла")
        else:
            st.session_state["action_data"] = action_df
            action_name = action_df.iloc[0].get("action_name", "Акция WB")
            st.success(f"✅ Загружено {len(action_df)} товаров из акции '{action_name}'")
    
    if st.session_state.get("action_data") is not None:
        action_df = st.session_state["action_data"]
        action_name = action_df.iloc[0].get("action_name", "Акция WB")
        
        st.markdown("---")
        st.subheader(f"📊 Анализ акции: '{action_name}'")
        
        active_df = action_df[
            ~action_df["status"].str.lower().str.contains("не участвует", na=False)
        ].copy()
        
        cost_prices = st.session_state.get("cost_prices", {})
        
        analysis_results = []
        no_data_articles = []
        
        for _, action_row in active_df.iterrows():
            article = action_row["article"].strip()
            
            action_price = action_row["action_price"]
            if action_price <= 0 and action_row["action_discount"] > 0 and action_row["current_price"] > 0:
                action_price = action_row["current_price"] * (1 - action_row["action_discount"] / 100)
            
            if action_price <= 0:
                continue
            
            product_in_base = df_results[df_results["article"] == article]
            
            if product_in_base.empty:
                if article in cost_prices:
                    cost = cost_prices[article]
                    commission = get_commission_by_category(action_row.get("subject", ""), force_model or "FBS")
                    logistics = estimate_logistics(0, force_model or "FBS")
                    
                    current = calculate_current_profit(
                        action_price, commission, logistics, cost,
                        buyout_rate, tax_rate, acceptance_fee,
                        return_processing_fee, damage_rate
                    )
                    
                    analysis_results.append({
                        "article": article,
                        "nm_id": action_row.get("nm_id", 0),
                        "name": action_row.get("name", ""),
                        "subject": action_row.get("subject", ""),
                        "current_price": action_row["current_price"],
                        "action_price": action_price,
                        "action_discount": action_row["action_discount"],
                        "cost_price": cost,
                        "commission_percent": commission,
                        "profit": current["profit"],
                        "margin": current["margin"],
                        "turnover": action_row.get("turnover", 0),
                        "stock_wb": action_row.get("stock_wb", 0),
                        "stock_seller": action_row.get("stock_seller", 0),
                        "days_on_site": action_row.get("days_on_site", 0),
                        "in_action": action_row.get("in_action", False),
                    })
                else:
                    no_data_articles.append(article)
            else:
                p = product_in_base.iloc[0]
                cost = p["cost_price"]
                commission = p["commission_percent"]
                logistics = p["logistics"]
                
                current = calculate_current_profit(
                    action_price, commission, logistics, cost,
                    buyout_rate, tax_rate, acceptance_fee,
                    return_processing_fee, damage_rate
                )
                
                analysis_results.append({
                    "article": article,
                    "nm_id": p["nm_id"],
                    "name": action_row.get("name", p.get("title", "")),
                    "subject": p["subject"],
                    "current_price": action_row["current_price"],
                    "action_price": action_price,
                    "action_discount": action_row["action_discount"],
                    "cost_price": cost,
                    "commission_percent": commission,
                    "profit": current["profit"],
                    "margin": current["margin"],
                    "turnover": action_row.get("turnover", 0),
                    "stock_wb": action_row.get("stock_wb", 0),
                    "stock_seller": action_row.get("stock_seller", 0),
                    "days_on_site": action_row.get("days_on_site", 0),
                    "in_action": action_row.get("in_action", False),
                })
        
        if analysis_results:
            analysis_df = pd.DataFrame(analysis_results)
            
            profitable_df = analysis_df[analysis_df["margin"] >= 5].copy()
            marginal_df = analysis_df[(analysis_df["margin"] >= 0) & (analysis_df["margin"] < 5)].copy()
            unprofitable_df = analysis_df[analysis_df["margin"] < 0].copy()
            
            total_profit = profitable_df["profit"].sum() if len(profitable_df) > 0 else 0
            total_loss = unprofitable_df["profit"].sum() if len(unprofitable_df) > 0 else 0
            
            col_a1, col_a2, col_a3, col_a4 = st.columns(4)
            with col_a1:
                st.metric("📊 Всего в акции", len(analysis_df))
            with col_a2:
                st.metric("🟢 Выгодно", len(profitable_df), help="Маржа > 5%")
            with col_a3:
                st.metric("🟡 Сомнительно", len(marginal_df), help="Маржа 0-5%")
            with col_a4:
                st.metric("🔴 Убыточно", len(unprofitable_df), help="Маржа < 0")
            
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                st.markdown(f"""
                <div class="success-box">
                    <h4 style='margin-top:0;'>💰 Ожидаемая прибыль</h4>
                    <div style='font-size: 28px; font-weight: 700; color: #059669;'>
                        +{total_profit:,.0f} ₽
                    </div>
                    <div style='color: #6B7280; margin-top: 5px;'>
                        если продать по 1 шт каждого выгодного товара
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_e2:
                if len(unprofitable_df) > 0:
                    st.markdown(f"""
                    <div class="loss-box">
                        <h4 style='margin-top:0;'>🚨 Потенциальные убытки</h4>
                        <div style='font-size: 28px; font-weight: 700; color: #DC2626;'>
                            {total_loss:,.0f} ₽
                        </div>
                        <div style='color: #6B7280; margin-top: 5px;'>
                            если участвовать во всех убыточных товарах
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                    <div class="success-box">
                        <h4 style='margin-top:0;'>✅ Убытков нет!</h4>
                        <div style='color: #6B7280;'>
                            Все товары выгодны для участия
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            if no_data_articles:
                with st.expander(f"⚠️ Нет себестоимости для {len(no_data_articles)} товаров"):
                    st.warning("""
                    Эти товары из акции WB не найдены в твоём Excel-файле себестоимости.
                    Добавь их в файл, чтобы получить точный расчёт.
                    """)
                    st.write(", ".join(no_data_articles[:50]))
                    if len(no_data_articles) > 50:
                        st.caption(f"...и ещё {len(no_data_articles) - 50}")
                    
                    no_data_df = pd.DataFrame({"Артикул": no_data_articles})
                    csv_no_data = no_data_df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        "📥 Скачать список для добавления в Excel",
                        csv_no_data,
                        file_name=f"no_data_articles_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
            
            st.markdown("---")
            
            if len(unprofitable_df) > 0:
                st.markdown("### 🚨 УБЫТОЧНЫЕ товары — НЕ участвовать!")
                
                unprofitable_display = unprofitable_df[[
                    "article", "name", "action_price", "action_discount", "profit", "margin"
                ]].copy()
                unprofitable_display.columns = ["Артикул", "Название", "Цена в акции", "Скидка %", "Убыток ₽", "Маржа %"]
                unprofitable_display = unprofitable_display.sort_values("Убыток ₽")
                
                st.dataframe(unprofitable_display, use_container_width=True, height=300)
            
            if len(profitable_df) > 0:
                st.markdown("### 🟢 ВЫГОДНЫЕ товары — можно участвовать!")
                
                profitable_display = profitable_df[[
                    "article", "name", "action_price", "action_discount", "profit", "margin", "turnover"
                ]].copy()
                profitable_display.columns = ["Артикул", "Название", "Цена в акции", "Скидка %", "Прибыль ₽", "Маржа %", "Оборач."]
                profitable_display = profitable_display.sort_values("Прибыль ₽", ascending=False)
                
                st.dataframe(profitable_display, use_container_width=True, height=400)
            
            st.markdown("---")
            st.markdown("### 📥 Экспорт результатов")
            
            col_ex1, col_ex2, col_ex3 = st.columns(3)
            
            with col_ex1:
                output_action = io.BytesIO()
                with pd.ExcelWriter(output_action, engine="openpyxl") as writer:
                    analysis_df.to_excel(writer, sheet_name="Все товары", index=False)
                    if len(profitable_df) > 0:
                        profitable_df.to_excel(writer, sheet_name="Выгодные", index=False)
                    if len(marginal_df) > 0:
                        marginal_df.to_excel(writer, sheet_name="Сомнительные", index=False)
                    if len(unprofitable_df) > 0:
                        unprofitable_df.to_excel(writer, sheet_name="Убыточные", index=False)
                
                st.download_button(
                    "📊 Полный отчёт Excel",
                    data=output_action.getvalue(),
                    file_name=f"action_analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            
            with col_ex2:
                if len(profitable_df) > 0:
                    prof_excel = io.BytesIO()
                    with pd.ExcelWriter(prof_excel, engine="openpyxl") as writer:
                        profitable_df.to_excel(writer, sheet_name="Выгодные для акции", index=False)
                    
                    st.download_button(
                        "🟢 Только выгодные",
                        data=prof_excel.getvalue(),
                        file_name=f"profitable_action_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
            
            with col_ex3:
                if len(unprofitable_df) > 0:
                    exclusions_df = unprofitable_df[["article", "nm_id"]].copy()
                    exclusions_df.columns = ["Артикул поставщика", "Артикул WB"]
                    
                    excl_excel = io.BytesIO()
                    with pd.ExcelWriter(excl_excel, engine="openpyxl") as writer:
                        exclusions_df.to_excel(writer, sheet_name="Исключить из акции", index=False)
                    
                    st.download_button(
                        "🚫 Исключения для WB",
                        data=excl_excel.getvalue(),
                        file_name=f"exclusions_wb_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        help="Список товаров которые НЕ надо включать в акцию"
                    )
        else:
            st.warning("⚠️ Нет товаров для анализа. Проверь файл акции.")
    
    else:
        st.info("👆 Загрузи файл акции от WB чтобы начать анализ")
