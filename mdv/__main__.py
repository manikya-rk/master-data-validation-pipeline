import argparse
from .pipeline import run

p = argparse.ArgumentParser(description="Validate warehouse master data and load clean records.")
p.add_argument("input", help="CSV file of warehouse records")
p.add_argument("--out", default="out", help="output folder (default: out)")
a = p.parse_args()
s = run(a.input, a.out)
print(f"{s['total']} records | {s['valid']} valid -> loaded | {s['rejected']} rejected | {s['seconds']}s")
print(f"See {a.out}/report.md and {a.out}/rejected.csv")
