from datetime import date

import pytest
from pydantic import ValidationError

from api.schemas import (
    PeakSeasonBulkCreate,
    peak_surcharge_for_room_type,
)


def test_bulk_peak_season_accepts_dates_without_client_rate_overrides():
    payload = PeakSeasonBulkCreate.model_validate({
        "tu_ngay": "2026-12-20",
        "den_ngay": "2026-12-31",
    })
    assert payload.tu_ngay == date(2026, 12, 20)
    assert payload.den_ngay == date(2026, 12, 31)
    assert payload.room_rates == []


def test_room_type_rates_are_applied_to_physical_rooms_by_type():
    assert peak_surcharge_for_room_type("Standard") == 0.20
    assert peak_surcharge_for_room_type("Deluxe") == 0.25
    assert peak_surcharge_for_room_type("VIP") == 0.30
    assert peak_surcharge_for_room_type("Family") == 0.35
    assert peak_surcharge_for_room_type("  family ") == 0.35


def test_unknown_room_type_is_rejected():
    with pytest.raises(ValueError):
        peak_surcharge_for_room_type("Suite")


def test_bulk_peak_season_rejects_unsupported_rate_when_legacy_client_sends_it():
    with pytest.raises(ValidationError):
        PeakSeasonBulkCreate.model_validate({
            "tu_ngay": "2026-12-20",
            "den_ngay": "2026-12-31",
            "room_rates": [{"phong_id": 1, "he_so_gia": 0.75}],
        })
