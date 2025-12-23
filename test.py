import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from cities import cities
from comparator import compare_analyses
from parsers.invitro_parser import parse_invitro_for_city
from parsers.gemotest_parser import parse_all_gemotest
from parsers.helix import parse_helix
import os
import datetime

# Настройка логгирования — вывод в консоль с уровнем INFO и выше
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

user_states = {}

def format_results(results):
    messages = []
    for r in results:
        lines = []
        lines.append(f"🔬 *{r['user_input'].capitalize()}*")
        cheapest = r['cheapest']
        if cheapest["lab"]:
            lines.append(f"💰 Самая дешевая: [{cheapest['lab']}]({cheapest['link']}) — *{cheapest['price']:.0f} ₽*")
        else:
            lines.append("💰 Самая дешевая: *нет данных*")
        for lab in ["invitro", "gemotest", "helix"]:
            data = r[lab]
            name = data["name"] or "—"
            price = data["price"]
            price_str = f"*{price:.0f} ₽*" if price is not None else "—"
            link = data["link"] or ""
            lab_display = lab.capitalize()
            if link:
                lines.append(f"• {lab_display}: [{name}]({link}) — {price_str}")
            else:
                lines.append(f"• {lab_display}: {name} — {price_str}")
        messages.append("\n".join(lines))
    return "\n\n".join(messages)

def is_file_fresh(path, max_age_hours=24):
    """Проверяет, что файл существует и не старше max_age_hours"""
    if not os.path.exists(path):
        return False
    mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(path))
    age = datetime.datetime.now() - mod_time
    return age.total_seconds() < max_age_hours * 3600

def find_city_in_cities(user_input):
    """Ищет город в словаре cities без учета регистра, пробелов и дефисов"""
    normalized_input = user_input.lower().replace(" ", "").replace("-", "")
    for city_key in cities.keys():
        normalized_key = city_key.lower().replace(" ", "").replace("-", "")
        if normalized_input == normalized_key:
            return city_key
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info(f"/start от пользователя {update.effective_user.id}")
    faq_text = (
        "👋 Привет! Это бот для поиска анализов по городам.\n\n"
        "📍 Напиши название города, например: Москва\n"
        "🔁 Чтобы вернуться к выбору города, пропиши /start\n\n"
        "⚠️ Важно: вводи точные названия анализов, например:\n"
        "  — Анализ мочи\n"
        "  — Витамин D\n\n"
        "Если хочешь завершить диалог — напиши /stop"
    )
    await update.message.reply_text(faq_text)
    user_states[update.effective_user.id] = {"step": "await_city", "analyses": []}

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    logging.info(f"Получено сообщение от {user_id}: {text}")

    if user_id not in user_states:
        await update.message.reply_text("Напиши /start чтобы начать.")
        logging.info(f"Пользователь {user_id} не в состоянии, предложено начать /start")
        return

    state = user_states[user_id]

    if text.lower() == "/stop":
        await update.message.reply_text("Диалог завершён. Спасибо!")
        user_states.pop(user_id)
        logging.info(f"Пользователь {user_id} завершил диалог командой /stop")
        return

    if state["step"] == "await_city":
        city_name = find_city_in_cities(text)
        if not city_name:
            await update.message.reply_text("Город не найден. Попробуйте ещё раз.")
            logging.warning(f"Пользователь {user_id} ввел несуществующий город: {text}")
            return

        state["city"] = city_name
        state["step"] = "await_analyses"
        await update.message.reply_text(
            f"Город выбран: {city_name}\n"
            "Теперь введи через запятую точные названия анализов для сравнения.\n"
            "Например: Анализ мочи, Витамин D"
        )
        logging.info(f"Пользователь {user_id} выбрал город {city_name}")

    elif state["step"] == "await_analyses":
        new_analyses = [x.strip() for x in text.split(",") if x.strip()]
        state["analyses"].extend(new_analyses)
        logging.info(f"Пользователь {user_id} добавил анализы: {new_analyses}")

        city_key = state["city"]
        city_info = cities[city_key]

        invitro_slug = city_info.get("invitro")
        gemotest_slug = city_info.get("gemotest")
        helix_id = city_info.get("helix")

        city_filename = city_key.lower()

        invitro_path = os.path.join("data", f"invitro_{city_filename}.csv")
        gemotest_path = os.path.join("data", f"gemotest_{city_filename}.csv")
        helix_path = os.path.join("data", f"helix_{city_filename}.csv")

        await update.message.reply_text("Обновляю данные, если нужно...")
        logging.info(f"Пользователь {user_id}: обновление данных для города {city_key}")

        try:
            if invitro_slug and invitro_slug != "-":
                if not is_file_fresh(invitro_path):
                    logging.info(f"Обновление Invitro для города {city_key}")
                    parse_invitro_for_city(city_key)

            if gemotest_slug and gemotest_slug != "-":
                if not is_file_fresh(gemotest_path):
                    logging.info(f"Обновление Gemotest для города {city_key}")
                    parse_all_gemotest(city_key)

            if helix_id and helix_id != "-":
                if not is_file_fresh(helix_path):
                    logging.info(f"Обновление Helix для города {city_key}")
                    parse_helix(city_key)
        except Exception as e:
            await update.message.reply_text(f"Ошибка при обновлении данных: {e}")
            logging.error(f"Ошибка обновления данных для пользователя {user_id}: {e}")
            user_states.pop(user_id)
            return

        await update.message.reply_text("Данные обновлены, ищу результаты...")
        logging.info(f"Пользователь {user_id}: поиск результатов для анализов")

        try:
            results = compare_analyses(state["analyses"], city_filename)
        except FileNotFoundError as e:
            await update.message.reply_text(str(e))
            logging.error(f"Файл не найден для пользователя {user_id}: {e}")
            user_states.pop(user_id)
            return

        msg = format_results(results)
        await update.message.reply_text(msg, parse_mode="Markdown", disable_web_page_preview=True)
        logging.info(f"Пользователь {user_id}: отправлены результаты")

        await update.message.reply_text(
            "Если хотите добавить ещё анализы — введите их через запятую.\n"
            "Или напишите /stop для завершения."
        )


def main():
    logging.info("Запуск бота")
    app = ApplicationBuilder().token("8285888480:AAHdhlwXehmKBoMdNE4zr_igXnchb0JoOwI").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logging.info("Бот запущен и ожидает сообщений")
    app.run_polling()


if __name__ == "__main__":
    main()