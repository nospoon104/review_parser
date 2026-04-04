import re
import csv
from pathlib import Path
import sys
from typing import Dict, List, Optional, Tuple

from scripts.catalogs import (
    DEFAULT_DISHES,
    DISH_ALIASES,
    REVIEW_TAG_KEYWORDS,
    FALLBACK_DISH_TAG_BY_NAME_KEYWORDS,
)


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
INPUT_FILE = BASE_DIR / "ПОЛОЖИТЬ_СЮДА_ФАЙЛ_С_ОТЗЫВАМИ" / "raw_reviews.txt"
OUTPUT_DIR = BASE_DIR / "ГОТОВЫЙ_РЕЗУЛЬТАТ"
OUTPUT_CSV = OUTPUT_DIR / "parsed_reviews.csv"
OUTPUT_DISHES_CSV = OUTPUT_DIR / "parsed_dishes.csv"

POSITIVE_MARKERS = [
    "вкусно",
    "очень вкусно",
    "безумно вкусно",
    "все вкусно",
    "всё вкусно",
    "все было вкусно",
    "всё было вкусно",
    "понравилось",
    "очень понравилось",
    "понравился",
    "понравилась",
    "понравились",
    "супер",
    "отлично",
    "прекрасно",
    "замечательно",
    "восхитительно",
    "идеально",
    "классно",
    "круто",
    "молодцы",
    "молодец",
    "на высоте",
    "топ",
    "огонь",
    "гости довольны",
    "гость доволен",
    "все довольны",
    "всё понравилось",
    "все понравилось",
    "всем довольны",
    "остались довольны",
    "в восторге",
    "быстро",
    "быстро принесли",
    "быстрая подача",
    "оперативно",
    "ждать не пришлось",
    "не пришлось ждать",
    "долго ждать не пришлось",
    "долго ждать не приходится",
    "не приходится ждать",
    "ждать не приходится",
    "уютно",
    "приятно",
    "комфортно",
    "атмосферно",
    "приятная атмосфера",
    "потрясающее место",
    "любимое место",
    "хорошее место",
    "приятное место",
    "вежливо",
    "вежливый",
    "вежливая",
    "доброжелательно",
    "приветливо",
    "внимательно",
    "заботливо",
    "хорошее обслуживание",
    "отличный сервис",
    "удобно",
    "очень удобно",
    "огромный плюс",
    "большой плюс",
    "классные аниматоры",
    "хорошая игровая",
    "детям понравилось",
    "рекомендуем",
    "рекомендую",
    "однозначно рекомендую",
    "вернемся",
    "вернёмся",
    "придем еще",
    "придём ещё",
    "вкусный",
    "вкусная",
    "вкусное",
    "вкусные",
    "хороший",
    "хорошая",
    "хорошее",
    "хорошие",
    "лучше чем обычно",
    "хорошо",
    "превосходно" "потрясающе",
]

NEGATIVE_MARKERS = [
    "не вкусно",
    "невкусно",
    "не вкусная",
    "не вкусный",
    "не вкусные",
    "вообще не вкус",
    "совсем не вкус",
    "есть невозможно",
    "есть не возможно",
    "невозможно есть",
    "не понравилось",
    "не понравился",
    "не понравились",
    "не понравилась",
    "не зашло",
    "ужасно",
    "отвратительно",
    "кошмар",
    "так себе",
    "плохо",
    "очень плохо",
    "не очень",
    "разочаровал",
    "разочаровало",
    "сырой",
    "сырая",
    "сырое",
    "недожарен",
    "недожарена",
    "недожарено",
    "недоварен",
    "недоварена",
    "недоварено",
    "подгорел",
    "подгорело",
    "пересолен",
    "пересолено",
    "слишком солен",
    "слишком солёный",
    "безвкусно",
    "пресно",
    "сухой",
    "сухая",
    "сухое",
    "жесткий",
    "жёсткий",
    "жёсткая",
    "жесткая",
    "водянистый",
    "водянистая",
    "водянситое",
    "жестковато",
    "жёстковато",
    "резиновый",
    "резиновая",
    "резиновое",
    "хрустят",
    "кислый",
    "кислая",
    "кислое",
    "горчит",
    "горький",
    "горькая",
    "холодный",
    "холодная",
    "холодное",
    "остывший",
    "остывшая",
    "остывшее",
    "передержали",
    "разваренные",
    "разварен",
    "много соли",
    "мало соли",
    "долго",
    "очень долго",
    "долго несли",
    "долго ждали",
    "ждали долго",
    "обслуживали долго",
    "слишком долго",
    "очень долгое ожидание",
    "ждали",
    "задержали",
    "не подходили",
    "не обращали внимания",
    "забыли",
    "перепутали",
    "не принесли",
    "не вынесли",
    "не подали",
    "не доставили",
    "не доложили",
    "не привезли",
    "нет части заказа",
    "не учли комментарий",
    "не тот заказ",
    "перепутали заказ",
    "без приборов",
    "без салфеток",
    "ни единой салфетки",
    "упаковка порвана",
    "упаковка протекла",
    "все пролилось",
    "всё пролилось",
    "грязно",
    "грязный",
    "грязная",
    "грязное",
    "мусор",
    "липкий стол",
    "не убрано",
    "неприятно пахнет",
    "воняет",
    "не прошли бонусы",
    "не приходит код",
    "не пришел код",
    "не пришёл код",
    "не работает приложение",
    "не работает сайт",
    "не грузит",
    "не загружается",
    "не списались бонусы",
    "не начислились бонусы",
    "стола нет",
    "нет стола",
    "не готово",
    "не забронировано",
    "разную информацию",
    "дезинформация",
    "я не знаю",
    "никто не знает",
    "не решает проблем",
    "ломающейся коммуникацией",
    "нервотрепкой",
    "нервотрепка",
    "сложно назвать организацией",
    "организация хромает",
    "отравление",
    "плохо стало",
    "тошнит",
    "болит живот",
    "отравились",
    "аллергия",
    "инородный предмет",
    "волос",
    "стекло",
    "осколок",
    "пластик",
    "кусок упаковки",
    "хромает",
    "никакой",
    "ни о чём",
]

MIXED_MARKERS = [
    "но",
    "однако",
    "при этом",
    "в целом",
    "в общем",
    "единственное",
    "из минусов",
    "из плюсов",
    "с одной стороны",
    "с другой стороны",
    "мнение разделились",
    "один говорит",
    "другой говорит",
    "отец говорит",
    "дочь утверждает",
    "вкусно, но",
    "хорошо, но",
    "понравилось, но",
    "в целом хорошо, но",
    "неплохо, но",
    "лишнее",
    "лишний",
    "лишняя",
    "странный",
    "странное",
    "странная",
    "привкус",
    "странное сочетание" "странные сочетания",
]

SERVICE_RECOVERY_MARKERS = [
    "извинились",
    "извинилась",
    "принесли извинения",
    "убрали из счета",
    "убрали из счёта",
    "не взяли в счет",
    "не взяли в счёт",
    "заменили",
    "переделали",
    "дожарили",
    "доготовили",
    "вернули деньги",
    "сделали скидку",
    "предложили десерт",
    "дали комплимент",
    "в комплимент",
    "угостили",
    "компенсировали",
]

NEGATIVE_EXCEPTIONS = [
    "долго ждать не приходится",
    "ждать не приходится",
    "не приходится ждать",
    "не пришлось долго ждать",
    "ждать не пришлось",
    "долго ждать не пришлось",
    "без проблем",
    "никаких проблем",
    "проблем не было",
    "никаких нареканий",
    "вопросов нет",
    "все прошло хорошо",
    "всё прошло хорошо",
    "все было отлично",
    "всё было отлично",
    "несмотря на полную посадку, быстро",
    "несмотря на полную посадку быстро",
]

REVIEW_KEYWORDS = [
    "гость",
    "гости",
    "гостю",
    "гостям",
    "заказ",
    "блюдо",
    "еда",
    "напиток",
    "доставка",
    "официант",
    "администратор",
    "аниматор",
    "игровая",
    "зал",
    "атмосфера",
    "обслуживание",
    "кухня",
    "бонусы",
    "промокод",
    "код",
    "сайт",
    "упаковка",
    "приборы",
    "салфетки",
    "пицца",
    "бургер",
    "боул",
    "омлет",
    "котлеты",
    "наггитсы",
    "суп",
    "борщ",
    "салат",
    "паста",
    "рис",
    "авокадо",
    "грибы",
    "ростбиф",
    "вода",
    "кофе",
    "чай",
    "десерт",
    "торт",
    "роллы",
    "шашлык",
    "стейк",
    "картошка",
]

NOISE_KEYWORDS = [
    "коллеги",
    "команда",
    "ребята",
    "друзья",
    "давайте",
    "нужно",
    "надо",
    "важно",
    "обязательно",
    "сюда пишем",
    "сюда прописываем",
    "заполняйте",
    "отмечайте",
    "в таблицу",
    "в программу",
    "в отчет",
    "в отчёт",
    "выгружать",
    "заливать",
    "загружать",
    "сводка",
    "отчёт",
    "отчет",
    "статистика",
    "кто будет",
    "кто сегодня",
    "проверьте",
    "проверяйте",
    "исправьте",
    "добавьте",
    "внесите",
    "не забывайте",
    "возобновляем",
    "активнее",
    "корректно",
    "фиксируйте",
    "завтра",
    "сегодня нужно",
    "потом",
    "позже",
    "до вечера",
    "до конца дня",
    "скиньте",
    "пришлите",
    "отправьте",
    "мне это",
    "мне надо",
    "мне нужно",
    "на коленях",
]

SHORT_REPLIES = {
    "ок",
    "окей",
    "ага",
    "угу",
    "ясно",
    "принято",
    "понял",
    "поняла",
    "хорошо",
    "добро",
    "+",
    "++",
    "+++",
    "-",
    "--",
    "---",
    "!",
    "!!",
    "!!!",
    "спс",
    "спасибо",
    "ок, спасибо",
}

MONTH_MAP = {
    "янв": "01",
    "янв.": "01",
    "фев": "02",
    "февр": "02",
    "февр.": "02",
    "мар": "03",
    "мар.": "03",
    "апр": "04",
    "апр.": "04",
    "мая": "05",
    "май": "05",
    "июн": "06",
    "июн.": "06",
    "июл": "07",
    "июл.": "07",
    "авг": "08",
    "авг.": "08",
    "сен": "09",
    "сен.": "09",
    "сент": "09",
    "сент.": "09",
    "окт": "10",
    "окт.": "10",
    "ноя": "11",
    "нояб": "11",
    "нояб.": "11",
    "дек": "12",
    "дек.": "12",
}


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
    month_num = MONTH_MAP.get(month_key)

    if not month_num:
        month_key = month_key.rstrip(".")
        month_num = MONTH_MAP.get(month_key)

    if not month_num:
        return normalize_spaces(date_str).strip()

    return f"{int(day):02d}.{month_num}.{year}"


def normalize_spaces(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def normalize_text_for_search(text: str) -> str:
    text = normalize_spaces(text).lower()
    text = text.replace("ё", "е")
    text = text.replace("йе ", " ")
    text = text.replace("яе ", " ")
    text = re.sub(r"[\"«»()]+", " ", text)
    text = re.sub(r"[^а-яa-z0-9#\-\s.,]", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


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


def split_messages(text: str) -> List[str]:

    # Поддерживает 2 формата заголовка:
    # 1) [04.04.2026 12:30] Имя:
    # 2) Alex, [4 апр. 2026 в 15:39]

    if not text or not text.strip():
        return []

    lines = text.splitlines()

    old_header_pattern = re.compile(r"^\[\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}\] .+?:.*$")
    new_header_pattern = re.compile(
        r"^.+?, \[\d{1,2} [А-Яа-яЁё.]+ \d{4} в \d{2}:\d{2}\]\s*$"
    )

    blocks = []
    current_block = []

    def is_header_line(line: str) -> bool:
        stripped = line.strip()
        return bool(
            old_header_pattern.match(stripped) or new_header_pattern.match(stripped)
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
    # 223
    # Мамин завтрак понравился
    new_header_pattern = re.compile(
        r"^(.+?), \[(\d{1,2} [А-Яа-яЁё.]+ \d{4}) в (\d{2}:\d{2})\]\s*(.*)$",
        re.DOTALL,
    )
    new_match = new_header_pattern.match(block)
    if new_match:
        author = new_match.group(1).strip()
        raw_date = new_match.group(2).strip()  # 4 апр. 2026
        time_part = new_match.group(3).strip()  # 15:39
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

    return None


def split_chat_into_subreviews(body: str) -> List[str]:
    body = body.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not body:
        return []

    lines = body.split("\n")

    blocks = []
    current_block = []

    table_only_pattern = re.compile(r"^\s*\d{2,4}\s*$")
    table_with_text_pattern = re.compile(r"^\s*\d{2,4}\b")
    explicit_table_pattern = re.compile(
        r"^\s*(?:Стол\s*\d{2,4}\b|\d{2,4}\s*стол\b|\d{2,4}\s*,)",
        re.IGNORECASE,
    )

    def starts_new_subreview(line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False

        return bool(
            table_only_pattern.match(stripped)
            or explicit_table_pattern.match(stripped)
            or table_with_text_pattern.match(stripped)
        )

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

    # 1. Первая непустая строка целиком состоит из номера стола
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines:
        first_line = lines[0]
        if re.fullmatch(r"\d{2,4}", first_line):
            return first_line

        match = re.match(r"^(\d{2,4})\b", first_line)
        if match:
            return match.group(1)

    # 2. Явные форматы "Стол 223" / "223 стол"
    patterns = [
        r"\bСтол\s*(\d{2,4})\b",
        r"\bстол\s*(\d{2,4})\b",
        r"\b(\d{2,4})\s*стол\b",
        r"^\s*(\d{2,4})[,\s.]",
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
    return any(phrase_in_text(text, marker) for marker in NEGATIVE_EXCEPTIONS)


def count_markers(text: str, markers: List[str]) -> int:
    return sum(1 for marker in markers if phrase_in_text(text, marker))


def classify_tonality_by_text(text: str) -> str:
    text_lower = normalize_text_for_search(text).strip()

    if not text_lower:
        return ""

    if has_negative_exception(text_lower):
        return "Позитив"

    pos_score = count_markers(text_lower, POSITIVE_MARKERS)
    neg_score = count_markers(text_lower, NEGATIVE_MARKERS)
    has_mixed = any(phrase_in_text(text_lower, marker) for marker in MIXED_MARKERS)
    has_recovery = any(
        phrase_in_text(text_lower, marker) for marker in SERVICE_RECOVERY_MARKERS
    )

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
        "очень плохо",
        "есть невозможно",
        "горчит",
        "холодная",
        "кошмар",
        "не зашел",
        "убрали из счета",
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
        "убрали из счёта",
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
        "не приняла заказ" "не принял",
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

    # Был негатив, но его попытались компенсировать
    if has_recovery and neg_score > 0:
        return "Негатив"

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
    text_lower = normalize_text_for_search(text).strip()

    if not text_lower:
        if review_tag == "Кухня":
            return "Кухня / Кухня", "Низкий"
        if review_tag == "Бар":
            return "Бар / Напитки", "Низкий"
        if review_tag == "Десерты":
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
            if review_tag == "Десерты":
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

    return list(unique.values())


def detect_review_tag(text: str, detected_dishes: List[Dict[str, str]]) -> str:
    if detected_dishes:
        priority_order = ["Кухня", "Бар", "Десерты", "Детское"]
        dish_tags = [
            item["dish_tag"] for item in detected_dishes if item.get("dish_tag")
        ]
        for tag in priority_order:
            if tag in dish_tags:
                return tag
        if dish_tags:
            return dish_tags[0]

    text_n = normalize_text_for_search(text)
    scores = {}
    for tag, keywords in REVIEW_TAG_KEYWORDS.items():
        score = sum(1 for keyword in keywords if phrase_in_text(text_n, keyword))
        if score > 0:
            scores[tag] = score

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

    if text_lower in SHORT_REPLIES:
        return True

    if not re.search(r"[а-яa-z0-9]", text_lower, re.IGNORECASE):
        return True

    review_score = 0
    noise_score = 0

    review_patterns = [
        r"\bстол\s*\d{2,4}\b",
        r"\b\d{2,4}\s*стол\b",
        r"^\s*\d{2,4}\s*,",
        r"\bгость\b",
        r"\bгости\b",
        r"\bгостю\b",
        r"\bгостям\b",
        r"\bзаказ\b",
        r"\bблюдо\b",
        r"\bеда\b",
        r"\bнапиток\b",
        r"\bдоставка\b",
        r"\bвкусно\b",
        r"\bневкусно\b",
        r"\bне вкусно\b",
        r"\bпонравилось\b",
        r"\bне понравилось\b",
        r"\bсырой\b",
        r"\bхолодн",
        r"\bгоряч",
        r"\bдолго\b",
        r"\bбыстро\b",
        r"\bгрязно\b",
        r"\bшумно\b",
        r"\bизвинил",
        r"\bубрали из счет",
        r"\bубрали из счёта",
        r"\bзаменили\b",
        r"\bпеределали\b",
        r"\bкомплимент\b",
        r"[★☆]{3,5}",
        r"\bяндекс\b",
        r"\b2гис\b",
        r"\bgastroreview\b",
    ]

    for pattern in review_patterns:
        if re.search(pattern, text_lower, re.IGNORECASE):
            review_score += 2

    review_score += sum(1 for word in REVIEW_KEYWORDS if word in text_lower)
    noise_score += sum(1 for word in NOISE_KEYWORDS if word in text_lower)

    if len(text_lower) < 20:
        noise_score += 2

    imperative_markers = [
        "давайте",
        "пишите",
        "вносите",
        "смотрите",
        "проверьте",
        "скиньте",
        "добавьте",
        "отправьте",
        "не забывайте",
        "фиксируйте",
    ]
    noise_score += sum(1 for word in imperative_markers if word in text_lower)

    if extract_table_number(text):
        review_score += 3

    if any(
        word in text_lower
        for word in [
            "гость",
            "гости",
            "вкусно",
            "невкусно",
            "заказ",
            "доставка",
            "омлет",
            "пицца",
            "бургер",
        ]
    ):
        review_score += 2

    if classify_tonality_by_text(text):
        review_score += 3

    if detect_dishes(text):
        review_score += 3

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
        dish_rows.append(
            {
                "date": base_row["date"],
                "source": base_row["source"],
                "cafe": base_row["cafe"],
                "table": base_row["table"],
                "dish": item["dish"],
                "dish_tag": item["dish_tag"],
                "review_text": base_row["review_text"],
                "mention_tonality": base_row["tonality"],
                "priority": base_row["priority"],
                "problem": base_row["problem"],
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
    cafe = "АндерСон Таганская 36"
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
        is_noise = detect_noise(review_text)

        tonality = "" if is_noise else ensure_tonality(review_text)
        problem = "" if is_noise else extract_problem(review_text)
        what_done = "" if is_noise else extract_what_done(review_text)
        detected_dishes = [] if is_noise else detect_dishes(review_text)
        review_tag = "" if is_noise else detect_review_tag(review_text, detected_dishes)
        review_type, priority = (
            ("", "") if is_noise else detect_type_and_priority(review_text, review_tag)
        )

        if not is_noise and not priority:
            priority = "Средний" if tonality in ["Негатив", "Смешанный"] else "Низкий"

        detected_dishes_str = ", ".join(item["dish"] for item in detected_dishes)

        row = {
            "date": "",
            "source": "TableVisit",
            "cafe": "АндерСон Таганская 36",
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
        dish_rows.extend(build_dish_rows(row, detected_dishes))

    return review_rows, dish_rows


def main():
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            raw_text = f.read()

        message_blocks = split_messages(raw_text)
        review_rows = []
        dish_rows = []

        for block in message_blocks:
            parsed = parse_message_block(block)
            if not parsed:
                continue

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

        OUTPUT_DIR.mkdir(exist_ok=True)

        with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=review_fieldnames)
            writer.writeheader()
            writer.writerows(review_rows)

        with open(OUTPUT_DISHES_CSV, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=dish_fieldnames)
            writer.writeheader()
            writer.writerows(dish_rows)

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


if __name__ == "__main__":
    sys.exit(main())
