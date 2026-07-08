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
    BUYOUT_RATE,
)
from wb_api_prices import (
    get_all_cards,
    get_prices,
    get_commissions,
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


# ============ ИНИЦИАЛИЗАЦИЯ SESSION STATE ============

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

    st.subheader("🎯 Параметры")

    target_margin = st.slider(
        "Целевая маржа, %",
        min_value=10,
        max_value=50,
        value=20,
        step=1,
        key="target_margin"
    )

    st.info(f"""
    📊 **Параметры расчёта:**
    - Налог: УСН 6%
    - % выкупа: {int(BUYOUT_RATE*100)}%
    - Эквайринг: 1.5%
    - Реклама: не учитывается
    - Хранение: не учитывается
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


# Показываем результат обновления цен (если недавно обновили)
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


# ============ КНОПКА ЗАГРУЗКИ ============

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
    st.session_state["df_results"] = None  # Сбрасываем чтобы пересчитать

if not st.session_state["calc_loaded"]:
    st.stop()


# ============ ЗАГРУЗКА И РАСЧЁТ ============

# Проверяем, есть ли уже рассчитанные данные в сессии
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

    merged = cards_df.merge(
        prices_df[["nm_id", "price", "discount", "discounted_price"]],
        on="nm_id",
        how="left"
    )

    merged["cost_price"] = merged["article"].astype(str).str.strip().map(cost_prices).fillna(0)

    if not commissions_df.empty:
        merged = merged.merge(
            commissions_df[["subject_id", "commission_fbo"]],
            on="subject_id",
            how="left"
        )
        merged["commission_percent"] = merged["commission_fbo"].fillna(
            merged["subject"].apply(get_commission_by_category)
        )
    else:
        merged["commission_percent"] = merged["subject"].apply(get_commission_by_category)

    merged["logistics"] = merged["volume_liters"].apply(estimate_logistics)

    results = []
    for _, row in merged.iterrows():
        if row["cost_price"] == 0 or row["price"] == 0:
            continue

        current = calculate_current_profit(
            price_with_discount=row["discounted_price"] or row["price"],
            commission_percent=row["commission_percent"],
            logistics=row["logistics"],
            cost_price=row["cost_price"]
        )

        recommended = calculate_recommended_price(
            cost_price=row["cost_price"],
            commission_percent=row["commission_percent"],
            logistics=row["logistics"],
            target_margin=target_margin,
            discount_percent=row["discount"] or 0
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
            "cost_price": row["cost_price"],
            "commission_percent": row["commission_percent"],
            "logistics": row["logistics"],
            "current_price": row["price"],
            "current_discount": row["discount"],
            "current_price_final": row["discounted_price"] or row["price"],
            "current_profit": current["profit"],
            "current_margin": current["margin"],
            "recommended_price": recommended["price_without_discount"],
            "recommended_final": recommended["price_with_discount"],
            "recommended_profit": recommended["profit"],
            "recommended_margin": recommended["margin"],
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


# ============ РЕЗУЛЬТАТЫ ============

st.markdown("---")
st.header("📊 Результаты")

total_products = len(df_results)
losing = df_results[df_results["category"] == "убыточные"]
below_target = df_results[df_results["category"] == "ниже цели"]
ok = df_results[df_results["category"] == "в норме"]

potential = df_results["profit_diff"].sum()

col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.metric("📦 Всего товаров", total_products)

with col_m2:
    st.metric("🔴 Убыточные", len(losing))

with col_m3:
    st.metric("🟡 Ниже цели", len(below_target))

with col_m4:
    st.metric("🟢 В норме", len(ok))

st.markdown(f"""
### 💰 Потенциал роста прибыли: 
## `+{potential:,.0f} ₽` за партию (если применить рекомендации)
""".replace(",", " "))


# ============ ФИЛЬТРЫ ============

st.markdown("---")

filter_choice = st.radio(
    "Фильтр товаров:",
    ["🔴 Убыточные", "🟡 Ниже цели", "🟢 В норме", "📋 Все"],
    horizontal=True,
    key="filter_choice"
)

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

to_update_from_filter = filtered[filtered["current_price"] != filtered["recommended_price"]]

st.info(f"📊 Отображено товаров: **{len(filtered)}** | Из них требуют обновления цены: **{len(to_update_from_filter)}**")


# ============ ТАБЛИЦА ============

if len(filtered) > 0:
    display_df = filtered[[
        "status_icon", "article", "subject", "cost_price",
        "commission_percent", "logistics",
        "current_price", "current_price_final", "current_margin",
        "recommended_price", "recommended_final", "recommended_margin",
        "profit_diff"
    ]].copy()

    display_df.columns = [
        "", "Артикул", "Категория", "Себест.",
        "Комис.%", "Логист.",
        "Цена", "Со скид.", "Маржа %",
        "Реком.цена", "Реком.скид.", "Реком.маржа %",
        "Δ Прибыль"
    ]

    st.dataframe(display_df, use_container_width=True, height=500)
else:
    st.info("Нет товаров в этой категории")


# ============ ЭКСПОРТ ============

st.markdown("---")
st.subheader("📤 Экспорт")

output = io.BytesIO()
with pd.ExcelWriter(output, engine="openpyxl") as writer:
    df_results.to_excel(writer, sheet_name="Все товары", index=False)
    losing.to_excel(writer, sheet_name="Убыточные", index=False)
    below_target.to_excel(writer, sheet_name="Ниже цели", index=False)
    ok.to_excel(writer, sheet_name="В норме", index=False)

    prices_to_update = df_results[["nm_id", "recommended_price", "current_discount"]].copy()
    prices_to_update.columns = ["nmID", "price", "discount"]
    prices_to_update.to_excel(writer, sheet_name="Цены для загрузки", index=False)

st.download_button(
    label="📥 Скачать Excel с расчётами (все листы)",
    data=output.getvalue(),
    file_name=f"wb_prices_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True
)


# ============ ОБНОВЛЕНИЕ ЦЕН ============

st.markdown("---")
st.subheader("💰 Обновление цен на WB")

# Если ещё не подтвердил
if st.session_state["show_confirm"] is None:
    st.warning(f"""
    ⚠️ Ты собираешься обновить цены на WB.

    Сейчас выбрана категория: **"{filter_choice}"**  
    Будет обновлено товаров: **{len(to_update_from_filter)}**
    """)

    col_upd1, col_upd2 = st.columns(2)

    with col_upd1:
        if st.button(
            f"💰 Обновить только {filter_name} ({len(to_update_from_filter)})",
            type="primary",
            use_container_width=True,
            disabled=(len(to_update_from_filter) == 0),
            key="btn_update_filtered"
        ):
            st.session_state["show_confirm"] = "filtered"
            st.session_state["to_update_data"] = to_update_from_filter.copy()
            st.rerun()

    with col_upd2:
        all_to_update = df_results[df_results["current_price"] != df_results["recommended_price"]]
        if st.button(
            f"⚡ Обновить ВСЕ ({len(all_to_update)})",
            use_container_width=True,
            disabled=(len(all_to_update) == 0),
            key="btn_update_all"
        ):
            st.session_state["show_confirm"] = "all"
            st.session_state["to_update_data"] = all_to_update.copy()
            st.rerun()

# Если нажал одну из кнопок обновления - показываем подтверждение
else:
    to_update = st.session_state["to_update_data"]

    st.error(f"""
    ## ⚠️ ПОДТВЕРЖДЕНИЕ ОБНОВЛЕНИЯ ЦЕН

    Будет обновлено **{len(to_update)}** товаров на Wildberries.

    Проверь список ниже перед подтверждением!
    """)

    preview = to_update[[
        "article", "subject", "current_price", "recommended_price",
        "current_margin", "recommended_margin"
    ]].copy()
    preview.columns = ["Артикул", "Категория", "Было ₽", "Станет ₽", "Была маржа %", "Станет маржа %"]
    st.dataframe(preview, use_container_width=True, height=400)

    col_conf1, col_conf2 = st.columns(2)

    with col_conf1:
        if st.button(
            "✅ ДА, обновить эти цены на WB",
            type="primary",
            use_container_width=True,
            key="btn_confirm_yes"
        ):
            price_updates = []
            for _, row in to_update.iterrows():
                price_updates.append({
                    "nmID": int(row["nm_id"]),
                    "price": int(row["recommended_price"]),
                    "discount": int(row["current_discount"]) if row["current_discount"] else 0
                })

            with st.spinner(f"💰 Обновляем {len(price_updates)} товаров на WB..."):
                result = update_prices(api_key, price_updates)

            # Сохраняем результат для отображения
            st.session_state["update_result"] = result
            st.session_state["show_confirm"] = None
            st.session_state["to_update_data"] = None
            st.rerun()

    with col_conf2:
        if st.button(
            "❌ Отмена",
            use_container_width=True,
            key="btn_confirm_no"
        ):
            st.session_state["show_confirm"] = None
            st.session_state["to_update_data"] = None
            st.rerun()


st.markdown("---")
st.caption("💡 Данные кешируются на 30-60 минут. Для обновления нажми 'Очистить кеш'")
