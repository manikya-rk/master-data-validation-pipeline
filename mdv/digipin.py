"""DigiPIN encoder / decoder.

DigiPIN is India Post's 10-character geocoded address system. India's bounding
box is split into a 4x4 grid ten times over, giving a ~4m x 4m cell per code,
written as XXX-XXX-XXXX.
"""
import re

GRID = [
    ["F", "C", "9", "8"],
    ["J", "3", "2", "7"],
    ["K", "4", "5", "6"],
    ["L", "M", "P", "T"],
]
SYMBOLS = {ch: (r, c) for r, row in enumerate(GRID) for c, ch in enumerate(row)}
MIN_LAT, MAX_LAT = 2.5, 38.5
MIN_LON, MAX_LON = 63.5, 99.5
PATTERN = re.compile(r"^[FC98J327K456LMPT]{3}-[FC98J327K456LMPT]{3}-[FC98J327K456LMPT]{4}$")


def in_bounds(lat: float, lon: float) -> bool:
    return MIN_LAT <= lat <= MAX_LAT and MIN_LON <= lon <= MAX_LON


def encode(lat: float, lon: float) -> str:
    if not in_bounds(lat, lon):
        raise ValueError(f"({lat}, {lon}) is outside the DigiPIN bounding box")
    min_lat, max_lat, min_lon, max_lon = MIN_LAT, MAX_LAT, MIN_LON, MAX_LON
    code = ""
    for level in range(1, 11):
        lat_div = (max_lat - min_lat) / 4
        lon_div = (max_lon - min_lon) / 4
        row = min(max(3 - int((lat - min_lat) / lat_div), 0), 3)
        col = min(max(int((lon - min_lon) / lon_div), 0), 3)
        code += GRID[row][col]
        if level in (3, 6):
            code += "-"
        max_lat = min_lat + lat_div * (4 - row)
        min_lat = min_lat + lat_div * (3 - row)
        min_lon = min_lon + lon_div * col
        max_lon = min_lon + lon_div
    return code


def decode(code: str) -> tuple[float, float]:
    """Return the centre (lat, lon) of a DigiPIN cell."""
    if not is_valid_format(code):
        raise ValueError(f"Invalid DigiPIN format: {code!r}")
    min_lat, max_lat, min_lon, max_lon = MIN_LAT, MAX_LAT, MIN_LON, MAX_LON
    for ch in code.replace("-", ""):
        row, col = SYMBOLS[ch]
        lat_div = (max_lat - min_lat) / 4
        lon_div = (max_lon - min_lon) / 4
        max_lat, min_lat = min_lat + lat_div * (4 - row), min_lat + lat_div * (3 - row)
        min_lon, max_lon = min_lon + lon_div * col, min_lon + lon_div * (col + 1)
    return (min_lat + max_lat) / 2, (min_lon + max_lon) / 2


def is_valid_format(code: str) -> bool:
    return bool(code) and bool(PATTERN.match(code.strip().upper()))
