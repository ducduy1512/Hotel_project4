from decimal import Decimal

from api.peak_season_display import peak_season_summary, enrich_peak_season_record


def test_new_snapshot_is_additive_surcharge():
    summary = peak_season_summary(True, [{
        "ngay": "2026-12-21",
        "mua_cao_diem_id": 1,
        "he_so_gia": 0.2,
        "gia_co_ban": 1_000_000,
        "tien_dem": 1_000_000,
        "phi_mua_cao_diem": 200_000,
    }])
    assert summary["tien_mua_cao_diem"] == "200000.00"
    assert summary["he_so_mua_cao_diem"] == ["0.2"]
    assert summary["mua_cao_diem_snapshot_status"] == "OK"


def test_legacy_multiplier_snapshot_remains_readable():
    summary = peak_season_summary(True, [{
        "ngay": "2026-12-21",
        "mua_cao_diem_id": 1,
        "he_so_gia": 1.2,
        "gia_co_ban": 1_000_000,
        "tien_dem": 1_200_000,
    }])
    assert summary["tien_mua_cao_diem"] == "200000.00"
    assert summary["he_so_mua_cao_diem"] == ["0.2"]


def test_non_peak_night_has_no_surcharge():
    summary = peak_season_summary(False, [{
        "mua_cao_diem_id": None, "he_so_gia": 1.0,
        "gia_co_ban": 1_000_000, "tien_dem": 1_000_000,
    }])
    assert summary["tien_mua_cao_diem"] == "0.00"
    assert summary["mua_cao_diem_snapshot_status"] == "NOT_APPLIED"


def test_persisted_fee_is_accounting_source_of_truth():
    row = {
        "ap_dung_mua_cao_diem": True,
        "tien_phu_phi_mua_cao_diem": Decimal("200000.00"),
        "chi_tiet_mua_cao_diem": [{
            "mua_cao_diem_id": 1, "he_so_gia": 0.2, "gia_co_ban": 1_000_000,
            "tien_dem": 1_000_000, "phi_mua_cao_diem": 200_000,
        }],
    }
    result = enrich_peak_season_record(row)
    assert result["tien_mua_cao_diem"] == "200000.00"


def test_requested_invoice_example():
    room = Decimal("1000000.00")
    service = Decimal("50000.00")
    surcharge = room * Decimal("0.20")
    assert room + service + surcharge == Decimal("1250000.0000")


def test_supported_peak_surcharge_rates_are_valid():
    from api.schemas import validate_peak_surcharge_rate

    for allowed in (0.6, 0.5, 0.4, 0.35, 0.3, 0.25, 0.2, 0.1):
        assert validate_peak_surcharge_rate(allowed) == allowed

    for rejected in (1.2, 1.0, 0.0, 0.15, 0.7):
        try:
            validate_peak_surcharge_rate(rejected)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Rate {rejected} should be rejected")
