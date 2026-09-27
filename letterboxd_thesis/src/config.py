"""Shared settings and paths for the Letterboxd thesis pipeline.

Every methodological parameter lives here so that one file documents
the exact rules used to build the dataset.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUT_DIR = DATA_DIR / "output"
LOGS_DIR = PROJECT_ROOT / "logs"
REPORTS_DIR = PROJECT_ROOT / "reports"

MOVIES_FILE = CONFIG_DIR / "movies.csv"
RAW_MANIFEST_FILE = RAW_DIR / "manifest.csv"
FRAME_SIZES_FILE = RAW_DIR / "frame_sizes.csv"

CSV_OUTPUT_NAME = "letterboxd_reviews_all.csv"
XLSX_OUTPUT_NAME = "letterboxd_reviews_dataset.xlsx"
SAMPLING_LOG_NAME = "sampling_log.csv"
VALIDATION_REPORT_NAME = "validation_report.txt"
PDF_REPORT_NAME = "Letterboxd_Data_Collection_Methodology.pdf"

# --- Study design -----------------------------------------------------------
TARGET_MOVIES = 40
SAMPLE_SIZE_PER_MOVIE = 500
RANDOM_SEED = 42
SAMPLING_METHOD = "Simple Random Sampling without replacement (pandas.DataFrame.sample)"

# --- Language identification -------------------------------------------------
# Lingua is the single language-identification tool used in this study.
# A review is labelled with the language that receives the highest
# confidence value among ALL languages Lingua supports; only reviews whose
# top language is English enter the eligible population.
TARGET_LANGUAGE = "en"
# Optional extra rule: minimum confidence of the English label.
# 0.0 means "top-ranked language only" (the default, documented rule).
MIN_LANGUAGE_CONFIDENCE = 0.0

# --- Cleaning ---------------------------------------------------------------
# A review is "invalid" when its text contains fewer than this many
# alphabetic characters (e.g. emoji-only, punctuation-only, blank).
MIN_ALPHA_CHARS = 1

# Excel stores at most 32,767 characters in one cell.
EXCEL_MAX_CELL_CHARS = 32767

# --- Status labels ----------------------------------------------------------
STATUS_COMPLETE = "COMPLETE"
STATUS_INSUFFICIENT = "INSUFFICIENT_ENGLISH_REVIEWS"
STATUS_AWAITING = "AWAITING_RAW_DATA"

FINAL_COLUMNS = [
    "movie_id",
    "movie_title",
    "movie_year",
    "review_id",
    "review_text",
    "rating",
    "review_date",
    "language",
    "language_confidence",
    "review_url",
    "reviewer_id",
    "sampling_seed",
    "source",
    "collected_at",
]

MOVIES_SHEET_COLUMNS = [
    "movie_id",
    "movie_title",
    "movie_year",
    "total_reviews_available",
    "reviews_retrieved",
    "english_reviews",
    "eligible_reviews",
    "sample_size",
    "collection_status",
]

SAMPLING_LOG_COLUMNS = [
    "movie_id",
    "movie_title",
    "total_reviews_available",
    "population_size",
    "invalid_removed",
    "english_population",
    "non_english_reviews",
    "duplicates_removed",
    "eligible_population",
    "sample_requested",
    "sample_obtained",
    "random_seed",
    "sampling_method",
    "collection_date",
    "source",
    "collection_status",
    "notes",
]
