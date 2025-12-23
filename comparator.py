import pandas as pd
from fuzzywuzzy import process
import os
import re
from synonym import SYNONYMS
from cities import cities  # словарь городов с id Helix

DATA_DIR = os.path.join("data")

def clean_price(price_str):
    if pd.isna(price_str):
        return None
    if isinstance(price_str, bytes):
        price_str = price_str.decode('utf-8')
    else:
        price_str = str(price_str)
    price_num = re.sub(r"[^\d,\.]", "", price_str)
    price_num = price_num.replace(',', '.')
    try:
        return float(price_num)
    except:
        return None

def format_price(price):
    if price is None:
        return "—"
    return f"{price:,.0f} ₽".replace(",", " ")

def normalize_input(user_input, threshold=85):
    user_input = user_input.strip().lower()
    
    # Точный поиск по синонимам
    for canonical, variants in SYNONYMS.items():
        if user_input == canonical.lower() or user_input in map(str.lower, variants):
            return canonical
    
    # Fuzzy поиск по всем вариантам
    all_terms = []
    mapping = {}
    for canonical, variants in SYNONYMS.items():
        all_terms.append(canonical)
        mapping[canonical] = canonical
        for variant in variants:
            all_terms.append(variant)
            mapping[variant] = canonical

    match, score = process.extractOne(user_input, all_terms)
    if match and score >= threshold:
        return mapping[match]
    
    return user_input

def find_best_match(name, choices, threshold=60):
    match, score = process.extractOne(name, choices)
    return match if score >= threshold else None

def get_helix_alias(city_id, helix_cities):
    for city in helix_cities:
        if city.get("id") == city_id:
            alias = city.get("alias")
            if alias and alias.strip():
                return alias
            else:
                name = city.get("name", str(city_id))
                slug = name.lower().replace(" ", "-")
                return slug
    return None

def fix_helix_link(link, city_rus_slug, helix_cities):
    city_info = cities.get(city_rus_slug)
    if not city_info:
        return link
    city_id = city_info.get("helix")
    if not city_id:
        return link
    alias = get_helix_alias(city_id, helix_cities)
    if not alias:
        return link
    
    # Заменяем в ссылке русскоязычный slug города на alias, учитывая регистр
    # Обычно ссылка имеет формат https://helix.ru/<город>/catalog/item/...
    # Находим в ссылке часть с городом и меняем на alias
    parts = link.split('/')
    # parts[3] — это город в ссылке (по формату: https://helix.ru/{city_slug}/catalog/item/{hxid})
    if len(parts) > 3:
        # Заменяем часть с городом на alias
        parts[3] = alias
        fixed_link = '/'.join(parts)
        return fixed_link
    else:
        return link

def compare_analyses(analysis_names, city_rus_slug, helix_cities):
    invitro_path = os.path.join(DATA_DIR, f"invitro_{city_rus_slug}.csv")
    gemotest_path = os.path.join(DATA_DIR, f"gemotest_{city_rus_slug}.csv")
    helix_path = os.path.join(DATA_DIR, f"helix_{city_rus_slug}.csv")

    for path in [invitro_path, gemotest_path, helix_path]:
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Файл не найден: {path}")

    invitro_df = pd.read_csv(invitro_path, encoding='utf-8-sig')
    gemotest_df = pd.read_csv(gemotest_path, encoding='utf-8-sig')
    helix_df = pd.read_csv(helix_path, encoding='utf-8-sig')

    invitro_df['title_lower'] = invitro_df['title'].str.lower()
    gemotest_df['title_lower'] = gemotest_df['title'].str.lower()
    helix_df['title_lower'] = helix_df['title'].str.lower()

    results = []

    for user_input in analysis_names:
        normalized_input = normalize_input(user_input)

        invitro_match = find_best_match(normalized_input, invitro_df["title_lower"].tolist())
        gemotest_match = find_best_match(normalized_input, gemotest_df["title_lower"].tolist())
        helix_match = find_best_match(normalized_input, helix_df["title_lower"].tolist())

        if invitro_match:
            i_row = invitro_df[invitro_df["title_lower"] == invitro_match].iloc[0]
            i_price = clean_price(i_row["price"])
            i_link = i_row["link"]
            i_name = i_row["title"]
        else:
            i_price = None
            i_link = None
            i_name = None

        if gemotest_match:
            g_row = gemotest_df[gemotest_df["title_lower"] == gemotest_match].iloc[0]
            g_price = clean_price(g_row["price"])
            g_link = g_row["link"]
            g_name = g_row["title"]
        else:
            g_price = None
            g_link = None
            g_name = None

        if helix_match:
            h_row = helix_df[helix_df["title_lower"] == helix_match].iloc[0]
            h_price = clean_price(h_row["price"])
            h_link_raw = h_row["link"]
            h_name = h_row["title"]

            # Исправляем ссылку Helix с alias города
            h_link = fix_helix_link(h_link_raw, city_rus_slug, helix_cities)
        else:
            h_price = None
            h_link = None
            h_name = None

        prices = []
        if i_price is not None:
            prices.append(("Инвитро", i_price, i_link))
        if g_price is not None:
            prices.append(("Гемотест", g_price, g_link))
        if h_price is not None:
            prices.append(("Хеликс", h_price, h_link))

        if prices:
            cheapest = min(prices, key=lambda x: x[1])
            cheapest_lab, cheapest_price, cheapest_link = cheapest
        else:
            cheapest_lab, cheapest_price, cheapest_link = None, None, None

        results.append({
            "user_input": user_input.strip(),
            "invitro": {"name": i_name, "price": i_price, "link": i_link},
            "gemotest": {"name": g_name, "price": g_price, "link": g_link},
            "helix": {"name": h_name, "price": h_price, "link": h_link},
            "cheapest": {"lab": cheapest_lab, "price": cheapest_price, "link": cheapest_link},
        })

    return results

