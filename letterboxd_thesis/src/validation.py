"""Automated validation of the final dataset.

Two kinds of checks are reported separately:
  * INTEGRITY    - must always PASS (duplicates, language, seed, provenance...)
  * COMPLETENESS - how far the dataset is from the 40 x 500 target
                   (can only PASS once permitted raw data has been supplied)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from clean_reviews import comparison_key
from sampling import sample_movie


def _row(kind, check, status, detail):
    return {"type": kind, "check": check, "status": status, "detail": str(detail)}


def validate(final: pd.DataFrame, movies: pd.DataFrame, sampling_log: pd.DataFrame,
             eligible: pd.DataFrame | None = None) -> tuple[pd.DataFrame, dict]:
    rows = []
    n_movies = len(movies)
    completed = int((sampling_log["collection_status"] == config.STATUS_COMPLETE).sum())
    insufficient = sampling_log.loc[sampling_log["collection_status"] == config.STATUS_INSUFFICIENT, "movie_title"].tolist()
    awaiting = int((sampling_log["collection_status"] == config.STATUS_AWAITING).sum())
    target_reviews = config.TARGET_MOVIES * config.SAMPLE_SIZE_PER_MOVIE

    # ---- Completeness ------------------------------------------------------
    rows.append(_row("COMPLETENESS", f"Movies configured = {config.TARGET_MOVIES}",
                     "PASS" if n_movies == config.TARGET_MOVIES else "FAIL", f"{n_movies} configured"))
    rows.append(_row("COMPLETENESS", "Movies completed (500 reviews each)",
                     "PASS" if completed == config.TARGET_MOVIES else "INCOMPLETE",
                     f"{completed}/{config.TARGET_MOVIES} complete; {len(insufficient)} insufficient; "
                     f"{awaiting} awaiting raw data"))
    rows.append(_row("COMPLETENESS", f"Reviews collected vs target {target_reviews:,}",
                     "PASS" if len(final) == target_reviews else "INCOMPLETE", f"{len(final):,}/{target_reviews:,}"))

    # ---- Integrity -----------------------------------------------------------
    per_movie = final.groupby("movie_id").size() if len(final) else pd.Series(dtype=int)
    over = per_movie[per_movie > config.SAMPLE_SIZE_PER_MOVIE]
    rows.append(_row("INTEGRITY", "No film exceeds 500 reviews", "PASS" if over.empty else "FAIL",
                     "ok" if over.empty else over.to_dict()))
    short_complete = [m for m, s in zip(sampling_log["movie_id"], sampling_log["collection_status"])
                      if s == config.STATUS_COMPLETE and per_movie.get(m, 0) != config.SAMPLE_SIZE_PER_MOVIE]
    rows.append(_row("INTEGRITY", "COMPLETE films have exactly 500 reviews",
                     "PASS" if not short_complete else "FAIL", short_complete or "ok"))

    non_en = int((final["language"] != config.TARGET_LANGUAGE).sum()) if len(final) else 0
    rows.append(_row("INTEGRITY", "Non-English records in final dataset = 0",
                     "PASS" if non_en == 0 else "FAIL", non_en))
    dup_ids = int(final["review_id"].duplicated().sum()) if len(final) else 0
    rows.append(_row("INTEGRITY", "Duplicate review IDs = 0", "PASS" if dup_ids == 0 else "FAIL", dup_ids))
    if len(final):
        urls = final["review_url"].fillna("")
        dup_urls = int(urls[urls != ""].str.rstrip("/").str.lower().duplicated().sum())
        keys = final["review_text"].map(comparison_key)
        dup_text_within = int(pd.DataFrame({"m": final["movie_id"], "k": keys}).duplicated().sum())
        dup_text_across = int(keys.duplicated().sum()) - dup_text_within
        missing_text = int((final["review_text"].fillna("").str.strip() == "").sum())
        bad_seed = int((final["sampling_seed"].astype(str) != str(config.RANDOM_SEED)).sum())
        no_source = int((final["source"].fillna("").astype(str).str.strip() == "").sum())
        no_collected = int((final["collected_at"].fillna("").astype(str).str.strip() == "").sum())
    else:
        dup_urls = dup_text_within = dup_text_across = missing_text = bad_seed = no_source = no_collected = 0
    rows.append(_row("INTEGRITY", "Duplicate review URLs = 0", "PASS" if dup_urls == 0 else "FAIL", dup_urls))
    rows.append(_row("INTEGRITY", "Exact duplicate review texts within a film = 0",
                     "PASS" if dup_text_within == 0 else "FAIL", dup_text_within))
    rows.append(_row("INFO", "Identical texts appearing under different films",
                     "INFO", f"{dup_text_across} (kept: different films are different reviews, "
                             "e.g. short texts such as 'masterpiece')"))
    rows.append(_row("INTEGRITY", "Missing review texts = 0", "PASS" if missing_text == 0 else "FAIL", missing_text))
    rows.append(_row("INTEGRITY", f"sampling_seed recorded (= {config.RANDOM_SEED}) on every record",
                     "PASS" if bad_seed == 0 else "FAIL", f"{bad_seed} records with other/missing seed"))
    rows.append(_row("INTEGRITY", "Every record states its source", "PASS" if no_source == 0 else "FAIL", no_source))
    rows.append(_row("INTEGRITY", "Every record states collected_at", "PASS" if no_collected == 0 else "FAIL", no_collected))
    leaked = [c for c in final.columns if c.lower() in {"username", "user", "author", "reviewer"}]
    rows.append(_row("INTEGRITY", "No username column in final dataset", "PASS" if not leaked else "FAIL", leaked or "ok"))
    missing_log = sorted(set(movies["movie_id"]) - set(sampling_log["movie_id"]))
    rows.append(_row("INTEGRITY", "Every film has a Sampling Log entry",
                     "PASS" if not missing_log else "FAIL", missing_log or f"{len(sampling_log)} entries"))

    if eligible is not None and len(final):
        outside = int((~final["review_id"].isin(eligible["review_id"])).sum())
        rows.append(_row("INTEGRITY", "Every sampled review belongs to the eligible population",
                         "PASS" if outside == 0 else "FAIL", outside))
        mismatched = []
        for movie_id, pop in eligible.groupby("movie_id"):
            redo, _ = sample_movie(pop)
            got = set(final.loc[final["movie_id"] == movie_id, "review_id"])
            if set(redo["review_id"]) != got:
                mismatched.append(movie_id)
        rows.append(_row("INTEGRITY", "Sampling is reproducible (re-drawn with same seed)",
                         "PASS" if not mismatched else "FAIL", mismatched or "identical samples"))

    report = pd.DataFrame(rows)
    integrity_ok = bool((report.loc[report["type"] == "INTEGRITY", "status"] == "PASS").all())
    summary = {
        "movies_requested": config.TARGET_MOVIES,
        "movies_configured": n_movies,
        "movies_completed": completed,
        "movies_insufficient": insufficient,
        "movies_awaiting_data": awaiting,
        "reviews_target": target_reviews,
        "reviews_collected": int(len(final)),
        "duplicate_review_ids": dup_ids,
        "non_english_records": non_en,
        "missing_review_texts": missing_text,
        "integrity_checks_passed": integrity_ok,
        "dataset_complete": completed == config.TARGET_MOVIES and len(final) == target_reviews,
    }
    return report, summary


def format_report(report: pd.DataFrame, summary: dict, run_at: str) -> str:
    lines = [
        "LETTERBOXD THESIS DATASET - VALIDATION REPORT",
        f"Generated: {run_at}",
        "",
        f"Movies requested: {summary['movies_requested']}",
        f"Movies completed: {summary['movies_completed']}/{summary['movies_requested']}",
        f"Movies with insufficient English reviews: {len(summary['movies_insufficient'])}"
        + (f" ({', '.join(summary['movies_insufficient'])})" if summary["movies_insufficient"] else ""),
        f"Movies awaiting raw data: {summary['movies_awaiting_data']}",
        f"Reviews target: {summary['reviews_target']:,}",
        f"Reviews collected: {summary['reviews_collected']:,}",
        f"Duplicate review IDs: {summary['duplicate_review_ids']}",
        f"Non-English records in final dataset: {summary['non_english_records']}",
        f"Missing review texts: {summary['missing_review_texts']}",
        "",
        f"Integrity checks: {'ALL PASS' if summary['integrity_checks_passed'] else 'FAILURES PRESENT'}",
        f"Dataset complete (40 x 500): {'YES' if summary['dataset_complete'] else 'NO'}",
        "",
        "Detailed checks",
        "---------------",
    ]
    for r in report.itertuples(index=False):
        lines.append(f"[{r.status:<10}] ({r.type}) {r.check}: {r.detail}")
    return "\n".join(lines) + "\n"
