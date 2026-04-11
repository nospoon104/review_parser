from pathlib import Path
from typing import List, Dict, Any, Tuple
import csv
import json
from datetime import datetime

from .config import get_config


class ReviewProcessor:
    """Главный класс-оркестратор."""

    def __init__(self):
        self.config = get_config()
        self.current_cafe: str = self.config.cafe_options[0]

    def set_cafe(self, cafe_name: str) -> None:
        if cafe_name in self.config.cafe_options:
            self.current_cafe = cafe_name

    def process(self, raw_text: str, cafe_name: str | None = None) -> Dict[str, Any]:
        if cafe_name:
            self.set_cafe(cafe_name)

        # Импортируем модуль внутри метода — это ломает цикл
        import scripts.parse_reviews as parse_module

        parse_module.CURRENT_CAFE = self.current_cafe

        # Вызываем старый main()
        exit_code = parse_module.main()

        # Читаем то, что создал старый парсер
        review_rows = []
        dish_rows = []

        reviews_path = self.config.output_dir / "parsed_reviews.csv"
        dishes_path = self.config.output_dir / "parsed_dishes.csv"

        if reviews_path.exists():
            with open(reviews_path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                review_rows = list(reader)

        if dishes_path.exists():
            with open(dishes_path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                dish_rows = list(reader)

        success, errors, report = self._create_quality_report(review_rows, dish_rows)

        return {
            "success": success,
            "review_rows": review_rows,
            "dish_rows": dish_rows,
            "quality_report": report,
            "errors": errors,
            "cafe": self.current_cafe,
        }

    def _create_quality_report(
        self, review_rows: List[Dict], dish_rows: List[Dict]
    ) -> Tuple[bool, List[str], Dict]:
        clean = [r for r in review_rows if str(r.get("is_noise", "")).lower() != "true"]
        total = len(review_rows)
        clean_count = len(clean)
        noise = total - clean_count

        def pct(v: int, base: int) -> float:
            return round((v / base) * 100, 2) if base > 0 else 0.0

        report = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "cafe": self.current_cafe,
            "counts": {
                "reviews_total": total,
                "reviews_clean": clean_count,
                "reviews_noise": noise,
                "dish_mentions_total": len(dish_rows),
            },
            "quality": {
                "empty_tonality_pct": pct(
                    sum(1 for r in clean if not str(r.get("tonality", "")).strip()),
                    clean_count,
                ),
                "empty_review_tag_pct": pct(
                    sum(1 for r in clean if not str(r.get("review_tag", "")).strip()),
                    clean_count,
                ),
                "empty_dish_pct": pct(
                    sum(1 for r in clean if not str(r.get("dish", "")).strip()),
                    clean_count,
                ),
                "mixed_pct": pct(
                    sum(
                        1
                        for r in clean
                        if str(r.get("tonality", "")).strip() == "Смешанный"
                    ),
                    clean_count,
                ),
            },
            "status": "ok",
            "errors": [],
        }

        self.config.output_dir.mkdir(exist_ok=True)
        (self.config.output_dir / "quality_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return True, [], report

    def save_to_csv(self, review_rows: List[Dict], dish_rows: List[Dict]) -> None:
        # Уже сохранено старым main(), ничего не делаем
        pass
