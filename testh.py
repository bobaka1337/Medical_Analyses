import json
import os
import requests
from utils import update_or_add_products
from cities import cities  # твой словарь городов с id Helix

def load_helix_cities(filename="helix_cities.json"):
    if not os.path.exists(filename):
        print(f"Файл {filename} не найден.")
        return []
    with open(filename, encoding="utf-8") as f:
        return json.load(f)

def get_helix_alias(city_id, helix_cities):
    for city in helix_cities:
        if city.get("id") == city_id:
            alias = city.get("alias")
            if alias and alias.strip():
                return alias
            else:
                # Если alias пустой, fallback на транслит (можно добавить unidecode)
                name = city.get("name", str(city_id))
                slug = name.lower().replace(" ", "-")
                return slug
    return None

def parse_helix(city_name, helix_cities):
    city_info = cities.get(city_name)
    if not city_info or city_info.get("helix") in [None, "-"]:
        print(f"[!] Город '{city_name}' не поддерживается Helix.")
        return

    city_id = city_info["helix"]
    city_slug = get_helix_alias(city_id, helix_cities)
    if not city_slug:
        print(f"[!] Не удалось получить alias для города с id={city_id}.")
        return

    category_id = 190
    take = 12
    skip = 0
    base_url = "https://helix.ru/api/catalog/items/list/v2"
    all_items = []

    # Первый запрос, чтобы узнать total
    params = {
        "cityId": city_id,
        "filter.categoryId": category_id,
        "pagination.take": take,
        "pagination.skip": skip,
    }

    try:
        r = requests.get(base_url, params=params)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"Ошибка при получении данных для города {city_name}: {e}")
        return

    total = data.get("total", 0)
    if total == 0:
        print("Нет анализов. Пропускаем.")
        return

    print(f"Всего анализов: {total}")

    while skip < total:
        params["pagination.skip"] = skip
        try:
            r = requests.get(base_url, params=params)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"Ошибка на skip={skip}: {e}")
            break

        items = data.get("catalogItems", [])
        if not items:
            print("catalogItems пустой. Прерываем.")
            break

        for item in items:
            hxid = item.get("hxid")
            title = item.get("title")
            price = item.get("price")
            url = f"https://helix.ru/{city_slug}/catalog/item/{hxid}"

            all_items.append({
                "title": title,
                "link": url,
                "price": str(price)
            })

        print(f"Парсим записи: {skip + 1} - {skip + len(items)}")
        skip += take

    if all_items:
        os.makedirs("data", exist_ok=True)
        filepath = f"data/helix_{city_slug}.csv"
        update_or_add_products(all_items, filepath)
        print(f"Сохранено: {filepath}")
    else:
        print("Не удалось собрать ни одного анализа.")

if __name__ == "__main__":
    helix_cities = load_helix_cities("helix_cities.json")
    # Пример запуска для Москвы:
    parse_helix("Москва", helix_cities)