#!/usr/bin/env python3
from pathlib import Path
import sys

print("DEBUG BOT FILE:", Path(__file__).resolve())
print("DEBUG CWD:", Path.cwd())
print("DEBUG PYTHON:", sys.executable)

import asyncio
import os
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
from scripts.load_reviews_to_excel import main as run_excel_converter

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
        [KeyboardButton("🏪 Сменить кафе")],
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
)


def build_cafe_menu():
    rows = []
    for cafe in config.cafe_options:
        rows.append([KeyboardButton(f"🏪 {cafe}")])
    rows.append([KeyboardButton("⬅️ В меню")])
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
    text = (
        f"📊 Текущий статус\n\n"
        f"Активное кафе: {processor.current_cafe}\n"
        f"Папка с результатами:\n{config.output_dir}"
    )
    await update.message.reply_text(text, reply_markup=MAIN_MENU)


async def show_cafe_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏪 Выберите кафе:",
        reply_markup=build_cafe_menu(),
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

    if len(text) < 40:
        await update.message.reply_text(
            "📏 Слишком мало текста. Пришлите минимум 8–10 отзывов одним сообщением или .txt файлом.",
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

        await update.message.reply_text(
            f"🔄 Обрабатываю отзывы для {cafe}...\nЭто может занять 15–25 секунд.",
            reply_markup=MAIN_MENU,
        )

        try:
            result = processor.process(text, cafe)
            q = result.get("quality_report", {}).get("counts", {})

            await update.message.reply_text(
                f"✅ Обработка завершена\n\n"
                f"Кафе: {cafe}\n"
                f"Всего отзывов: {q.get('reviews_total', 0)}\n"
                f"Полезных: {q.get('reviews_clean', 0)}\n"
                f"Отфильтровано шума: {q.get('reviews_noise', 0)}",
                reply_markup=MAIN_MENU,
            )

            run_excel_converter()
            excel_file = config.output_dir / "ГОТОВАЯ_ТАБЛИЦА.xlsx"

            if excel_file.exists():
                with open(excel_file, "rb") as f:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
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
            await update.message.reply_text(
                f"🚨 Ошибка при обработке:\n{e}",
                reply_markup=MAIN_MENU,
            )


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if processing_lock.locked():
        await update.message.reply_text(
            "⏳ Бот уже обрабатывает предыдущий запрос. Пожалуйста, подождите.",
            reply_markup=MAIN_MENU,
        )
        return

    document = update.message.document
    if not document or not document.file_name.lower().endswith(".txt"):
        await update.message.reply_text(
            "Пришлите .txt файл с отзывами.",
            reply_markup=MAIN_MENU,
        )
        return

    async with processing_lock:
        cafe = processor.current_cafe
        status_msg = await update.message.reply_text(
            f"🔄 Загружаю и обрабатываю файл для {cafe}...",
            reply_markup=MAIN_MENU,
        )

        try:
            file = await document.get_file()
            file_bytes = await file.download_as_bytearray()
            raw_text = file_bytes.decode("utf-8")

            result = processor.process(raw_text, cafe)
            q = result.get("quality_report", {}).get("counts", {})

            await update.message.reply_text(
                f"✅ Обработка завершена\n\n"
                f"Кафе: {cafe}\n"
                f"Всего отзывов: {q.get('reviews_total', 0)}\n"
                f"Полезных: {q.get('reviews_clean', 0)}\n"
                f"Отфильтровано шума: {q.get('reviews_noise', 0)}"
            )

            run_excel_converter()
            excel_file = config.output_dir / "ГОТОВАЯ_ТАБЛИЦА.xlsx"

            if excel_file.exists():
                with open(excel_file, "rb") as f:
                    await context.bot.send_document(
                        chat_id=update.effective_chat.id,
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
            await update.message.reply_text(f"🚨 Ошибка при обработке:\n{e}")


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🤖 Бот запущен")
    print(f"Активное кафе: {processor.current_cafe}")
    app.run_polling()


if __name__ == "__main__":
    main()
