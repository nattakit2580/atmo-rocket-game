"""Export the final sampled dataset to UTF-8 CSV."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import config


def to_final_schema(sample: pd.DataFrame, redact_urls: bool = False) -> pd.DataFrame:
    """Keep only the published columns, in the documented order.

    Letterboxd review URLs contain the reviewer's username. With
    redact_urls=True the URL column is blanked so the public dataset holds
    no direct identifier (the private working copy keeps it).
    """
    out = sample.copy()
    for col in config.FINAL_COLUMNS:
        if col not in out.columns:
            out[col] = ""
    out = out[config.FINAL_COLUMNS]
    if redact_urls:
        out["review_url"] = ""
    return out.sort_values(["movie_id", "review_id"], kind="mergesort").reset_index(drop=True)


def export_csv(final: pd.DataFrame, path: Path | None = None) -> Path:
    path = path or config.OUTPUT_DIR / config.CSV_OUTPUT_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    final.to_csv(path, index=False, encoding="utf-8", lineterminator="\n")
    return path
