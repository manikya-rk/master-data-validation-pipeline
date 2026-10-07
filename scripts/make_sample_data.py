"""Generate a synthetic warehouse CSV with a realistic mix of good and bad rows."""
import csv
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mdv import digipin
from mdv.rules import gstin_checksum, STATE_CODES

random.seed(7)
SITES = [  # (city, state, pincode, lat, lon, state_abbr)
    ("Bengaluru", "Karnataka", "562123", 13.1035, 77.5890, "KA"),
    ("Hosur Road", "Karnataka", "560100", 12.8452, 77.6602, "KA"),
    ("Bhiwandi", "Maharashtra", "421302", 19.2967, 73.0631, "MH"),
    ("Chakan", "Maharashtra", "410501", 18.7606, 73.8636, "MH"),
    ("Sriperumbudur", "Tamil Nadu", "602105", 12.9675, 79.9419, "TN"),
    ("Sanand", "Gujarat", "382110", 22.9921, 72.3816, "GJ"),
    ("Narela", "Delhi", "110040", 28.8527, 77.0929, "DL"),
    ("Shamshabad", "Telangana", "501218", 17.2403, 78.4294, "TS"),
    ("Greater Noida", "Uttar Pradesh", "201306", 28.4744, 77.5040, "UP"),
    ("Dankuni", "West Bengal", "712311", 22.6800, 88.2931, "WB"),
]


def gstin(state):
    pan = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=5)) + f"{random.randint(1000, 9999)}" + random.choice("ABCDEFGH")
    body = STATE_CODES[state] + pan + "1Z"
    return body + gstin_checksum(body)


rows = []
for n in range(1, 41):
    city, state, pin, lat, lon, ab = SITES[n % len(SITES)]
    lat += random.uniform(-0.05, 0.05)
    lon += random.uniform(-0.05, 0.05)
    rows.append({
        "warehouse_code": f"WH-{ab}-{n:04d}",
        "name": f"Northstar Logistics {city} DC {n}",
        "gstin": gstin(state),
        "address": f"Plot {random.randint(1, 300)}, Industrial Area, {city}",
        "city": city, "state": state, "pincode": pin,
        "latitude": f"{lat:.6f}", "longitude": f"{lon:.6f}",
        "digipin": digipin.encode(lat, lon),
        "capacity_sqft": str(random.choice([25000, 40000, 60000, 85000, 120000])),
    })

# inject the kinds of issues seen in real onboarding data
rows[3]["gstin"] = rows[3]["gstin"][:-1] + ("A" if rows[3]["gstin"][-1] != "A" else "B")  # bad checksum
rows[6]["pincode"] = "11004"                                         # 5-digit pincode
rows[9]["digipin"] = digipin.encode(26.9124, 75.7873)               # pin from another city
rows[12]["warehouse_code"] = rows[11]["warehouse_code"]             # duplicate code
rows[15]["latitude"], rows[15]["longitude"] = "51.5072", "-0.1276"  # outside India
rows[18]["capacity_sqft"] = "-500"
rows[20]["gstin"] = "27" + rows[20]["gstin"][2:14]                  # Maharashtra GSTIN on a Karnataka site
rows[20]["gstin"] += gstin_checksum(rows[20]["gstin"])
rows[24]["name"] = ""                                                # missing field
rows[27]["digipin"] = rows[26]["digipin"]                            # same site twice
rows[27]["latitude"], rows[27]["longitude"] = rows[26]["latitude"], rows[26]["longitude"]
rows[30]["digipin"] = "ABC-123-XYZ0"                                 # bad format
rows[33]["warehouse_code"] = "WH-KA-12"                              # bad code pattern
rows[35]["name"] = "  northstar   logistics  messy   spacing  "      # cleaned, still valid
rows[35]["city"] = "bengaluru"

out = Path(__file__).resolve().parents[1] / "data" / "sample_warehouses.csv"
with open(out, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print(f"wrote {len(rows)} rows to {out}")
