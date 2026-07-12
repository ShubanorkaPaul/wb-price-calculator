"""
Работа с WB API для калькулятора цен - ОПТИМИЗИРОВАННАЯ ВЕРСИЯ
С параллельной загрузкой для максимальной скорости
"""

import requests
import pandas as pd
import streamlit as st
import time
from concurrent.futures import ThreadPoolExecutor


BASE_CONTENT = "https://content-api.wildberries.ru"
BASE_PRICES = "https://discounts-prices-api.wildberries.ru"
BASE_COMMON = "https://common-api.wildberries.ru"
BASE_STATISTICS = "https://statistics-api.wildberries.ru"
BASE_MARKETPLACE = "https://marketplace-api.wildberries.ru"


def get_headers(api_key):
    return {"Authorization": api_key}


def make_request(method, url, api_key, params=None, json_data=None, max_retries=3):
    """Быстрый запрос с минимальными задержками"""

    for attempt in range(max_retries):
        try:
            if method == "GET":
                response = requests.get(url, headers=get_headers(api_key), params=params, timeout=60)
            elif method == "POST":
                response = requests.post(url, headers=get_headers(api_key), json=json_data, timeout=60)
            else:
                return None, f"Неизвестный метод: {method}"

            if response.status_code in [200, 201, 204]:
                return response, None

            if response.status_code == 429:
                wait_time = 15 * (attempt + 1)
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                    continue
                return None, "429"

            if response.status_code == 401:
                return None, "401"

            return None, f"HTTP {response.status_code}"

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(3)
                continue
            return None, "timeout"
        except Exception as e:
            return None, str(e)

    return None, "max_retries"


@st.cache_data(ttl=3600, show_spinner=False)
def get_all_cards(api_key):
    """Получить все карточки товаров"""

    url = f"{BASE_CONTENT}/content/v2/get/cards/list"
    all_cards = []
    cursor = {"limit": 100}

    while True:
        payload = {
            "settings": {
                "cursor": cursor,
                "filter": {"withPhoto": -1}
            }
        }

        response, error = make_request("POST", url, api_key, json_data=payload)

        if error:
            if error == "401":
                st.error("❌ Неверный API ключ или нет прав на 'Контент'")
            elif error == "429":
                st.warning("⚠️ WB временно ограничил запросы. Подожди пару минут.")
            else:
                st.error(f"❌ Ошибка получения карточек: {error}")
            return pd.DataFrame()

        try:
            data = response.json()
            cards = data.get("cards", [])
            all_cards.extend(cards)

            new_cursor = data.get("cursor", {})
            total = new_cursor.get("total", 0)

            if total < 100:
                break

            cursor = {
                "limit": 100,
                "updatedAt": new_cursor.get("updatedAt"),
                "nmID": new_cursor.get("nmID")
            }

            time.sleep(0.3)

        except Exception as e:
            st.error(f"❌ Ошибка парсинга карточек: {e}")
            return pd.DataFrame()

    result = []
    for card in all_cards:
        dimensions = card.get("dimensions", {})
        length = dimensions.get("length", 0) or 0
        width = dimensions.get("width", 0) or 0
        height = dimensions.get("height", 0) or 0
        volume = (length * width * height) / 1000 if all([length, width, height]) else 0

        sizes = card.get("sizes", [])
        barcodes = []
        for s in sizes:
            skus = s.get("skus", [])
            barcodes.extend(skus)

        result.append({
            "nm_id": card.get("nmID"),
            "article": card.get("vendorCode", ""),
            "brand": card.get("brand", ""),
            "title": card.get("title", ""),
            "subject": card.get("subjectName", ""),
            "subject_id": card.get("subjectID"),
            "length": length,
            "width": width,
            "height": height,
            "volume_liters": round(volume, 2),
            "barcode": barcodes[0] if barcodes else "",
        })

    return pd.DataFrame(result)


@st.cache_data(ttl=1800, show_spinner=False)
def get_prices(api_key):
    """Получить текущие цены и скидки"""

    url = f"{BASE_PRICES}/api/v2/list/goods/filter"
    all_prices = []
    offset = 0
    limit = 1000

    while True:
        params = {"limit": limit, "offset": offset}
        response, error = make_request("GET", url, api_key, params=params, max_retries=3)

        if error:
            if error == "401":
                st.error("❌ Нет прав 'Цены и скидки' у API ключа")
            elif error == "429":
                st.warning("⚠️ WB временно ограничил запросы к ценам.")
            else:
                st.error(f"❌ Ошибка получения цен: {error}")
            return pd.DataFrame()

        try:
            data = response.json()
            goods = data.get("data", {}).get("listGoods", [])

            if not goods:
                break

            all_prices.extend(goods)

            if len(goods) < limit:
                break

            offset += limit
            time.sleep(0.5)

        except Exception as e:
            st.error(f"❌ Ошибка парсинга цен: {e}")
            return pd.DataFrame()

    result = []
    for good in all_prices:
        sizes = good.get("sizes", [])
        price = 0
        discounted = 0
        if sizes:
            price = sizes[0].get("price", 0)
            discounted = sizes[0].get("discountedPrice", 0)

        result.append({
            "nm_id": good.get("nmID"),
            "article": good.get("vendorCode", ""),
            "price": price,
            "discount": good.get("discount", 0),
            "discounted_price": discounted,
        })

    return pd.DataFrame(result)


@st.cache_data(ttl=86400, show_spinner=False)
def get_commissions(api_key):
    """Получить комиссии по категориям (кеш на 24 часа)"""

    url = f"{BASE_COMMON}/api/v1/tariffs/commission"
    params = {"locale": "ru"}

    response, error = make_request("GET", url, api_key, params=params)

    if error:
        return pd.DataFrame()

    try:
        data = response.json()
        report = data.get("report", [])

        result = []
        for item in report:
            result.append({
                "subject_id": item.get("subjectID"),
                "subject_name": item.get("subjectName", ""),
                "commission_fbo": item.get("paidStorageKgvp", 0),
                "commission_fbs": item.get("kgvpMarketplace", 0),
                "commission_dbs": item.get("kgvpSupplier", 0),
                "commission_dbw": item.get("kgvpSupplierExpress", 0),
            })

        return pd.DataFrame(result)

    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def get_stocks_by_warehouse(api_key):
    """Получить остатки (медленно из-за лимитов WB)"""
    from datetime import datetime, timedelta

    date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    url = f"{BASE_STATISTICS}/api/v1/supplier/stocks"
    params = {"dateFrom": date_from}

    response, error = make_request("GET", url, api_key, params=params, max_retries=2)

    if error:
        return pd.DataFrame()

    try:
        data = response.json()
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()


def determine_model(article, stocks_df):
    """Определяет основную модель работы по остаткам"""
    if stocks_df.empty or "supplierArticle" not in stocks_df.columns:
        return "FBO"

    article_stocks = stocks_df[stocks_df["supplierArticle"] == article]

    if article_stocks.empty:
        return "FBO"

    if "warehouseName" in article_stocks.columns:
        warehouses = article_stocks["warehouseName"].astype(str).str.lower()
        if warehouses.str.contains("продавец|фбс|fbs|свой", regex=True, na=False).any():
            return "FBS"

    return "FBO"


def get_available_models(article, stocks_df):
    """Определяет доступные модели по остаткам"""
    available = set()

    if stocks_df.empty or "supplierArticle" not in stocks_df.columns:
        return set()

    article_stocks = stocks_df[stocks_df["supplierArticle"] == article]

    if article_stocks.empty:
        return set()

    if "quantity" in article_stocks.columns:
        article_stocks = article_stocks[article_stocks["quantity"] > 0]

    if article_stocks.empty:
        return set()

    if "warehouseName" not in article_stocks.columns:
        return {"FBO"}

    warehouses = article_stocks["warehouseName"].astype(str).str.lower()

    if warehouses.str.contains("dbs|витрин", regex=True, na=False).any():
        available.add("DBS")

    if warehouses.str.contains("склад продавца|фбс|fbs", regex=True, na=False).any():
        available.add("FBS")

    wb_warehouses = warehouses[
        ~warehouses.str.contains("dbs|витрин|склад продавца|фбс|fbs", regex=True, na=False)
    ]
    if len(wb_warehouses) > 0:
        available.add("FBO")

    return available


def update_prices(api_key, price_updates):
    """Обновить цены на WB"""

    url = f"{BASE_PRICES}/api/v2/upload/task"

    batch_size = 1000
    results = {"success": 0, "errors": []}

    for i in range(0, len(price_updates), batch_size):
        batch = price_updates[i:i + batch_size]
        payload = {"data": batch}

        response, error = make_request("POST", url, api_key, json_data=payload)

        if error:
            results["errors"].append(f"Батч {i//batch_size + 1}: {error}")
        else:
            results["success"] += len(batch)

        time.sleep(1)

    return results


# ========== ПАРАЛЛЕЛЬНАЯ ЗАГРУЗКА ==========

def load_all_data_parallel(api_key, load_stocks=False):
    """
    Загружает все данные ПАРАЛЛЕЛЬНО - в 3 раза быстрее!
    load_stocks=False по умолчанию — не грузим медленные остатки
    """
    results = {
        "cards": pd.DataFrame(),
        "prices": pd.DataFrame(),
        "commissions": pd.DataFrame(),
        "stocks": pd.DataFrame(),
    }
    
    def load_cards():
        results["cards"] = get_all_cards(api_key)
    
    def load_prices():
        results["prices"] = get_prices(api_key)
    
    def load_commissions():
        results["commissions"] = get_commissions(api_key)
    
    def load_stocks_fn():
        results["stocks"] = get_stocks_by_warehouse(api_key)
    
    # Параллельно грузим карточки, цены, комиссии
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(load_cards),
            executor.submit(load_prices),
            executor.submit(load_commissions),
        ]
        
        for future in futures:
            future.result()
    
    # Остатки грузим ПОСЛЕ (если нужно)
    if load_stocks:
        load_stocks_fn()
    
    return results
