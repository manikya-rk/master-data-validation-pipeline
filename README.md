# Master Data Validation Pipeline

A Python + SQL pipeline that validates warehouse master data **before** it reaches downstream systems such as an ERP. It cleans each record, runs field-level and cross-record rules (including GSTIN checksums and DigiPIN location checks), loads the clean records into a database, and writes a rejection report the client can act on.

> Personal demo project using **synthetic data**. It shows the approach I use for master-data onboarding in enterprise implementations. It contains no client code or data.

## Why this exists

When warehouses are onboarded by hand, the same issues come up again and again: mistyped GSTINs, a location code copied from another site, the same warehouse registered twice, 5-digit pincodes. Every bad record that reaches the ERP has to be found and fixed later. This pipeline stops bad records at the door and tells people exactly what to fix.

## What it checks

| Rule | Example of what it catches |
|---|---|
| Required fields | Missing name, address or coordinates |
| Warehouse code pattern | `WH-KA-12` instead of `WH-KA-0012` |
| GSTIN format + **checksum** | One mistyped character in a 15-char GSTIN |
| GSTIN state ↔ site state | A Maharashtra GSTIN (27…) on a Karnataka site |
| Pincode | 5 digits, or a leading zero |
| Coordinates | A point outside India |
| **DigiPIN** format + consistency | A DigiPIN more than 100 m from the site's coordinates |
| Capacity | Negative or non-numeric values |
| Duplicates (cross-record) | Same warehouse code twice; two codes at the same DigiPIN |

Records are also normalised first (trimmed, upper-cased IDs, collapsed whitespace, title-cased city) so trivial formatting differences don't cause rejections.

## Run it

```bash
python -m mdv data/sample_warehouses.csv --out out
# 40 records | 29 valid -> loaded | 11 rejected | 0.008s
```

Outputs in `out/`:

- `valid.csv`: clean records
- `rejected.csv`: rejected records, with the source row number and every reason
- `master.db`: a SQLite `warehouse_master` table. The load is an **upsert**, so re-running is safe.
- `report.md`: a summary for stakeholders

Sample report:

| Row | Code | Errors |
|---|---|---|
| 5 | WH-TN-0004 | gstin '33OBBFR8005F1ZA' fails checksum |
| 11 | WH-KA-0010 | digipin '33C-635-JK43' is 1545.2 km from the coordinates |
| 14 | WH-MH-0012 | duplicate warehouse_code (first seen on row 13) |
| 22 | WH-KA-0021 | gstin state code 27 does not match Karnataka (29) |
| 29 | WH-UP-0028 | same DigiPIN as row 28 - possible duplicate site |

## Tests

```bash
pip install -r requirements.txt
python -m pytest -q      # 23 passed
```

The tests cover DigiPIN encoding and decoding, every rule, the end-to-end pipeline and idempotent re-runs.

## Project structure

```
mdv/
  digipin.py     DigiPIN encoder/decoder (India Post 4x4 grid, 10 levels)
  rules.py       validation rules - one function per rule, easy to extend per client
  pipeline.py    CSV -> normalise -> validate -> valid/rejected CSV, SQLite upsert, report
scripts/
  make_sample_data.py   generates the synthetic dataset with realistic errors
tests/
```

## Tech

Python 3.10+ (standard library only) · SQL / SQLite · pytest
