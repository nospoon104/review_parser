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
    return f"""Ты — помощник, который готовит текст отзывов специально для парсера.

Твоя задача — **максимально сохранить оригинальную структуру** отзывов, но привести текст к чистому и удобному виду.

Правила:
- Каждый отзыв должен начинаться с новой строки.
- Если в начале отзыва есть "Стол X" — оставляй его в начале строки.
- Формат должен быть примерно таким:
  Стол 7: текст отзыва здесь
  Стол 14: другой текст отзыва
- Если есть реплики вроде ">Алексей:" или "Максим, добавь это в отчет" — оставляй их как отдельные строки.
- Не добавляй префиксы "[Дата неизвестна] Гость:" везде. Это ломает парсер.
- Исправляй только грубые опечатки.
- Не склеивай разные столы в один отзыв.
- Выводи **только** обработанный текст, без каких-либо объяснений.

Вот сырой текст:

{raw_text}

Обработанный текст (только чистые отзывы, каждый с новой строки):"""


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
