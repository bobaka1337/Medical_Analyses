import requests
from bs4 import BeautifulSoup
import os
from cities import cities
from utils import update_or_add_products
from urllib.parse import quote

BASE_URL = "https://www.invitro.ru"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def parse_city_invitro(city_name, city_slug):
    url = f"{BASE_URL}/analizes/for-doctors/{quote(city_slug)}/"
    print(f"\n[Invitro] Парсинг {city_name}: {url}")

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Ошибка при загрузке страницы {url}: {e}")
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    items = soup.select('.analyzes-item')

    results = []
    for item in items:
        title_elem = item.select_one('.analyzes-item__title a')
        desc_elem = item.select_one('.analyzes-item__description')
        price_elem = item.select_one('.analyzes-item__total--sum')

        title = title_elem.text.strip() if title_elem else ''
        link = BASE_URL + title_elem['href'] if title_elem and title_elem.has_attr('href') else ''
        description = desc_elem.text.strip() if desc_elem else ''
        price = price_elem.text.strip() if price_elem else ''

        if title:
            results.append({
                'title': title,
                'link': link,
                'description': description,
                'price': price
            })

    print(f"— Найдено {len(results)} анализов в {city_name}")
    return results


def parse_all_invitro():
    os.makedirs("data", exist_ok=True)

    for city_name, city_info in cities.items():
        city_slug = city_info.get("invitro")
        if not city_slug or city_slug.strip() == "-":
            print(f"[!] Пропуск {city_name} — нет слуга для Invitro")
            continue

        rus_slug = city_info.get("slug", city_name.lower())  # русская транскрипция для имени файла

        analyses = parse_city_invitro(city_name, city_slug)

        if analyses:
            filepath = os.path.join("data", f"invitro_{rus_slug}.csv")
            update_or_add_products(analyses, filepath)
            print(f"[✓] Сохранено в {filepath}")
        else:
            print(f"[!] Нет данных для {city_name}")


def parse_invitro_for_city(city_name):
    city_info = cities.get(city_name)
    if not city_info or city_info.get("invitro") in [None, "-"]:
        print(f"[!] Город '{city_name}' не поддерживается Invitro.")
        return

    city_slug = city_info["invitro"]
    rus_slug = city_info.get("slug")
    if not rus_slug:
        rus_slug = city_name.lower().replace(" ", "-").replace("ё", "е")

    analyses = parse_city_invitro(city_name, city_slug)
    if analyses:
        os.makedirs("data", exist_ok=True)
        filepath = os.path.join("data", f"invitro_{rus_slug}.csv")
        update_or_add_products(analyses, filepath)
        print(f"[✓] Данные Invitro сохранены в {filepath}")
    else:
        print(f"[!] Нет данных Invitro для {city_name}")
