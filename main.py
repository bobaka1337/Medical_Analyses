import os
import datetime
from parsers.invitro_parser import parse_invitro_for_city
from parsers.gemotest_parser import parse_all_gemotest
from parsers.helix import parse_helix, load_helix_cities
from comparator import compare_analyses
from cities import cities

def normalize_city_filename(city_name: str) -> str:
    return city_name.lower().replace(" ", "-").replace("ё", "е")

def is_file_fresh(filepath):
    if not os.path.exists(filepath):
        return False
    modified_time = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
    now = datetime.datetime.now()
    return modified_time.date() == now.date()

def main():
    helix_cities = load_helix_cities("helix_cities.json")

    user_city_input = input("Введите название города (например, Рязань): ").strip()
    city_name = None
    for city_key in cities.keys():
        if city_key.lower() == user_city_input.lower():
            city_name = city_key
            break

    if not city_name:
        print(f"Город '{user_city_input}' не найден в базе.")
        return

    city_info = cities[city_name]
    invitro_slug = city_info.get("invitro")
    gemotest_slug = city_info.get("gemotest")
    helix_id = city_info.get("helix")

    city_filename = normalize_city_filename(city_name)

    invitro_path = f"data/invitro_{city_filename}.csv"
    gemotest_path = f"data/gemotest_{city_filename}.csv"
    helix_path = f"data/helix_{city_filename}.csv"

    msg = ""

    if not invitro_slug or invitro_slug == "-":
        msg += f"Нет данных Invitro для города {city_name}\n"
    else:
        if not is_file_fresh(invitro_path):
            msg += f"Сбор информации Invitro для города: {city_name}...\n"
            parse_invitro_for_city(city_name)

    if not gemotest_slug or gemotest_slug == "-":
        msg += f"Нет данных Gemotest для города {city_name}\n"
    else:
        if not is_file_fresh(gemotest_path):
            msg += f"Сбор информации Gemotest для города: {city_name}...\n"
            parse_all_gemotest(city_name)

    if not helix_id or helix_id == "-":
        msg += f"Нет данных Helix для города {city_name}\n"
    else:
        if not is_file_fresh(helix_path):
            msg += f"Сбор информации Helix для города: {city_name}...\n"
            parse_helix(city_name, helix_cities)

    if msg:
        print(msg.strip())

    analysis_names = input("\nВведите названия анализов через запятую для сравнения: ").split(",")
    compare_analyses([x.strip() for x in analysis_names], city_filename)

if __name__ == "__main__":
    main()