"""
Работа с WB API для калькулятора цен - ОПТИМИЗИРОВАННАЯ ВЕРСИЯ
С параллельной загрузкой и парсером акций
"""

import requests
import pandas as pd
import streamlit as st
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed


BASE_CONTENT = "https://content-api.wildberries.ru"
BASE_PRICES = "https://discounts-prices-api.wildberries.ru"
BASE_COMMON = "https://common-api.wildberries.ru"
BASE_STATISTICS = "https://statistics-api.wildberries.ru"
BASE_MARKETPLACE = "https://marketplace-api.wildberries.ru"


def get_headers(api_key):
    return {"Authorization": api_key}


def make_request(method, url, api_key, params=None, json_data=None, max_retries=3):
    """Универсальный запрос с повторными попытками"""

    for attempt in range(max_retries):
        try:
            if method == "GET":
                response = requests.get(url, headers=get_headers(api_key), params=params, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=get_headers(api_key), json=json_data, timeout=30)
            else:
                return None, f"Неизвестный метод: {method}"

            if response.status_code in [200, 201, 204]:
                return response, None

            if response.status_code == 429:
                wait_time = 2 * (attempt + 1)
                print(f"[WB API] Rate limit 429 for {url}, waiting {wait_time}s...")
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                    continue
                return None, "429"

            if response.status_code == 401:
                return None, "401"

            return None, f"HTTP {response.status_code}"

        except requests.exceptions.Timeout:
            print(f"[WB API] Timeout for {url} (attempt {attempt+1})")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            return None, "timeout"
        except Exception as e:
            print(f"[WB API] Exception for {url}: {e}")
            return None, str(e)

    return None, "max_retries"


@st.cache_data(ttl=3600, show_spinner=False)
def get_all_cards(api_key):
    """Получить все карточки товаров"""

    url = f"{BASE_CONTENT}/content/v2/get/cards/list"
    all_cards = []
    cursor = {"limit": 100}

    print("[WB API] Starting get_all_cards...")
    page_count = 0
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
                print("[WB API] get_all_cards 401 Unauthorized")
            elif error == "429":
                st.warning("⚠️ WB временно ограничил запросы. Подожди пару минут.")
                print("[WB API] get_all_cards 429 Rate Limit")
            else:
                st.error(f"❌ Ошибка получения карточек: {error}")
                print(f"[WB API] get_all_cards error: {error}")
            return pd.DataFrame()

        try:
            data = response.json()
            cards = data.get("cards", [])
            all_cards.extend(cards)
            page_count += 1

            new_cursor = data.get("cursor", {})
            total = new_cursor.get("total", 0)

            if total < 100 or not cards:
                break

            cursor = {
                "limit": 100,
                "updatedAt": new_cursor.get("updatedAt"),
                "nmID": new_cursor.get("nmID")
            }

            time.sleep(0.1)

        except Exception as e:
            print(f"[WB API] get_all_cards exception: {e}")
            st.error(f"❌ Ошибка парсинга карточек: {e}")
            return pd.DataFrame()

    print(f"[WB API] get_all_cards finished. Total cards: {len(all_cards)}")
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

    print("[WB API] Starting get_prices...")
    while True:
        params = {"limit": limit, "offset": offset}
        response, error = make_request("GET", url, api_key, params=params, max_retries=3)

        if error:
            if error == "401":
                st.error("❌ Нет прав 'Цены и скидки' у API ключа")
                print("[WB API] get_prices 401 Unauthorized")
            elif error == "429":
                st.warning("⚠️ WB временно ограничил запросы. Подожди 5-10 минут.")
                print("[WB API] get_prices 429 Rate Limit")
            else:
                st.error(f"❌ Ошибка получения цен: {error}")
                print(f"[WB API] get_prices error: {error}")
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
            time.sleep(0.1)

        except Exception as e:
            print(f"[WB API] get_prices exception: {e}")
            st.error(f"❌ Ошибка парсинга цен: {e}")
            return pd.DataFrame()

    print(f"[WB API] get_prices finished. Total prices: {len(all_prices)}")
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
    @st.cache_data(ttl=86400, show_spinner=False)
def get_commissions(api_key):
    """
    Получить комиссии по категориям из WB API.

    ВАЖНО:
    WB отдаёт несколько похожих полей:
    - kgvpMarketplace      — обычно Маркетплейс / FBS
    - paidStorageKgvp      — часто Склад WB / FBO
    - kgvpSupplier         — Витрина / DBS
    - kgvpSupplierExpress  — Курьер WB / DBW

    Но у WB названия и логика могут меняться, поэтому в app.py
    мы даём пользователю выбрать источник комиссии вручную.
    """

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

                # Сырые поля WB
                "kgvpMarketplace": item.get("kgvpMarketplace", 0),
                "paidStorageKgvp": item.get("paidStorageKgvp", 0),
                "kgvpSupplier": item.get("kgvpSupplier", 0),
                "kgvpSupplierExpress": item.get("kgvpSupplierExpress", 0),

                # Алиасы для удобства
                "commission_fbs_default": item.get("kgvpMarketplace", 0),
                "commission_fbo_default": item.get("paidStorageKgvp", 0),
                "commission_dbs_default": item.get("kgvpSupplier", 0),
                "commission_dbw_default": item.get("kgvpSupplierExpress", 0),
            })

        df = pd.DataFrame(result)

        if df.empty:
            return df

        # Приводим к числам
        numeric_cols = [
            "subject_id",
            "kgvpMarketplace",
            "paidStorageKgvp",
            "kgvpSupplier",
            "kgvpSupplierExpress",
            "commission_fbs_default",
            "commission_fbo_default",
            "commission_dbs_default",
            "commission_dbw_default",
        ]

        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # Убираем дубли по subject_id, если вдруг WB вернул повторы
        if "subject_id" in df.columns:
            df = df.drop_duplicates(subset=["subject_id"])

        return df

    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def get_stocks_by_warehouse(api_key):
    """Получить остатки по складам"""
    from datetime import datetime, timedelta

    date_from = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    url = f"{BASE_STATISTICS}/api/v1/supplier/stocks"
    params = {"dateFrom": date_from}

    response, error = make_request("GET", url, api_key, params=params, max_retries=2)

    if error:
        print(f"[WB API] get_stocks_by_warehouse error: {error}")
        return pd.DataFrame()

    try:
        data = response.json()
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)
    except Exception as e:
        print(f"[WB API] get_stocks_by_warehouse exception: {e}")
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


# ============ ПАРАЛЛЕЛЬНАЯ ЗАГРУЗКА ============

def load_all_data_parallel(api_key, load_stocks=False):
    """Загружает все данные параллельно"""
    results = {
        "cards": pd.DataFrame(),
        "prices": pd.DataFrame(),
        "commissions": pd.DataFrame(),
        "stocks": pd.DataFrame(),
    }
    
    def load_cards():
        try:
            results["cards"] = get_all_cards(api_key)
        except Exception as e:
            print(f"[Load] Cards exception: {e}")
    
    def load_prices_fn():
        try:
            results["prices"] = get_prices(api_key)
        except Exception as e:
            print(f"[Load] Prices exception: {e}")
    
    def load_commissions_fn():
        try:
            results["commissions"] = get_commissions(api_key)
        except Exception as e:
            print(f"[Load] Commissions exception: {e}")
    
    def load_stocks_fn():
        try:
            results["stocks"] = get_stocks_by_warehouse(api_key)
        except Exception as e:
            print(f"[Load] Stocks exception: {e}")
    
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(load_cards): "cards",
            executor.submit(load_prices_fn): "prices",
            executor.submit(load_commissions_fn): "commissions",
        }
        
        for future in as_completed(futures, timeout=90):
            try:
                future.result()
            except Exception as e:
                print(f"[Load] Future error for {futures[future]}: {e}")
    
    if load_stocks:
        load_stocks_fn()
    
    return results


# ============ ПАРСЕР ФАЙЛА АКЦИЙ WB ============

def parse_action_file(uploaded_file):
    """
    Парсит Excel файл акции от WB.
    Возвращает: (DataFrame, error_message)
    """
    try:
        action_name = "Акция WB"
        try:
            file_name = uploaded_file.name
            name_without_ext = file_name.rsplit('.', 1)[0]
            match = re.search(r'[а-яА-ЯёЁ][а-яА-ЯёЁ\s\-_]+', name_without_ext)
            if match:
                action_name = match.group(0).strip().replace('_', ' ').replace('-', ' ')
        except:
            pass
        
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
        
        column_mappings = {
            'article': ['артикул поставщика', 'артикул продавца', 'артикул', 'vendor', 'sku'],
            'nm_id': ['артикул wb', 'nm_id', 'nmid'],
            'action_price': ['плановая цена для акции', 'плановая цена', 'цена в акции', 'action price'],
            'action_discount': ['загружаемая скидка для участия в акции', 'загружаемая скидка', 'скидка для акции'],
            'current_price': ['текущая розничная цена', 'текущая цена', 'розничная цена'],
            'current_discount': ['текущая скидка на сайте', 'текущая скидка'],
            'min_price': ['минимальная цена для применения скидки', 'минимальная цена', 'мин цена'],
            'status': ['статус'],
            'turnover': ['оборачиваемость'],
            'stock_wb': ['остаток товара на складах wb', 'остаток wb'],
            'stock_seller': ['остаток товара на складе продавца', 'остаток продавца'],
            'name': ['наименование', 'название'],
            'brand': ['бренд'],
            'subject': ['предмет'],
            'days_on_site': ['количество дней на сайте', 'дней на сайте'],
            'in_action': ['товар уже участвует в акции', 'участвует в акции'],
        }
        
        col_map = {}
        for target_col, possible_names in column_mappings.items():
            for actual_col in df.columns:
                actual_lower = str(actual_col).lower().strip()
                for possible in possible_names:
                    if possible in actual_lower:
                        col_map[target_col] = actual_col
                        break
                if target_col in col_map:
                    break
        
        if 'article' not in col_map:
            return None, "Не найдена колонка 'Артикул поставщика' в файле"
        
        result = pd.DataFrame()
        result['article'] = df[col_map['article']].astype(str).str.strip()
        
        if 'action_price' in col_map:
            result['action_price'] = pd.to_numeric(df[col_map['action_price']], errors='coerce').fillna(0)
        else:
            result['action_price'] = 0
        
        if 'action_discount' in col_map:
            result['action_discount'] = pd.to_numeric(df[col_map['action_discount']], errors='coerce').fillna(0)
        else:
            result['action_discount'] = 0
        
        if 'current_price' in col_map:
            result['current_price'] = pd.to_numeric(df[col_map['current_price']], errors='coerce').fillna(0)
        else:
            result['current_price'] = 0
        
        if 'min_price' in col_map:
            result['min_price'] = pd.to_numeric(df[col_map['min_price']], errors='coerce').fillna(0)
        else:
            result['min_price'] = 0
        
        if 'status' in col_map:
            result['status'] = df[col_map['status']].astype(str).fillna('')
        else:
            result['status'] = ''
        
        if 'turnover' in col_map:
            result['turnover'] = pd.to_numeric(df[col_map['turnover']], errors='coerce').fillna(0)
        else:
            result['turnover'] = 0
        
        if 'stock_wb' in col_map:
            result['stock_wb'] = pd.to_numeric(df[col_map['stock_wb']], errors='coerce').fillna(0)
        else:
            result['stock_wb'] = 0
        
        if 'stock_seller' in col_map:
            result['stock_seller'] = pd.to_numeric(df[col_map['stock_seller']], errors='coerce').fillna(0)
        else:
            result['stock_seller'] = 0
        
        if 'name' in col_map:
            result['name'] = df[col_map['name']].astype(str).fillna('')
        else:
            result['name'] = ''
        
        if 'brand' in col_map:
            result['brand'] = df[col_map['brand']].astype(str).fillna('')
        else:
            result['brand'] = ''
        
        if 'subject' in col_map:
            result['subject'] = df[col_map['subject']].astype(str).fillna('')
        else:
            result['subject'] = ''
        
        if 'days_on_site' in col_map:
            result['days_on_site'] = pd.to_numeric(df[col_map['days_on_site']], errors='coerce').fillna(0)
        else:
            result['days_on_site'] = 0
        
        if 'in_action' in col_map:
            result['in_action'] = df[col_map['in_action']].astype(str).str.lower().str.contains('да|yes', na=False)
        else:
            result['in_action'] = False
        
        if 'nm_id' in col_map:
            result['nm_id'] = pd.to_numeric(df[col_map['nm_id']], errors='coerce').fillna(0).astype(int)
        else:
            result['nm_id'] = 0
        
        result = result[result['article'] != 'nan']
        result = result[result['article'].str.len() > 0]
        result['action_name'] = action_name
        
        return result, None
    
    except Exception as e:
        return None, f"Ошибка при чтении файла: {str(e)}"
