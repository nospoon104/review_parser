from pathlib import Path
import sys
import csv
from typing import List, Dict, Tuple, Any

from core.config import get_config
from core.processor import ReviewProcessor


def main() -> int:
    """
    Тонкая обёртка для совместимости со старым GUI.
    Сейчас просто вызывает новый процессор.
    """
    try:
        config = get_config()
        processor = ReviewProcessor()

        with open(config.input_file, "r", encoding="utf-8") as f:
            raw_text = f.read()

        if not raw_text.strip():
            print("Ошибка: raw_reviews.txt пустой")
            return 1

        result = processor.process(raw_text)

        if result["success"]:
            processor.save_to_csv(result["review_rows"], result["dish_rows"])
            print("Парсинг завершён успешно.")
            print(
                f"Всего строк отзывов: {result['quality_report']['counts']['reviews_total']}"
            )
            print(
                f"Полезных отзывов: {result['quality_report']['counts']['reviews_clean']}"
            )
            print(
                f"Шумовых строк: {result['quality_report']['counts']['reviews_noise']}"
            )
            print(f"CSV отзывов сохранён в: {config.output_dir / 'parsed_reviews.csv'}")
            print(f"CSV блюд сохранён в: {config.output_dir / 'parsed_dishes.csv'}")
            return 0
        else:
            print("Ошибка на этапе парсинга.")
            for err in result.get("errors", []):
                print(f"ERROR: {err}")
            return 1

    except Exception as e:
        print(f"Критическая ошибка парсинга: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
