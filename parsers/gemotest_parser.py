import requests
from bs4 import BeautifulSoup
import os
from cities import cities
from utils import update_or_add_products

BASE_URL = "https://gemotest.ru"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def parse_city_gemotest(city_name, city_slug):
    print(f"\n[Гемотест] Парсинг {city_name}")

    base_url = f"{BASE_URL}/{city_slug}/catalog"
    urls = [
        f"{base_url}/",
        f"{base_url}/issledovaniya-krovi/gormony/",
        f"{base_url}/issledovaniya-krovi/biokhimiya/"
    ]

    results = []

    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            print(f"[Ошибка] Не удалось загрузить: {url} → {e}")
            continue

        soup = BeautifulSoup(resp.content, 'html.parser')
        items = soup.select('.analysis-item')

        for item in items:
            title = item.get('data-eec-name', '').strip()
            link_part = item.select_one('a.analysis-item__title')
            link = BASE_URL + link_part['href'] if link_part and link_part.has_attr('href') else ''
            price = item.get('data-eec-price', '').strip() + ' ₽' if item.get('data-eec-price') else ''

            if title:
                results.append({
                    'title': title,
                    'link': link,
                    'description': '',
                    'price': price
                })

    print(f"— Найдено {len(results)} анализов в {city_name}")
    return results


def parse_all_gemotest():
    os.makedirs("data", exist_ok=True)

    for city_name, city_info in cities.items():
        city_slug = city_info.get("gemotest")
        if not city_slug or city_slug.strip() == "-":
            print(f"[!] Пропуск {city_name} — нет слуга для Гемотеста")
            continue

        rus_slug = city_info.get("slug", city_name.lower().replace(" ", "-"))

        analyses = parse_city_gemotest(city_name, city_slug)

        if analyses:
            filepath = os.path.join("data", f"gemotest_{rus_slug}.csv")
            update_or_add_products(analyses, filepath)
            print(f"[✓] Сохранено в {filepath}")
        else:
            print(f"[!] Нет данных для {city_name}")


def parse_all_gemotest(city_name):
    city_info = cities.get(city_name)
    if not city_info or city_info.get("gemotest") in [None, "-"]:
        print(f"[!] Город '{city_name}' не поддерживается Гемотестом.")
        return

    city_slug = city_info["gemotest"]
    rus_slug = city_info.get("slug", city_name.lower().replace(" ", "-"))

    analyses = parse_city_gemotest(city_name, city_slug)
    if analyses:
        os.makedirs("data", exist_ok=True)
        filepath = os.path.join("data", f"gemotest_{rus_slug}.csv")
        update_or_add_products(analyses, filepath)
        print(f"[✓] Данные Гемотеста сохранены в {filepath}")
    else:
        print(f"[!] Нет данных Гемотеста для {city_name}")
