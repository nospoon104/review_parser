from pathlib import Path
import sys
import os

from scripts.parse_reviews import main as parse_reviews_main
from scripts.load_reviews_to_excel import main as load_reviews_to_excel_main


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = get_base_dir()

INPUT_DIR = BASE_DIR / "ПОЛОЖИТЬ_СЮДА_ФАЙЛ_С_ОТЗЫВАМИ"
OUTPUT_DIR = BASE_DIR / "ГОТОВЫЙ_РЕЗУЛЬТАТ"
TEMPLATE_DIR = BASE_DIR / "ШАБЛОН_НЕ_ТРОГАТЬ"

INPUT_FILE = INPUT_DIR / "raw_reviews.txt"
TEMPLATE_FILE = TEMPLATE_DIR / "feedback_template.xlsx"


def pause():
    input("\nНажми Enter для выхода...")


def clear_console():
    os.system("cls" if os.name == "nt" else "clear")


def print_header():
    print("=" * 55)
    print(" Автоматическая обработка отзывов v0.1")
    print("=" * 55)
    print()


def ensure_directories():
    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    TEMPLATE_DIR.mkdir(exist_ok=True)


def validate_files():
    if not INPUT_FILE.exists():
        print("Ошибка: не найден файл raw_reviews.txt")
        print(f"Ожидаемый путь: {INPUT_FILE}")
        print("\nЧто нужно сделать:")
        print("1. Открой папку 'ПОЛОЖИТЬ_СЮДА_ФАЙЛ_С_ОТЗЫВАМИ'")
        print("2. Положи туда файл raw_reviews.txt")
        return False

    if not TEMPLATE_FILE.exists():
        print("Ошибка: не найден шаблон feedback_template.xlsx")
        print(f"Ожидаемый путь: {TEMPLATE_FILE}")
        print("\nПроверь, что шаблон лежит в папке 'ШАБЛОН_НЕ_ТРОГАТЬ'")
        return False

    return True


def main():
    clear_console()
    print_header()
    ensure_directories()

    if not validate_files():
        pause()
        sys.exit(1)

    print("[1/2] Анализ и парсинг отзывов...")
    if parse_reviews_main() != 0:
        print("Ошибка на этапе парсинга отзывов.")
        pause()
        sys.exit(1)
    print("Готово.\n")

    print("[2/2] Формирование Excel-файла...")
    if load_reviews_to_excel_main() != 0:
        print("Ошибка на этапе формирования Excel.")
        pause()
        sys.exit(1)
    print("Готово.\n")

    print("Обработка завершена успешно.")
    print(f"Результат лежит в папке: {OUTPUT_DIR}")
    pause()


if __name__ == "__main__":
    main()
