import streamlit as st
import pandas as pd
import io
import json
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
)


st.set_page_config(
    page_title="Калькулятор цен WB",
    page_icon="🧮",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stMetric { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    .loss-box { background-color: #ffeaea; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4b4b; margin-bottom: 10px; }
    .cat-box { background-color: #eaf4ff; padding: 15px; border-radius: 10px; border-left: 5px solid #4b8bff; margin-bottom: 10px; }
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
                        st.caption("💡 Можешь добавить колонку 'Модель' в Excel для точности")
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

    st.markdown("---")

    st.subheader("🎯 Параметры расчёта")
    target_margin = st.slider("Целевая маржа, %", 10, 50, 20, 1)
    buyout_percent = st.slider("% выкупа", 30, 100, 90, 1)
    buyout_rate = buyout_percent / 100
    
    acceptance_fee = st.number_input(
        "Платная приёмка (₽ на ед.)", 
        min_value=0, max_value=500, value=0, step=5,
        help="Средняя стоимость платной приёмки на склад WB"
    )

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
    tax_display = f"{tax_rate*100:.1f}%"

    st.markdown("---")

    st.subheader("🎁 Скидка")
    discount_mode = st.radio("Как менять скидку?", ["🛡️ Плавно", "🎯 Установить максимум", "🔒 Не менять"], index=0)
    if discount_mode == "🎯 Установить максимум":
        max_discount, max_discount_change, keep_discount = st.slider("Макс. скидка, %", 0, 90, 30, 5), 100, False
    elif discount_mode == "🛡️ Плавно":
        max_discount = st.slider("Целевая скидка, %", 0, 90, 30, 5)
        max_discount_change = st.slider("Макс. изменение за раз, %", 1, 20, 5, 1)
        keep_discount = False
    else:
        max_discount, max_discount_change, keep_discount = 100, 0, True

    st.markdown("---")
    if st.button("🗑️ Очистить кеш и данные", use_container_width=True):
        st.cache_data.clear()
        st.session_state["calc_loaded"] = False
        st.session_state["df_results"] = None
        st.session_state["show_confirm"] = None
        st.session_state["to_update_data"] = None
        st.session_state["skipped_no_stock"] = 0
        st.session_state["current_page"] = 1
        st.rerun()


# ============ ГЛАВНАЯ ============

st.title("🧮 Умный калькулятор цен WB")

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
    st.caption("💡 Колонка 'Модель' опциональна — можно указать FBS/FBO/DBS для точного расчёта")
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
    st.info("⏱️ Загрузка 1-3 минуты. Данные кешируются.")

if load_button:
    st.session_state["calc_loaded"] = True
    st.session_state["df_results"] = None
    st.session_state["current_page"] = 1

if not st.session_state["calc_loaded"]:
    st.stop()


# ============ РАСЧЁТ ============

if st.session_state["df_results"] is None:
    with st.spinner("📥 Загружаем карточки товаров..."):
        cards_df = get_all_cards(api_key)
    if cards_df.empty: st.error("❌ Ошибка"); st.stop()

    with st.spinner("💰 Загружаем цены..."):
        prices_df = get_prices(api_key)
    if prices_df.empty: st.error("❌ Ошибка"); st.stop()

    with st.spinner("📊 Загружаем комиссии..."):
        commissions_df = get_commissions(api_key)

    with st.spinner("📦 Загружаем остатки по складам..."):
        stocks_df = get_stocks_by_warehouse(api_key)

    merged = cards_df.merge(prices_df[["nm_id", "price", "discount", "discounted_price"]], on="nm_id", how="left")
    merged["cost_price"] = merged["article"].astype(str).str.strip().map(st.session_state["cost_prices"]).fillna(0)

    merged["available_models"] = merged["article"].apply(lambda x: get_available_models(x, stocks_df))

    # ==== УМНОЕ ОПРЕДЕЛЕНИЕ МОДЕЛИ ====
    saved_models = st.session_state.get("cost_models", {})
    
    def determine_final_model(row):
        """
        Приоритет:
        1. Модель из Excel (если указана)
        2. Модель из WB API (если есть остатки)
        3. Модель по умолчанию (из настроек)
        """
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
    
    # Определяем доступность
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
            row["logistics"], row["cost_price"], buyout_rate, tax_rate, acceptance_fee
        )

        recommended = calculate_recommended_price(
            row["cost_price"], row["commission_percent"], row["logistics"], target_margin,
            row["discount"] or 0, max_discount, max_discount_change, keep_discount, 
            buyout_rate, tax_rate, acceptance_fee
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
        st.warning("⚠️ Нет товаров для расчёта. Проверь себестоимость и цены.")
        st.session_state["calc_loaded"] = False
        st.stop()

    st.session_state["df_results"] = pd.DataFrame(results)
    st.session_state["skipped_no_stock"] = skipped_no_stock


df_results = st.session_state["df_results"]


# ============ СВОДКА И АНАЛИТИКА ============

st.markdown("---")
st.header("📊 Аналитика и сводка")

total_products = len(df_results)
losing_df = df_results[df_results["category"] == "убыточные"]
below_target = df_results[df_results["category"] == "ниже цели"]
ok = df_results[df_results["category"] == "в норме"]
potential = df_results["profit_diff"].sum()

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
with col_m1: st.metric("📦 Всего", total_products)
with col_m2: st.metric("🔴 Убыточные", len(losing_df))
with col_m3: st.metric("🟡 Ниже цели", len(below_target))
with col_m4: st.metric("🟢 В норме", len(ok))

# Источники определения модели
if force_model and "model_source" in df_results.columns:
    excel_source = len(df_results[df_results["model_source"] == "excel"])
    wb_source = len(df_results[df_results["model_source"] == "wb_stocks"])
    default_source = len(df_results[df_results["model_source"] == "default"])
    
    if excel_source > 0 or wb_source > 0 or default_source > 0:
        with st.expander("🔍 Как определилась модель для товаров"):
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                st.metric("📋 Из Excel", excel_source, help="Модель указана в файле себестоимости")
            with col_s2:
                st.metric("📦 Из WB API", wb_source, help="Модель определена по остаткам")
            with col_s3:
                st.metric("⚙️ По умолчанию", default_source, help="Использована модель из настроек")
            
            if default_source > 0:
                st.warning(f"""
                ⚠️ Для **{default_source} товаров** модель определена по настройке.
                
                Для точности — добавь в Excel колонку **"Модель"** с указанием FBS/FBO/DBS.
                """)

# Убыточные товары
if len(losing_df) > 0:
    total_loss_per_unit = abs(losing_df["current_profit"].sum())
    
    st.markdown(f"""
    <div class="loss-box">
        <h4>🚨 Внимание! У тебя {len(losing_df)} убыточных товаров!</h4>
        <b>Суммарный убыток с продажи 1 шт каждого: <span style='color:red;'>− {total_loss_per_unit:,.0f} ₽</span></b><br>
        <i>(Если продать по 100 шт каждого = потеряешь {-total_loss_per_unit * 100:,.0f} ₽!)</i>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("**Топ-3 самых убыточных товара:**")
    worst = losing_df.sort_values("current_profit").head(3)
    for _, row in worst.iterrows():
        st.write(f"🩸 `{row['article']}` — убыток **{row['current_profit']:.0f} ₽** с каждой продажи (Маржа: {row['current_margin']:.1f}%)")

# Анализ по категориям
with st.expander("📁 Анализ по категориям (какие ниши тянут вниз)"):
    cat_analysis = df_results.groupby("subject").agg(
        Товаров=("article", "count"),
        Средняя_маржа=("current_margin", "mean"),
        Убыточных=("category", lambda x: (x == "убыточные").sum())
    ).reset_index()
    
    cat_analysis = cat_analysis.sort_values("Средняя_маржа")
    cat_analysis["Средняя_маржа"] = cat_analysis["Средняя_маржа"].round(1)
    
    def color_cat_margin(val):
        color = '#ffcccc' if val < 0 else '#fff4cc' if val < target_margin else '#ccffcc'
        return f'background-color: {color}; color: black'

    st.dataframe(cat_analysis.style.map(color_cat_margin, subset=['Средняя_маржа']), use_container_width=True)

st.success(f"💰 **Потенциал роста прибыли:** `+{potential:,.0f} ₽` (если применить все рекомендованные цены)")


# ============ ФИЛЬТРЫ И ПАГИНАЦИЯ ============

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


# ============ ТАБЛИЦА С ЦВЕТОМ ============

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
            if v < 0: return 'background-color: #ffcccc; color: black'
            elif v < target_margin - 2: return 'background-color: #fff4cc; color: black'
            else: return 'background-color: #ccffcc; color: black'
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
st.caption("Скачай отчёт в удобном формате")

col_exp1, col_exp2, col_exp3, col_exp4 = st.columns(4)

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
        use_container_width=True,
        help="Excel файл с 5 листами"
    )

with col_exp2:
    csv_data = df_results.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📄 CSV",
        data=csv_data,
        file_name=f"wb_prices_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True,
        help="CSV для импорта в Google Sheets, 1С"
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
        use_container_width=True,
        help="JSON для API интеграций"
    )

with col_exp4:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.enums import TA_CENTER
        
        try:
            pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
            pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
            base_font = 'DejaVuSans'
            bold_font = 'DejaVuSans-Bold'
        except:
            base_font = 'Helvetica'
            bold_font = 'Helvetica-Bold'
        
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            pdf_buffer, pagesize=landscape(A4),
            rightMargin=1*cm, leftMargin=1*cm,
            topMargin=1*cm, bottomMargin=1*cm
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle('CustomTitle', parent=styles['Title'],
            fontName=bold_font, fontSize=22, textColor=colors.HexColor('#1e40af'),
            alignment=TA_CENTER, spaceAfter=20)
        h2_style = ParagraphStyle('CustomH2', parent=styles['Heading2'],
            fontName=bold_font, fontSize=14, textColor=colors.HexColor('#374151'),
            spaceAfter=10, spaceBefore=15)
        normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'],
            fontName=base_font, fontSize=10, spaceAfter=6)
        
        elements.append(Paragraph("Отчёт по анализу цен Wildberries", title_style))
        elements.append(Paragraph(f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}", normal_style))
        elements.append(Spacer(1, 0.5*cm))
        
        elements.append(Paragraph("Параметры расчёта", h2_style))
        params_data = [
            ["Параметр", "Значение"],
            ["Модель работы", force_model if force_model else "Смешанная"],
            ["Целевая маржа", f"{target_margin}%"],
            ["% выкупа", f"{buyout_percent}%"],
            ["Налог", tax_mode],
            ["Платная приёмка", f"{acceptance_fee} ₽" if acceptance_fee > 0 else "не учитывается"],
        ]
        params_table = Table(params_data, colWidths=[6*cm, 8*cm])
        params_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3B82F6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), bold_font),
            ('FONTNAME', (0, 1), (-1, -1), base_font),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(params_table)
        elements.append(Spacer(1, 0.5*cm))
        
        elements.append(Paragraph("Общая статистика", h2_style))
        stats_data = [
            ["Показатель", "Значение"],
            ["Всего товаров", str(total_products)],
            ["Убыточных", str(len(losing_df))],
            ["Ниже цели", str(len(below_target))],
            ["В норме", str(len(ok))],
            ["Потенциал прибыли", f"+{potential:,.0f} ₽".replace(",", " ")],
        ]
        stats_table = Table(stats_data, colWidths=[10*cm, 6*cm])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10B981')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), bold_font),
            ('FONTNAME', (0, 1), (-1, -1), base_font),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(stats_table)
        
        if len(losing_df) > 0:
            elements.append(PageBreak())
            elements.append(Paragraph(f"Убыточные товары ({len(losing_df)} шт)", h2_style))
            losing_data = [["Артикул", "Категория", "Цена", "Маржа", "Убыток", "Реком.", "Реком.маржа"]]
            for _, row in losing_df.head(30).iterrows():
                losing_data.append([
                    str(row["article"])[:20], str(row["subject"])[:20],
                    f"{row['current_price_final']:.0f}", f"{row['current_margin']:.1f}%",
                    f"{row['current_profit']:.0f}", f"{row['recommended_final']:.0f}",
                    f"{row['recommended_margin']:.1f}%",
                ])
            losing_table = Table(losing_data, colWidths=[3.5*cm, 3.5*cm, 2.5*cm, 2.5*cm, 2.5*cm, 3*cm, 3*cm])
            losing_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#EF4444')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), bold_font),
                ('FONTNAME', (0, 1), (-1, -1), base_font),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('PADDING', (0, 0), (-1, -1), 5),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(losing_table)
        
        elements.append(PageBreak())
        elements.append(Paragraph("Анализ по категориям", h2_style))
        cat_stats = df_results.groupby("subject").agg(
            count=("article", "count"),
            avg_margin=("current_margin", "mean"),
            losing=("category", lambda x: (x == "убыточные").sum())
        ).reset_index().sort_values("avg_margin")
        
        cat_data = [["Категория", "Товаров", "Ср. маржа", "Убыточных"]]
        for _, row in cat_stats.head(20).iterrows():
            cat_data.append([
                str(row["subject"])[:35], str(row["count"]),
                f"{row['avg_margin']:.1f}%", str(row["losing"]),
            ])
        cat_table = Table(cat_data, colWidths=[9*cm, 3*cm, 4*cm, 3*cm])
        cat_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8B5CF6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), bold_font),
            ('FONTNAME', (0, 1), (-1, -1), base_font),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(cat_table)
        
        doc.build(elements)
        pdf_data = pdf_buffer.getvalue()
        pdf_buffer.close()
        
        st.download_button(
            label="📕 PDF-отчёт",
            data=pdf_data,
            file_name=f"wb_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
            mime="application/pdf",
            use_container_width=True,
            help="Красивый PDF-отчёт"
        )
    except ImportError:
        st.button("📕 PDF", disabled=True, use_container_width=True, help="Требуется reportlab в requirements.txt")
    except Exception as e:
        st.button("📕 PDF", disabled=True, use_container_width=True, help=f"Ошибка: {str(e)[:100]}")


with st.expander("💡 Какой формат для чего использовать?"):
    st.markdown("""
    - **📊 Excel** — полный анализ, 5 листов (все, убыточные, ниже цели, в норме, цены для загрузки)
    - **📄 CSV** — импорт в Google Sheets, 1С, МойСклад
    - **🔧 JSON** — программные интеграции, API
    - **📕 PDF** — отчёты для клиентов и презентаций
    
    **Google Sheets:** скачай CSV или Excel → Файл → Импорт (30 секунд)
    """)


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
