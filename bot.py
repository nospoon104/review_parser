#!/usr/bin/env python3
from pathlib import Path
import sys
import asyncio
import os
import traceback

from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from core.config import get_config
from core.processor import ReviewProcessor
from core.jobs import create_job_dir, save_job_meta
from scripts.load_reviews_to_excel import build_excel_from_dir

print("DEBUG BOT FILE:", Path(__file__).resolve())
print("DEBUG CWD:", Path.cwd())
print("DEBUG PYTHON:", sys.executable)

config = get_config()
processor = ReviewProcessor()
processing_lock = asyncio.Lock()

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Не задана переменная окружения TELEGRAM_BOT_TOKEN")


MAIN_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📋 Инструкция"), KeyboardButton("📊 Статус")],
        [KeyboardButton("🏪 Сменить кафе"), KeyboardButton("🧠 ИИ-чистка")],
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
)


def build_cafe_menu():
    rows = []
    for cafe in config.cafe_options:
        rows.append([KeyboardButton(f"🏪 {cafe}")])
    rows.append([KeyboardButton("⬅ В меню")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False)


async def send_main_menu(message, text=None):
    if text is None:
        text = (
            "👋 Автоматизатор обработки отзывов АндерСОн\n\n"
            "Меню всегда под рукой. Выберите действие или просто вставьте отзывы одним сообщением."
        )
    await message.reply_text(text, reply_markup=MAIN_MENU)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_main_menu(update.message)


async def show_instruction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📋 Инструкция по сбору отзывов\n\n"
        "1. Откройте чат с отзывами\n"
        "2. Выделите большой блок сообщений\n"
        "3. Скопируйте всё одним куском\n"
        "4. Вставьте сюда одним сообщением\n\n"
        "Важно:\n"
        "- не разбивайте вручную на части\n"
        "- если текст очень большой, лучше прислать .txt файлом\n"
        "- можно копировать вместе с датами и именами"
    )
    await update.message.reply_text(text, reply_markup=MAIN_MENU)


async def show_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config.jobs_dir.mkdir(parents=True, exist_ok=True)
    jobs_dir = config.jobs_dir

    text = (
        f"📊 Текущий статус\n\n"
        f"Активное кафе: {processor.current_cafe}\n"
        f"Папка результатов по умолчанию:\n{config.output_dir}\n\n"
        f"Папка задач:\n{jobs_dir}"
    )
    await update.message.reply_text(text, reply_markup=MAIN_MENU)


async def show_cafe_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏪 Выберите кафе:",
        reply_markup=build_cafe_menu(),
    )


async def toggle_ai_normalizer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config = get_config()
    current = getattr(config, "ai_normalizer_enabled", True)

    new_state = not current

    if hasattr(config, "_config_instance") and config._config_instance:
        object.__setattr__(config._config_instance, "ai_normalizer_enabled", new_state)

    status = "✅ ВКЛЮЧЕНА" if new_state else "❌ ВЫКЛЮЧЕНА"

    await update.message.reply_text(
        f"🧠 ИИ-чистка отзывов: {status}\n\n"
        f"Сейчас нейросеть {'будет' if new_state else 'не будет'} "
        f"автоматически приводить кривые отзывы к нормальному виду перед парсингом и созданием таблицы.",
        reply_markup=MAIN_MENU,
    )


async def process_reviews_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    raw_text: str,
    source_type: str,
    original_filename: str | None = None,
):
    if len(raw_text) < 40:
        await update.message.reply_text(
            "📏 Слишком мало текста. Пришлите минимум 8–10 отзывов одним сообщением или .txt файлом.",
            reply_markup=MAIN_MENU,
        )
        return

    if len(raw_text) > config.max_text_length:
        await update.message.reply_text(
            "📦 Текст слишком большой для безопасной обработки сообщением. Лучше пришлите его .txt файлом. \nДля этого откройте блокнот на вашем компьютере, вставьте туда отзывы, сохраните файл и отправьте боту",
            reply_markup=MAIN_MENU,
        )
        return

    if processing_lock.locked():
        await update.message.reply_text(
            "⏳ Бот уже обрабатывает предыдущий запрос. Пожалуйста, подождите.",
            reply_markup=MAIN_MENU,
        )
        return

    async with processing_lock:
        cafe = processor.current_cafe
        user = update.effective_user
        chat = update.effective_chat

        config.jobs_dir.mkdir(parents=True, exist_ok=True)
        job_dir = create_job_dir(config.jobs_dir, cafe, user.id)

        (job_dir / "input.txt").write_text(raw_text, encoding="utf-8")

        save_job_meta(
            job_dir,
            {
                "user_id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "chat_id": chat.id,
                "source_type": source_type,
                "original_filename": original_filename,
                "cafe": cafe,
                "job_dir": str(job_dir),
            },
        )

        await update.message.reply_text(
            f"🔄 Обрабатываю отзывы для {cafe}...\n"
            f"Задача: {job_dir.name}\n"
            f"Это может занять до 5 минут.",
            reply_markup=MAIN_MENU,
        )

        try:
            result = processor.process(raw_text, cafe, output_dir=job_dir)
            q = result.get("quality_report", {}).get("counts", {})

            excel_file = build_excel_from_dir(job_dir)

            await update.message.reply_text(
                f"✅ Обработка завершена\n\n"
                f"Кафе: {cafe}\n"
                f"Всего отзывов: {q.get('reviews_total', 0)}\n"
                f"Полезных: {q.get('reviews_clean', 0)}\n"
                f"Отфильтровано шума: {q.get('reviews_noise', 0)}\n",
                reply_markup=MAIN_MENU,
            )

            if excel_file.exists():
                with open(excel_file, "rb") as f:
                    await context.bot.send_document(
                        chat_id=chat.id,
                        document=f,
                        filename="ГОТОВАЯ_ТАБЛИЦА.xlsx",
                        caption=f"Готовая таблица для {cafe}",
                    )
            else:
                await update.message.reply_text(
                    "⚠️ Не удалось создать Excel-файл.",
                    reply_markup=MAIN_MENU,
                )

        except Exception as e:
            tb = traceback.format_exc()
            (job_dir / "error.txt").write_text(tb, encoding="utf-8")

            await update.message.reply_text(
                f"🚨 Ошибка при обработке:\n{e}\n\nЗадача: {job_dir.name}",
                reply_markup=MAIN_MENU,
            )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()

    if text == "📋 Инструкция":
        await show_instruction(update, context)
        return

    if text == "📊 Статус":
        await show_status(update, context)
        return

    if text == "🏪 Сменить кафе":
        await show_cafe_menu(update, context)
        return

    if text == "⬅️ В меню":
        await send_main_menu(update.message)
        return

    if text.startswith("🏪 "):
        cafe_name = text.removeprefix("🏪 ").strip()
        if cafe_name in config.cafe_options:
            processor.set_cafe(cafe_name)
            await update.message.reply_text(
                f"✅ Кафе изменено на: {cafe_name}",
                reply_markup=MAIN_MENU,
            )
        else:
            await update.message.reply_text(
                "❌ Неизвестное кафе.",
                reply_markup=MAIN_MENU,
            )
        return

    if text == "🧠 ИИ-чистка":
        await toggle_ai_normalizer(update, context)
        return

    await process_reviews_request(
        update=update,
        context=context,
        raw_text=text,
        source_type="text",
    )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document

    if not document or not document.file_name.lower().endswith(".txt"):
        await update.message.reply_text(
            "Пришлите .txt файл с отзывами.",
            reply_markup=MAIN_MENU,
        )
        return

    if document.file_size and document.file_size > config.max_file_size_bytes:
        await update.message.reply_text(
            "📦 Файл слишком большой. Разбейте его или сократите содержимое.",
            reply_markup=MAIN_MENU,
        )
        return

    try:
        file = await document.get_file()
        file_bytes = await file.download_as_bytearray()

        try:
            raw_text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                raw_text = file_bytes.decode("utf-8-sig")
            except UnicodeDecodeError:
                raw_text = file_bytes.decode("cp1251")

    except Exception as e:
        await update.message.reply_text(
            f"🚨 Не удалось прочитать файл:\n{e}",
            reply_markup=MAIN_MENU,
        )
        return

    await process_reviews_request(
        update=update,
        context=context,
        raw_text=raw_text,
        source_type="document",
        original_filename=document.file_name,
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print("Exception while handling update:")
    traceback.print_exception(
        type(context.error),
        context.error,
        context.error.__traceback__,
    )


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_error_handler(error_handler)

    print("🤖 Бот запущен")
    print(f"Активное кафе: {processor.current_cafe}")
    config.jobs_dir.mkdir(parents=True, exist_ok=True)
    print(f"Jobs dir: {config.jobs_dir}")
    app.run_polling()


if __name__ == "__main__":
    main()
