"""Step 5 - Simple Random Sampling of the eligible English population.

For every film the eligible population (valid, English, de-duplicated
reviews) is first put into a canonical order (sorted by review_id), so that
the result does not depend on the order in which raw files were read or on
the order the website displayed reviews. Then

    population.sample(n=500, random_state=42)

draws a simple random sample without replacement. If fewer than 500
eligible reviews exist, ALL of them are kept (no duplication / no
over-sampling) and the film is flagged INSUFFICIENT_ENGLISH_REVIEWS.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import config


def canonical_order(population: pd.DataFrame) -> pd.DataFrame:
    return population.sort_values("review_id", kind="mergesort").reset_index(drop=True)


def sample_movie(population: pd.DataFrame,
                 n: int = config.SAMPLE_SIZE_PER_MOVIE,
                 seed: int = config.RANDOM_SEED) -> tuple[pd.DataFrame, str]:
    """Return (sample, status) for one film's eligible population."""
    if len(population) == 0:
        return population.iloc[0:0].copy(), config.STATUS_AWAITING
    ordered = canonical_order(population)
    if len(ordered) >= n:
        sample = ordered.sample(n=n, random_state=seed, replace=False)
        status = config.STATUS_COMPLETE
    else:
        sample = ordered.copy()
        status = config.STATUS_INSUFFICIENT
    sample = sample.assign(sampling_seed=seed)
    return sample.sort_values("review_id", kind="mergesort"), status


def sample_all(eligible: pd.DataFrame, movie_ids: list[str],
               n: int = config.SAMPLE_SIZE_PER_MOVIE,
               seed: int = config.RANDOM_SEED) -> tuple[pd.DataFrame, dict[str, str]]:
    samples, statuses = [], {}
    for movie_id in movie_ids:
        pop = eligible[eligible["movie_id"] == movie_id]
        sample, status = sample_movie(pop, n=n, seed=seed)
        statuses[movie_id] = status
        if len(sample):
            samples.append(sample)
    if samples:
        return pd.concat(samples, ignore_index=True), statuses
    return eligible.iloc[0:0].assign(sampling_seed=pd.Series(dtype="int64")), statuses
