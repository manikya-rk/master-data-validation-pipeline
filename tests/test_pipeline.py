import sqlite3
from pathlib import Path
from mdv.pipeline import run

DATA = Path(__file__).resolve().parents[1] / "data" / "sample_warehouses.csv"


def test_pipeline_end_to_end(tmp_path):
    s = run(str(DATA), str(tmp_path))
    assert s["total"] == 40
    assert s["rejected"] == 11 and s["valid"] == 29
    db = sqlite3.connect(tmp_path / "master.db")
    assert db.execute("select count(*) from warehouse_master").fetchone()[0] == 29
    # cleaned values were normalised before load
    assert db.execute("select city from warehouse_master where name like 'northstar logistics messy%'").fetchone()[0] == "Bengaluru"
    assert "Rejected records" in (tmp_path / "report.md").read_text()


def test_rerun_is_idempotent(tmp_path):
    run(str(DATA), str(tmp_path))
    run(str(DATA), str(tmp_path))
    db = sqlite3.connect(tmp_path / "master.db")
    assert db.execute("select count(*) from warehouse_master").fetchone()[0] == 29
