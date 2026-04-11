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
        print("DEBUG raw_text length:", len(raw_text))
        print("DEBUG raw_text preview:", raw_text[:300])
        if cafe_name:
            self.set_cafe(cafe_name)

        import scripts.parse_reviews as parse_module

        review_rows, dish_rows = parse_module.parse_raw_text(
            raw_text, self.current_cafe
        )
        parse_module.save_parsed_to_csv(review_rows, dish_rows, self.config.output_dir)

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
        import scripts.parse_reviews as parse_module

        parse_module.save_parsed_to_csv(review_rows, dish_rows, self.config.output_dir)
