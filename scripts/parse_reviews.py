import re
import csv
from pathlib import Path
import sys
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from scripts.catalogs import (
    DEFAULT_DISHES,
    DISH_ALIASES,
    REVIEW_TAG_KEYWORDS,
    FALLBACK_DISH_TAG_BY_NAME_KEYWORDS,
)

from core.config import get_config

config = get_config()


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
INPUT_FILE = BASE_DIR / "ПОЛОЖИТЬ_СЮДА_ФАЙЛ_С_ОТЗЫВАМИ" / "raw_reviews.txt"
OUTPUT_DIR = BASE_DIR / "ГОТОВЫЙ_РЕЗУЛЬТАТ"
OUTPUT_CSV = OUTPUT_DIR / "parsed_reviews.csv"
OUTPUT_DISHES_CSV = OUTPUT_DIR / "parsed_dishes.csv"

CURRENT_CAFE = "АндерСон Таганская 36"


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def parse_raw_text(
    raw_text: str, cafe_name: str
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    global CURRENT_CAFE
    CURRENT_CAFE = cafe_name

    raw_text = normalize_spaces(raw_text)

    review_rows = []
    dish_rows = []

    primary_blocks = split_messages(raw_text)

    if len(primary_blocks) <= 1:
        fallback_blocks = split_fallback_review_blocks(raw_text)
        if len(fallback_blocks) > 1:
            message_blocks = fallback_blocks
        else:
            message_blocks = primary_blocks
    else:
        fallback_blocks = []
        message_blocks = primary_blocks

    used_fallback_blocks = len(fallback_blocks) > 1

    if len(message_blocks) == 1 and (
        looks_like_plain_table_dump(raw_text)
        or looks_like_table_review_stream(raw_text)
    ):
        extra_review_rows, extra_dish_rows = parse_chat_body(raw_text)
        review_rows.extend(extra_review_rows)
        dish_rows.extend(extra_dish_rows)
        return review_rows, dish_rows

    for block in message_blocks:
        parsed = parse_message_block(block)

        if parsed:
            author = parsed["author"]
            body = parsed["body"]

            if author == "GastroReview":
                extra_review_rows, extra_dish_rows = parse_aggregator_body(body)
            else:
                extra_review_rows, extra_dish_rows = parse_chat_body(body)

            for row in extra_review_rows:
                if not row["date"]:
                    row["date"] = parsed["review_date"]
                review_rows.append(row)

            for drow in extra_dish_rows:
                if not drow["date"]:
                    drow["date"] = parsed["review_date"]
                dish_rows.append(drow)

        else:
            if used_fallback_blocks or is_review_start_line(block.strip()):
                extra_review_rows, extra_dish_rows = parse_chat_body(block)
                review_rows.extend(extra_review_rows)
                dish_rows.extend(extra_dish_rows)
            elif looks_like_plain_table_dump(block) or looks_like_table_review_stream(
                block
            ):
                extra_review_rows, extra_dish_rows = parse_chat_body(block)
                review_rows.extend(extra_review_rows)
                dish_rows.extend(extra_dish_rows)

    return review_rows, dish_rows


def save_parsed_to_csv(
    review_rows: List[Dict[str, object]],
    dish_rows: List[Dict[str, object]],
    output_dir: Path | None = None,
) -> None:
    if output_dir is None:
        output_dir = OUTPUT_DIR

    output_dir.mkdir(exist_ok=True)

    review_fieldnames = [
        "date",
        "source",
        "cafe",
        "table",
        "dish",
        "problem",
        "review_text",
        "tonality",
        "type",
        "priority",
        "what_done",
        "tags",
        "review_tag",
        "is_noise",
    ]

    dish_fieldnames = [
        "date",
        "source",
        "cafe",
        "table",
        "dish",
        "dish_tag",
        "review_text",
        "mention_tonality",
        "priority",
        "problem",
        "is_noise",
    ]

    output_csv = output_dir / "parsed_reviews.csv"
    output_dishes_csv = output_dir / "parsed_dishes.csv"

    with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=review_fieldnames)
        writer.writeheader()
        writer.writerows(review_rows)

    with open(output_dishes_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=dish_fieldnames)
        writer.writeheader()
        writer.writerows(dish_rows)


def normalize_telegram_date(date_str: str) -> str:
    """
    Преобразует дату вида '4 апр. 2026' в '04.04.2026'.
    Если не удалось распарсить, возвращает исходную строку без лишних пробелов.
    """
    if not date_str:
        return ""

    cleaned = normalize_spaces(date_str).strip().lower()
    match = re.match(r"^(\d{1,2})\s+([а-яё.]+)\s+(\d{4})$", cleaned, re.IGNORECASE)
    if not match:
        return normalize_spaces(date_str).strip()

    day, month_raw, year = match.groups()
    month_key = month_raw.lower().strip()
    month_num = config.month_map.get(month_key)

    if not month_num:
        month_key = month_key.rstrip(".")
        month_num = config.month_map.get(month_key)

    if not month_num:
        return normalize_spaces(date_str).strip()

    return f"{int(day):02d}.{month_num}.{year}"


def normalize_spaces(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_text_for_search(text: str) -> str:
    text = normalize_spaces(text).lower()
    text = text.replace("ё", "е")
    text = text.replace("—", "-").replace("–", "-")
    text = re.sub(r"[\"«»()]+", " ", text)
    text = re.sub(r"[^а-яa-z0-9#\-\s.,]", " ", text, flags=re.IGNORECASE)
    text = text.replace("-", " ")
    text = re.sub(r"\s+", " ", text).strip()

    for bad, good in config.typo_map.items():
        text = text.replace(bad, good)

    return text


def clean_review_text(text: str) -> str:
    text = normalize_spaces(text)
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip(" ,.-_")


def phrase_in_text(text: str, phrase: str) -> bool:
    text_n = normalize_text_for_search(text)
    phrase_n = normalize_text_for_search(phrase)

    if not phrase_n:
        return False

    phrase_n = phrase_n.replace(r"\*", "")

    escaped = re.escape(phrase_n)
    pattern = rf"(?<![а-яa-z0-9]){escaped}(?![а-яa-z0-9])"
    return re.search(pattern, text_n, re.IGNORECASE) is not None


def looks_like_plain_table_dump(text: str) -> bool:
    # они не остановтяся находить новые способы копирования ОС, боже мой...
    if not text or not text.strip():
        return False

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return False

    table_like_count = 0

    patterns = [
        r"^\s*Стол\s*\d{1,4}\s*[:.,]?\s*$",
        r"^\s*\d{1,4}\s*стол\s*[:.,]?\s*$",
        r"^\s*\d{1,4}\s*[:.,]?\s*$",
        r"^\s*Стол\s*\d{1,4}\s*[:.,]?\s*.+$",
        r"^\s*\d{1,4}\s*стол\s*[:.,]?\s*.+$",
        r"^\s*\d{1,4}\s*[:.,]\s*.+$",
        r"^\s*\d{1,4}\s+.+$",
    ]

    for line in lines:
        if any(re.match(p, line, re.IGNORECASE) for p in patterns):
            table_like_count += 1

    return table_like_count >= 2


# Если долго смотреть в бездну входных форматов, бездна начнёт смотреть на тебя


def is_review_start_line(line: str) -> bool:
    if not line or not line.strip():
        return False

    stripped = line.strip()

    patterns = [
        r"^\s*Стол\s*\d{1,4}\s*[:.,]?\s*.*$",
        r"^\s*\d{1,4}\s*стол\s*[:.,]?\s*.*$",
        r"^\s*\d{1,4}\s*[:.,]\s*.*$",
        r"^\s*\d{1,4}\s+.+$",
    ]

    return any(re.match(p, stripped, re.IGNORECASE) for p in patterns)


def is_pseudo_chat_header(line: str) -> bool:
    if not line or not line.strip():
        return False

    stripped = line.strip()

    # > Massimo:
    # > Ms.Anastesha🩶:
    return bool(re.match(r"^>\s*[^:\n]{1,80}:\s*$", stripped))


def looks_like_table_review_stream(text: str) -> bool:
    if not text or not text.strip():
        return False

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return False

    review_start_count = sum(1 for line in lines if is_review_start_line(line))
    pseudo_header_count = sum(1 for line in lines if is_pseudo_chat_header(line))

    return review_start_count >= 2 or (
        pseudo_header_count >= 1 and review_start_count >= 1
    )


def split_fallback_review_blocks(text: str) -> List[str]:
    if not text or not text.strip():
        return []

    lines = text.splitlines()
    blocks = []
    current_block = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            if current_block:
                current_block.append(line)
            continue

        if is_pseudo_chat_header(stripped) or is_review_start_line(stripped):
            if current_block:
                block = "\n".join(current_block).strip()
                if block:
                    blocks.append(block)
            current_block = [line]
        else:
            if current_block:
                current_block.append(line)
            else:
                current_block = [line]

    if current_block:
        block = "\n".join(current_block).strip()
        if block:
            blocks.append(block)

    return blocks


def split_messages(text: str) -> List[str]:
    # Поддерживает форматы заголовка:
    # 1) [04.04.2026 12:30] Имя:
    # 2) Alex, [4 апр. 2026 в 15:39]
    # 3) Alex, [04.04.2026 15:39]
    # 4) > Alex:

    if not text or not text.strip():
        return []

    lines = text.splitlines()

    old_header_pattern = re.compile(r"^\[\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}\] .+?:.*$")

    new_header_pattern_text_month = re.compile(
        r"^.+?, \[\d{1,2} [А-Яа-яЁё.]+ \d{4} в \d{2}:\d{2}\]\s*$"
    )

    new_header_pattern_numeric = re.compile(
        r"^.+?, \[\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}\]\s*$"
    )

    pseudo_header_pattern = re.compile(r"^>\s*[^:\n]{1,80}:\s*$")

    blocks = []
    current_block = []

    def is_header_line(line: str) -> bool:
        stripped = line.strip()
        return bool(
            old_header_pattern.match(stripped)
            or new_header_pattern_text_month.match(stripped)
            or new_header_pattern_numeric.match(stripped)
            or pseudo_header_pattern.match(stripped)
        )

    for line in lines:
        if is_header_line(line):
            if current_block:
                block = "\n".join(current_block).strip()
                if block:
                    blocks.append(block)
            current_block = [line]
        else:
            current_block.append(line)

    if current_block:
        block = "\n".join(current_block).strip()
        if block:
            blocks.append(block)

    return blocks


def parse_message_block(block: str) -> Optional[Dict[str, str]]:
    if not block or not block.strip():
        return None

    block = block.strip()

    # Формат 1:
    # [04.04.2026 12:30] Имя: текст
    old_header_pattern = re.compile(
        r"^\[(\d{2}\.\d{2}\.\d{4} \d{2}:\d{2})\] (.+?):\s*(.*)$",
        re.DOTALL,
    )
    old_match = old_header_pattern.match(block)
    if old_match:
        message_datetime = old_match.group(1).strip()
        author = old_match.group(2).strip()
        body = old_match.group(3).strip()
        review_date = message_datetime.split()[0]

        return {
            "message_datetime": message_datetime,
            "review_date": review_date,
            "author": author,
            "body": body,
            "raw_block": block,
        }

    # Формат 2:
    # Alex, [4 апр. 2026 в 15:39]
    # текст
    new_header_pattern = re.compile(
        r"^(.+?), \[(\d{1,2} [А-Яа-яЁё.]+ \d{4}) в (\d{2}:\d{2})\]\s*(.*)$",
        re.DOTALL,
    )
    new_match = new_header_pattern.match(block)
    if new_match:
        author = new_match.group(1).strip()
        raw_date = new_match.group(2).strip()
        time_part = new_match.group(3).strip()
        body = new_match.group(4).strip()

        review_date = normalize_telegram_date(raw_date)
        message_datetime = f"{review_date} {time_part}" if review_date else time_part

        return {
            "message_datetime": message_datetime,
            "review_date": review_date,
            "author": author,
            "body": body,
            "raw_block": block,
        }

    # Формат 3:
    # Alex, [04.04.2026 15:39]
    # текст
    numeric_header_pattern = re.compile(
        r"^(.+?), \[(\d{2}\.\d{2}\.\d{4}) (\d{2}:\d{2})\]\s*(.*)$",
        re.DOTALL,
    )
    numeric_match = numeric_header_pattern.match(block)
    if numeric_match:
        author = numeric_match.group(1).strip()
        review_date = numeric_match.group(2).strip()
        time_part = numeric_match.group(3).strip()
        body = numeric_match.group(4).strip()

        message_datetime = f"{review_date} {time_part}"

        return {
            "message_datetime": message_datetime,
            "review_date": review_date,
            "author": author,
            "body": body,
            "raw_block": block,
        }

    # Формат 4:
    # > Massimo:
    # текст
    pseudo_header_pattern = re.compile(
        r"^>\s*([^:\n]{1,80}):\s*(.*)$",
        re.DOTALL,
    )
    pseudo_match = pseudo_header_pattern.match(block)
    if pseudo_match:
        author = pseudo_match.group(1).strip()
        body = pseudo_match.group(2).strip()

        return {
            "message_datetime": "",
            "review_date": "",
            "author": author,
            "body": body,
            "raw_block": block,
        }
    # хватит, я умоляю
    return None


def split_chat_into_subreviews(body: str) -> List[str]:
    body = body.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not body:
        return []

    lines = body.split("\n")

    blocks = []
    current_block = []

    review_start_pattern = re.compile(
        r"^\s*(?:"
        r"Стол\s*\d{1,4}\s*[:.,]?\s*.*|"
        r"\d{1,4}\s*стол\s*[:.,]?\s*.*|"
        r"\d{1,4}\s*(?:[:.,]\s*.*|\s+.+)?"
        r")$",
        re.IGNORECASE,
    )

    def starts_new_subreview(line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False
        return bool(review_start_pattern.match(stripped))

    for line in lines:
        if starts_new_subreview(line):
            if current_block:
                block = "\n".join(current_block).strip()
                if block:
                    blocks.append(block)
            current_block = [line]
        else:
            if current_block:
                current_block.append(line)
            else:
                current_block = [line]

    if current_block:
        block = "\n".join(current_block).strip()
        if block:
            blocks.append(block)

    return blocks


def extract_table_number(text: str) -> str:
    if not text or not text.strip():
        return ""

    text = text.strip()

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines:
        first_line = lines[0]

        first_line_patterns = [
            r"^\s*Стол\s*(\d{1,4})\s*[:.,]?\s*.*$",
            r"^\s*(\d{1,4})\s*стол\s*[:.,]?\s*.*$",
            r"^\s*(\d{1,4})\s*[:.,]\s*.*$",
            r"^\s*(\d{1,4})\s+.+$",
            r"^\s*(\d{1,4})\s*[:.,]?\s*$",
        ]

        for pattern in first_line_patterns:
            match = re.match(pattern, first_line, re.IGNORECASE)
            if match:
                return match.group(1)

    patterns = [
        r"\bСтол\s*(\d{1,4})\b",
        r"\bстол\s*(\d{1,4})\b",
        r"\b(\d{1,4})\s*стол\b",
        r"^\s*(\d{1,4})\s*[:.,]",
        r"^\s*(\d{1,4})\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)

    return ""


def extract_rating(text: str) -> str:
    stars_match = re.search(r"([★☆]{3,5})", text)
    if not stars_match:
        return ""
    return str(stars_match.group(1).count("★"))


def extract_platform_and_review_date(text: str) -> Tuple[str, str]:
    match = re.search(r"[★☆]{3,5}\s*·\s*(.*?)\s*·\s*(\d{2}\.\d{2}\.\d{4})", text)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return "", ""


def extract_tags(text: str) -> str:
    tags = re.findall(r"(#\S+)", text)
    return " ".join(tags)


def extract_what_done(text: str) -> str:
    actions = []
    text_lower = normalize_text_for_search(text)

    action_phrases = [
        "извинились",
        "извинилась",
        "принесли извинения",
        "убрали из счета",
        "убрали из счёта",
        "исправили",
        "забрали и дожарили",
        "дожарили",
        "доготовили",
        "в комплимент",
        "комплимент",
        "дали ребенку пирожное",
        "дали ребенку",
        "отдали",
        "заменили",
        "переделали",
        "вернули деньги",
        "сделали скидку",
        "предложили десерт",
        "угостили",
        "компенсировали",
    ]

    for phrase in action_phrases:
        if phrase_in_text(text_lower, phrase):
            actions.append(phrase)

    unique_actions = []
    seen = set()
    for action in actions:
        if action not in seen:
            seen.add(action)
            unique_actions.append(action)

    return ", ".join(unique_actions)


def has_negative_exception(text: str) -> bool:
    return any(phrase_in_text(text, marker) for marker in config.negative_exceptions)


def count_markers(text: str, markers: List[str]) -> int:
    return sum(1 for marker in markers if phrase_in_text(text, marker))


POSITIVE_STEMS = [
    r"восторг\w*",
    r"шикар\w*",
    r"великолеп\w*",
    r"идеальн\w*",
    r"бомб\w*",
    r"нежн\w*",
    r"сытн\w*",
    r"сбалансирован\w*",
    r"понрав\w*",
    r"отличн\w*",
]

NEGATIVE_STEMS = [
    r"\bневкус\w*|\bне\s+вкус\w*",
    r"\bсыр(ой|ая|ое|ые|оват\w*)\b",
    r"\bнедожар\w*|\bнедовар\w*",
    r"\bпересол\w*",
    r"\bж[её]стк\w*",
    r"\bхолодн\w*|\bостыв\w*",
    r"\bдолг\w*|\bжда\w*",
    r"\bгрязн\w*",
    r"\bне\s+(принес\w*|подал\w*|принял\w*|заметил\w*)\b|\bзабыл\w*",
]

NEGATED_POSITIVE_PATTERNS = [
    r"\bне\s+уют\w*",
    r"\bне\s+комфорт\w*",
    r"\bне\s+прият\w*",
]


def _count_regex_hits(text: str, patterns: List[str]) -> int:
    return sum(1 for p in patterns if re.search(p, text, re.IGNORECASE))


def classify_tonality_by_text(text: str) -> str:
    text_lower = normalize_text_for_search(text).strip()
    if not text_lower:
        return ""

    if has_negative_exception(text_lower):
        return "Позитив"

    pos_score = count_markers(text_lower, config.positive_markers)
    neg_score = count_markers(text_lower, config.negative_markers)
    has_mixed = any(
        phrase_in_text(text_lower, marker) for marker in config.mixed_markers
    )
    has_recovery = any(
        phrase_in_text(text_lower, marker) for marker in config.service_recovery_markers
    )

    pos_score += _count_regex_hits(text_lower, POSITIVE_STEMS)
    neg_score += _count_regex_hits(text_lower, NEGATIVE_STEMS)
    neg_score += _count_regex_hits(text_lower, NEGATED_POSITIVE_PATTERNS)

    strong_negative_markers = [
        "не забронировано",
        "пресно",
        "холодный",
        "отравление",
        "не работает",
        "отравились",
        "мутный",
        "испорчено",
        "испорчен",
        "кислая",
        "не съедобно",
        "сырая",
        "жесткий",
        "не зашел",
        "не зашёл",
        "не вкусные",
        "есть не возможно",
        "безвкусно",
        "кислый",
        "очень долго",
        "сырые",
        "жестковато",
        "нагрубили",
        "плохо",
        "не приняли",
        "холодные",
        "не доставили",
        "испорчена",
        "не вкусно",
        "обслуживали долго",
        "сырое",
        "мутное",
        "сырой",
        "невкусная",
        "ужасно",
        "жёсткий",
        "не понравился",
        "долго",
        "остывший",
        "очнь плохо",
        "есть невозможно",
        "горчит",
        "холодная",
        "кошмар",
        "убрали из счета",
        "убрали из счёта",
        "холодное",
        "отвратительно",
        "не вкусное",
        "ждали час",
        "сухое",
        "стола нет",
        "хамили",
        "не готово",
        "грязно",
        "не принесли",
        "не вкусный",
        "невкусные",
        "не привезли",
        "не понравилось",
        "остывшее",
        "нет стола",
        "невозможно есть",
        "мутная",
        "невкусно",
        "мутные",
        "не зашло",
        "жёстковато",
        "забыли",
        "сухая",
        "нет части заказа",
        "долго ждали",
        "невкусный",
        "пресновато",
        "не понравилась",
        "не понравились",
        "кислое",
        "невкусное",
        "сухой",
        "остыла",
        "суховато",
        "хуже",
        "не вкусная",
        "не доложили",
        "пересолили",
        "пересолено",
        "пересол",
        "пересолен",
        "пересолена",
        "недовольны",
        "недоволен",
        "не принял заказ",
        "не приняли заказ",
        "не приняла заказ",
        "не принял",
        "можно обжечься",
        "обжегся",
        "обожглись",
        "обожглась",
    ]

    strong_negative_count = sum(
        1 for marker in strong_negative_markers if phrase_in_text(text_lower, marker)
    )
    has_strong_negative = strong_negative_count > 0

    # Явно смешанный случай
    if pos_score > 0 and neg_score > 0 and has_mixed:
        if strong_negative_count >= 1 and neg_score >= pos_score:
            return "Негатив"
        return "Смешанный"

    # Есть и позитив, и негатив
    if pos_score > 0 and neg_score > 0:
        # компенсация сервиса -> не позитив, обычно mixed/negative
        if has_recovery and neg_score >= pos_score:
            return "Негатив"
        if strong_negative_count >= 2:
            return "Негатив"
        if has_strong_negative and neg_score >= pos_score:
            return "Негатив"
        if has_strong_negative and pos_score <= 1:
            return "Негатив"
        return "Смешанный"

    # Только негатив
    if neg_score > 0 and pos_score == 0:
        return "Негатив"

    # Только позитив
    if pos_score > 0 and neg_score == 0:
        return "Позитив"

    fallback_positive_patterns = [
        "все понравилось",
        "всё понравилось",
        "все было вкусно",
        "всё было вкусно",
        "очень вкусный",
        "очень вкусная",
        "очень вкусное",
        "очень вкусные",
        "все супер",
        "все отлично",
        "всё отлично",
        "всё ок",
        "волшеб",
        "понравился",
        "понравилась",
        "понравились",
        "вкусный",
        "вкусная",
        "вкусное",
        "вкусные",
        "все очень понравилось",
        "всё очень понравилось",
        "ушли с улыбками",
        "ушли с улыбкой",
        "не пожалели",
    ]
    if any(phrase_in_text(text_lower, p) for p in fallback_positive_patterns):
        return "Позитив"

    fallback_negative_patterns = [
        "совсем не вкусно",
        "есть невозможно",
        "не рекомендую",
        "больше не придем",
        "больше не придём",
        "больше не вернемся",
        "больше не вернёмся",
        "не зашло",
        "не зашел",
        "не зашёл",
        "не понравился",
        "не понравилась",
        "не понравились",
        "суховато",
        "пресновато",
    ]
    if any(phrase_in_text(text_lower, p) for p in fallback_negative_patterns):
        return "Негатив"

    return ""


def classify_dish_mention_tonality(review_text: str, dish_name: str) -> str:
    """
    Определяет тональность конкретно по блюду.
    Если в отзыве несколько блюд — старается найти ближайший контекст.
    """
    text_n = normalize_text_for_search(review_text)
    dish_n = normalize_text_for_search(dish_name)

    # Если блюдо вообще не найдено — падаем на общую тональность
    if dish_n not in text_n:
        return ensure_tonality(review_text)

    # Разбиваем отзыв на предложения (простой сплит по . ! ?)
    sentences = re.split(r"[.!?]+", review_text)
    dish_sentences = []

    for sent in sentences:
        sent_n = normalize_text_for_search(sent)
        if dish_n in sent_n or any(word in sent_n for word in dish_n.split()):
            dish_sentences.append(sent.strip())

    if not dish_sentences:
        return ensure_tonality(review_text)

    # Берём первое (или единственное) предложение про это блюдо
    context = " ".join(dish_sentences[:2])  # на всякий случай два
    return ensure_tonality(context)


def classify_tonality_aggregator(rating: str, text: str) -> str:
    text_result = classify_tonality_by_text(text)
    if text_result in ["Негатив", "Смешанный", "Позитив"]:
        return text_result

    if rating in ["4", "5"]:
        return "Позитив"
    if rating == "3":
        return "Смешанный"
    if rating in ["1", "2"]:
        return "Негатив"

    text_lower = normalize_text_for_search(text)
    if any(
        stem in text_lower for stem in ["вкусн", "понрав", "отлич", "супер", "прекрас"]
    ):
        return "Позитив"
    if any(
        stem in text_lower
        for stem in ["невкус", "ужас", "плох", "сыр", "гряз", "долго"]
    ):
        return "Негатив"

    return "Смешанный"


def extract_problem(text: str) -> str:
    text_lower = normalize_text_for_search(text)

    if has_negative_exception(text_lower):
        return "Проблема не определена"

    problems_map = [
        (
            "Не доложили / не доставили часть заказа",
            [
                "не доставили",
                "не доложили",
                "не привезли",
                "нет части заказа",
                "не тот заказ",
                "перепутали заказ",
            ],
        ),
        (
            "Нет салфеток / приборов",
            ["ни единой салфетки", "без салфеток", "без приборов"],
        ),
        (
            "Блюдо невкусное",
            [
                "не вкусно",
                "невкусно",
                "вообще не вкус",
                "совсем не вкус",
                "есть невозможно",
                "есть не возможно",
                "невозможно есть",
                "не понравилось",
                "не понравился",
                "не понравилась",
                "не понравились",
                "безвкусно",
                "пресно",
                "горчит",
                "кислый",
                "кислая",
                "кислое",
            ],
        ),
        (
            "Блюдо сырое / недоготовлено",
            [
                "сырой",
                "сырая",
                "сырое",
                "недовар",
                "недожар",
                "хрустят",
                "холодное",
                "недоделали",
                "не доделали",
            ],
        ),
        (
            "Блюдо холодное / остывшее",
            [
                "холодный",
                "холодная",
                "холодное",
                "холодные",
                "остывший",
                "остыла",
                "остывшее",
                "остыло",
                "прохладный",
                "прохладная",
                "прохладное",
                "еле тёплый",
                "еле теплый",
                "еле тёплая",
                "еле тёплое",
                "еле теплое",
            ],
        ),
        (
            "Долгое обслуживание",
            [
                "долго",
                "долго несли",
                "обслуживали долго",
                "ждали",
                "слишком долго",
                "очень долгое ожидание",
                "не подходили",
                "ждали больше",
                "больше 20 минут",
                "больше 30 минут",
                "никто так и не подошёл",
            ],
        ),
        (
            "Проблема с бонусами / промо",
            [
                "не прошли бонусы",
                "не приходит код",
                "не пришел код",
                "не пришёл код",
                "mindbonus",
                "биглион",
                "не списались бонусы",
                "не начислились бонусы",
                "бонусы",
                "клуб-друзей",
                "не начислили",
                "не работает код",
                "не работает промокод",
                "промокод",
            ],
        ),
        (
            "Коммуникация / дезинформация",
            [
                "разную информацию",
                "я не знаю",
                "не решает проблем",
                "дезинформация",
                "никто не знает",
            ],
        ),
        (
            "Проблема организации / брони",
            [
                "стола нет",
                "не готово",
                "депозит",
                "организацией мероприятия",
                "нет стола",
                "не забронировано",
            ],
        ),
        (
            "Вода / напиток плохого качества",
            ["мутная", "горчит напиток", "невкусный кофе", "невкусный чай"],
        ),
    ]

    found = []
    for label, patterns in problems_map:
        if any(pattern in text_lower for pattern in patterns):
            found.append(label)

    if not found:
        return "Проблема не определена"

    seen = set()
    unique = []
    for item in found:
        if item not in seen:
            seen.add(item)
            unique.append(item)

    return "; ".join(unique)


def detect_type_and_priority(text: str, review_tag: str = "") -> Tuple[str, str]:
    review_tag = normalize_review_tag(review_tag)
    text_lower = normalize_text_for_search(text).strip()

    if not text_lower:
        if review_tag == "Кухня":
            return "Кухня / Кухня", "Низкий"
        if review_tag == "Бар":
            return "Бар / Напитки", "Низкий"
        if review_tag == "Десерт":
            return "Кухня / Десерты", "Низкий"
        if review_tag == "Детское":
            return "Кухня / Детское", "Низкий"
        return "Сервис / Обслуживание", "Низкий"

    if has_negative_exception(text_lower):
        tonality = classify_tonality_by_text(text)
        if tonality == "Позитив":
            if review_tag == "Кухня":
                return "Кухня / Кухня", "Низкий"
            if review_tag == "Бар":
                return "Бар / Напитки", "Низкий"
            if review_tag == "Десерт":
                return "Кухня / Десерты", "Низкий"
            if review_tag == "Детское":
                return "Кухня / Детское", "Низкий"
            return "Сервис / Обслуживание", "Низкий"

    rules = [
        {
            "type": "Доставка / Нет части заказа",
            "priority": "Критический",
            "patterns": [
                "не доставили",
                "не доложили",
                "не привезли",
                "нет части заказа",
                "не тот заказ",
                "перепутали заказ",
            ],
        },
        {
            "type": "Доставка / Приборы",
            "priority": "Высокий",
            "patterns": [
                "ни единой салфетки",
                "без приборов",
                "без салфеток",
            ],
        },
        {
            "type": "Кухня / Кухня",
            "priority": "Высокий",
            "patterns": [
                "сырой",
                "сырая",
                "сырое",
                "сырые",
                "не вкусно",
                "невкусно",
                "вообще не вкус",
                "совсем не вкус",
                "есть невозможно",
                "есть не возможно",
                "невозможно есть",
                "много соли",
                "разваренные",
                "недовар",
                "недожар",
                "передержали",
                "хрустят",
                "жестковато",
                "жёстковато",
                "жесткий",
                "жёсткий",
                "резиновый",
                "резиновая",
                "резиновое",
                "сухой",
                "сухая",
                "сухое",
                "суховато",
                "горчит",
                "кислый",
                "кислая",
                "кислое",
                "холодный",
                "холодная",
                "холодное",
                "холодные",
                "кухня",
                "со стороны кухни",
                "забыли положить",
                "не учли",
                "не положили",
                "не добавили",
                "плохо прожарено",
                "плохо прожарили",
                "забыли добавить",
                "остыла",
                "остыл",
                "остыло",
                "остывшее",
                "еле тёплый",
                "еле теплый",
                "еле теплое",
                "еле тёплая",
                "не понравился",
                "не понравилась",
                "не понравились",
                "не зашло",
                "не зашел",
                "не зашёл",
                "безвкусно",
                "пресно",
                "пресновато",
                "пересолили",
                "пересолено",
                "пересол",
                "пересолен",
                "пересолена",
            ],
        },
        {
            "type": "Сервис / Обслуживание",
            "priority": "Высокий",
            "patterns": [
                "долго",
                "долго несли",
                "обслуживали долго",
                "ждали",
                "слишком долго",
                "очень долгое ожидание",
                "не подходили",
                "не обращали внимания",
                "забыли",
                "не принесли",
                "не вынесли",
            ],
        },
        {
            "type": "Сервис / Обслуживание",
            "priority": "Высокий",
            "patterns": [
                "разную информацию",
                "я не знаю",
                "ломающейся коммуникацией",
                "не решает проблем",
                "дезинформация",
                "никто не знает",
            ],
        },
        {
            "type": "Маркетинг / Программа лояльности",
            "priority": "Средний",
            "patterns": [
                "не прошли бонусы",
                "не приходит код",
                "не пришел код",
                "не пришёл код",
                "биглион",
                "mindbonus",
                "не списались бонусы",
                "не начислились бонусы",
            ],
        },
        {
            "type": "Праздник / Организация",
            "priority": "Критический",
            "patterns": [
                "праздник",
                "депозит",
                "в подвале",
                "организацией мероприятия",
                "не забронировано",
                "не готово",
                "стола нет",
                "нет стола",
            ],
        },
    ]

    matched = []
    for rule in rules:
        if any(phrase_in_text(text_lower, pattern) for pattern in rule["patterns"]):
            matched.append(rule)

    if matched:
        matched = sorted(
            matched,
            key=lambda x: {
                "Критический": 4,
                "Высокий": 3,
                "Средний": 2,
                "Низкий": 1,
            }.get(x["priority"], 0),
            reverse=True,
        )
        best = matched[0]
        return best["type"], best["priority"]

    tonality = classify_tonality_by_text(text)

    if review_tag == "Кухня":
        if tonality in ("Негатив", "Смешанный"):
            return "Кухня / Кухня", "Средний"
        return "Кухня / Кухня", "Низкий"

    if review_tag == "Бар":
        if tonality in ("Негатив", "Смешанный"):
            return "Бар / Напитки", "Средний"
        return "Бар / Напитки", "Низкий"

    if review_tag == "Десерты":
        if tonality in ("Негатив", "Смешанный"):
            return "Кухня / Десерты", "Средний"
        return "Кухня / Десерты", "Низкий"

    if review_tag == "Детское":
        if tonality in ("Негатив", "Смешанный"):
            return "Кухня / Детское", "Средний"
        return "Кухня / Детское", "Низкий"

    if tonality == "Негатив":
        return "Сервис / Обслуживание", "Средний"
    if tonality == "Смешанный":
        return "Сервис / Обслуживание", "Средний"
    if tonality == "Позитив":
        return "Сервис / Обслуживание", "Низкий"

    return "Сервис / Обслуживание", "Низкий"


def fallback_dish_tag_by_name(dish_name: str) -> str:
    dish_lower = normalize_text_for_search(dish_name)
    for tag, keywords in FALLBACK_DISH_TAG_BY_NAME_KEYWORDS.items():
        if any(keyword in dish_lower for keyword in keywords):
            return tag
    return "Кухня"


def build_dish_catalog() -> List[Dict[str, object]]:
    dish_entries = []

    for dish_name, meta in DISH_ALIASES.items():
        dish_entries.append(
            {
                "dish": dish_name,
                "tag": meta.get("tag", fallback_dish_tag_by_name(dish_name)),
                "strong": meta.get("strong", []),
                "medium": meta.get("medium", []),
                "weak": meta.get("weak", []),
            }
        )

    aliases_existing = set(DISH_ALIASES.keys())
    for dish_name in DEFAULT_DISHES:
        if dish_name in aliases_existing:
            continue
        dish_entries.append(
            {
                "dish": dish_name,
                "tag": fallback_dish_tag_by_name(dish_name),
                "strong": [dish_name],
                "medium": [],
                "weak": [],
            }
        )

    return dish_entries


DISH_CATALOG = build_dish_catalog()


def _is_generic_dish_name(name: str) -> bool:
    n = normalize_text_for_search(name)
    return "неуточнен" in n or "неуточн" in n


def _generic_family_tokens(name: str) -> set:
    n = normalize_text_for_search(name)
    n = re.sub(r"\bнеуточнен\w*\b", " ", n)
    n = re.sub(r"\bнеуточн\w*\b", " ", n)
    tokens = [t for t in n.split() if t]
    return set(tokens)


def remove_generic_dish_matches(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    def norm(s: str) -> str:
        return normalize_text_for_search(s).strip()

    result = []
    for item in items:
        item_name = item["dish"]
        item_name_n = norm(item_name)

        # если не generic — оставляем
        if not _is_generic_dish_name(item_name):
            result.append(item)
            continue

        # generic удаляем, если есть более конкретное блюдо того же "семейства"
        family = _generic_family_tokens(item_name)
        should_drop = False

        for other in items:
            if item is other:
                continue

            other_name = other["dish"]
            other_name_n = norm(other_name)

            if _is_generic_dish_name(other_name):
                continue

            other_tokens = set(other_name_n.split())

            if family and family.issubset(other_tokens):
                should_drop = True
                break

            mp = normalize_text_for_search(item.get("matched_phrase", ""))
            if mp and re.search(
                rf"(?<![а-яa-z0-9]){re.escape(mp)}(?![а-яa-z0-9])", other_name_n
            ):
                should_drop = True
                break

        if not should_drop:
            result.append(item)

    return result


def detect_dishes(text: str) -> List[Dict[str, str]]:
    text_n = normalize_text_for_search(text)
    found = []

    for entry in DISH_CATALOG:
        dish_name = str(entry["dish"])
        dish_tag = str(entry["tag"])

        matched_level = None
        matched_phrase = None

        for phrase in entry.get("strong", []):
            if phrase_in_text(text_n, str(phrase)):
                matched_level = "strong"
                matched_phrase = str(phrase)
                break

        if matched_level is None:
            for phrase in entry.get("medium", []):
                if phrase_in_text(text_n, str(phrase)):
                    matched_level = "medium"
                    matched_phrase = str(phrase)
                    break

        if matched_level is None:
            for phrase in entry.get("weak", []):
                if phrase_in_text(text_n, str(phrase)):
                    matched_level = "weak"
                    matched_phrase = str(phrase)
                    break

        if matched_level:
            found.append(
                {
                    "dish": dish_name,
                    "dish_tag": dish_tag,
                    "match_level": matched_level,
                    "matched_phrase": matched_phrase or "",
                }
            )

    unique = {}
    level_weight = {"strong": 3, "medium": 2, "weak": 1}

    for item in found:
        dish = item["dish"]
        if dish not in unique:
            unique[dish] = item
        else:
            current_weight = level_weight[item["match_level"]]
            saved_weight = level_weight[unique[dish]["match_level"]]
            if current_weight > saved_weight:
                unique[dish] = item

    result = list(unique.values())
    return remove_generic_dish_matches(result)


def _keyword_weight(keyword: str) -> float:
    n = len(normalize_text_for_search(keyword).split())
    if n >= 3:
        return 2.2
    if n == 2:
        return 1.6
    return 1.0


def normalize_review_tag(tag: str) -> str:
    if tag == "Десерты":
        return "Десерт"
    return tag


def detect_review_tag(text: str, detected_dishes: List[Dict[str, str]]) -> str:
    if detected_dishes:
        priority_order = ["Кухня", "Бар", "Десерт", "Детское"]
        dish_tags = [
            normalize_review_tag(item.get("dish_tag", ""))
            for item in detected_dishes
            if item.get("dish_tag")
        ]
        for tag in priority_order:
            if tag in dish_tags:
                return tag
        if dish_tags:
            return dish_tags[0]

    text_n = normalize_text_for_search(text)
    scores: Dict[str, float] = {}

    for tag, keywords in REVIEW_TAG_KEYWORDS.items():
        score = 0.0
        for keyword in keywords:
            kw = normalize_text_for_search(keyword)
            if not kw:
                continue
            if len(kw.split()) == 1:
                if re.search(rf"\b{re.escape(kw)}\b", text_n):
                    score += _keyword_weight(kw)
            else:
                if kw in text_n:
                    score += _keyword_weight(kw)
        tag_n = normalize_review_tag(tag)
        if score > 0:
            scores[tag_n] = scores.get(tag_n, 0.0) + score

    if not scores:
        tonality = classify_tonality_by_text(text)
        if tonality in ("Позитив", "Негатив", "Смешанный"):
            return "Другое"
        return ""

    return max(scores.items(), key=lambda x: x[1])[0]


def detect_noise(text: str) -> bool:
    text_lower = normalize_text_for_search(text).strip()

    if not text_lower:
        return True
    if text_lower in config.short_replies:
        return True
    if not re.search(r"[а-яa-z0-9]", text_lower, re.IGNORECASE):
        return True

    has_table = bool(extract_table_number(text))
    has_guest_anchor = bool(re.search(r"\bгост(ь|и|ю|ям|ями|ях)\b", text_lower))
    has_order_anchor = bool(
        re.search(
            r"\b(заказ|счет|счёт|официант|чек|принесли|подали|принес|подал)\b",
            text_lower,
        )
    )
    has_review_anchor = has_table or has_guest_anchor or has_order_anchor

    # Операционный/внутренний диалоговый шум (без якорей отзыва)
    operational_markers = [
        "давайте",
        "мы должны",
        "не будем",
        "выжидать",
        "предупреждать",
        "сделай",
        "сюда пишем",
        "в таблицу",
        "в программу",
        "в отчет",
        "в отчёт",
        "заливать",
        "фиксируйте",
        "проверьте",
        "скиньте",
        "отправьте",
        "добавьте",
    ]
    has_operational = any(phrase_in_text(text_lower, m) for m in operational_markers)

    # Имя в обращении: "нет, макс ...", "макс, ..."
    has_name_call = bool(
        re.search(r"\b(нет|слушай|смотри|ну)\s*,?\s*[а-яё]{3,}\b", text_lower)
        or re.search(r"^[а-яё]{3,}\s*,", text_lower)
    )

    # Варианты про TV/ТВ
    has_tv_meta = bool(re.search(r"\bсделай\s+еще\s+([tт][vв]|тв)\b", text_lower))

    # Жесткое правило: нет якорей + операционный контекст
    if not has_review_anchor and (has_operational or has_name_call or has_tv_meta):
        return True

    review_score = 0
    noise_score = 0

    review_patterns = [
        r"\bстол\s*\d{1,4}\b",
        r"\b\d{1,4}\s*стол\b",
        r"\bгость\b",
        r"\bгости\b",
        r"\bзаказ\b",
        r"\bблюдо\b",
        r"\bвкусно\b",
        r"\bневкусно\b",
        r"\bне вкусно\b",
        r"\bне понравилось\b",
        r"\bхолодн\w*\b",
        r"\bгоряч\w*\b",
        r"\bдолго\b",
        r"\bгрязно\b",
        r"[★☆]{3,5}",
    ]
    matched_review_patterns = sum(
        1 for p in review_patterns if re.search(p, text_lower, re.IGNORECASE)
    )

    # Без якорей — ослабляем "отзывность"
    review_score += matched_review_patterns * (2 if has_review_anchor else 1)

    # ВАЖНО: по словам считаем с границами, не через "in"
    review_score += sum(
        1
        for w in config.review_keywords
        if re.search(
            rf"(?<![а-яa-z0-9]){re.escape(w)}(?![а-яa-z0-9])", text_lower, re.IGNORECASE
        )
    )
    noise_score += sum(
        1
        for w in config.noise_keywords
        if re.search(
            rf"(?<![а-яa-z0-9]){re.escape(w)}(?![а-яa-z0-9])", text_lower, re.IGNORECASE
        )
    )

    if len(text_lower) < 20:
        noise_score += 2
    elif len(text_lower) < 35:
        noise_score += 1

    if re.search(r"\b(что|чтобы|если|когда|но|а|и)\s*$", text_lower):
        noise_score += 2

    if not has_review_anchor and bool(classify_tonality_by_text(text)):
        # Тональность без якорей часто ложная для обрывков речи
        noise_score += 1

    if review_score == 0 and noise_score >= 2:
        return True
    if noise_score >= review_score + 2:
        return True

    return False


def parse_aggregator_review_text(body: str) -> Tuple[str, str, str, str]:
    body = normalize_spaces(body)
    lines = [line.strip() for line in body.splitlines() if line.strip()]

    platform, review_date = extract_platform_and_review_date(body)
    rating = extract_rating(body)
    author_inside = ""
    review_text = ""

    rating_line_index = None
    for i, line in enumerate(lines):
        if re.search(r"[★☆]{3,5}\s*·\s*.*?\s*·\s*\d{2}\.\d{2}\.\d{4}", line):
            rating_line_index = i
            break

    if rating_line_index is not None:
        if rating_line_index + 1 < len(lines):
            author_inside = lines[rating_line_index + 1]

        review_text_lines = []
        for line in lines[rating_line_index + 2 :]:
            if line.startswith("#"):
                break
            review_text_lines.append(line)

        review_text = clean_review_text(" ".join(review_text_lines))

    return platform, review_date, rating, review_text


def build_dish_rows(
    base_row: Dict[str, object], detected_dishes: List[Dict[str, str]]
) -> List[Dict[str, object]]:
    dish_rows = []
    for item in detected_dishes:
        dish_tonality = classify_dish_mention_tonality(
            base_row["review_text"], item["dish"]
        )

        dish_rows.append(
            {
                "date": base_row["date"],
                "source": base_row["source"],
                "cafe": base_row["cafe"],
                "table": base_row["table"],
                "dish": item["dish"],
                "dish_tag": item["dish_tag"],
                "review_text": base_row["review_text"],
                "mention_tonality": dish_tonality,  # ← было base_row["tonality"]
                "priority": base_row[
                    "priority"
                ],  # можно тоже сделать dish-specific позже
                "problem": base_row["problem"],  # можно тоже уточнить
                "is_noise": base_row["is_noise"],
            }
        )
    return dish_rows


def ensure_tonality(text: str, rating: str = "") -> str:
    result = classify_tonality_by_text(text)
    if result:
        return result

    if rating:
        if rating in ["4", "5"]:
            return "Позитив"
        if rating == "3":
            return "Смешанный"
        if rating in ["1", "2"]:
            return "Негатив"

    text_n = normalize_text_for_search(text)
    if any(
        stem in text_n
        for stem in ["вкусн", "понрав", "отлич", "супер", "прекрас", "рекоменд"]
    ):
        return "Позитив"
    if any(
        stem in text_n
        for stem in ["невкус", "ужас", "плох", "сыр", "долго", "гряз", "не принесли"]
    ):
        return "Негатив"

    return "Смешанный"


def parse_aggregator_body(
    body: str,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    body = normalize_spaces(body)
    cafe = CURRENT_CAFE
    _, review_date, rating, review_text = parse_aggregator_review_text(body)
    tags = extract_tags(body)

    tonality = ensure_tonality(review_text, rating)
    detected_dishes = detect_dishes(review_text)
    review_tag = detect_review_tag(review_text, detected_dishes)
    review_type, priority = detect_type_and_priority(review_text, review_tag)
    if not priority:
        priority = "Средний" if tonality in ["Негатив", "Смешанный"] else "Низкий"

    problem = extract_problem(review_text)
    what_done = extract_what_done(review_text)
    detected_dishes_str = ", ".join(item["dish"] for item in detected_dishes)

    row = {
        "date": review_date if review_date else "",
        "source": "GastroReview",
        "cafe": cafe,
        "table": "",
        "dish": detected_dishes_str,
        "problem": problem,
        "review_text": review_text,
        "tonality": tonality,
        "type": review_type,
        "priority": priority,
        "what_done": what_done,
        "tags": tags,
        "review_tag": review_tag,
        "is_noise": False,
    }

    dish_rows = build_dish_rows(row, detected_dishes)
    return [row], dish_rows


def has_table_anchor_only(table_number: str) -> bool:
    """
    Жесткое правило:
    если в сообщении нет номера стола -> это шум, а то я с ума сойду эвристики для шума и правила придумывать.
    """
    return bool(table_number and table_number.strip())


def parse_chat_body(
    body: str,
) -> Tuple[List[Dict[str, object]], List[Dict[str, object]]]:
    subreviews = split_chat_into_subreviews(body)
    if not subreviews:
        subreviews = [body]

    review_rows = []
    dish_rows = []

    for subreview in subreviews:
        table_number = extract_table_number(subreview)
        review_text = clean_review_text(subreview)

        if not has_table_anchor_only(table_number):
            is_noise = True
            tonality = ""
            problem = ""
            what_done = ""
            detected_dishes = []
            review_tag = ""
            review_type, priority = "", ""
        else:
            is_noise = detect_noise(review_text)
            detected_dishes = [] if is_noise else detect_dishes(review_text)
            review_tag = (
                "" if is_noise else detect_review_tag(review_text, detected_dishes)
            )

            # Общая тональность отзыва (для главной строки)
            tonality = "" if is_noise else ensure_tonality(review_text)
            problem = "" if is_noise else extract_problem(review_text)
            what_done = "" if is_noise else extract_what_done(review_text)
            review_type, priority = (
                ("", "")
                if is_noise
                else detect_type_and_priority(review_text, review_tag)
            )

            if not is_noise and not priority:
                priority = (
                    "Средний" if tonality in ["Негатив", "Смешанный"] else "Низкий"
                )

        detected_dishes_str = ", ".join(item["dish"] for item in detected_dishes)

        row = {
            "date": "",
            "source": "TableVisit",
            "cafe": CURRENT_CAFE,
            "table": table_number,
            "dish": detected_dishes_str,
            "problem": problem if problem else "Проблема не определена",
            "review_text": review_text,
            "tonality": tonality,
            "type": review_type,
            "priority": priority,
            "what_done": what_done,
            "tags": "",
            "review_tag": review_tag if review_tag else "Другое",
            "is_noise": is_noise,
        }

        review_rows.append(row)

        if not is_noise and detected_dishes:
            dish_rows.extend(build_dish_rows(row, detected_dishes))
        elif not is_noise:

            dish_rows.extend(
                build_dish_rows(row, [{"dish": "", "dish_tag": review_tag}])
            )

    return review_rows, dish_rows


# def _self_test_noise():
#     samples = [
#         "Доброе утро. Тогда давайте блюдо холодной давать в будем",
#         "Нет, Макс мы ничего выжидать не будем",
#         "Мы должны предупреждать родителей, о том, что нагнетая горячие",
#         "можно с ними посидеть подуть им чтобы не горячо было",
#         "Макс, сделай еще тv, мало за сегодня",
#         "Гость: пицца холодная, заменили, извинились",  # это НЕ шум
#     ]
#     print("\n=== SELF TEST detect_noise ===")
#     for s in samples:
#         print(detect_noise(s), " | ", s)
#     print("=== END SELF TEST ===\n")


def main():
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            raw_text = f.read()

        review_rows, dish_rows = parse_raw_text(raw_text, CURRENT_CAFE)
        save_parsed_to_csv(review_rows, dish_rows, OUTPUT_DIR)

        total_rows = len(review_rows)
        noise_rows = sum(1 for row in review_rows if row["is_noise"] is True)
        clean_rows = total_rows - noise_rows

        print("Парсинг завершён успешно.")
        print(f"Всего строк отзывов: {total_rows}")
        print(f"Полезных отзывов: {clean_rows}")
        print(f"Шумовых строк: {noise_rows}")
        print(f"CSV отзывов сохранён в: {OUTPUT_CSV}")
        print(f"CSV блюд сохранён в: {OUTPUT_DISHES_CSV}")

        return 0

    except Exception as e:
        print(f"Ошибка парсинга: {e}")
        return 1
