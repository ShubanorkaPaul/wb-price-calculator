"""
Работа с WB API для калькулятора цен
"""

import requests
import pandas as pd
import streamlit as st
import time


BASE_CONTENT = "https://content-api.wildberries.ru"
BASE_PRICES = "https://discounts-prices-api.wildberries.ru"
BASE_COMMON = "https://common-api.wildberries.ru"


def get_headers(api_key):
	return {"Authorization": api_key}


def make_request(method, url, api_key, params=None, json_data=None, max_retries=3):
	"""Универсальный запрос с повторными попытками"""

	for attempt in range(max_retries):
		try:
			if method == "GET":
				response = requests.get(url, headers=get_headers(api_key), params=params, timeout=90)
			elif method == "POST":
				response = requests.post(url, headers=get_headers(api_key), json=json_data, timeout=90)
			else:
				return None, f"Неизвестный метод: {method}"

			if response.status_code in [200, 201, 204]:
				return response, None

			if response.status_code == 429:
				wait_time = 30 * (attempt + 1)
				if attempt < max_retries - 1:
					with st.spinner(f"⏳ WB просит подождать ({wait_time} сек)..."):
						time.sleep(wait_time)
					continue
				return None, "429"

			if response.status_code == 401:
				return None, "401"

			return None, f"HTTP {response.status_code}: {response.text[:200]}"

		except requests.exceptions.Timeout:
			if attempt < max_retries - 1:
				time.sleep(5)
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

			time.sleep(0.5)

		except Exception as e:
			st.error(f"❌ Ошибка парсинга карточек: {e}")
			return pd.DataFrame()

	# Преобразуем в DataFrame
	result = []
	for card in all_cards:
		# Габариты
		dimensions = card.get("dimensions", {})
		length = dimensions.get("length", 0) or 0
		width = dimensions.get("width", 0) or 0
		height = dimensions.get("height", 0) or 0
		volume = (length * width * height) / 1000 if all([length, width, height]) else 0

		# Баркоды
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
		response, error = make_request("GET", url, api_key, params=params)

		if error:
			if error == "401":
				st.error("❌ Нет прав 'Цены и скидки' у API ключа")
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

	# Преобразуем в DataFrame
	result = []
	for good in all_prices:
		sizes = good.get("sizes", [])
		# Берём первый размер (обычно у всех размеров одна цена)
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
	"""Получить комиссии по категориям"""

	url = f"{BASE_COMMON}/api/v1/tariffs/commission"
	params = {"locale": "ru"}

	response, error = make_request("GET", url, api_key, params=params)

	if error:
		# Не критично, будем использовать примерные
		return pd.DataFrame()

	try:
		data = response.json()
		report = data.get("report", [])

		result = []
		for item in report:
			result.append({
				"subject_id": item.get("subjectID"),
				"subject_name": item.get("subjectName", ""),
				"commission_fbo": item.get("kgvpMarketplace", 0),
				"commission_fbs": item.get("kgvpSupplier", 0),
			})

		return pd.DataFrame(result)

	except Exception:
		return pd.DataFrame()


def update_prices(api_key, price_updates):
	"""
	Обновить цены на WB
	price_updates: список {"nmID": 123, "price": 2000, "discount": 30}
	"""

	url = f"{BASE_PRICES}/api/v2/upload/task"

	# Отправляем батчами по 1000
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