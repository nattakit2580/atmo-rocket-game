# Compliance Review — Letterboxd data access

**Date of review:** 2026-09-27
**Question:** Can review data be collected from Letterboxd automatically, and if not, which route is permitted?

## 1. What was checked

| Item | Finding |
|---|---|
| Letterboxd Terms of Use (<https://letterboxd.com/legal/terms-of-use/>) | *"Except as explicitly authorized in these Terms, you must not employ any robot, spider, scraper, deep-link, or other automated data gathering or extraction tool, program, or algorithm to access, acquire, copy, or monitor any portion of the Service."* |
| Letterboxd API (<https://letterboxd.com/api-beta/>) | Access **by request only** (api@letterboxd.com). Letterboxd states it does **not** grant access for data-analysis, visualisation or recommendation projects, for LLM/GPT-related use, or for private/personal projects. Applications are not individually answered. |
| Direct network access from the build environment | Connections to letterboxd.com were refused by the environment's network policy, so nothing was downloaded from Letterboxd. |
| Third-party "Letterboxd scrapers" (e.g. on Apify) | These scrape the website. Using them would breach the Terms of Use in the same way as scraping directly, so they are **not** a permitted route. |

The ToS and API policy wording above was confirmed via web search results that quote the Letterboxd pages. Check it against the live pages on the day you submit, because terms change.

## 2. Decision

1. **Automated scraping of letterboxd.com is not used.** No scraper, crawler, headless browser, Selenium/Playwright, undetected-chromedriver, fingerprint spoofing, proxy rotation, CAPTCHA/Cloudflare bypass, private endpoint or authentication bypass is used or supported. The project's code contains **no web-access code at all**.
2. **The official API is unlikely to be granted** for this purpose, because the API policy excludes data-analysis projects. It may still be requested (see route B).
3. The dataset is built only from data obtained through one of these routes, in order of preference:

| Route | What to do | Status |
|---|---|---|
| A. Official API (approved) | Apply to api@letterboxd.com; use only if approved and only within the approved scope | Unlikely (policy excludes data analysis) |
| B. **Written permission for academic research** | Send `docs/permission_request_email.md` to Letterboxd (api@letterboxd.com / support). Keep the reply as evidence. Collect only as the permission allows. | **Recommended first step** |
| C. Authorised dataset | Use an existing dataset only if its licence **and** its original collection were permitted. Most public "Letterboxd review" dumps on Kaggle/GitHub were scraped, so check their provenance before use. | Check case by case |
| D. User-provided data | Data the researcher is entitled to use, e.g. an export Letterboxd provides to a member for their own account, or data from participants who consent | Possible, but small |
| E. Manual-assisted collection | A human reads public review pages in a normal browser and records reviews, with no automation and no bypass | Only if route B permits it; see limitations |
| F. Pipeline for researcher-collected data | `src/pipeline.py` does ingestion, cleaning, language ID, sampling, export and validation automatically | **Implemented** |

## 3. Consequences for the methodology

* The sampling frame is **"reviews accessible through the permitted route"**, not "all Letterboxd reviews". The PDF's Limitations section states this.
* If route E (manual) is used, the frame is whatever a person could practically enumerate. For films with tens of thousands of reviews, a complete enumeration may be impractical. In that case the sampling is **not** a simple random sample of all reviews and must not be described as one. Instead, reduce the target, choose films with smaller review counts, or describe the design honestly (for example, as a random sample from a documented subset).
* Every record must carry `source` and `collected_at`, or the pipeline rejects it.
