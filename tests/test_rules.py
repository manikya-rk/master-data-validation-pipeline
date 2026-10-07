from mdv import digipin
from mdv.rules import validate_record, find_duplicates, gstin_checksum


def good_record(**over):
    body = "29ABCDE1234F1Z"
    r = {
        "warehouse_code": "WH-KA-0001", "name": "Test DC", "gstin": body + gstin_checksum(body),
        "address": "Plot 1", "city": "Bengaluru", "state": "Karnataka", "pincode": "560100",
        "latitude": "12.9716", "longitude": "77.5946", "digipin": digipin.encode(12.9716, 77.5946),
        "capacity_sqft": "40000",
    }
    r.update(over)
    return r


def test_good_record_passes():
    assert validate_record(good_record()) == []


def test_known_real_gstin_checksum():
    assert gstin_checksum("27AAPFU0939F1Z") == "V"


def test_missing_field():
    assert "missing name" in validate_record(good_record(name=""))


def test_gstin_checksum_failure():
    r = good_record()
    r["gstin"] = r["gstin"][:-1] + ("0" if r["gstin"][-1] != "0" else "1")
    assert any("checksum" in e for e in validate_record(r))


def test_gstin_state_mismatch():
    body = "27ABCDE1234F1Z"
    errs = validate_record(good_record(gstin=body + gstin_checksum(body)))
    assert any("does not match Karnataka" in e for e in errs)


def test_digipin_from_wrong_place():
    errs = validate_record(good_record(digipin=digipin.encode(28.61, 77.20)))
    assert any("km from the coordinates" in e for e in errs)


def test_small_gps_drift_is_tolerated():
    assert validate_record(good_record(latitude="12.97162", longitude="77.59461")) == []


def test_bad_pincode_and_capacity():
    errs = validate_record(good_record(pincode="05601", capacity_sqft="abc"))
    assert len(errs) == 2


def test_duplicates():
    a, b = good_record(), good_record()
    dupes = find_duplicates([a, b])
    assert 1 in dupes and len(dupes[1]) == 2


def test_drift_beyond_tolerance_rejected():
    errs = validate_record(good_record(latitude="12.9736"))  # ~220 m away
    assert any("km from the coordinates" in e for e in errs)
