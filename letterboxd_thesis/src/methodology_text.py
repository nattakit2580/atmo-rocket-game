"""Single source of the methodology text used by the PDF and the Excel sheet.

All numbers (counts, dates, versions) are injected from the actual pipeline
run, so the documents always describe what was really done.
"""
from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import config

# Facts established during the compliance review (see docs/COMPLIANCE_REVIEW.md).
COMPLIANCE_CHECK_DATE = "2026-09-27"
TOS_CLAUSE = ("Except as explicitly authorized in these Terms, you must not employ any robot, "
              "spider, scraper, deep-link, or other automated data gathering or extraction tool, "
              "program, or algorithm to access, acquire, copy, or monitor any portion of the Service.")
TOS_URL = "https://letterboxd.com/legal/terms-of-use/"
API_URL = "https://letterboxd.com/api-beta/"
API_POLICY = ("Access to the Letterboxd API is by request only (api@letterboxd.com). Letterboxd states "
              "that it does not grant API access for data-analysis, visualisation or recommendation "
              "projects, for LLM/GPT-related use, or for private or personal projects.")

FLOW_STEPS = [
    "Movie Selection",
    "Permitted Data Acquisition",
    "Review Population Construction",
    "Data Cleaning",
    "Language Detection",
    "English Review Filtering",
    "Deduplication",
    "Simple Random Sampling",
    "500 Reviews / Movie",
    "CSV / XLSX Dataset",
]


def _pending(value: str) -> bool:
    return str(value).strip().upper().startswith("PENDING")


def build_sections(ctx: dict) -> list[tuple[str, list[str]]]:
    """Return [(heading, [paragraph, ...]), ...]. `ctx` comes from pipeline.py."""
    ds = ctx["data_source"]
    t = ctx["totals"]
    has_data = t["reviews_retrieved"] > 0
    n = config.SAMPLE_SIZE_PER_MOVIE
    seed = config.RANDOM_SEED
    lingua_v = ctx["versions"].get("lingua-language-detector", "unknown")

    status_sentence = (
        f"At the time this report was generated ({ctx['run_at']}), {t['reviews_retrieved']:,} review "
        f"records had been ingested for {t['movies_with_data']} of {t['movies']} films, and the final "
        f"dataset contained {t['reviews_final']:,} of the {t['movies'] * n:,} targeted reviews "
        f"({t['movies_complete']} films complete, {t['movies_insufficient']} with insufficient English "
        f"reviews, {t['movies_awaiting']} awaiting permitted raw data)."
        if has_data else
        f"At the time this report was generated ({ctx['run_at']}), no review data had yet been obtained "
        "through a permitted channel. The pipeline, templates and documentation are complete, and the "
        "dataset is produced by re-running the pipeline once permitted data is placed in data/raw/. "
        "All counts in this report therefore read zero; they are regenerated automatically on each run."
    )

    sections = [
        ("1. Objective", [
            f"The objective of this data-collection stage is to construct a dataset of English-language "
            f"film reviews for {config.TARGET_MOVIES} films, with {n} reviews per film "
            f"({config.TARGET_MOVIES * n:,} reviews in total), for subsequent text analysis in this thesis.",
            "To limit sampling bias, reviews are not taken from the order in which the platform displays "
            "them (most recent, oldest, popular, most liked, or first page). Instead, for every film a "
            "sampling frame of all reviews accessible through the permitted data source is built first, "
            "the frame is cleaned and restricted to English, and a simple random sample is then drawn "
            "from the resulting eligible population with a fixed random seed.",
            status_sentence,
        ]),
        ("2. Data Source", [
            f"Platform: {ds['platform']}.",
            f"Acquisition route: {ds['acquisition_route']}",
            f"Source description: {ds['source_description']}",
            f"Permission / licence reference: {ds['permission_reference']}",
            f"Collection period: {ds['collection_period']}",
            f"Sampling frame definition: {ds['frame_definition']}",
            f"Terms of Service review ({COMPLIANCE_CHECK_DATE}). Letterboxd's Terms of Use ({TOS_URL}) "
            f"state: \"{TOS_CLAUSE}\" Automated scraping of the Letterboxd website is therefore not "
            "permitted without explicit authorisation, and no scraping of letterboxd.com was performed "
            f"for this study. {API_POLICY} ({API_URL})",
            "Consequently the study relies only on data obtained through a permitted route, in this order "
            "of preference: (1) the official API with approved access; (2) written permission from "
            "Letterboxd for academic research; (3) a dataset whose terms allow this use; (4) review data "
            "supplied by the researcher; (5) manual, human-performed collection that does not bypass any "
            "protection. The collection software itself contains no web-access code: it only reads files "
            "that the researcher places in data/raw/, and each file must carry provenance (source and "
            "collection timestamp) or it is rejected.",
            "Safeguards against bypassing access restrictions: no Cloudflare or CAPTCHA circumvention, "
            "no undetected/stealth browser automation, no browser-fingerprint spoofing, no proxy rotation "
            "to evade rate limits, no use of private or undocumented endpoints, and no circumvention of "
            "authentication or access control were used or are supported by the software.",
        ]),
        ("3. Software and Tools", [
            f"Python {ctx['python_version']} was used for all processing. Package versions recorded at run "
            "time: " + "; ".join(f"{k} {v}" for k, v in ctx["versions"].items()) + ".",
            "pandas was used for data handling, cleaning, de-duplication and sampling (DataFrame.sample); "
            "NumPy is the numerical back-end of pandas' random number generation; Lingua "
            "(lingua-language-detector) for language identification; openpyxl to write the Excel "
            "workbook; ReportLab to generate this PDF; pytest to run automated tests of the pipeline. "
            "Microsoft Excel (or any XLSX viewer) can be used to inspect the workbook. The code is plain "
            "Python scripts (src/) executed from the command line; no notebook is required.",
        ]),
        ("4. Data Collection Procedure", [
            "The procedure follows the flow shown in Figure 1. Each step is implemented as a separate "
            "module in src/ and executed in order by src/pipeline.py.",
            "(a) Movie selection: the 40 films are listed in config/movies.csv with a stable identifier "
            "(M01-M40), title, year and Letterboxd slug. (b) Permitted data acquisition: raw review files "
            "are obtained outside the software through one of the permitted routes in Section 2. "
            "(c) Review population construction (src/ingest.py): all raw files are merged into one "
            "sampling frame, column names are standardised, each record is matched to a configured film, "
            "ratings and dates are normalised, a stable review_id is generated where the source provides "
            "none, and the username is replaced by a pseudonymous reviewer_id. (d) Cleaning "
            "(src/clean_reviews.py), (e) language detection and English filtering "
            "(src/language_detection.py), (f) de-duplication, (g) simple random sampling "
            "(src/sampling.py), and (h) export to CSV and XLSX (src/export_csv.py, src/export_excel.py), "
            "followed by automated validation (src/validation.py).",
        ]),
        ("5. Random Sampling Method", [
            "Simple Random Sampling without replacement is used, applied separately to each film. The "
            "sample is drawn only after the eligible English review population of the film has been "
            f"constructed; it is not a selection of the first {n} reviews shown by the website.",
            f"Before sampling, the eligible population is sorted by review_id so that the result does not "
            f"depend on file order or on the platform's display order. The sample is then drawn with "
            f"pandas: population.sample(n={n}, random_state={seed}). Every review in the eligible "
            f"population therefore has the same inclusion probability, {n}/N, where N is the size of that "
            "film's eligible population.",
            f"The fixed random seed ({seed}) makes the sample reproducible: running the pipeline again on "
            "the same raw data produces exactly the same reviews, which the validation step verifies by "
            "re-drawing every sample. The seed is stored in the sampling_seed column of every record and "
            "in the Sampling Log.",
            f"If a film has fewer than {n} eligible English reviews, all eligible reviews are kept, no "
            f"review is duplicated to reach {n}, and the film is flagged {config.STATUS_INSUFFICIENT} with "
            "its actual count in the Sampling Log.",
        ]),
        ("6. Language Identification", [
            "Language identification was performed before random sampling. Only reviews classified as "
            "English were retained in the eligible sampling population.",
            f"A single tool, Lingua (lingua-language-detector, version {lingua_v}), was used for "
            "reproducibility. The detector was built from all languages supported by Lingua, in its "
            "default high-accuracy mode. For each review, Lingua's confidence values for every language "
            "were computed; the review was labelled with the top-ranked language (ISO 639-1 code, stored "
            "in the language column) and its confidence value (language_confidence). Reviews without any "
            "identifiable language are labelled 'und'. A review is eligible when its top-ranked language "
            "is English"
            + (f" with confidence of at least {config.MIN_LANGUAGE_CONFIDENCE}." if config.MIN_LANGUAGE_CONFIDENCE > 0
               else "; no additional confidence threshold was applied."),
            "Lingua was chosen because it is designed for short and informal texts, which are common on "
            "Letterboxd. Very short reviews and reviews that mix languages remain harder to classify; see "
            "Section 10.",
        ]),
        ("7. Data Cleaning", [
            f"Invalid records were removed before language detection: empty texts and texts with fewer "
            f"than {config.MIN_ALPHA_CHARS} alphabetic character(s), such as emoji-only or "
            "punctuation-only reviews. Records that could not be matched to a configured film or lacked "
            "provenance were rejected at ingestion and listed in data/processed/rejected_rows.csv.",
            "Duplicates were removed after English filtering, in this order: identical review_id; "
            "identical review URL; and exact identical text within the same film (compared after Unicode "
            "NFC normalisation and whitespace collapsing only). For each duplicate group the "
            "earliest-dated record is kept. Identical short texts under different films (e.g. "
            "'masterpiece') are distinct reviews and are kept; their number is reported by validation.",
            "Reviews were never removed because of their sentiment or rating. The original review text "
            "is preserved unchanged in the dataset. No lower-casing, stemming, lemmatisation, "
            "tokenisation, stop-word removal or spelling correction was applied; such text "
            "pre-processing for machine learning/NLP is a separate, later stage of the thesis.",
        ]),
        ("8. Reproducibility", [
            f"The following are recorded automatically on every run: Python version ({ctx['python_version']}), "
            "package versions (Section 3, logs/run_metadata.json), random seed "
            f"({seed}), collection dates (collected_at per record and collection_date per film), the "
            "Sampling Log (logs/sampling_log.csv) with population counts before and after each cleaning "
            "step, the list of every removed record with its reason (data/processed/removed_records.csv), "
            "and the validation report (logs/validation_report.txt). requirements.txt pins the package "
            "versions.",
            "Given the same raw files in data/raw/, the command python src/pipeline.py regenerates the "
            "identical dataset, workbook, logs and this report.",
        ]),
        ("9. Ethical Considerations", [
            "The data are used solely for non-commercial academic research. Only data obtained within the "
            "scope permitted by the data source are used; anti-bot mechanisms, Cloudflare, CAPTCHA, rate "
            "limits and authentication were not bypassed.",
            "Personal data are minimised. Usernames are used only to derive a pseudonymous reviewer_id "
            "(SHA-256 hash, optionally keyed with a private salt through the LB_HASH_SALT environment "
            "variable) and are never written to any output file. No other profile information is "
            "collected. Because Letterboxd review URLs contain the username, the pipeline can blank the "
            "review_url column (--redact-urls) for any copy of the dataset that is shared outside the "
            "research team. Reviews are reported in aggregate; verbatim quotations in the thesis should "
            "be kept short and not attributed to identifiable members.",
            "If a salt is not used, an unsalted SHA-256 hash of a public username can be re-identified "
            "by hashing candidate usernames; it is therefore pseudonymous, not anonymous, and the dataset "
            "should be stored and shared accordingly.",
        ]),
        ("10. Limitations", [
            "The sampling population represents the set of reviews accessible through the permitted data "
            "acquisition method and should not necessarily be interpreted as the complete population of "
            "all Letterboxd reviews for the film. The sample is a simple random sample of that accessible "
            "population only; it is not claimed to be random with respect to all reviews on Letterboxd.",
            "Where the platform-reported number of reviews for a film is known, it is listed as "
            "total_reviews_available next to the number actually retrieved, so the coverage of each "
            "sampling frame can be judged. Where it is not known, coverage cannot be quantified.",
            "Letterboxd reviewers are not representative of all film audiences, and reviews are "
            "self-selected; findings describe Letterboxd reviewers, not viewers in general.",
            "Automatic language identification makes errors, especially on very short or mixed-language "
            "reviews, so a small number of English reviews may be excluded and a small number of "
            "non-English reviews may be included. Removing emoji-only and empty reviews slightly shifts "
            "the population toward reviews containing words.",
            "Reviews can be edited or deleted after collection; the dataset reflects their state on the "
            "collection date. Films with fewer than 500 eligible English reviews are reported as "
            "insufficient rather than padded, so per-film sample sizes may differ.",
            "Only data obtained through a permitted route can be used; if Letterboxd does not grant "
            "access, the scale or composition of the dataset may differ from the original plan, and any "
            "such change must be reported.",
        ]),
    ]

    pending = [k for k, v in ds.items() if not k.startswith("_") and _pending(v)]
    if pending:
        sections[1][1].insert(0, "NOTE: the data-source fields marked PENDING must be completed in "
                                 "config/data_source.json once the permitted source is confirmed ("
                                 + ", ".join(pending) + ").")
    return sections


def excel_rows(ctx: dict) -> list[tuple[str, str]]:
    rows = []
    for heading, paragraphs in build_sections(ctx):
        rows.append((heading, "\n\n".join(paragraphs)))
    rows.insert(4, ("Collection Flow", "  ->  ".join(FLOW_STEPS)))
    rows.append(("Random seed", str(config.RANDOM_SEED)))
    rows.append(("Sampling method", config.SAMPLING_METHOD))
    rows.append(("Report generated", ctx["run_at"]))
    return rows
