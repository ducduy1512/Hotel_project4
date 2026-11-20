"""Helpers for displaying immutable peak-season surcharge snapshots.

New snapshots store the base nightly room amount in ``tien_dem`` and the
additional fee in ``phi_mua_cao_diem``. Legacy snapshots (created with a
multiplier such as 1.20) are still understood during a rolling migration.
"""

import json
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def _decimal(value, default=ZERO):
    if value is None:
        return default
    try:
        return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError):
        return default


def parse_peak_snapshot(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError):
            return None
    return value if isinstance(value, list) else None


def _night_surcharge(item):
    """Return (fee, surcharge-rate, is-peak) supporting current and old JSON."""
    base = _decimal(item.get("gia_co_ban"))
    raw_rate = item.get("he_so_gia")
    try:
        rate = Decimal(str(raw_rate if raw_rate is not None else 0))
    except (InvalidOperation, TypeError, ValueError):
        rate = ZERO

    season_id = item.get("mua_cao_diem_id")
    explicit_fee = item.get("phi_mua_cao_diem")

    # New format: factor is already a surcharge rate in [0.1, 0.6].
    if explicit_fee is not None:
        fee = _decimal(explicit_fee)
        return fee, rate.quantize(CENT), season_id is not None or fee > ZERO

    # Legacy format: factor was a room-price multiplier (1.20, 1.60, ...)
    # and tien_dem already included the increase.
    if rate > Decimal("1.00"):
        old_applied = _decimal(item.get("tien_dem"), base * rate)
        fee = max(old_applied - base, ZERO)
        surcharge_rate = (rate - Decimal("1.00")).quantize(CENT)
        return fee, surcharge_rate, season_id is not None or fee > ZERO

    # Transitional format without an explicit fee.
    is_peak = season_id is not None or rate > ZERO
    fee = (base * rate).quantize(CENT, rounding=ROUND_HALF_UP) if is_peak else ZERO
    return fee, rate.quantize(CENT), is_peak


def peak_season_summary(applied_flag, snapshot):
    """Summarize the separately additive peak-season surcharge."""
    if not bool(applied_flag):
        return {
            "tien_mua_cao_diem": "0.00",
            "he_so_mua_cao_diem": [],
            "mua_cao_diem_snapshot_status": "NOT_APPLIED",
        }

    details = parse_peak_snapshot(snapshot)
    if not details:
        return {
            "tien_mua_cao_diem": None,
            "he_so_mua_cao_diem": [],
            "mua_cao_diem_snapshot_status": "MISSING",
        }

    surcharge_total = ZERO
    factors = []
    seasonal_nights = 0
    for item in details:
        if not isinstance(item, dict):
            continue
        fee, rate, is_peak = _night_surcharge(item)
        if not is_peak:
            continue
        surcharge_total += fee
        seasonal_nights += 1
        factor_text = format(rate.normalize(), "f")
        if factor_text not in factors:
            factors.append(factor_text)

    if seasonal_nights == 0:
        return {
            "tien_mua_cao_diem": None,
            "he_so_mua_cao_diem": [],
            "mua_cao_diem_snapshot_status": "MISSING",
        }

    return {
        "tien_mua_cao_diem": str(surcharge_total.quantize(CENT)),
        "he_so_mua_cao_diem": factors,
        "mua_cao_diem_snapshot_status": "OK",
    }


def enrich_peak_season_record(record):
    """Mutate and return one API row with derived peak-fee display fields."""
    if record is None:
        return None
    snapshot = record.get("chi_tiet_mua_cao_diem")
    if isinstance(snapshot, str):
        parsed = parse_peak_snapshot(snapshot)
        if parsed is not None:
            record["chi_tiet_mua_cao_diem"] = parsed
            snapshot = parsed
    summary = peak_season_summary(record.get("ap_dung_mua_cao_diem"), snapshot)
    # Persisted Booking/Pay/Invoice fee columns are the accounting source of truth;
    # the JSON snapshot remains the source for showing which nightly rates applied.
    stored_fee = record.get("tien_phu_phi_mua_cao_diem")
    if stored_fee is not None:
        summary["tien_mua_cao_diem"] = str(_decimal(stored_fee))
        if not bool(record.get("ap_dung_mua_cao_diem")):
            summary["mua_cao_diem_snapshot_status"] = "NOT_APPLIED"
    record.update(summary)
    return record


def enrich_peak_season_records(records):
    for record in records:
        enrich_peak_season_record(record)
    return records
