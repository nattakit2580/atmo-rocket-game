"""Step 3 - Language identification with Lingua.

Lingua (lingua-language-detector) is the single language-identification
tool used in this study. The detector is built from ALL languages Lingua
supports (not only a shortlist), in high-accuracy mode, so that a review
is only labelled English when English outranks every other language.

For each review we record:
  language             ISO 639-1 code of the top-ranked language ("und" if
                       Lingua cannot assign any language, e.g. no letters)
  language_confidence  Lingua's relative confidence value (0-1) for it
"""
from __future__ import annotations

import sys
from functools import lru_cache
from importlib.metadata import version
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import config

UNDETERMINED = "und"


def lingua_version() -> str:
    try:
        return version("lingua-language-detector")
    except Exception:  # pragma: no cover
        return "unknown"


@lru_cache(maxsize=1)
def get_detector():
    from lingua import LanguageDetectorBuilder
    return LanguageDetectorBuilder.from_all_languages().build()


def detect_languages(texts: list[str]) -> list[tuple[str, float]]:
    if not texts:
        return []
    detector = get_detector()
    results = detector.compute_language_confidence_values_in_parallel(list(texts))
    out = []
    for values in results:
        if not values or values[0].value <= 0:
            out.append((UNDETERMINED, 0.0))
            continue
        top = values[0]
        out.append((top.language.iso_code_639_1.name.lower(), round(float(top.value), 4)))
    return out


def add_language_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    labels = detect_languages(df["review_text"].astype(str).tolist())
    df["language"] = [lang for lang, _ in labels]
    df["language_confidence"] = [conf for _, conf in labels]
    return df


def is_target_language(df: pd.DataFrame,
                       target: str = config.TARGET_LANGUAGE,
                       min_conf: float = config.MIN_LANGUAGE_CONFIDENCE) -> pd.Series:
    return (df["language"] == target) & (df["language_confidence"] >= min_conf)
