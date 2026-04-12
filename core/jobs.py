from pathlib import Path
from datetime import datetime
import json
import re


def slugify(text: str) -> str:
    text = text.strip().lower().replace("ё", "е")
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^a-zа-я0-9_]+", "_", text, flags=re.IGNORECASE)
    text = re.sub(r"_+", "_", text)
    return text.strip("_") or "unknown"


def create_job_dir(base_jobs_dir: Path, cafe_name: str, user_id: int) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cafe_slug = slugify(cafe_name)
    job_dir = base_jobs_dir / f"{timestamp}_{cafe_slug}_{user_id}"
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_dir


def save_job_meta(job_dir: Path, data: dict) -> None:
    meta_file = job_dir / "meta.json"
    meta_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
