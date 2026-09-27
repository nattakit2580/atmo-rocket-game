"""Step 2 and 4 - Remove invalid records and duplicates.

Cleaning never edits the review text that is kept: the original text is
preserved exactly as ingested. Whitespace/case normalisation is used only
to *compare* texts when detecting duplicates. No stemming, tokenisation,
stop-word removal or spelling correction is performed here; that belongs to
the later NLP pre-processing stage, separate from data collection.

Reviews are never removed because of their sentiment or rating.
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import config

WS_RE = re.compile(r"\s+")


def alpha_char_count(text: str) -> int:
    return sum(1 for ch in text if unicodedata.category(ch).startswith("L"))


def comparison_key(text: str) -> str:
    """Key used ONLY for exact-duplicate detection (text itself is unchanged)."""
    return WS_RE.sub(" ", unicodedata.normalize("NFC", str(text))).strip()


def remove_invalid(df: pd.DataFrame, min_alpha: int = config.MIN_ALPHA_CHARS):
    """Drop empty / emoji-only / punctuation-only reviews.

    Returns (valid, removed) where removed has a `removal_reason` column.
    """
    text = df["review_text"].fillna("").astype(str)
    empty = text.str.strip() == ""
    too_little = ~empty & (text.map(alpha_char_count) < min_alpha)
    removed = pd.concat([
        df[empty].assign(removal_reason="EMPTY_TEXT"),
        df[too_little].assign(removal_reason=f"FEWER_THAN_{min_alpha}_LETTERS"),
    ])
    return df[~empty & ~too_little].copy(), removed


def _deterministic_order(df: pd.DataFrame) -> pd.DataFrame:
    """Earliest review first, then by review_id, independent of file order."""
    order = df.assign(_date=df["review_date"].replace("", "9999-12-31"))
    order = order.sort_values(["movie_id", "_date", "review_id"], kind="mergesort")
    return order.drop(columns="_date")


def deduplicate(df: pd.DataFrame):
    """Remove duplicate records.

    Rules, applied in this order (the earliest-dated record is kept):
      1. same review_id           (global)
      2. same review_url          (global, when a URL is present)
      3. identical review text    (within the same film, whitespace-normalised)

    Returns (unique, removed) where removed has a `removal_reason` column.
    """
    work = _deterministic_order(df)
    removed = []

    dup = work.duplicated(subset=["review_id"], keep="first")
    removed.append(work[dup].assign(removal_reason="DUPLICATE_REVIEW_ID"))
    work = work[~dup]

    has_url = work["review_url"].fillna("") != ""
    url_key = work["review_url"].fillna("").str.strip().str.rstrip("/").str.lower()
    dup = has_url & url_key.duplicated(keep="first")
    removed.append(work[dup].assign(removal_reason="DUPLICATE_REVIEW_URL"))
    work = work[~dup]

    key = work["review_text"].map(comparison_key)
    dup = pd.DataFrame({"m": work["movie_id"], "k": key}).duplicated(keep="first")
    removed.append(work[dup].assign(removal_reason="DUPLICATE_TEXT_SAME_MOVIE"))
    work = work[~dup]

    return work.copy(), pd.concat(removed)
