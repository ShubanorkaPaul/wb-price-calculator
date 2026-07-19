"""
Модуль расчёта цен и юнит-экономики
С учётом возвратов и точки безубыточности
"""

import math

ACQUIRING = 0.015  # Эквайринг 1.5%


def safe_float(val, default=0.0):
    try:
        if val is None:
            return default
        v = float(val)
        if math.isnan(v) or math.isinf(v):
            return default
        return v
    except:
        return default


def calculate_current_profit(
    price_with_discount, 
    commission_percent, 
    logistics, 
    cost_price, 
    buyout_rate=0.90, 
    tax_rate=0.06, 
    acceptance_fee=0,
    return_processing_fee=30,
    damage_rate=0.10
):
    """Считает текущую прибыль по товару с полным учётом возвратов"""
    p = safe_float(price_with_discount, 0.0)
    cp = safe_float(commission_percent, 22.0)
    log = safe_float(logistics, 65.0)
    cost = safe_float(cost_price, 0.0)
    bo = safe_float(buyout_rate, 0.90)
    tr = safe_float(tax_rate, 0.06)
    acc = safe_float(acceptance_fee, 0.0)
    r_proc = safe_float(return_processing_fee, 30.0)
    dmg = safe_float(damage_rate, 0.10)

    commission = p * (cp / 100.0)
    acquiring = p * ACQUIRING

    return_rate = max(0.0, min(1.0, 1.0 - bo))
    return_logistics = log
    return_processing = r_proc
    return_damage = cost * dmg
    
    cost_per_return = return_logistics + return_processing + return_damage
    returns_cost = cost_per_return * return_rate

    for_pay = p - commission - acquiring - log - returns_cost - acc
    tax = p * tr
    profit = for_pay - cost - tax

    margin = (profit / p * 100.0) if p > 0 else 0.0

    return {
        "price": p,
        "commission": round(commission, 2),
        "acquiring": round(acquiring, 2),
        "logistics": round(log, 2),
        "returns_cost": round(returns_cost, 2),
        "return_logistics": round(return_logistics * return_rate, 2),
        "return_processing": round(return_processing * return_rate, 2),
        "return_damage": round(return_damage * return_rate, 2),
        "acceptance_fee": round(acc, 2),
        "tax": round(tax, 2),
        "cost_price": round(cost, 2),
        "for_pay": round(for_pay, 2),
        "profit": round(profit, 2),
        "margin": round(margin, 2),
    }


def calculate_break_even_price(
    cost_price,
    commission_percent,
    logistics,
    buyout_rate=0.90,
    tax_rate=0.06,
    acceptance_fee=0,
    return_processing_fee=30,
    damage_rate=0.10
):
    """
    Рассчитывает ТОЧКУ БЕЗУБЫТОЧНОСТИ
    """
    cost = safe_float(cost_price, 0.0)
    cp = safe_float(commission_percent, 22.0)
    log = safe_float(logistics, 65.0)
    bo = safe_float(buyout_rate, 0.90)
    tr = safe_float(tax_rate, 0.06)
    acc = safe_float(acceptance_fee, 0.0)
    r_proc = safe_float(return_processing_fee, 30.0)
    dmg = safe_float(damage_rate, 0.10)

    commission_rate = cp / 100.0
    return_rate = max(0.0, min(1.0, 1.0 - bo))
    
    return_logistics = log
    return_processing = r_proc
    return_damage = cost * dmg
    cost_per_return = return_logistics + return_processing + return_damage
    returns_cost = cost_per_return * return_rate
    
    denominator = 1.0 - commission_rate - ACQUIRING - tr
    
    if denominator <= 0:
        return None
    
    break_even = (log + returns_cost + acc + cost) / denominator
    
    return round(break_even, 2)


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
    acceptance_fee=0,
    return_processing_fee=30,
    damage_rate=0.10
):
    """Считает рекомендуемую цену исходя из целевой маржи"""
    cost = safe_float(cost_price, 0.0)
    cp = safe_float(commission_percent, 22.0)
    log = safe_float(logistics, 65.0)
    tm = safe_float(target_margin, 20.0)
    cd = safe_float(current_discount, 0.0)
    md = safe_float(max_discount, 30.0)
    mdc = safe_float(max_discount_change, 5.0)
    bo = safe_float(buyout_rate, 0.90)
    tr = safe_float(tax_rate, 0.06)
    acc = safe_float(acceptance_fee, 0.0)
    r_proc = safe_float(return_processing_fee, 30.0)
    dmg = safe_float(damage_rate, 0.10)

    commission_rate = cp / 100.0
    margin_rate = tm / 100.0
    return_rate = max(0.0, min(1.0, 1.0 - bo))
    
    return_logistics = log
    return_processing = r_proc
    return_damage = cost * dmg
    cost_per_return = return_logistics + return_processing + return_damage
    returns_cost = cost_per_return * return_rate

    denominator = 1.0 - commission_rate - ACQUIRING - tr - margin_rate

    if denominator <= 0:
        return None

    price_with_discount = (log + returns_cost + acc + cost) / denominator

    if keep_discount:
        new_discount = cd
    else:
        if cd > md:
            new_discount = max(cd - mdc, md)
        elif cd < md:
            new_discount = cd
        else:
            new_discount = md
    
    if not keep_discount:
        new_discount = min(new_discount, md)

    if new_discount > 0 and new_discount < 100:
        price_without_discount = price_with_discount / (1.0 - new_discount / 100.0)
    else:
        price_without_discount = price_with_discount

    price_without_discount = round(price_without_discount / 10.0) * 10.0
    price_with_discount = price_without_discount * (1.0 - new_discount / 100.0)

    result = calculate_current_profit(
        price_with_discount, cp, log, cost, 
        bo, tr, acc,
        r_proc, dmg
    )
    result["price_without_discount"] = price_without_discount
    result["price_with_discount"] = price_with_discount
    result["discount_percent"] = new_discount
    result["discount_change"] = new_discount - cd

    return result


def get_status(current_margin, target_margin):
    cm = safe_float(current_margin, 0.0)
    tm = safe_float(target_margin, 20.0)
    if cm < 0:
        return "🔴", "УБЫТОК"
    elif cm < tm - 2:
        return "🟡", "Ниже цели"
    elif cm < tm + 5:
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
            if str(model).upper() == "FBS": return max(value - 4, 10)
            return value
    return 22.0 if str(model).upper() == "FBO" else 18.0


def estimate_logistics(volume_liters, model="FBO"):
    v = safe_float(volume_liters, 0.0)
    if v <= 0: base = 65.0
    elif v <= 1: base = 43.0
    elif v <= 5: base = 65.0
    elif v <= 10: base = 85.0
    elif v <= 20: base = 120.0
    else: base = 120.0 + (v - 20) * 5

    if str(model).upper() == "FBS": base = base * 1.25
    return round(base, 2)
