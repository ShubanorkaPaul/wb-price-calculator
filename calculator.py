"""
Модуль расчёта цен и юнит-экономики
"""

ACQUIRING = 0.015  # Эквайринг 1.5%


def calculate_current_profit(price_with_discount, commission_percent, logistics, cost_price, buyout_rate=0.90, tax_rate=0.06, acceptance_fee=0):
    """Считает текущую прибыль по товару"""

    commission = price_with_discount * (commission_percent / 100)
    acquiring = price_with_discount * ACQUIRING

    return_rate = 1 - buyout_rate
    returns_cost = logistics * return_rate

    for_pay = price_with_discount - commission - acquiring - logistics - returns_cost - acceptance_fee
    tax = price_with_discount * tax_rate
    profit = for_pay - cost_price - tax

    margin = (profit / price_with_discount * 100) if price_with_discount > 0 else 0

    return {
        "price": price_with_discount,
        "commission": round(commission, 2),
        "acquiring": round(acquiring, 2),
        "logistics": round(logistics, 2),
        "returns_cost": round(returns_cost, 2),
        "acceptance_fee": round(acceptance_fee, 2),
        "tax": round(tax, 2),
        "cost_price": round(cost_price, 2),
        "for_pay": round(for_pay, 2),
        "profit": round(profit, 2),
        "margin": round(margin, 2),
    }


def calculate_recommended_price(
    cost_price,
    commission_percent,
    logistics,
    target_margin,
    current_discount=0,
    max_discount=30,
    max_discount_change=5,
    keep_discount=False,
    buyout_rate=0.90,
    tax_rate=0.06,
    acceptance_fee=0
):
    """
    Считает рекомендуемую цену исходя из целевой маржи.
    Защита от гигантских цен: скидка ограничивается max_discount.
    """

    commission_rate = commission_percent / 100
    margin_rate = target_margin / 100
    return_rate = 1 - buyout_rate
    returns_cost = logistics * return_rate

    denominator = 1 - commission_rate - ACQUIRING - tax_rate - margin_rate

    if denominator <= 0:
        return None

    # Считаем нужную цену для покупателя (со скидкой)
    price_with_discount = (logistics + returns_cost + acceptance_fee + cost_price) / denominator

    # Определяем целевую скидку
    if keep_discount:
        new_discount = current_discount
    else:
        if current_discount > max_discount:
            # Плавно снижаем: не больше чем на max_discount_change за раз
            new_discount = max(current_discount - max_discount_change, max_discount)
        elif current_discount < max_discount:
            # Не повышаем искусственно
            new_discount = current_discount
        else:
            new_discount = max_discount
    
    # Защита от гигантской цены
    if not keep_discount:
        new_discount = min(new_discount, max_discount)

    # Считаем цену до скидки
    if new_discount > 0 and new_discount < 100:
        price_without_discount = price_with_discount / (1 - new_discount / 100)
    else:
        price_without_discount = price_with_discount

    # Округляем до красивых цифр
    price_without_discount = round(price_without_discount / 10) * 10
    price_with_discount = price_without_discount * (1 - new_discount / 100)

    result = calculate_current_profit(
        price_with_discount, commission_percent, logistics, cost_price, 
        buyout_rate, tax_rate, acceptance_fee
    )
    result["price_without_discount"] = price_without_discount
    result["price_with_discount"] = price_with_discount
    result["discount_percent"] = new_discount
    result["discount_change"] = new_discount - current_discount

    return result


def get_status(current_margin, target_margin):
    if current_margin < 0:
        return "🔴", "УБЫТОК"
    elif current_margin < target_margin - 2:
        return "🟡", "Ниже цели"
    elif current_margin < target_margin + 5:
        return "🟢", "В норме"
    else:
        return "💚", "Отлично"


def get_commission_by_category(subject_name, model="FBO"):
    commissions_fbo = {
        "одежда": 24.5, "обувь": 24.5, "аксессуары": 24.5, "белье": 24.5,
        "косметика": 20.0, "парфюм": 20.0, "здоровье": 15.0, "электроника": 15.0,
        "техника": 15.0, "автотовары": 15.0, "инструменты": 15.0, "спорт": 22.0,
        "детск": 20.0, "игрушк": 20.0, "книг": 15.0, "канцтовар": 20.0,
        "для дома": 22.0, "мебель": 20.0, "посуда": 20.0, "продукт": 15.0,
        "зоотовар": 20.0, "сад": 20.0, "украшен": 25.0, "ювелир": 25.0,
        "набор": 22.0, "опыт": 22.0,
    }
    if not subject_name: return 22.0
    subject_lower = str(subject_name).lower()
    for key, value in commissions_fbo.items():
        if key in subject_lower:
            if model == "FBS": return max(value - 4, 10)
            return value
    return 22.0 if model == "FBO" else 18.0


def estimate_logistics(volume_liters, model="FBO"):
    if not volume_liters or volume_liters <= 0: base = 65.0
    elif volume_liters <= 1: base = 43.0
    elif volume_liters <= 5: base = 65.0
    elif volume_liters <= 10: base = 85.0
    elif volume_liters <= 20: base = 120.0
    else: base = 120.0 + (volume_liters - 20) * 5

    if model == "FBS": base = base * 1.25
    return round(base, 2)
