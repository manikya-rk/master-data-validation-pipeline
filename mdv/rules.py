"""Field-level and record-level validation rules.

Each rule returns a list of error strings; an empty list means the record passed.
Rules are plain functions so new client-specific checks can be added in one place.
"""
import math
import re
from . import digipin

MAX_PIN_DRIFT_M = 100

GSTIN_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
GSTIN_RE = re.compile(r"^\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
CODE_RE = re.compile(r"^WH-[A-Z]{2}-\d{4}$")
PINCODE_RE = re.compile(r"^[1-9]\d{5}$")

# GST state codes for the states used in the sample data
STATE_CODES = {
    "Karnataka": "29", "Maharashtra": "27", "Tamil Nadu": "33", "Gujarat": "24",
    "Delhi": "07", "Telangana": "36", "Uttar Pradesh": "09", "West Bengal": "19",
}

REQUIRED = ["warehouse_code", "name", "gstin", "address", "city", "state",
            "pincode", "latitude", "longitude", "digipin", "capacity_sqft"]


def gstin_checksum(gstin14: str) -> str:
    total = 0
    for i, ch in enumerate(gstin14):
        product = GSTIN_CHARS.index(ch) * (1 if i % 2 == 0 else 2)
        total += product // 36 + product % 36
    return GSTIN_CHARS[(36 - total % 36) % 36]


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def check_required(r):
    return [f"missing {f}" for f in REQUIRED if not str(r.get(f, "")).strip()]


def check_code(r):
    c = r.get("warehouse_code", "")
    return [] if not c or CODE_RE.match(c) else [f"warehouse_code '{c}' must look like WH-KA-0001"]


def check_gstin(r):
    g = r.get("gstin", "").strip().upper()
    if not g:
        return []
    if not GSTIN_RE.match(g):
        return [f"gstin '{g}' has an invalid format"]
    errs = []
    if gstin_checksum(g[:14]) != g[14]:
        errs.append(f"gstin '{g}' fails checksum")
    expected = STATE_CODES.get(r.get("state", ""))
    if expected and g[:2] != expected:
        errs.append(f"gstin state code {g[:2]} does not match {r['state']} ({expected})")
    return errs


def check_state(r):
    s = r.get("state", "")
    return [] if not s or s in STATE_CODES else [f"unknown state '{s}'"]


def check_pincode(r):
    p = r.get("pincode", "").strip()
    return [] if not p or PINCODE_RE.match(p) else [f"pincode '{p}' must be 6 digits"]


def check_capacity(r):
    v = r.get("capacity_sqft", "").strip()
    if not v:
        return []
    try:
        return [] if float(v) > 0 else ["capacity_sqft must be positive"]
    except ValueError:
        return [f"capacity_sqft '{v}' is not a number"]


def check_location(r):
    lat, lon, pin = r.get("latitude", ""), r.get("longitude", ""), r.get("digipin", "").strip().upper()
    if not lat or not lon:
        return []
    try:
        lat, lon = float(lat), float(lon)
    except ValueError:
        return ["latitude/longitude must be numeric"]
    if not digipin.in_bounds(lat, lon):
        return [f"coordinates ({lat}, {lon}) are outside India"]
    if not pin:
        return []
    if not digipin.is_valid_format(pin):
        return [f"digipin '{pin}' has an invalid format"]
    plat, plon = digipin.decode(pin)
    dist = haversine_m(lat, lon, plat, plon)
    # tolerate GPS drift, but catch a DigiPIN copied from a different site
    if dist > MAX_PIN_DRIFT_M:
        return [f"digipin '{pin}' is {dist / 1000:.1f} km from the coordinates (expected {digipin.encode(lat, lon)})"]
    return []


RECORD_RULES = [check_required, check_code, check_gstin, check_state,
                check_pincode, check_capacity, check_location]


def validate_record(r: dict) -> list[str]:
    errors = []
    for rule in RECORD_RULES:
        errors.extend(rule(r))
    return errors


def find_duplicates(records: list[dict]) -> dict[int, list[str]]:
    """Cross-record checks: duplicate codes and two codes registered at one location."""
    seen_code, seen_pin, dupes = {}, {}, {}
    for i, r in enumerate(records):
        code, pin = r.get("warehouse_code", ""), r.get("digipin", "").strip().upper()
        if code in seen_code:
            dupes.setdefault(i, []).append(f"duplicate warehouse_code (first seen on row {seen_code[code] + 2})")
        elif code:
            seen_code[code] = i
        if pin and pin in seen_pin:
            dupes.setdefault(i, []).append(f"same DigiPIN as row {seen_pin[pin] + 2} - possible duplicate site")
        elif pin:
            seen_pin[pin] = i
    return dupes
