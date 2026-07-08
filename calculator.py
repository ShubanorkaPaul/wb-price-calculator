"""
Модуль расчёта цен и юнит-экономики
"""


TAX_RATE = 0.06  # УСН 6%
BUYOUT_RATE = 0.90  # % выкупа
ACQUIRING = 0.015  # Эквайринг 1.5%


def calculate_current_profit(price_with_discount, commission_percent, logistics, cost_price):
	"""
	Считает текущую прибыль по товару

	Args:
		price_with_discount: цена со скидкой (что платит покупатель)
		commission_percent: комиссия WB в % (например 22)
		logistics: логистика в рублях
		cost_price: себестоимость товара

	Returns:
		dict с расчётом
	"""

	# WB забирает комиссию
	commission = price_with_discount * (commission_percent / 100)

	# Эквайринг
	acquiring = price_with_discount * ACQUIRING

	# Учёт возвратов (при выкупе 90% на 10 отправленных 1 возврат = дополнительная логистика)
	return_rate = 1 - BUYOUT_RATE
	returns_cost = logistics * return_rate

	# То, что получаем от WB
	for_pay = price_with_discount - commission - acquiring - logistics - returns_cost

	# Налог УСН 6% с суммы продажи
	tax = price_with_discount * TAX_RATE

	# Чистая прибыль
	profit = for_pay - cost_price - tax

	# Маржа в % от цены
	margin = (profit / price_with_discount * 100) if price_with_discount > 0 else 0

	return {
		"price": price_with_discount,
		"commission": round(commission, 2),
		"acquiring": round(acquiring, 2),
		"logistics": round(logistics, 2),
		"returns_cost": round(returns_cost, 2),
		"tax": round(tax, 2),
		"cost_price": round(cost_price, 2),
		"for_pay": round(for_pay, 2),
		"profit": round(profit, 2),
		"margin": round(margin, 2),
	}


def calculate_recommended_price(cost_price, commission_percent, logistics, target_margin, discount_percent=0):
	"""
	Считает рекомендуемую цену исходя из целевой маржи

	Args:
		cost_price: себестоимость
		commission_percent: комиссия WB в %
		logistics: логистика в рублях
		target_margin: целевая маржа в %
		discount_percent: скидка WB в %

	Returns:
		dict с рекомендуемой ценой
	"""

	# Формула:
	# profit = price - price*commission - price*acquiring - logistics - returns_cost - price*tax - cost
	# margin = profit / price
	#
	# Решаем: какая должна быть price чтобы margin = target_margin
	#
	# price*(1 - commission - acquiring - tax - margin) = logistics + returns_cost + cost
	# price = (logistics + returns_cost + cost) / (1 - commission - acquiring - tax - margin)

	commission_rate = commission_percent / 100
	margin_rate = target_margin / 100
	return_rate = 1 - BUYOUT_RATE
	returns_cost = logistics * return_rate

	denominator = 1 - commission_rate - ACQUIRING - TAX_RATE - margin_rate

	if denominator <= 0:
		return None

	# Цена со скидкой (что платит покупатель)
	price_with_discount = (logistics + returns_cost + cost_price) / denominator
	price_with_discount = round(price_with_discount, 0)

	# Цена без скидки (что установим в WB)
	if discount_percent > 0 and discount_percent < 100:
		price_without_discount = price_with_discount / (1 - discount_percent / 100)
		price_without_discount = round(price_without_discount, 0)
	else:
		price_without_discount = price_with_discount

	# Округляем до красивых цифр (кратно 10)
	price_without_discount = round(price_without_discount / 10) * 10
	price_with_discount = price_without_discount * (1 - discount_percent / 100)

	# Проверяем итоговую прибыль
	result = calculate_current_profit(price_with_discount, commission_percent, logistics, cost_price)
	result["price_without_discount"] = price_without_discount
	result["price_with_discount"] = price_with_discount
	result["discount_percent"] = discount_percent

	return result


def get_status(current_margin, target_margin):
	"""Определяет статус товара по марже"""

	if current_margin < 0:
		return "🔴", "УБЫТОК"
	elif current_margin < target_margin - 2:
		return "🟡", "Ниже цели"
	elif current_margin < target_margin + 5:
		return "🟢", "В норме"
	else:
		return "💚", "Отлично"


def get_commission_by_category(subject_name):
	"""
	Возвращает примерную комиссию по категории
	(запасной вариант если API не отдал)
	"""

	# Примерные комиссии по крупным категориям WB на 2025
	commissions = {
		"одежда": 24.5,
		"обувь": 24.5,
		"аксессуары": 24.5,
		"белье": 24.5,
		"косметика": 20.0,
		"парфюм": 20.0,
		"здоровье": 15.0,
		"электроника": 15.0,
		"техника": 15.0,
		"автотовары": 15.0,
		"инструменты": 15.0,
		"спорт": 22.0,
		"детск": 20.0,
		"игрушк": 20.0,
		"книг": 15.0,
		"канцтовар": 20.0,
		"для дома": 22.0,
		"мебель": 20.0,
		"посуда": 20.0,
		"продукт": 15.0,
		"зоотовар": 20.0,
		"сад": 20.0,
		"украшен": 25.0,
		"ювелир": 25.0,
	}

	if not subject_name:
		return 22.0  # по умолчанию

	subject_lower = str(subject_name).lower()

	for key, value in commissions.items():
		if key in subject_lower:
			return value

	return 22.0  # по умолчанию


def estimate_logistics(volume_liters):
	"""
	Оценка логистики по объёму (примерные тарифы WB FBO)
	"""

	if not volume_liters or volume_liters <= 0:
		return 65.0  # средняя

	if volume_liters <= 1:
		return 43.0
	elif volume_liters <= 5:
		return 65.0
	elif volume_liters <= 10:
		return 85.0
	elif volume_liters <= 20:
		return 120.0
	else:
		return 120.0 + (volume_liters - 20) * 5