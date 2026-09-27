"""Run the full pipeline: ingest -> clean -> language -> dedup -> sample -> export -> validate -> report.

Usage (from the project root):
    python src/pipeline.py                 # full run
    python src/pipeline.py --redact-urls   # blank review_url in the published outputs
"""
from __future__ import annotations

import argparse
import json
import platform
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from build_report import build_pdf
from clean_reviews import deduplicate, remove_invalid
from export_csv import export_csv, to_final_schema
from export_excel import export_excel
from ingest import ingest, load_frame_sizes, load_manifest, load_movies
from language_detection import add_language_columns, is_target_language
from methodology_text import excel_rows
from sampling import sample_all
from validation import format_report, validate

PACKAGES = ["pandas", "numpy", "openpyxl", "lingua-language-detector", "reportlab", "pytest"]


def package_versions() -> dict[str, str]:
    out = {}
    for pkg in PACKAGES:
        try:
            out[pkg] = version(pkg)
        except Exception:
            out[pkg] = "not installed"
    return out


def _date_range(values: pd.Series) -> str:
    dates = sorted({str(v)[:10] for v in values if str(v).strip()})
    if not dates:
        return ""
    return dates[0] if dates[0] == dates[-1] else f"{dates[0]} to {dates[-1]}"


def build_sampling_log(movies, frame, invalid, labelled, english, duplicates, eligible, sample,
                       statuses, frame_sizes) -> pd.DataFrame:
    rows = []
    for m in movies.itertuples(index=False):
        mid = m.movie_id
        retrieved = int((frame["movie_id"] == mid).sum())
        n_invalid = int((invalid["movie_id"] == mid).sum()) if len(invalid) else 0
        lab = labelled[labelled["movie_id"] == mid]
        n_english = int((english["movie_id"] == mid).sum())
        n_dup = int((duplicates["movie_id"] == mid).sum()) if len(duplicates) else 0
        n_eligible = int((eligible["movie_id"] == mid).sum())
        n_sample = int((sample["movie_id"] == mid).sum()) if len(sample) else 0
        status = statuses.get(mid, config.STATUS_AWAITING)
        sub = frame[frame["movie_id"] == mid]
        notes = []
        if status == config.STATUS_AWAITING:
            notes.append("No permitted raw review data supplied yet.")
        if status == config.STATUS_INSUFFICIENT:
            notes.append(f"{config.STATUS_INSUFFICIENT}: only {n_eligible} eligible English reviews; "
                         f"all kept, none duplicated.")
        if len(lab):
            und = int((lab["language"] == "und").sum())
            if und:
                notes.append(f"{und} review(s) with undetermined language.")
        if mid not in frame_sizes and retrieved:
            notes.append("Platform-reported total not supplied; coverage not quantified.")
        rows.append({
            "movie_id": mid,
            "movie_title": m.movie_title,
            "total_reviews_available": frame_sizes.get(mid, ""),
            "population_size": retrieved,
            "invalid_removed": n_invalid,
            "english_population": n_english,
            "non_english_reviews": len(lab) - n_english,
            "duplicates_removed": n_dup,
            "eligible_population": n_eligible,
            "sample_requested": config.SAMPLE_SIZE_PER_MOVIE,
            "sample_obtained": n_sample,
            "random_seed": config.RANDOM_SEED,
            "sampling_method": config.SAMPLING_METHOD,
            "collection_date": _date_range(sub["collected_at"]),
            "source": "; ".join(sorted(set(sub["source"]))) if len(sub) else "",
            "collection_status": status,
            "notes": " ".join(notes),
        })
    return pd.DataFrame(rows, columns=config.SAMPLING_LOG_COLUMNS)


def run(redact_urls: bool = False, raw_dir: Path = config.RAW_DIR, make_pdf: bool = True) -> dict:
    run_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    for d in (config.PROCESSED_DIR, config.OUTPUT_DIR, config.LOGS_DIR, config.REPORTS_DIR):
        d.mkdir(parents=True, exist_ok=True)

    movies = load_movies()
    frame, rejected = ingest(raw_dir, movies, load_manifest(raw_dir / config.RAW_MANIFEST_FILE.name))
    frame_sizes = load_frame_sizes(raw_dir / config.FRAME_SIZES_FILE.name)

    valid, invalid = remove_invalid(frame)
    labelled = add_language_columns(valid)
    english = labelled[is_target_language(labelled)]
    eligible, duplicates = deduplicate(english)
    sample, statuses = sample_all(eligible, movies["movie_id"].tolist())

    # Audit trail (no usernames are stored anywhere).
    frame.to_csv(config.PROCESSED_DIR / "01_sampling_frame.csv", index=False, encoding="utf-8")
    labelled.to_csv(config.PROCESSED_DIR / "02_language_labelled.csv", index=False, encoding="utf-8")
    eligible.to_csv(config.PROCESSED_DIR / "03_eligible_population.csv", index=False, encoding="utf-8")
    non_english = labelled[~is_target_language(labelled)].assign(removal_reason="NOT_ENGLISH")
    removed = pd.concat([invalid, non_english, duplicates], ignore_index=True)
    keep = [c for c in ["movie_id", "review_id", "raw_file", "raw_row", "language",
                        "language_confidence", "removal_reason"] if c in removed.columns]
    removed.reindex(columns=keep).to_csv(config.PROCESSED_DIR / "removed_records.csv", index=False, encoding="utf-8")
    rejected.to_csv(config.PROCESSED_DIR / "rejected_rows.csv", index=False, encoding="utf-8")

    log = build_sampling_log(movies, frame, invalid, labelled, english, duplicates, eligible,
                             sample, statuses, frame_sizes)
    log.to_csv(config.LOGS_DIR / config.SAMPLING_LOG_NAME, index=False, encoding="utf-8")

    final = to_final_schema(sample, redact_urls=redact_urls)
    csv_path = export_csv(final)

    report, summary = validate(final, movies, log, eligible)
    (config.LOGS_DIR / config.VALIDATION_REPORT_NAME).write_text(format_report(report, summary, run_at), encoding="utf-8")

    movies_sheet = log.rename(columns={"population_size": "reviews_retrieved",
                                       "english_population": "english_reviews",
                                       "eligible_population": "eligible_reviews",
                                       "sample_obtained": "sample_size"})
    movies_sheet = movies_sheet.merge(movies[["movie_id", "movie_year"]], on="movie_id")
    movies_sheet = movies_sheet[config.MOVIES_SHEET_COLUMNS]

    versions = package_versions()
    ds = json.loads((config.CONFIG_DIR / "data_source.json").read_text(encoding="utf-8"))
    totals = {
        "movies": len(movies),
        "movies_with_data": int((log["population_size"] > 0).sum()),
        "movies_complete": int((log["collection_status"] == config.STATUS_COMPLETE).sum()),
        "movies_insufficient": int((log["collection_status"] == config.STATUS_INSUFFICIENT).sum()),
        "movies_awaiting": int((log["collection_status"] == config.STATUS_AWAITING).sum()),
        "reviews_retrieved": int(len(frame)),
        "invalid_removed": int(len(invalid)),
        "english": int(len(english)),
        "non_english": int(len(labelled) - len(english)),
        "duplicates_removed": int(len(duplicates)),
        "eligible": int(len(eligible)),
        "reviews_final": int(len(final)),
        "rejected_rows": int(len(rejected)),
    }
    ctx = {"run_at": run_at, "python_version": platform.python_version(), "versions": versions,
           "data_source": ds, "totals": totals, "sampling_log": log, "movies": movies,
           "validation": report, "summary": summary, "redact_urls": redact_urls}

    xlsx_path, truncated = export_excel(final, movies_sheet, log, excel_rows(ctx), report)
    metadata = {"run_at": run_at, "python_version": platform.python_version(), "platform": platform.platform(),
                "packages": versions, "random_seed": config.RANDOM_SEED,
                "sample_size_per_movie": config.SAMPLE_SIZE_PER_MOVIE, "target_language": config.TARGET_LANGUAGE,
                "min_language_confidence": config.MIN_LANGUAGE_CONFIDENCE,
                "min_alpha_chars": config.MIN_ALPHA_CHARS, "redact_urls": redact_urls,
                "excel_cells_truncated": truncated, "totals": totals, "validation_summary": summary}
    (config.LOGS_DIR / "run_metadata.json").write_text(json.dumps(metadata, indent=2, default=str), encoding="utf-8")

    pdf_path = build_pdf(ctx) if make_pdf else None
    print(format_report(report, summary, run_at))
    print(f"CSV : {csv_path}\nXLSX: {xlsx_path}\nPDF : {pdf_path}\nLOG : {config.LOGS_DIR / config.SAMPLING_LOG_NAME}")
    return {"summary": summary, "totals": totals, "final": final, "log": log}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--redact-urls", action="store_true",
                        help="blank review_url (contains usernames) in the published CSV/XLSX")
    args = parser.parse_args()
    run(redact_urls=args.redact_urls)
