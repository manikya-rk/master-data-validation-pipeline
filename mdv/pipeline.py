"""Run the validation pipeline: CSV in -> valid / rejected CSVs, SQLite load, report."""
import csv
import sqlite3
import time
from datetime import datetime
from pathlib import Path

from .rules import validate_record, find_duplicates

SCHEMA = """
CREATE TABLE IF NOT EXISTS warehouse_master (
    warehouse_code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    gstin TEXT NOT NULL,
    address TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    pincode TEXT NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    digipin TEXT NOT NULL UNIQUE,
    capacity_sqft REAL NOT NULL,
    loaded_at TEXT NOT NULL
);
"""


def normalise(r: dict) -> dict:
    out = {k: (v or "").strip() for k, v in r.items()}
    for k in ("gstin", "digipin", "warehouse_code"):
        out[k] = out.get(k, "").upper()
    out["name"] = " ".join(out.get("name", "").split())
    out["city"] = out.get("city", "").title()
    return out


def run(input_csv: str, out_dir: str = "out") -> dict:
    start = time.perf_counter()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    with open(input_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames
        records = [normalise(r) for r in reader]

    dupes = find_duplicates(records)
    valid, rejected = [], []
    for i, r in enumerate(records):
        errors = validate_record(r) + dupes.get(i, [])
        (rejected if errors else valid).append((i, r, errors))

    with open(out / "valid.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(r for _, r, _ in valid)
    with open(out / "rejected.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["source_row"] + fields + ["errors"])
        w.writeheader()
        for i, r, errs in rejected:
            w.writerow({"source_row": i + 2, **r, "errors": "; ".join(errs)})

    db = sqlite3.connect(out / "master.db")
    db.executescript(SCHEMA)
    now = datetime.now().isoformat(timespec="seconds")
    db.executemany(
        """INSERT INTO warehouse_master VALUES
           (:warehouse_code,:name,:gstin,:address,:city,:state,:pincode,
            :latitude,:longitude,:digipin,:capacity_sqft,:loaded_at)
           ON CONFLICT(warehouse_code) DO UPDATE SET
             name=excluded.name, address=excluded.address, capacity_sqft=excluded.capacity_sqft,
             loaded_at=excluded.loaded_at""",
        [{**r, "loaded_at": now} for _, r, _ in valid],
    )
    db.commit()
    db.close()

    elapsed = time.perf_counter() - start
    summary = {"total": len(records), "valid": len(valid), "rejected": len(rejected),
               "seconds": round(elapsed, 3)}
    write_report(out / "report.md", summary, rejected)
    return summary


def write_report(path: Path, s: dict, rejected) -> None:
    lines = [
        "# Warehouse master data validation report", "",
        f"_Generated {datetime.now():%d %b %Y %H:%M}_", "",
        "| Total | Valid (loaded) | Rejected | Run time |",
        "|---|---|---|---|",
        f"| {s['total']} | {s['valid']} | {s['rejected']} | {s['seconds']}s |", "",
    ]
    if rejected:
        lines += ["## Rejected records", "", "| Row | Code | Errors |", "|---|---|---|"]
        lines += [f"| {i + 2} | {r.get('warehouse_code') or '—'} | {'<br>'.join(e)} |" for i, r, e in rejected]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
