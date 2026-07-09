import streamlit as st
import pandas as pd
import io
from datetime import datetime
from calculator import (
    calculate_current_profit,
    calculate_recommended_price,
    get_status,
    get_commission_by_category,
    estimate_logistics,
    TAX_RATE,
)
from wb_api_prices import (
    get_all_cards,
    get_prices,
    get_commissions,
    get_stocks_by_warehouse,
    determine_model,
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
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)


# ============ SESSION STATE ============

if "calc_loaded" not in st.session_state:
    st.session_state["calc_loaded"] = False
if "df_results" not in st.session_state:
    st.session_state["df_results"] = None
if "cost_prices" not in st.session_state:
    st.session_state["cost_prices"] = {}
if "show_confirm" not in st.session_state:
    st.session_state["show_confirm"] = None
if "to_update_data" not in st.session_state:
    st.session_state["to_update_data"] = None
if "update_result" not in st.session_state:
    st.session_state["update_result"] = None


# ============ SIDEBAR ============

with st.sidebar:
    st.title("⚙️ Настройки")

    api_key = st.text_input("🔑 API ключ WB", type="password", key="api_key_input")

    if api_key:
        st.success("✅ Ключ введён")

    st.markdown("---")

    st.subheader("💰 Себестоимость")

    cost_file = st.file_uploader(
        "Excel файл",
        type=["xlsx", "xls", "csv"],
        help="Колонки: Артикул | Себестоимость"
    )

    if cost_file:
        try:
            if cost_file.name.endswith(".csv"):
                cost_df = pd.read_csv(cost_file)
            else:
                cost_df = pd.read_excel(cost_file)

            cols = list(cost_df.columns)
            article_col = None
            cost_col = None

            for c in cols:
                c_lower = str(c).lower().strip()
                if article_col is None and ("артикул" in c_lower or "article" in c_lower or "sku" in c_lower):
                    article_col = c
                if cost_col is None and ("себест" in c_lower or "cost" in c_lower or "закуп" in c_lower):
                    cost_col = c

            if article_col and cost_col:
                new_costs = {}
                for _, row in cost_df.iterrows():
                    art = str(row[article_col]).strip()
                    try:
                        cost = float(str(row[cost_col]).replace(",", ".").replace(" ", ""))
                        if art and art.lower() != "nan" and cost > 0:
                            new_costs[art] = cost
                    except:
                        pass

                if new_costs:
                    st.session_state["cost_prices"] = new_costs
                    st.success(f"✅ Загружено {len(new_costs)} товаров")
            else:
                st.error(f"❌ Не найдены колонки. Доступные: {cols}")
        except Exception as e:
            st.error(f"❌ Ошибка: {e}")

    saved_costs = st.session_state.get("cost_prices", {})
    if saved_costs:
        st.info(f"💾 В памяти: {len(saved_costs)} товаров")

    st.markdown("---")

    # ======== МОДЕЛЬ РАБОТЫ ========
    st.subheader("🏬 Модель работы")

    work_model = st.radio(
        "По какой модели работаешь?",
        [
            "📦 FBS (свой склад)",
            "🏬 FBO (склад WB)",
            "🔀 Смешанная (авто по остаткам)",
        ],
        index=0,
        help="Влияет на расчёт комиссии и логистики"
    )

    if work_model == "📦 FBS (свой склад)":
        force_model = "FBS"
    elif work_model == "🏬 FBO (склад WB)":
        force_model = "FBO"
    else:
        force_model = None

    st.markdown("---")

    # ======== ПАРАМЕТРЫ РАСЧЁТА ========
    st.subheader("🎯 Параметры расчёта")

    target_margin = st.slider(
        "Целевая маржа, %",
        min_value=10,
        max_value=50,
        value=20,
        step=1,
        key="target_margin"
    )

    buyout_percent = st.slider(
        "% выкупа",
        min_value=30,
        max_value=100,
        value=90,
        step=1,
        key="buyout_percent",
        help="Средний процент выкупа твоих товаров. Влияет на расчёт возвратов."
    )

    buyout_rate = buyout_percent / 100

    if buyout_percent < 60:
        st.warning(f"⚠️ Низкий % выкупа ({buyout_percent}%) — много возвратов, цена будет выше")
    elif buyout_percent > 90:
        st.success(f"✅ Высокий % выкупа ({buyout_percent}%)")

    st.markdown("---")

    # ======== СКИДКА ========
    st.subheader("🎁 Управление скидкой")

    discount_mode = st.radio(
        "Как менять скидку?",
        [
            "🛡️ Плавно (безопасно от карантина)",
            "🎯 Установить максимум",
            "🔒 Не менять скидку",
        ],
        index=0,
        help="Резкое изменение скидки может отправить товар в карантин WB"
    )

    if discount_mode == "🎯 Установить максимум":
        max_discount = st.slider(
            "Максимальная скидка, %",
            min_value=0,
            max_value=90,
            value=30,
            step=5
        )
        max_discount_change = 100
        keep_discount = False

    elif discount_mode == "🛡️ Плавно (безопасно от карантина)":
        max_discount = st.slider(
            "Целевая скидка, %",
            min_value=0,
            max_value=90,
            value=30,
            step=5
        )
        max_discount_change = st.slider(
            "Макс. изменение скидки за раз, %",
            min_value=1,
            max_value=20,
            value=5,
            step=1
        )
        keep_discount = False

    else:
        max_discount = 100
        max_discount_change = 0
        keep_discount = True

    st.markdown("---")

    st.info(f"""
    📊 **Параметры:**
    - Модель: **{force_model if force_model else "Авто"}**
    - Маржа: **{target_margin}%**
    - % выкупа: **{buyout_percent}%**
    - Налог: УСН 6%
    - Эквайринг: 1.5%
    - Реклама: не учитывается
    - Хранение: не учитывается
    
    💡 Маржа от **цены покупателя**
    """)

    st.markdown("---")

    if st.button("🗑️ Очистить кеш и данные", use_container_width=True):
        st.cache_data.clear()
        st.session_state["calc_loaded"] = False
        st.session_state["df_results"] = None
        st.session_state["show_confirm"] = None
        st.session_state["to_update_data"] = None
        st.rerun()


# ============ ГЛАВНАЯ ============

st.title("🧮 Умный калькулятор цен WB")
st.caption("Автоматический расчёт оптимальных цен с учётом всех расходов")


if not api_key:
    st.warning("👈 Введи API ключ в боковой панели")
    st.stop()

cost_prices = st.session_state.get("cost_prices", {})

if not cost_prices:
    st.warning("👈 Загрузи файл с себестоимостью в боковой панели")

    st.markdown("### 📋 Пример файла себестоимости:")

    example_df = pd.DataFrame({
        "Артикул": ["A123-BLK", "B456-RED", "C789-BLU"],
        "Себестоимость": [500, 400, 450]
    })
    st.dataframe(example_df, use_container_width=False)

    st.stop()


if st.session_state.get("update_result"):
    result = st.session_state["update_result"]
    st.success(f"✅ Отправлено на WB: **{result['success']}** товаров")
    if result.get("errors"):
        st.error("Ошибки при обновлении:")
        for err in result["errors"]:
            st.text(err)
    st.info("💡 Цены появятся на WB через 5-15 минут")

    if st.button("Скрыть уведомление"):
        st.session_state["update_result"] = None
        st.rerun()

    st.markdown("---")


with st.expander("ℹ️ Как правильно понимать цены, скидки и параметры"):
    st.markdown("""
    ### 📊 3 цены в WB:
    
    | Название в WB | В калькуляторе | Что это |
    |--------------|----------------|---------|
    | Цена продавца до скидки | **Цена до скидки** | Ты вводишь в кабинет |
    | Скидка продавца, % | **% скидки** | Процент скидки |
    | Цена со скидкой | **Цена покупателя** | Что видит покупатель |
    
    ### 💰 От какой цены маржа?
    
    Маржа считается от **Цены покупателя** — реальных денег.
    
    ### 🏬 Модели работы в WB:
    
    - **FBO** — товар на складе WB, WB доставляет
    - **FBS** — товар на твоём складе, WB доставляет (Маркетплейс)
    - **DBS** — товар на твоём складе, ты доставляешь (Витрина)
    - **DBW** — курьер WB (Экспресс)
    
    ⚠️ У каждой модели **своя комиссия**! Мы автоматически берём правильную.
    
    ### 🎯 Процент выкупа:
    
    - **90%+** — отличный, низкие возвраты
    - **70-90%** — средний
    - **50-70%** — много возвратов
    - **<50%** — цена должна быть выше
    """)


col1, col2 = st.columns([1, 3])
with col1:
    load_button = st.button(
        "🚀 Загрузить и рассчитать",
        type="primary",
        use_container_width=True
    )

with col2:
    st.info("⏱️ Загрузка занимает 1-3 минуты. Данные кешируются.")


if load_button:
    st.session_state["calc_loaded"] = True
    st.session_state["df_results"] = None

if not st.session_state["calc_loaded"]:
    st.stop()


# ============ РАСЧЁТ ============

if st.session_state["df_results"] is None:
    with st.spinner("📥 Загружаем карточки товаров..."):
        cards_df = get_all_cards(api_key)

    if cards_df.empty:
        st.error("❌ Не удалось получить карточки товаров")
        st.session_state["calc_loaded"] = False
        st.stop()

    st.success(f"✅ Загружено карточек: {len(cards_df)}")

    with st.spinner("💰 Загружаем текущие цены..."):
        prices_df = get_prices(api_key)

    if prices_df.empty:
        st.error("❌ Не удалось получить цены")
        st.session_state["calc_loaded"] = False
        st.stop()

    st.success(f"✅ Загружено цен: {len(prices_df)}")

    with st.spinner("📊 Загружаем комиссии по категориям..."):
        commissions_df = get_commissions(api_key)

    stocks_df = pd.DataFrame()
    if force_model is None:
        with st.spinner("📦 Определяем модели по остаткам..."):
            stocks_df = get_stocks_by_warehouse(api_key)

    merged = cards_df.merge(
        prices_df[["nm_id", "price", "discount", "discounted_price"]],
        on="nm_id",
        how="left"
    )

    merged["cost_price"] = merged["article"].astype(str).str.strip().map(cost_prices).fillna(0)

    if force_model:
        merged["model"] = force_model
    else:
        merged["model"] = merged["article"].apply(lambda x: determine_model(x, stocks_df))

    if not commissions_df.empty:
        merged = merged.merge(
            commissions_df[["subject_id", "commission_fbo", "commission_fbs", "commission_dbs", "commission_dbw"]],
            on="subject_id",
            how="left"
        )
        merged["commission_percent"] = merged.apply(
            lambda row: (
                row["commission_fbs"] if row["model"] == "FBS" and row.get("commission_fbs", 0) > 0
                else row["commission_fbo"] if row["model"] == "FBO" and row.get("commission_fbo", 0) > 0
                else get_commission_by_category(row["subject"], row["model"])
            ),
            axis=1
        )
    else:
        merged["commission_percent"] = merged.apply(
            lambda row: get_commission_by_category(row["subject"], row["model"]),
            axis=1
        )
        # Заполняем пустыми чтобы не было ошибок в диагностике
        merged["commission_fbo"] = 0
        merged["commission_fbs"] = 0
        merged["commission_dbs"] = 0
        merged["commission_dbw"] = 0

    merged["logistics"] = merged.apply(
        lambda row: estimate_logistics(row["volume_liters"], row["model"]),
        axis=1
    )

    results = []
    for _, row in merged.iterrows():
        if row["cost_price"] == 0 or row["price"] == 0:
            continue

        current = calculate_current_profit(
            price_with_discount=row["discounted_price"] or row["price"],
            commission_percent=row["commission_percent"],
            logistics=row["logistics"],
            cost_price=row["cost_price"],
            buyout_rate=buyout_rate
        )

        recommended = calculate_recommended_price(
            cost_price=row["cost_price"],
            commission_percent=row["commission_percent"],
            logistics=row["logistics"],
            target_margin=target_margin,
            current_discount=row["discount"] or 0,
            max_discount=max_discount,
            max_discount_change=max_discount_change,
            keep_discount=keep_discount,
            buyout_rate=buyout_rate
        )

        if not recommended:
            continue

        status_icon, status_text = get_status(current["margin"], target_margin)

        if current["margin"] < 0:
            category = "убыточные"
        elif current["margin"] < target_margin - 2:
            category = "ниже цели"
        else:
            category = "в норме"

        results.append({
            "nm_id": row["nm_id"],
            "article": row["article"],
            "title": row["title"],
            "subject": row["subject"],
            "model": row["model"],
            "cost_price": row["cost_price"],
            "commission_percent": row["commission_percent"],
            # Все комиссии для диагностики
            "commission_fbo": row.get("commission_fbo", 0),
            "commission_fbs": row.get("commission_fbs", 0),
            "commission_dbs": row.get("commission_dbs", 0),
            "commission_dbw": row.get("commission_dbw", 0),
            "logistics": row["logistics"],
            "current_price": row["price"],
            "current_discount": row["discount"] or 0,
            "current_price_final": row["discounted_price"] or row["price"],
            "current_profit": current["profit"],
            "current_margin": current["margin"],
            "recommended_price": recommended["price_without_discount"],
            "recommended_discount": recommended["discount_percent"],
            "recommended_final": recommended["price_with_discount"],
            "recommended_profit": recommended["profit"],
            "recommended_margin": recommended["margin"],
            "discount_change": recommended["discount_change"],
            "profit_diff": recommended["profit"] - current["profit"],
            "status_icon": status_icon,
            "status_text": status_text,
            "category": category,
        })

    if not results:
        st.warning("⚠️ Нет товаров для расчёта. Проверь себестоимость и цены.")
        st.session_state["calc_loaded"] = False
        st.stop()

    st.session_state["df_results"] = pd.DataFrame(results)


df_results = st.session_state["df_results"]


# ============ СВОДКА ============

st.markdown("---")
st.header("📊 Результаты")

if force_model:
    st.success(f"🏬 Модель: **{force_model}** | Маржа: **{target_margin}%** | Выкуп: **{buyout_percent}%**")
else:
    st.info(f"🔀 Модель: **Авто** | Маржа: **{target_margin}%** | Выкуп: **{buyout_percent}%**")

total_products = len(df_results)
losing = df_results[df_results["category"] == "убыточные"]
below_target = df_results[df_results["category"] == "ниже цели"]
ok = df_results[df_results["category"] == "в норме"]
potential = df_results["profit_diff"].sum()

col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.metric("📦 Всего", total_products)
with col_m2:
    st.metric("🔴 Убыточные", len(losing))
with col_m3:
    st.metric("🟡 Ниже цели", len(below_target))
with col_m4:
    st.metric("🟢 В норме", len(ok))

if not force_model:
    fbo_count = len(df_results[df_results["model"] == "FBO"])
    fbs_count = len(df_results[df_results["model"] == "FBS"])

    col_mod1, col_mod2 = st.columns(2)
    with col_mod1:
        st.metric("🏬 FBO", fbo_count)
    with col_mod2:
        st.metric("📦 FBS", fbs_count)

st.markdown(f"""
### 💰 Потенциал роста прибыли: 
## `+{potential:,.0f} ₽` за партию
""".replace(",", " "))


# ============ ФИЛЬТРЫ ============

st.markdown("---")

if not force_model:
    col_f1, col_f2 = st.columns([2, 1])

    with col_f1:
        filter_choice = st.radio(
            "Фильтр по марже:",
            ["🔴 Убыточные", "🟡 Ниже цели", "🟢 В норме", "📋 Все"],
            horizontal=True,
            key="filter_choice"
        )

    with col_f2:
        model_filter = st.radio(
            "Фильтр по модели:",
            ["Все", "FBO", "FBS"],
            horizontal=True,
            key="model_filter"
        )
else:
    filter_choice = st.radio(
        "Фильтр по марже:",
        ["🔴 Убыточные", "🟡 Ниже цели", "🟢 В норме", "📋 Все"],
        horizontal=True,
        key="filter_choice"
    )
    model_filter = "Все"

if filter_choice == "🔴 Убыточные":
    filtered = losing.copy()
    filter_name = "убыточные"
elif filter_choice == "🟡 Ниже цели":
    filtered = below_target.copy()
    filter_name = "ниже цели"
elif filter_choice == "🟢 В норме":
    filtered = ok.copy()
    filter_name = "в норме"
else:
    filtered = df_results.copy()
    filter_name = "все"

if model_filter != "Все":
    filtered = filtered[filtered["model"] == model_filter]
    filter_name = f"{filter_name} ({model_filter})"

to_update_from_filter = filtered[
    (filtered["current_price"] != filtered["recommended_price"]) |
    (filtered["current_discount"] != filtered["recommended_discount"])
]

st.info(f"📊 Показано: **{len(filtered)}** | Требуют обновления: **{len(to_update_from_filter)}**")


# ============ ТАБЛИЦА ============

if len(filtered) > 0:
    if force_model:
        display_df = filtered[[
            "status_icon", "article", "subject",
            "cost_price", "commission_percent", "logistics",
            "current_price", "current_discount", "current_price_final", "current_margin",
            "recommended_price", "recommended_discount", "recommended_final", "recommended_margin",
            "discount_change", "profit_diff"
        ]].copy()

        display_df.columns = [
            "", "Артикул", "Категория",
            "Себест. ₽", "Комис. %", "Логист. ₽",
            "Цена до скидки", "Скидка %", "Цена покупателя", "Маржа %",
            "Реком. цена", "Реком. скидка %", "Реком. покупателю", "Реком. маржа %",
            "Δ Скидка %", "Δ Прибыль ₽"
        ]
    else:
        display_df = filtered[[
            "status_icon", "article", "subject", "model",
            "cost_price", "commission_percent", "logistics",
            "current_price", "current_discount", "current_price_final", "current_margin",
            "recommended_price", "recommended_discount", "recommended_final", "recommended_margin",
            "discount_change", "profit_diff"
        ]].copy()

        display_df.columns = [
            "", "Артикул", "Категория", "Модель",
            "Себест. ₽", "Комис. %", "Логист. ₽",
            "Цена до скидки", "Скидка %", "Цена покупателя", "Маржа %",
            "Реком. цена", "Реком. скидка %", "Реком. покупателю", "Реком. маржа %",
            "Δ Скидка %", "Δ Прибыль ₽"
        ]

    st.dataframe(display_df, use_container_width=True, height=500)
else:
    st.info("Нет товаров в этой категории")


# ============ ДИАГНОСТИКА КОМИССИЙ ============

st.markdown("---")

with st.expander("🔍 Диагностика: проверить все комиссии"):
    st.markdown("""
    ### Проверь что комиссии соответствуют кабинету WB
    
    В WB зайди в **"Тарифы"** → найди свою категорию → сравни:
    
    - **Склад WB (FBO), %** ← колонка "FBO"
    - **Маркетплейс (FBS), %** ← колонка "FBS"  ⭐ основная для тебя
    - **Витрина (DBS), %** ← колонка "DBS"
    - **Курьер WB (DBW), %** ← колонка "DBW"
    """)

    if not df_results.empty:
        # Уникальные категории (чтобы не дублировать)
        diag_df = df_results[[
            "subject", "commission_fbo", "commission_fbs", 
            "commission_dbs", "commission_dbw",
            "model", "commission_percent"
        ]].drop_duplicates(subset=["subject"]).copy()

        diag_df.columns = [
            "Категория",
            "FBO %", "FBS % ⭐", "DBS %", "DBW %",
            "Твоя модель", "Используется %"
        ]

        st.dataframe(diag_df, use_container_width=True, height=400)

        st.info("""
        ⭐ **FBS %** — это то, что применяется при работе по модели "Маркетплейс FBS"
        
        Если значение не совпадает с кабинетом WB — сообщи!
        """)


# ============ ЭКСПОРТ ============

st.markdown("---")
st.subheader("📤 Экспорт")

output = io.BytesIO()
with pd.ExcelWriter(output, engine="openpyxl") as writer:
    df_results.to_excel(writer, sheet_name="Все товары", index=False)
    losing.to_excel(writer, sheet_name="Убыточные", index=False)
    below_target.to_excel(writer, sheet_name="Ниже цели", index=False)
    ok.to_excel(writer, sheet_name="В норме", index=False)

    prices_to_update = df_results[[
        "nm_id", "recommended_price", "recommended_discount"
    ]].copy()
    prices_to_update.columns = ["nmID", "price", "discount"]
    prices_to_update.to_excel(writer, sheet_name="Цены для загрузки", index=False)

st.download_button(
    label="📥 Скачать Excel с расчётами",
    data=output.getvalue(),
    file_name=f"wb_prices_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True
)


# ============ ОБНОВЛЕНИЕ ============

st.markdown("---")
st.subheader("💰 Обновление цен на WB")

if st.session_state["show_confirm"] is None:
    st.warning(f"""
    ⚠️ Отправить изменения на Wildberries.

    Категория: **"{filter_choice}"** | Модель: **{model_filter}**
    Товаров к обновлению: **{len(to_update_from_filter)}**
    """)

    col_upd1, col_upd2 = st.columns(2)

    with col_upd1:
        if st.button(
            f"💰 Обновить {filter_name} ({len(to_update_from_filter)})",
            type="primary",
            use_container_width=True,
            disabled=(len(to_update_from_filter) == 0),
            key="btn_update_filtered"
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
            use_container_width=True,
            disabled=(len(all_to_update) == 0),
            key="btn_update_all"
        ):
            st.session_state["show_confirm"] = "all"
            st.session_state["to_update_data"] = all_to_update.copy()
            st.rerun()

else:
    to_update = st.session_state["to_update_data"]

    st.error(f"""
    ## ⚠️ ПОДТВЕРЖДЕНИЕ

    Будет обновлено **{len(to_update)}** товаров на Wildberries.
    """)

    big_changes = to_update[abs(to_update["discount_change"]) > 10]
    if len(big_changes) > 0:
        st.warning(f"""
        ⚠️ Внимание! У **{len(big_changes)}** товаров скидка меняется больше чем на 10%.
        Это может отправить товар в карантин WB.
        """)

    preview = to_update[[
        "article", "subject",
        "current_price", "recommended_price",
        "current_discount", "recommended_discount",
        "current_price_final", "recommended_final",
        "current_margin", "recommended_margin"
    ]].copy()
    preview.columns = [
        "Артикул", "Категория",
        "Было цена", "Станет цена",
        "Было скидка %", "Станет скидка %",
        "Было покупателю", "Станет покупателю",
        "Была маржа %", "Станет маржа %"
    ]
    st.dataframe(preview, use_container_width=True, height=400)

    col_conf1, col_conf2 = st.columns(2)

    with col_conf1:
        if st.button(
            "✅ ДА, обновить",
            type="primary",
            use_container_width=True,
            key="btn_confirm_yes"
        ):
            price_updates = []
            for _, row in to_update.iterrows():
                price_updates.append({
                    "nmID": int(row["nm_id"]),
                    "price": int(row["recommended_price"]),
                    "discount": int(row["recommended_discount"])
                })

            with st.spinner(f"💰 Обновляем {len(price_updates)} товаров..."):
                result = update_prices(api_key, price_updates)

            st.session_state["update_result"] = result
            st.session_state["show_confirm"] = None
            st.session_state["to_update_data"] = None
            st.rerun()

    with col_conf2:
        if st.button("❌ Отмена", use_container_width=True, key="btn_confirm_no"):
            st.session_state["show_confirm"] = None
            st.session_state["to_update_data"] = None
            st.rerun()


st.markdown("---")
st.caption("💡 Данные кешируются на 30-60 минут")
