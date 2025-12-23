import csv
import os

def update_or_add_products(new_data, filename):
    if not new_data:
        print("Нет новых данных для обновления.")
        return

    if not os.path.exists(filename):
        with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=new_data[0].keys())
            writer.writeheader()
            writer.writerows(new_data)
        print(f"Файл {filename} создан и сохранено {len(new_data)} записей")
        return

    with open(filename, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        existing = list(reader)

    key_field = 'title'
    existing_dict = {item[key_field]: item for item in existing}

    updated_count = 0
    added_count = 0

    for new_item in new_data:
        key = new_item[key_field]
        if key in existing_dict:
            if existing_dict[key]['price'] != new_item['price']:
                existing_dict[key]['price'] = new_item['price']
                updated_count += 1
        else:
            existing_dict[key] = new_item
            added_count += 1

    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=new_data[0].keys())
        writer.writeheader()
        writer.writerows(existing_dict.values())

    print(f"Обновлено записей: {updated_count}, добавлено новых: {added_count}")