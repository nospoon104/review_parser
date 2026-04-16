import json
import hashlib
from pathlib import Path
import requests
from typing import Optional
from core.config import get_config
import os

config = get_config()

# Папка для кэша
CACHE_DIR = config.base_dir / "cache" / "ai_normalizer"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

CHAD_API_URL = (
    "https://ask.chadgpt.ru/api/public/gpt-5.4-nano"  # самая лёгкая и дешёвая
)


def get_cache_key(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def load_from_cache(cache_key: str) -> Optional[str]:
    cache_file = CACHE_DIR / f"{cache_key}.txt"
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8")
    return None


def save_to_cache(cache_key: str, normalized_text: str) -> None:
    cache_file = CACHE_DIR / f"{cache_key}.txt"
    cache_file.write_text(normalized_text, encoding="utf-8")


def build_prompt(raw_text: str) -> str:
    return f"""Ты — предобработчик отзывов для парсера ресторана.

Твоя задача — привести текст к формату, который **идеально** разбирается существующим парсером.

Правила (строго):
- Каждый отзыв должен начинаться с "Стол X:" или "Стол X " в начале строки.
- Не добавляй никаких "[Дата неизвестна]", "[Гость]", "Гость:" и т.п. — это ломает парсер.
- Сохраняй оригинальные номера столов.
- Реплики менеджеров (типа ">Алексей:", "Максим, добавь это в отчет") оставляй как отдельные строки.
- Не объединяй разные столы в один отзыв.
- Исправляй только явные опечатки, остальное оставляй близко к оригиналу.
- Выводи ТОЛЬКО чистый текст, без объяснений.

Пример желаемого вывода:
Стол 7: эта их утиная ножка ваще не прожаренная была пипец холодная внутри официантка извинилась убрала из счета но всё равно неприятно блин
>Алексей: ладно запишем негатив по кухне
Стол 14: рулет фисташковый обалденный но официант долго не подходил минут 25 ждали кофе
Максим, добавь это в отчет пожалуйста
Стол 119: ну че сказать борщ был теплый а не горячий, пельмени вообще резиновые, официант молодой вообще не знал что делать, в итоге сделали комплимент и извинились но впечатление испорчено.
Стол 111: салат цезарь был с теплыми креветками это странно очень, но индейка в азиатском на второе было огонь

Текст для обработки:

{raw_text}

Выдай только обработанный текст:"""


def normalize_with_ai(raw_text: str) -> str:
    if not raw_text or len(raw_text.strip()) < 40:
        return raw_text

    cache_key = get_cache_key(raw_text)
    cached = load_from_cache(cache_key)
    if cached:
        print("=== AI NORMALIZER: взято из кэша ===")
        return cached

    api_key = os.getenv("CHAD_API_KEY")
    if not api_key:
        print("=== AI NORMALIZER: CHAD_API_KEY не найден, пропускаем ===")
        return raw_text

    try:
        prompt = build_prompt(raw_text)

        request_json = {"message": prompt, "api_key": api_key}

        response = requests.post(url=CHAD_API_URL, json=request_json, timeout=30)

        if response.status_code != 200:
            print(f"=== AI NORMALIZER: HTTP ошибка {response.status_code} ===")
            return raw_text

        resp_json = response.json()

        if not resp_json.get("is_success", False):
            error = resp_json.get("error_message", "Неизвестная ошибка")
            print(f"=== AI NORMALIZER: ошибка API: {error} ===")
            return raw_text

        normalized = resp_json.get("response", "").strip()

        if normalized:
            save_to_cache(cache_key, normalized)
            used = resp_json.get("used_words_count", 0)
            print(f"=== AI NORMALIZER: успешно обработал (потрачено слов: {used}) ===")
            return normalized

        return raw_text

    except Exception as e:
        print(f"=== AI NORMALIZER: исключение, работаем без ИИ: {e} ===")
        return raw_text
