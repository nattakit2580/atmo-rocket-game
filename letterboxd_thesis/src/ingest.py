"""Step 1 - Build the sampling frame from permitted raw review files.

This module does NOT download anything. It reads review files that the
researcher obtained through a permitted channel (written permission from
Letterboxd, an approved API key, an authorised dataset, or manual
collection that does not bypass any protection) and placed in data/raw/.

Accepted inputs in data/raw/ (files whose name starts with "_" are ignored):
  * *.csv   (UTF-8)
  * *.jsonl (one JSON object per line)
  * *.json  (a JSON array of objects)

Each record needs at least a review text and a way to identify the film
(movie_id, letterboxd_slug, or movie_title + movie_year). See
data/raw/_TEMPLATE_raw_reviews.csv and README.md for the full schema.

Provenance (source, collected_at) must be given per row or per file in
data/raw/manifest.csv - records without provenance are rejected so that no
review in the dataset has an undocumented origin.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path

import pandas as pd

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import config

COLUMN_ALIASES = {
    "review_text": ["review_text", "text", "review", "content", "body", "review_body"],
    "review_id": ["review_id", "id", "viewing_id", "entry_id", "lid"],
    "review_url": ["review_url", "url", "link", "letterboxd_uri", "permalink"],
    "review_date": ["review_date", "date", "published", "watched_date", "created_at", "whenreviewed"],
    "rating": ["rating", "stars", "score", "member_rating"],
    "username": ["username", "user", "author", "reviewer", "member", "user_name"],
    "movie_id": ["movie_id"],
    "letterboxd_slug": ["letterboxd_slug", "film_slug", "slug"],
    "movie_title": ["movie_title", "film_title", "title", "name", "film_name"],
    "movie_year": ["movie_year", "film_year", "year", "release_year"],
    "source": ["source", "data_source"],
    "collected_at": ["collected_at", "retrieved_at", "scraped_at", "collection_date"],
}

INGESTED_COLUMNS = [
    "movie_id", "movie_title", "movie_year", "review_id", "review_id_generated",
    "review_text", "rating", "review_date", "review_url", "reviewer_id",
    "source", "collected_at", "raw_file", "raw_row",
]

STAR_RE = re.compile(r"^[★½\s]+$")


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def load_movies(path: Path = config.MOVIES_FILE) -> pd.DataFrame:
    movies = pd.read_csv(path, dtype=str, keep_default_na=False)
    required = {"movie_id", "movie_title", "movie_year"}
    missing = required - set(movies.columns)
    if missing:
        raise ValueError(f"{path} is missing columns: {sorted(missing)}")
    if movies["movie_id"].duplicated().any():
        raise ValueError(f"{path} contains duplicate movie_id values")
    if "letterboxd_slug" not in movies.columns:
        movies["letterboxd_slug"] = ""
    return movies


def load_manifest(path: Path = config.RAW_MANIFEST_FILE) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=["file", "source", "collected_at", "access_method",
                                     "permission_reference", "notes"])
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def load_frame_sizes(path: Path = config.FRAME_SIZES_FILE) -> dict[str, int]:
    """Optional: platform-reported number of reviews per film (for coverage)."""
    if not path.exists():
        return {}
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    out = {}
    for _, row in df.iterrows():
        value = str(row.get("total_reviews_available", "")).replace(",", "").strip()
        if row.get("movie_id") and value.isdigit():
            out[row["movie_id"]] = int(value)
    return out


def hash_username(username: str, salt: str | None = None) -> str:
    """SHA-256 pseudonym for a username.

    If the environment variable LB_HASH_SALT is set it is prepended to the
    username (a keyed/salted hash), which prevents re-identification by
    hashing a list of public usernames. The salt must be kept private and
    must NOT be published with the dataset.
    """
    if username is None or str(username).strip() == "":
        return ""
    salt = os.environ.get("LB_HASH_SALT", "") if salt is None else salt
    normalised = str(username).strip().lower()
    return hashlib.sha256((salt + normalised).encode("utf-8")).hexdigest()


def parse_rating(value) -> float | None:
    """Convert '4', '4.5', '★★★★½', '8/10' into a 0.5-5.0 star value."""
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "null"}:
        return None
    if STAR_RE.match(text):
        stars = text.count("★") + 0.5 * text.count("½")
        return stars if stars > 0 else None
    if "/" in text:
        num, _, den = text.partition("/")
        try:
            num_f, den_f = float(num), float(den)
            if den_f == 10:
                return round(num_f / 2 * 2) / 2
            if den_f == 5:
                return num_f
        except ValueError:
            return None
        return None
    try:
        rating = float(text)
    except ValueError:
        return None
    return rating if 0 < rating <= 5 else None


def parse_date(value) -> str:
    if value is None or str(value).strip() == "":
        return ""
    parsed = pd.to_datetime(str(value).strip(), errors="coerce", utc=True)
    if pd.isna(parsed):
        return ""
    return parsed.strftime("%Y-%m-%d")


def parse_timestamp(value) -> str:
    if value is None or str(value).strip() == "":
        return ""
    parsed = pd.to_datetime(str(value).strip(), errors="coerce", utc=True)
    if pd.isna(parsed):
        return ""
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


def stable_review_id(row: pd.Series) -> str:
    """Deterministic identifier when the source does not provide one."""
    if row.get("review_url"):
        basis = "url|" + str(row["review_url"]).strip().rstrip("/").lower()
    else:
        basis = "|".join([
            "rec", str(row.get("movie_id", "")), str(row.get("reviewer_id", "")),
            str(row.get("review_date", "")), str(row.get("review_text", "")),
        ])
    return "RID-" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:20]


def _standardise_columns(df: pd.DataFrame) -> pd.DataFrame:
    lower = {c: c.strip().lower().replace(" ", "_") for c in df.columns}
    df = df.rename(columns=lower)
    rename = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        if canonical in df.columns:
            continue
        for alias in aliases:
            if alias in df.columns and alias not in rename:
                rename[alias] = canonical
                break
    return df.rename(columns=rename)


def _read_raw_file(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8")
    if suffix == ".jsonl":
        return pd.read_json(path, lines=True, dtype=False).astype(str)
    if suffix == ".json":
        with open(path, encoding="utf-8") as fh:
            payload = json.load(fh)
        if isinstance(payload, dict):
            payload = payload.get("reviews", payload.get("items", []))
        return pd.DataFrame(payload).astype(str)
    raise ValueError(f"Unsupported file type: {path}")


def list_raw_files(raw_dir: Path = config.RAW_DIR) -> list[Path]:
    skip = {config.RAW_MANIFEST_FILE.name, config.FRAME_SIZES_FILE.name}
    files = []
    for path in sorted(raw_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".csv", ".jsonl", ".json"}:
            continue
        if path.name in skip or path.name.startswith(("_", ".")):
            continue
        files.append(path)
    return files


def _map_movies(df: pd.DataFrame, movies: pd.DataFrame) -> pd.Series:
    """Return the movie_id for each raw row ('' when it cannot be matched)."""
    ids = pd.Series([""] * len(df), index=df.index, dtype=object)
    known_ids = set(movies["movie_id"])
    if "movie_id" in df.columns:
        mask = df["movie_id"].isin(known_ids)
        ids[mask] = df.loc[mask, "movie_id"]
    if "letterboxd_slug" in df.columns:
        slug_map = {s.strip().lower(): m for s, m in zip(movies["letterboxd_slug"], movies["movie_id"]) if s}
        todo = ids == ""
        ids[todo] = df.loc[todo, "letterboxd_slug"].str.strip().str.lower().map(slug_map).fillna("")
    if "movie_title" in df.columns and "movie_year" in df.columns:
        key_map = {(t.strip().lower(), str(y).strip()): m
                   for t, y, m in zip(movies["movie_title"], movies["movie_year"], movies["movie_id"])}
        todo = ids == ""
        keys = zip(df.loc[todo, "movie_title"].str.strip().str.lower(),
                   df.loc[todo, "movie_year"].astype(str).str.strip().str[:4])
        ids[todo] = [key_map.get(k, "") for k in keys]
    return ids


# --------------------------------------------------------------------------
# Main entry point
# --------------------------------------------------------------------------
def ingest(raw_dir: Path = config.RAW_DIR, movies: pd.DataFrame | None = None,
           manifest: pd.DataFrame | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Read every permitted raw file into one standardised sampling frame.

    Returns (frame, rejected) where `rejected` lists raw rows that could not
    be attributed to a configured film or lack provenance, with a reason.
    """
    movies = load_movies() if movies is None else movies
    manifest = load_manifest() if manifest is None else manifest
    manifest_by_file = {row["file"]: row.to_dict() for _, row in manifest.iterrows()} if len(manifest) else {}

    frames, rejected = [], []
    for path in list_raw_files(raw_dir):
        rel = path.relative_to(raw_dir).as_posix()
        df = _standardise_columns(_read_raw_file(path))
        df["raw_file"] = rel
        df["raw_row"] = range(1, len(df) + 1)
        meta = manifest_by_file.get(rel) or manifest_by_file.get(path.name) or {}

        for col in ("source", "collected_at"):
            if col not in df.columns:
                df[col] = ""
            default = str(meta.get(col, "")).strip()
            df[col] = df[col].astype(str).str.strip().replace({"nan": ""})
            df.loc[df[col] == "", col] = default

        if "review_text" not in df.columns:
            raise ValueError(f"{rel}: no review text column found "
                             f"(expected one of {COLUMN_ALIASES['review_text']})")

        df["movie_id"] = _map_movies(df, movies)
        no_movie = df["movie_id"] == ""
        no_prov = (df["source"] == "") | (df["collected_at"] == "")
        for mask, reason in ((no_movie, "UNMATCHED_MOVIE"), (~no_movie & no_prov, "MISSING_PROVENANCE")):
            if mask.any():
                bad = df.loc[mask, ["raw_file", "raw_row"]].copy()
                bad["reason"] = reason
                rejected.append(bad)
        frames.append(df[~no_movie & ~no_prov])

    if not frames:
        empty = pd.DataFrame(columns=INGESTED_COLUMNS)
        return empty, pd.DataFrame(columns=["raw_file", "raw_row", "reason"])

    frame = pd.concat(frames, ignore_index=True)
    for col in ("review_id", "review_url", "review_date", "rating", "username"):
        if col not in frame.columns:
            frame[col] = ""
        frame[col] = frame[col].fillna("").astype(str).replace({"nan": "", "None": ""})

    meta = movies.set_index("movie_id")
    frame["movie_title"] = frame["movie_id"].map(meta["movie_title"])
    frame["movie_year"] = frame["movie_id"].map(meta["movie_year"])
    frame["review_text"] = frame["review_text"].fillna("").astype(str)
    frame["rating"] = frame["rating"].map(parse_rating)
    frame["review_date"] = frame["review_date"].map(parse_date)
    frame["collected_at"] = frame["collected_at"].map(lambda v: parse_timestamp(v) or v)
    frame["review_url"] = frame["review_url"].str.strip()
    frame["reviewer_id"] = frame["username"].map(hash_username)
    frame["review_id"] = frame["review_id"].str.strip()
    frame["review_id_generated"] = frame["review_id"] == ""
    gen = frame["review_id_generated"]
    frame.loc[gen, "review_id"] = frame[gen].apply(stable_review_id, axis=1)

    # The username is only needed to derive reviewer_id; it is never stored.
    frame = frame.drop(columns=["username"])
    rejected_df = (pd.concat(rejected, ignore_index=True) if rejected
                   else pd.DataFrame(columns=["raw_file", "raw_row", "reason"]))
    return frame[INGESTED_COLUMNS], rejected_df


if __name__ == "__main__":
    frame, rejected = ingest()
    config.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(config.PROCESSED_DIR / "01_sampling_frame.csv", index=False, encoding="utf-8")
    print(f"Ingested {len(frame):,} records from {len(list_raw_files())} raw file(s); "
          f"{len(rejected):,} rejected.")
