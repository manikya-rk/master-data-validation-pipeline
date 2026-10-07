import pytest
from mdv import digipin


def test_format_and_symbols():
    code = digipin.encode(12.9716, 77.5946)
    assert digipin.is_valid_format(code)
    assert len(code) == 12 and code[3] == "-" and code[7] == "-"


@pytest.mark.parametrize("lat,lon", [(12.9716, 77.5946), (28.6139, 77.2090), (19.0760, 72.8777), (8.5, 76.9)])
def test_round_trip_within_cell(lat, lon):
    clat, clon = digipin.decode(digipin.encode(lat, lon))
    assert abs(clat - lat) < 0.0001 and abs(clon - lon) < 0.0001


def test_decoded_centre_encodes_to_same_code():
    code = digipin.encode(22.5726, 88.3639)
    assert digipin.encode(*digipin.decode(code)) == code


def test_outside_bounds_rejected():
    with pytest.raises(ValueError):
        digipin.encode(51.5, -0.12)


@pytest.mark.parametrize("bad", ["", "ABC-123-XYZ0", "39J4385LMT", "39J-438-LMT"])
def test_bad_formats(bad):
    assert not digipin.is_valid_format(bad)
