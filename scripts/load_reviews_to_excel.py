import csv
from openpyxl import load_workbook
from pathlib import Path
import sys


def get_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
OUTPUT_DIR = BASE_DIR / "ГОТОВЫЙ_РЕЗУЛЬТАТ"
TEMPLATE_FILE = BASE_DIR / "ШАБЛОН_НЕ_ТРОГАТЬ" / "feedback_template.xlsx"
INPUT_CSV = OUTPUT_DIR / "parsed_reviews.csv"
INPUT_DISHES_CSV = OUTPUT_DIR / "parsed_dishes.csv"
OUTPUT_XLSX = OUTPUT_DIR / "ГОТОВАЯ_ТАБЛИЦА.xlsx"


def is_capa_needed(priority, tonality):
    return priority in ["Высокий", "Критический"] or tonality == "Негатив"


def approximate_row_height(text: str, base=18, chunk=55, max_height=120):
    if not text:
        return base
    lines = max(1, (len(str(text)) // chunk) + 1)
    return min(max_height, base * lines)


def build_excel_from_dir(input_dir: Path, output_file: Path | None = None) -> Path:
    input_dir = Path(input_dir)

    input_csv = input_dir / "parsed_reviews.csv"
    input_dishes_csv = input_dir / "parsed_dishes.csv"

    if output_file is None:
        output_file = input_dir / "ГОТОВАЯ_ТАБЛИЦА.xlsx"

    if not TEMPLATE_FILE.exists():
        raise FileNotFoundError(f"Не найден шаблон Excel: {TEMPLATE_FILE}")

    if not input_csv.exists():
        raise FileNotFoundError(f"Не найден CSV-файл: {input_csv}")

    if not input_dishes_csv.exists():
        raise FileNotFoundError(f"Не найден CSV-файл по блюдам: {input_dishes_csv}")

    wb = load_workbook(TEMPLATE_FILE)
    ws_reviews = wb["Отзывы"]
    ws_dishes = wb["Блюда"]
    ws_capa = wb["CAPA"]

    with open(input_csv, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        review_rows = list(reader)

    with open(input_dishes_csv, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        dish_rows = list(reader)

    review_row = 2
    capa_row = 4
    capa_id = 1
    skipped_noise = 0
    written_reviews = 0

    for row in review_rows:
        if str(row.get("is_noise", "")).strip().lower() == "true":
            skipped_noise += 1
            continue

        ws_reviews[f"A{review_row}"] = row["date"]
        ws_reviews[f"B{review_row}"] = row["source"]
        ws_reviews[f"C{review_row}"] = row["cafe"]
        ws_reviews[f"D{review_row}"] = row["table"]
        ws_reviews[f"E{review_row}"] = row["dish"]
        ws_reviews[f"F{review_row}"] = row["problem"]
        ws_reviews[f"G{review_row}"] = row["review_text"]
        ws_reviews[f"H{review_row}"] = row["tonality"]
        ws_reviews[f"I{review_row}"] = row["type"]
        ws_reviews[f"J{review_row}"] = row["priority"]
        ws_reviews[f"K{review_row}"] = row["what_done"]
        ws_reviews[f"L{review_row}"] = row.get("review_tag", "Другое")

        ws_reviews.row_dimensions[review_row].height = max(
            approximate_row_height(row["review_text"]),
            approximate_row_height(row.get("what_done", ""), base=16, chunk=35),
        )

        if is_capa_needed(row["priority"], row["tonality"]):
            ws_capa[f"A{capa_row}"] = f"CAPA-{capa_id:04d}"
            ws_capa[f"B{capa_row}"] = row["date"]
            ws_capa[f"C{capa_row}"] = row["source"]
            ws_capa[f"D{capa_row}"] = row["table"]
            ws_capa[f"E{capa_row}"] = row["dish"]
            ws_capa[f"F{capa_row}"] = row["problem"]
            ws_capa[f"G{capa_row}"] = row["review_text"]
            ws_capa[f"H{capa_row}"] = row["type"]
            ws_capa[f"I{capa_row}"] = row["priority"]

            ws_capa.row_dimensions[capa_row].height = approximate_row_height(
                row["review_text"]
            )

            capa_row += 1
            capa_id += 1

        review_row += 1
        written_reviews += 1

    dish_excel_row = 2
    written_dishes = 0
    skipped_dish_noise = 0

    for row in dish_rows:
        if str(row.get("is_noise", "")).strip().lower() == "true":
            skipped_dish_noise += 1
            continue

        ws_dishes[f"A{dish_excel_row}"] = row["date"]
        ws_dishes[f"B{dish_excel_row}"] = row["source"]
        ws_dishes[f"C{dish_excel_row}"] = row["cafe"]
        ws_dishes[f"D{dish_excel_row}"] = row["table"]
        ws_dishes[f"E{dish_excel_row}"] = row["dish"]
        ws_dishes[f"F{dish_excel_row}"] = row["dish_tag"]
        ws_dishes[f"G{dish_excel_row}"] = row["review_text"]
        ws_dishes[f"H{dish_excel_row}"] = row["mention_tonality"]
        ws_dishes[f"I{dish_excel_row}"] = row["priority"]
        ws_dishes[f"J{dish_excel_row}"] = row["problem"]

        ws_dishes.row_dimensions[dish_excel_row].height = approximate_row_height(
            row["review_text"]
        )

        dish_excel_row += 1
        written_dishes += 1

    wb.save(output_file)

    print(f"Готово! Файл '{output_file}' заполнен.")
    print(f"Записано отзывов в Excel: {written_reviews}")
    print(f"Пропущено шумовых строк: {skipped_noise}")
    print(f"Создано CAPA-записей: {capa_id - 1}")
    print(f"Записано упоминаний блюд: {written_dishes}")
    print(f"Пропущено шумовых строк по блюдам: {skipped_dish_noise}")

    return output_file


def main():
    try:
        build_excel_from_dir(OUTPUT_DIR, OUTPUT_XLSX)
        return 0
    except PermissionError:
        print("Ошибка: не удалось сохранить Excel-файл.")
        print(
            "Возможно, файл ГОТОВАЯ_ТАБЛИЦА.xlsx уже открыт. Закрой его и попробуй снова."
        )
        return 1
    except Exception as e:
        print(f"Ошибка формирования Excel: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
