# Letterboxd Movie Review Dataset — Thesis Data Pipeline

Pipeline สำหรับสร้าง Dataset รีวิวภาพยนตร์ภาษาอังกฤษ **40 เรื่อง × 500 รีวิว = 20,000 รีวิว** ด้วย Simple Random Sampling (seed = 42) ที่ reproducible และตรวจสอบได้

## ⚠️ สถานะปัจจุบัน

| รายการ | สถานะ |
|---|---|
| Pipeline, sampling engine, language detection, cleaning, validation | ✅ เสร็จและผ่าน test |
| CSV / Excel / Sampling log / Validation report / Methodology PDF | ✅ สร้างแล้ว (ตอนนี้ **ยังไม่มีข้อมูลรีวิว** ทุกเรื่องมีสถานะ `AWAITING_RAW_DATA`) |
| ข้อมูลรีวิวจริง | ❌ **ยังไม่มี** ต้องได้มาจากช่องทางที่ได้รับอนุญาตก่อน |

**ทำไมถึงยังไม่มีข้อมูล:** Terms of Use ของ Letterboxd ห้ามใช้ robot, spider หรือ scraper ทุกชนิด และ Letterboxd ระบุว่าจะไม่ให้ API สำหรับงาน data-analysis ด้วย ดังนั้นโปรเจคนี้ **ไม่ scraping Letterboxd** และในโค้ดไม่มีส่วนที่เชื่อมต่อเว็บเลย รายละเอียดอยู่ใน [`docs/COMPLIANCE_REVIEW.md`](docs/COMPLIANCE_REVIEW.md)

**ขั้นตอนถัดไปที่แนะนำ:** ส่งอีเมลขออนุญาตใช้ข้อมูลเพื่องานวิชาการ โดยใช้แม่แบบใน [`docs/permission_request_email.md`](docs/permission_request_email.md)

## โครงสร้างโปรเจค

```
letterboxd_thesis/
├── README.md
├── requirements.txt
├── config/
│   ├── movies.csv            ← รายชื่อ 40 เรื่อง (PROPOSED — แก้ได้ตามหัวข้อ Thesis)
│   └── data_source.json      ← ข้อมูลแหล่งข้อมูลที่ได้รับอนุญาต (กรอกช่อง PENDING)
├── data/
│   ├── raw/                  ← ★ วางไฟล์รีวิวดิบที่ได้รับอนุญาตที่นี่
│   │   ├── _TEMPLATE_raw_reviews.csv
│   │   ├── manifest.csv      ← ที่มาของแต่ละไฟล์ (source, collected_at)
│   │   └── frame_sizes.csv   ← (optional) จำนวนรีวิวทั้งหมดที่ platform รายงาน
│   ├── processed/            ← audit trail ของแต่ละขั้น
│   └── output/               ← letterboxd_reviews_all.csv, letterboxd_reviews_dataset.xlsx
├── src/
│   ├── config.py             ← พารามิเตอร์ทั้งหมด (seed, n, language rules)
│   ├── ingest.py             ← Step 1: สร้าง sampling frame
│   ├── clean_reviews.py      ← Step 2/4: invalid + dedup
│   ├── language_detection.py ← Step 3: Lingua
│   ├── sampling.py           ← Step 5: SRS n=500 seed=42
│   ├── export_csv.py / export_excel.py
│   ├── validation.py
│   ├── methodology_text.py / build_report.py ← PDF
│   ├── pipeline.py           ← รันทุกขั้นตอน
│   └── make_zip.py           ← สร้าง ZIP สำหรับส่งงาน
├── reports/Letterboxd_Data_Collection_Methodology.pdf
├── logs/
│   ├── sampling_log.csv
│   ├── validation_report.txt
│   └── run_metadata.json
├── docs/                     ← compliance review + permission email
└── tests/                    ← pytest (ใช้ข้อมูลสังเคราะห์ใน temp dir เท่านั้น)
```

## วิธีใช้งาน

```bash
cd letterboxd_thesis
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q tests        # ทดสอบ pipeline
python src/pipeline.py           # สร้าง dataset + logs + PDF
python src/make_zip.py           # สร้าง dist/Letterboxd_Thesis_Dataset_Project.zip
```

ถ้าจะแชร์ dataset ออกนอกทีมวิจัย ให้รัน `python src/pipeline.py --redact-urls` เพราะ URL ของรีวิว Letterboxd มี username อยู่ในนั้น

สำหรับ pseudonym ที่ปลอดภัยกว่า ให้ตั้ง salt ลับก่อนรัน เช่น `export LB_HASH_SALT="<random secret>"` แล้ว **ห้ามเผยแพร่ค่า salt**

## ★ วิธีนำข้อมูลดิบมาใส่ (Raw Review Population)

1. ได้ข้อมูลมาจาก **ช่องทางที่ได้รับอนุญาตเท่านั้น** (API ที่อนุมัติแล้ว, หนังสืออนุญาต, dataset ที่ license อนุญาต, หรือเก็บด้วยมือโดยไม่ bypass ระบบใด ๆ)
2. เก็บ **รีวิวทั้งหมดที่เข้าถึงได้** ของแต่ละเรื่อง อย่าเก็บแค่หน้าแรกหรือ 500 รีวิวแรก เพราะ pipeline จะสุ่มให้เอง
3. วางไฟล์ `.csv` (UTF-8), `.jsonl` หรือ `.json` ไว้ใน `data/raw/` ตั้งชื่อไฟล์อย่างไรก็ได้ แต่ไฟล์ที่ขึ้นต้นด้วย `_` จะถูกข้าม
4. คอลัมน์ต่าง ๆ (ดูตัวอย่างใน `_TEMPLATE_raw_reviews.csv`):

| คอลัมน์ | จำเป็น? | หมายเหตุ |
|---|---|---|
| `review_text` | **ต้องมี** | ข้อความเต็ม ไม่ต้องทำความสะอาดเอง |
| `movie_id` หรือ `letterboxd_slug` หรือ (`movie_title` + `movie_year`) | **ต้องมี** อย่างใดอย่างหนึ่ง | ใช้จับคู่กับ `config/movies.csv` |
| `review_id` | แนะนำ | ถ้าไม่มี จะสร้าง `RID-<sha256>` จาก URL ให้ |
| `review_url` | แนะนำ | ใช้ตรวจรีวิวซ้ำ |
| `review_date` | แนะนำ | |
| `rating` | ถ้ามี | รับได้ทั้ง `4.5`, `★★★★½`, `9/10` |
| `username` | ถ้าจำเป็น | ถูก hash เป็น `reviewer_id` ทันที และ **ไม่ถูกบันทึก** ลงไฟล์ใด |
| `source`, `collected_at` | **ต้องมี** | ใส่ในแต่ละแถว หรือใส่ครั้งเดียวต่อไฟล์ใน `manifest.csv` |

5. กรอก `data/raw/manifest.csv` ให้ครบทุกไฟล์ ถ้ารู้จำนวนรีวิวทั้งหมดที่ platform แสดง ให้กรอก `frame_sizes.csv` ด้วย เพื่อรายงาน coverage ของ sampling frame
6. กรอกช่อง `PENDING` ใน `config/data_source.json` ค่าพวกนี้จะไปปรากฏใน PDF และในชีต Methodology โดยตรง
7. รัน `python src/pipeline.py` แล้วตรวจ `logs/validation_report.txt`

แถวที่ไม่มี provenance หรือจับคู่กับหนังไม่ได้จะถูกปฏิเสธ และบันทึกไว้ใน `data/processed/rejected_rows.csv`

## Methodology (สรุป)

1. **Ingest:** รวมไฟล์ทั้งหมดเป็น sampling frame เดียว, hash username, สร้าง review_id ที่คงที่
2. **Cleaning:** ตัด text ว่าง หรือไม่มีตัวอักษรเลย (emoji หรือเครื่องหมายล้วน) โดยไม่แก้ไขข้อความต้นฉบับ
3. **Language detection:** ใช้ Lingua 2.1.1 จากทุกภาษาที่รองรับ แล้วติดป้ายภาษาอันดับ 1 เก็บเฉพาะ `en`
4. **Dedup:** ตัดซ้ำตามลำดับ review_id → URL → text ที่เหมือนกันทุกตัวในหนังเรื่องเดียวกัน โดยเก็บรายการที่เก่าที่สุดไว้
5. **Sampling:** เรียงตาม `review_id` แล้วใช้ `df.sample(n=500, random_state=42)` ต่อเรื่อง
   - ถ้ามีน้อยกว่า 500 → เก็บทั้งหมด, **ไม่ duplicate**, และติดสถานะ `INSUFFICIENT_ENGLISH_REVIEWS`
6. **Validation:** ตรวจ integrity และทดลองสุ่มซ้ำเพื่อยืนยันว่า reproducible

ไม่ลบรีวิวเพราะ sentiment หรือ rating และไม่ทำ stemming/tokenization ในขั้นนี้

## Outputs

| ไฟล์ | เนื้อหา |
|---|---|
| `data/output/letterboxd_reviews_all.csv` | Dataset หลัก (UTF-8) 14 คอลัมน์ตาม spec |
| `data/output/letterboxd_reviews_dataset.xlsx` | ชีต Reviews, Movies, Sampling_Log, Methodology, Validation |
| `logs/sampling_log.csv` | สถิติต่อเรื่อง: population, invalid, English, non-English, duplicates, eligible, sample, seed, source, date |
| `logs/validation_report.txt` | ผลการตรวจสอบ |
| `logs/run_metadata.json` | Python และ package versions, พารามิเตอร์, จำนวนรวม |
| `reports/Letterboxd_Data_Collection_Methodology.pdf` | รายงาน Methodology สำหรับ Thesis ซึ่งสร้างใหม่ทุกครั้งที่รัน |
| `data/processed/*` | audit trail: sampling frame, language labels, eligible population, removed records (พร้อมเหตุผล) |

## หมายเหตุเรื่องรายชื่อหนัง

`config/movies.csv` เป็นรายชื่อ **ที่เสนอไว้ (PROPOSED)** 40 เรื่อง เลือกจากหนังที่น่าจะมีรีวิวภาษาอังกฤษเกิน 500 รีวิว และยังไม่ได้ตรวจ slug กับเว็บจริง ควรเปลี่ยนเป็นรายชื่อที่สอดคล้องกับคำถามวิจัย และอธิบายเกณฑ์การเลือกไว้ใน Thesis

## ข้อจำกัดที่ต้องเขียนใน Thesis

> The sampling population represents the set of reviews accessible through the permitted data acquisition method and should not necessarily be interpreted as the complete population of all Letterboxd reviews for the film.

ห้ามอ้างว่าเป็นการสุ่มจากรีวิวทั้งหมดบน Letterboxd หากไม่ได้เข้าถึง population ทั้งหมดจริง
