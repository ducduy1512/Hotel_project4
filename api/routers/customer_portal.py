"""Customer-only endpoints. All queries are restricted to the signed-in customer."""
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from database import Error
from pydantic import BaseModel, Field

from api.database import get_db
from api.routers.auth import require_customer
from api.qr_payment_service import get_qr_config, build_vietqr_url, payment_code_for

router = APIRouter(prefix="/api/customer", tags=["Customer Portal"])
PAYMENT_METHODS = {"TIEN_MAT", "CHUYEN_KHOAN", "THE"}


class CustomerServiceSelection(BaseModel):
    dichvu_id: int = Field(gt=0)
    so_luong: int = Field(gt=0, le=99)


class CustomerBookingCreate(BaseModel):
    phong_id: int = Field(gt=0)
    ngay_nhan: date
    ngay_tra: date
    # Danh sách dịch vụ mặc định và bổ sung khách chọn; [] = không chọn dịch vụ.
    dich_vu: list[CustomerServiceSelection] = Field(default_factory=list)


class CustomerPaymentRequest(BaseModel):
    method: str


@router.get("/payment-methods")
def customer_payment_methods(current_user=Depends(require_customer)):
    """Expose available payment methods without turning missing QR config into an API error."""
    try:
        get_qr_config()
        qr_available = True
        qr_message = None
    except RuntimeError as exc:
        qr_available = False
        qr_message = str(exc)

    return {
        "cash_available": True,
        "card_available": True,
        "qr_available": qr_available,
        "qr_message": qr_message,
    }


def _room_price_preview(cursor, room_id: int, ngay_nhan: date, ngay_tra: date):
    """Quote the base room rate and the peak-season surcharge separately."""
    cursor.execute(
        """SELECT lp.gia_co_ban FROM phong p
           JOIN loaiphong lp ON lp.id = p.loai_phong_id WHERE p.id = %s""",
        (room_id,),
    )
    room = cursor.fetchone()
    if room is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy phòng.")

    cent = Decimal("0.01")
    base_rate = Decimal(str(room["gia_co_ban"])).quantize(cent, rounding=ROUND_HALF_UP)
    day = ngay_nhan
    nightly = []
    room_total = Decimal("0.00")
    surcharge_total = Decimal("0.00")
    has_peak = False
    while day < ngay_tra:
        cursor.execute(
            """SELECT m.id, pm.he_so_phu_thu AS he_so_gia
               FROM muacaodiem m
               JOIN phong_muacaodiem pm ON pm.muacaodiem_id = m.id
               WHERE pm.phong_id = %s AND %s BETWEEN m.tu_ngay AND m.den_ngay
               ORDER BY pm.he_so_phu_thu DESC, m.id DESC LIMIT 1""",
            (room_id, day),
        )
        season = cursor.fetchone()
        factor = Decimal(str(season["he_so_gia"])) if season else Decimal("0.00")
        season_id = season["id"] if season else None
        if season:
            has_peak = True
        nightly_room = base_rate
        nightly_surcharge = (base_rate * factor).quantize(cent, rounding=ROUND_HALF_UP)
        room_total += nightly_room
        surcharge_total += nightly_surcharge
        nightly.append({
            "ngay": day.isoformat(),
            "mua_cao_diem_id": season_id,
            "he_so_gia": float(factor),
            "gia_co_ban": float(base_rate),
            "tien_dem": float(nightly_room),
            "phi_mua_cao_diem": float(nightly_surcharge),
        })
        day += timedelta(days=1)

    total_before_services = (room_total + surcharge_total).quantize(cent, rounding=ROUND_HALF_UP)
    peak_rates = sorted({
        int((Decimal(str(item["he_so_gia"])) * Decimal("100")).quantize(Decimal("1")))
        for item in nightly
        if item.get("mua_cao_diem_id") is not None and Decimal(str(item["he_so_gia"])) > 0
    })
    return {
        "phong_id": room_id,
        "ngay_nhan": ngay_nhan,
        "ngay_tra": ngay_tra,
        "so_dem": len(nightly),
        "gia_co_ban": float(base_rate),
        "tien_phong_du_kien": float(room_total),
        "tien_phu_phi_mua_cao_diem": float(surcharge_total),
        "tong_tien_phong_va_phu_phi": float(total_before_services),
        "ap_dung_mua_cao_diem": has_peak,
        "he_so_mua_cao_diem": peak_rates,
        "chi_tiet_mua_cao_diem": nightly,
    }


def _decode_json_field(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value
    return value


def _calculate_peak_season_surcharge(snapshot, applied) -> Decimal:
    """Calculate the additive fee from the immutable snapshot (legacy-safe)."""
    if not applied:
        return Decimal("0.00")
    nights = _decode_json_field(snapshot)
    if not isinstance(nights, list):
        return Decimal("0.00")

    surcharge = Decimal("0.00")
    for night in nights:
        if not isinstance(night, dict):
            continue
        try:
            base_rate = Decimal(str(night.get("gia_co_ban") or 0))
            explicit_fee = night.get("phi_mua_cao_diem")
            if explicit_fee is not None:
                nightly_fee = Decimal(str(explicit_fee))
            else:
                factor = Decimal(str(night.get("he_so_gia") or 0))
                if factor > Decimal("1.00"):
                    old_applied = Decimal(str(night.get("tien_dem") or (base_rate * factor)))
                    nightly_fee = max(old_applied - base_rate, Decimal("0.00"))
                elif night.get("mua_cao_diem_id") is not None:
                    nightly_fee = base_rate * factor
                else:
                    nightly_fee = Decimal("0.00")
            surcharge += nightly_fee
        except Exception:
            continue
    return surcharge.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _read_procedure_rows(cursor):
    rows = []
    for result_cursor in cursor.stored_results():
        try:
            rows.extend(result_cursor.fetchall())
        finally:
            result_cursor.close()
    return rows


def _assert_booking_owner(cursor, booking_id: int, khach_id: int):
    cursor.execute(
        "SELECT id, trang_thai FROM booking WHERE id = %s AND khach_id = %s",
        (booking_id, khach_id),
    )
    booking = cursor.fetchone()
    if booking is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy Booking của tài khoản này.")
    return booking


@router.get("/me")
def customer_profile(current_user=Depends(require_customer)):
    return {"success": True, "user": current_user}


@router.get("/room-types")
def customer_room_types(
    current_user=Depends(require_customer),
    db=Depends(get_db),
):
    """Return room types, room counts and aggregated default services for Customer cards.

    Default services are rows in dichvu with phong_id set and booking_id IS NULL.
    The summary is grouped by room type, service name and unit price. The exact
    service list for an individual room is still loaded by /rooms/{room_id}/services.
    """
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT lp.id, lp.ten, lp.gia_co_ban, lp.suc_chua,
                      COUNT(DISTINCT p.id) AS so_phong
               FROM loaiphong AS lp
               LEFT JOIN phong AS p ON p.loai_phong_id = lp.id
               GROUP BY lp.id, lp.ten, lp.gia_co_ban, lp.suc_chua
               ORDER BY lp.id"""
        )
        room_types = cursor.fetchall()

        cursor.execute(
            """SELECT p.loai_phong_id,
                      d.ten,
                      d.don_gia,
                      COUNT(DISTINCT p.id) AS so_phong_ap_dung,
                      MIN(d.so_luong) AS so_luong_min,
                      MAX(d.so_luong) AS so_luong_max,
                      d.don_vi_tinh,
                      d.nhom_dich_vu
               FROM phong AS p
               INNER JOIN dichvu AS d ON d.phong_id = p.id
               WHERE d.booking_id IS NULL
                 AND d.loai_dichvu = 'MAC_DINH'
              AND d.dang_hoat_dong = 1
               GROUP BY p.loai_phong_id, d.ten, d.don_gia, d.don_vi_tinh, d.nhom_dich_vu
               ORDER BY p.loai_phong_id, d.ten, d.don_gia"""
        )
        service_rows = cursor.fetchall()

        services_by_type = {}
        for service in service_rows:
            type_id = int(service["loai_phong_id"])
            services_by_type.setdefault(type_id, []).append({
                "ten": service["ten"],
                "don_gia": service["don_gia"],
                "so_phong_ap_dung": int(service["so_phong_ap_dung"] or 0),
                "so_luong_min": int(service["so_luong_min"] or 0),
                "so_luong_max": int(service["so_luong_max"] or 0),
                "don_vi_tinh": service.get("don_vi_tinh") or "phần",
                "nhom_dich_vu": service.get("nhom_dich_vu") or "DO_DUNG",
            })

        for room_type in room_types:
            room_type["id"] = int(room_type["id"])
            room_type["so_phong"] = int(room_type["so_phong"] or 0)
            default_services = services_by_type.get(room_type["id"], [])
            # Giữ hai tên khóa để tương thích với cả giao diện HTML5 hiện tại
            # và các client cũ đang đọc default_services.
            room_type["dich_vu_mac_dinh"] = default_services
            room_type["default_services"] = default_services
            for service in default_services:
                service["so_phong_co_dich_vu"] = service["so_phong_ap_dung"]

        return room_types
    except Error as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Không tải được danh sách loại phòng: {exc}",
        ) from exc
    finally:
        cursor.close()


@router.get("/available-rooms")
def available_rooms(
    ngay_nhan: date = Query(...),
    ngay_tra: date = Query(...),
    loai_phong_id: int | None = Query(default=None, gt=0),
    current_user=Depends(require_customer),
    db=Depends(get_db),
):
    if ngay_tra <= ngay_nhan:
        raise HTTPException(status_code=422, detail="Ngày trả phải sau ngày nhận.")

    cursor = db.cursor(dictionary=True)
    try:
        room_ids_of_type = None
        room_type_name = None
        if loai_phong_id is not None:
            cursor.execute(
                "SELECT id, ten FROM loaiphong WHERE id = %s",
                (loai_phong_id,),
            )
            room_type = cursor.fetchone()
            if room_type is None:
                raise HTTPException(status_code=404, detail="Loại phòng không tồn tại.")
            room_type_name = room_type["ten"]

            # Filter on the actual FK value, not the display name returned by a procedure.
            cursor.execute(
                "SELECT id FROM phong WHERE loai_phong_id = %s",
                (loai_phong_id,),
            )
            room_ids_of_type = {int(row["id"]) for row in cursor.fetchall()}

        # Preserve the existing Stored Procedure as the source of availability rules.
        cursor.callproc("sp_kiem_tra_phong_trong", [ngay_nhan, ngay_tra])
        rooms = []
        for result_cursor in cursor.stored_results():
            try:
                rooms.extend(result_cursor.fetchall())
            finally:
                result_cursor.close()

        if room_ids_of_type is not None:
            rooms = [
                room for room in rooms
                if int(room.get("phong_id", room.get("id"))) in room_ids_of_type
            ]

        for room in rooms:
            room_id = int(room.get("phong_id", room.get("id")))
            preview = _room_price_preview(cursor, room_id, ngay_nhan, ngay_tra)
            room.update({
                "tien_phong_du_kien": preview["tien_phong_du_kien"],
                "tien_phu_phi_mua_cao_diem": preview["tien_phu_phi_mua_cao_diem"],
                "tong_tien_phong_va_phu_phi": preview["tong_tien_phong_va_phu_phi"],
                "ap_dung_mua_cao_diem": preview["ap_dung_mua_cao_diem"],
                "he_so_mua_cao_diem": preview["he_so_mua_cao_diem"],
                "chi_tiet_mua_cao_diem": preview["chi_tiet_mua_cao_diem"],
            })

        return {
            "ngay_nhan": ngay_nhan,
            "ngay_tra": ngay_tra,
            "loai_phong_id": loai_phong_id,
            "loai_phong": room_type_name,
            "total": len(rooms),
            "rooms": rooms,
        }
    except HTTPException:
        raise
    except Error as exc:
        raise HTTPException(status_code=400, detail=f"Không tìm được phòng: {exc}") from exc
    finally:
        cursor.close()


@router.get("/rooms/{room_id}/price-preview")
def customer_room_price_preview(
    room_id: int,
    ngay_nhan: date = Query(...),
    ngay_tra: date = Query(...),
    current_user=Depends(require_customer),
    db=Depends(get_db),
):
    if ngay_tra <= ngay_nhan:
        raise HTTPException(status_code=422, detail="Ngày trả phải sau ngày nhận.")
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM phong WHERE id=%s AND trang_thai <> 'BAO_TRI'", (room_id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Phòng không tồn tại hoặc đang bảo trì.")
        return _room_price_preview(cursor, room_id, ngay_nhan, ngay_tra)
    except HTTPException:
        raise
    except Error as exc:
        raise HTTPException(status_code=500, detail=f"Không tính được giá phòng: {exc}") from exc
    finally:
        cursor.close()


@router.get("/rooms/{room_id}/services")
def customer_room_services(
    room_id: int,
    current_user=Depends(require_customer),
    db=Depends(get_db),
):
    """Expose active free defaults for the room and active global paid add-ons to the signed-in customer."""
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, so_phong FROM phong WHERE id = %s AND trang_thai <> 'BAO_TRI'",
            (room_id,),
        )
        room = cursor.fetchone()
        if room is None:
            raise HTTPException(status_code=404, detail="Phòng không tồn tại hoặc đang bảo trì.")
        cursor.execute(
            """
            SELECT id AS dichvu_id, ten, don_gia, so_luong, loai_dichvu,
                   nhom_dich_vu, don_vi_tinh
            FROM dichvu
            WHERE phong_id = %s AND booking_id IS NULL
              AND loai_dichvu = 'MAC_DINH' AND dang_hoat_dong = 1
            ORDER BY ten, id
            """,
            (room_id,),
        )
        default_services = cursor.fetchall()
        cursor.execute(
            """
            SELECT id AS dichvu_id, ten, don_gia, so_luong, loai_dichvu,
                   nhom_dich_vu, don_vi_tinh
            FROM dichvu
            WHERE phong_id IS NULL AND booking_id IS NULL
              AND loai_dichvu = 'TUY_CHON' AND dang_hoat_dong = 1
            ORDER BY nhom_dich_vu, ten, id
            """
        )
        addon_services = cursor.fetchall()
        return {
            "phong": room,
            "total": len(default_services) + len(addon_services),
            "services": default_services,
            "default_services": default_services,
            "addon_services": addon_services,
        }
    except HTTPException:
        raise
    except Error as exc:
        raise HTTPException(status_code=500, detail=f"Không tải được dịch vụ phòng: {exc}") from exc
    finally:
        cursor.close()


@router.post("/bookings", status_code=201)
def create_customer_booking(
    data: CustomerBookingCreate,
    current_user=Depends(require_customer),
    db=Depends(get_db),
):
    if data.ngay_tra <= data.ngay_nhan:
        raise HTTPException(status_code=422, detail="Ngày trả phải sau ngày nhận.")
    cursor = db.cursor(dictionary=True)
    try:
        # Customer ID is taken from the authenticated token, never from request JSON.
        # The stored procedure atomically creates the Booking and stores only the
        # selected room defaults plus explicitly selected paid add-ons.
        selected_services = [
            {"dichvu_id": item.dichvu_id, "so_luong": item.so_luong}
            for item in data.dich_vu
        ]
        cursor.callproc(
            "sp_tao_booking_customer",
            [
                data.phong_id,
                current_user["khach_id"],
                data.ngay_nhan,
                data.ngay_tra,
                json.dumps(selected_services, ensure_ascii=False),
            ],
        )
        rows = _read_procedure_rows(cursor)
        result = rows[0] if rows else {}
        booking_id = result.get("booking_id") if isinstance(result, dict) else None
        if not booking_id:
            raise HTTPException(status_code=500, detail="Đã tạo Booking nhưng không đọc được mã Booking.")

        cursor.execute(
            """
            SELECT id AS dichvu_id, ten, don_gia, so_luong, loai_dichvu,
                   nhom_dich_vu, don_vi_tinh,
                   don_gia * so_luong AS thanh_tien
            FROM dichvu
            WHERE booking_id = %s
            ORDER BY id
            """,
            (booking_id,),
        )
        chosen = cursor.fetchall()
        cursor.execute(
            """SELECT tien_phong_du_kien, tien_phu_phi_mua_cao_diem,
                      ap_dung_mua_cao_diem, chi_tiet_mua_cao_diem
               FROM booking WHERE id=%s""", (booking_id,)
        )
        season_snapshot = cursor.fetchone() or {}
        season_snapshot["chi_tiet_mua_cao_diem"] = _decode_json_field(season_snapshot.get("chi_tiet_mua_cao_diem"))
        return {
            "success": True,
            "message": "Đặt phòng thành công. Giá mùa cao điểm đã được chốt theo ngày đặt.",
            "booking_id": booking_id,
            "tien_phong_du_kien": season_snapshot.get("tien_phong_du_kien"),
            "tien_phu_phi_mua_cao_diem": season_snapshot.get("tien_phu_phi_mua_cao_diem"),
            "tong_tien_phong_va_phu_phi": float(Decimal(str(season_snapshot.get("tien_phong_du_kien") or 0)) + Decimal(str(season_snapshot.get("tien_phu_phi_mua_cao_diem") or 0))),
            "ap_dung_mua_cao_diem": bool(season_snapshot.get("ap_dung_mua_cao_diem")),
            "chi_tiet_mua_cao_diem": season_snapshot.get("chi_tiet_mua_cao_diem"),
            "dich_vu": chosen,
            "tong_tien_dich_vu": sum(
                (item["don_gia"] * item["so_luong"] for item in chosen), 0
            ),
        }
    except HTTPException:
        raise
    except Error as exc:
        raise HTTPException(status_code=409, detail=f"Không thể đặt phòng: {exc}") from exc
    finally:
        cursor.close()


@router.get("/bookings")
def my_bookings(current_user=Depends(require_customer), db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT b.id AS booking_id, b.phong_id, p.so_phong, lp.ten AS loai_phong,
                      b.ngay_nhan, b.ngay_tra, CAST(julianday(b.ngay_tra)-julianday(b.ngay_nhan) AS INTEGER) AS so_dem,
                      b.trang_thai, b.tien_phong_du_kien, b.tien_phu_phi_mua_cao_diem,
                      b.ap_dung_mua_cao_diem, b.chi_tiet_mua_cao_diem,
                      (SELECT COUNT(*) FROM dichvu d WHERE d.booking_id=b.id) AS so_dich_vu,
                      (SELECT COALESCE(SUM(py.so_tien),0) FROM pay py WHERE py.booking_id=b.id AND py.status='THANH_CONG') AS da_thanh_toan
               FROM booking b
               JOIN phong p ON p.id=b.phong_id
               JOIN loaiphong lp ON lp.id=p.loai_phong_id
               WHERE b.khach_id=%s
               ORDER BY b.id DESC""",
            (current_user["khach_id"],),
        )
        rows = cursor.fetchall()
        for row in rows:
            row["chi_tiet_mua_cao_diem"] = _decode_json_field(row.get("chi_tiet_mua_cao_diem"))
        return {"total": len(rows), "bookings": rows}
    except Error as exc:
        raise HTTPException(status_code=500, detail=f"Không tải được lịch sử Booking: {exc}") from exc
    finally:
        cursor.close()


@router.get("/bookings/{booking_id}")
def my_booking_detail(booking_id: int, current_user=Depends(require_customer), db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    try:
        booking = _assert_booking_owner(cursor, booking_id, current_user["khach_id"])
        cursor.execute(
            """SELECT b.id AS booking_id, b.trang_thai, b.ngay_nhan, b.ngay_tra,
                      p.id AS phong_id, p.so_phong, lp.ten AS loai_phong,
                      lp.gia_co_ban, CAST(julianday(b.ngay_tra)-julianday(b.ngay_nhan) AS INTEGER) AS so_dem,
                      b.tien_phong_du_kien, b.tien_phu_phi_mua_cao_diem,
                      b.ap_dung_mua_cao_diem, b.chi_tiet_mua_cao_diem
               FROM booking b JOIN phong p ON p.id=b.phong_id
               JOIN loaiphong lp ON lp.id=p.loai_phong_id
               WHERE b.id=%s AND b.khach_id=%s""",
            (booking_id, current_user["khach_id"]),
        )
        detail = cursor.fetchone()
        detail["chi_tiet_mua_cao_diem"] = _decode_json_field(detail.get("chi_tiet_mua_cao_diem"))
        cursor.execute(
            "SELECT id AS dichvu_id, ten, don_gia, so_luong, loai_dichvu, nhom_dich_vu, don_vi_tinh, don_gia*so_luong AS thanh_tien FROM dichvu WHERE booking_id=%s ORDER BY id",
            (booking_id,),
        )
        detail["dich_vu"] = cursor.fetchall()
        cursor.execute(
            """SELECT py.id AS pay_id, py.so_tien, py.method, py.status,
                      py.tien_phong_ap_dung, py.tien_phu_phi_mua_cao_diem,
                      py.ap_dung_mua_cao_diem, py.chi_tiet_mua_cao_diem,
                      py.ngay_thanh_toan, h.id AS hoa_don_id, h.tien_phu_phi_mua_cao_diem AS hoa_don_phu_phi,
                      h.tong_tien, h.ngay_lap
               FROM pay py LEFT JOIN hoadon h ON h.pay_id=py.id
               WHERE py.booking_id=%s ORDER BY py.id DESC""",
            (booking_id,),
        )
        detail["thanh_toan"] = cursor.fetchall()
        for payment in detail["thanh_toan"]:
            payment["chi_tiet_mua_cao_diem"] = _decode_json_field(payment.get("chi_tiet_mua_cao_diem"))
        return detail
    except HTTPException:
        raise
    except Error as exc:
        raise HTTPException(status_code=500, detail=f"Không tải được chi tiết Booking: {exc}") from exc
    finally:
        cursor.close()


@router.post("/bookings/{booking_id}/cancel")
def cancel_my_booking(booking_id: int, current_user=Depends(require_customer), db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    try:
        _assert_booking_owner(cursor, booking_id, current_user["khach_id"])
        cursor.callproc("sp_huy_booking", [booking_id])
        rows = _read_procedure_rows(cursor)
        row = rows[0] if rows else {}
        return {"success": True, "message": "Đã gửi yêu cầu hủy Booking.", "result": row}
    except HTTPException:
        raise
    except Error as exc:
        raise HTTPException(status_code=409, detail=f"Không thể hủy Booking: {exc}") from exc
    finally:
        cursor.close()


@router.get("/invoices")
def my_invoices(current_user=Depends(require_customer), db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT h.id AS hoa_don_id, h.pay_id, h.tien_phong, h.tien_phu_phi_mua_cao_diem,
                      h.tien_dich_vu, h.tong_tien, h.ngay_lap, py.booking_id, py.so_tien,
                      py.tien_phong_ap_dung, py.ap_dung_mua_cao_diem,
                      py.chi_tiet_mua_cao_diem,
                      py.method, py.status AS trang_thai_thanh_toan, py.ngay_thanh_toan,
                      p.so_phong, b.ngay_nhan, b.ngay_tra
               FROM hoadon h JOIN pay py ON py.id=h.pay_id
               JOIN booking b ON b.id=py.booking_id JOIN phong p ON p.id=b.phong_id
               WHERE b.khach_id=%s ORDER BY h.id DESC""",
            (current_user["khach_id"],),
        )
        rows = cursor.fetchall()
        for row in rows:
            row["chi_tiet_mua_cao_diem"] = _decode_json_field(row.get("chi_tiet_mua_cao_diem"))
        return {"total": len(rows), "invoices": rows}
    except Error as exc:
        raise HTTPException(status_code=500, detail=f"Không tải được hóa đơn: {exc}") from exc
    finally:
        cursor.close()


@router.post("/bookings/{booking_id}/payment", status_code=201)
def request_booking_payment(
    booking_id: int,
    data: CustomerPaymentRequest,
    current_user=Depends(require_customer),
    db=Depends(get_db),
):
    if data.method not in PAYMENT_METHODS:
        raise HTTPException(status_code=422, detail=f"Phương thức hợp lệ: {sorted(PAYMENT_METHODS)}")
    if data.method == "CHUYEN_KHOAN":
        try:
            get_qr_config()
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    cursor = db.cursor(dictionary=True)
    try:
        booking = _assert_booking_owner(cursor, booking_id, current_user["khach_id"])
        if booking["trang_thai"] not in ("DA_XAC_NHAN", "DANG_O", "HOAN_THANH"):
            raise HTTPException(status_code=409, detail="Booking cần được khách sạn xác nhận trước khi yêu cầu thanh toán.")
        # Nếu đã có hóa đơn cho lần thanh toán đang chờ/thành công, không tạo trùng.
        cursor.execute(
            """SELECT h.id AS hoa_don_id, py.id AS pay_id, py.status, py.method,
                      h.tien_phong, h.tien_phu_phi_mua_cao_diem, h.tien_dich_vu, h.tong_tien, h.ngay_lap,
                      py.tien_phong_ap_dung, py.tien_phu_phi_mua_cao_diem, py.ap_dung_mua_cao_diem,
                      py.chi_tiet_mua_cao_diem
               FROM pay py LEFT JOIN hoadon h ON h.pay_id=py.id
               WHERE py.booking_id=%s AND py.status IN ('CHO_THANH_TOAN','THANH_CONG')
               ORDER BY py.id DESC LIMIT 1""",
            (booking_id,),
        )
        existing = cursor.fetchone()
        if existing:
            if existing.get("hoa_don_id"):
                if existing.get("method") != data.method:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            f"Booking đã có giao dịch bằng phương thức {existing.get('method')}. "
                            "Không thể đổi phương thức khi giao dịch đang chờ hoặc đã thanh toán."
                        ),
                    )
                return {
                    "success": True,
                    "message": "Booking đã có hóa đơn cho giao dịch hiện tại.",
                    "invoice": existing,
                    "qr_available": data.method == "CHUYEN_KHOAN",
                }
            raise HTTPException(status_code=409, detail="Giao dịch đang tồn tại nhưng chưa có hóa đơn. Vui lòng liên hệ lễ tân.")

        # Procedure tự quản lý transaction; không bao bởi transaction khác.
        cursor.callproc("sp_tinh_tien_va_tao_hoa_don", [booking_id, data.method])
        rows = _read_procedure_rows(cursor)
        procedure_result = rows[0] if rows else {}
        pay_id = procedure_result.get("pay_id") if isinstance(procedure_result, dict) else None
        if not pay_id:
            cursor.execute("SELECT id FROM pay WHERE booking_id=%s ORDER BY id DESC LIMIT 1", (booking_id,))
            row = cursor.fetchone()
            pay_id = row["id"] if row else None
        if not pay_id:
            raise HTTPException(status_code=500, detail="Không lấy được mã giao dịch vừa tạo.")
        cursor.execute(
            """SELECT h.id AS hoa_don_id, h.pay_id, h.tien_phong, h.tien_phu_phi_mua_cao_diem,
                      h.tien_dich_vu, h.tong_tien, h.ngay_lap, py.status, py.method,
                      py.tien_phong_ap_dung, py.tien_phu_phi_mua_cao_diem,
                      py.ap_dung_mua_cao_diem, py.chi_tiet_mua_cao_diem
               FROM hoadon h JOIN pay py ON py.id=h.pay_id WHERE py.id=%s""",
            (pay_id,),
        )
        invoice = cursor.fetchone()
        if invoice is None:
            raise HTTPException(status_code=500, detail="Giao dịch được tạo nhưng chưa tìm thấy hóa đơn.")
        return {
            "success": True,
            "message": (
                "Đã tạo giao dịch và hóa đơn. Hãy quét QR, chuyển đúng số tiền và giữ nguyên nội dung chuyển khoản."
                if data.method == "CHUYEN_KHOAN"
                else "Đã tạo yêu cầu thanh toán. Giao dịch đang chờ khách sạn xác nhận."
            ),
            "invoice": invoice,
            "qr_available": data.method == "CHUYEN_KHOAN",
        }
    except HTTPException:
        raise
    except Error as exc:
        raise HTTPException(status_code=409, detail=f"Không thể tạo yêu cầu thanh toán: {exc}") from exc
    finally:
        cursor.close()


@router.get("/payments/{pay_id}/qr")
def get_customer_payment_qr(
    pay_id: int,
    current_user=Depends(require_customer),
    db=Depends(get_db),
):
    """Create or retrieve the unique VietQR instructions for the signed-in customer's Pay."""
    try:
        config = get_qr_config()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT py.id, py.booking_id, py.so_tien, py.method, py.status,
                      py.ap_dung_mua_cao_diem, py.chi_tiet_mua_cao_diem,
                      py.tien_phong_ap_dung, py.tien_phu_phi_mua_cao_diem,
                      h.tong_tien, b.trang_thai AS booking_status
               FROM pay py
               JOIN booking b ON b.id=py.booking_id
               LEFT JOIN hoadon h ON h.pay_id=py.id
               WHERE py.id=%s AND py.khach_id=%s""",
            (pay_id, current_user["khach_id"]),
        )
        payment = cursor.fetchone()
        if payment is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch của tài khoản này.")
        if payment["method"] != "CHUYEN_KHOAN":
            raise HTTPException(status_code=409, detail="Giao dịch này không sử dụng phương thức chuyển khoản QR.")
        if payment["status"] not in ("CHO_THANH_TOAN", "THANH_CONG"):
            raise HTTPException(status_code=409, detail=f"Giao dịch đang ở trạng thái {payment['status']}, không thể tạo QR.")
        if payment["booking_status"] == "DA_HUY":
            raise HTTPException(status_code=409, detail="Booking đã hủy, không thể thanh toán.")
        if payment["tong_tien"] is None:
            raise HTTPException(status_code=409, detail="Giao dịch chưa có hóa đơn.")
        amount = Decimal(str(payment["so_tien"])).quantize(Decimal("0.01"))
        invoice_amount = Decimal(str(payment["tong_tien"])).quantize(Decimal("0.01"))
        peak_season_applied = bool(payment.get("ap_dung_mua_cao_diem"))
        snapshot_fee = _calculate_peak_season_surcharge(
            payment.get("chi_tiet_mua_cao_diem"), peak_season_applied
        )
        peak_season_amount = Decimal(str(
            payment.get("tien_phu_phi_mua_cao_diem")
            if payment.get("tien_phu_phi_mua_cao_diem") is not None
            else snapshot_fee
        )).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if amount != invoice_amount:
            raise HTTPException(status_code=409, detail="Số tiền Pay không khớp hóa đơn; không thể tạo QR.")
        if amount <= 0:
            raise HTTPException(status_code=422, detail="Số tiền cần thanh toán phải lớn hơn 0 để tạo QR.")
        if amount != amount.to_integral_value():
            raise HTTPException(status_code=422, detail="Số tiền phải là số nguyên VNĐ để tạo QR chuyển khoản.")

        cursor.execute("SELECT payment_code FROM payment_qr WHERE pay_id=%s FOR UPDATE", (pay_id,))
        qr_record = cursor.fetchone()
        if qr_record is None and payment["status"] == "CHO_THANH_TOAN":
            payment_code = payment_code_for(pay_id)
            cursor.execute(
                "INSERT INTO payment_qr (pay_id, payment_code) VALUES (%s, %s)",
                (pay_id, payment_code),
            )
            db.commit()
        elif qr_record:
            payment_code = qr_record["payment_code"]
        else:
            payment_code = None
        db.commit()

        if not payment_code:
            return {
                "success": True, "pay_id": pay_id, "status": payment["status"],
                "already_paid": True, "message": "Giao dịch đã hoàn tất; không cần QR.",
            }

        qr_url = build_vietqr_url(config, int(amount), payment_code)
        return {
            "success": True,
            "pay_id": pay_id,
            "booking_id": payment["booking_id"],
            "status": payment["status"],
            "payment_code": payment_code,
            "amount": int(amount),
            "peak_season_applied": peak_season_applied,
            "peak_season_amount": float(peak_season_amount),
            "room_amount": float(payment.get("tien_phong_ap_dung") or 0),
            "service_amount": float(Decimal(str(payment.get("so_tien") or 0)) - Decimal(str(payment.get("tien_phong_ap_dung") or 0)) - peak_season_amount),
            "peak_season_label": "CÓ" if peak_season_applied else "KHÔNG",
            "bank_code": config["bank_code"],
            "account_number": config["account_number"],
            "account_name": config["account_name"],
            "qr_url": qr_url,
            "message": "Quét QR bằng ứng dụng ngân hàng và giữ nguyên nội dung chuyển khoản.",
        }
    except HTTPException:
        db.rollback()
        raise
    except Error as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Không tạo được thông tin QR: {exc}") from exc
    finally:
        cursor.close()


@router.get("/payments/{pay_id}/status")
def get_customer_payment_status(
    pay_id: int,
    current_user=Depends(require_customer),
    db=Depends(get_db),
):
    """Polling endpoint; it never lets a customer set the payment status."""
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT py.id AS pay_id, py.booking_id, py.so_tien, py.method, py.status,
                      q.payment_code, q.sepay_reference_code, q.received_amount, q.received_at
               FROM pay py
               LEFT JOIN payment_qr q ON q.pay_id=py.id
               WHERE py.id=%s AND py.khach_id=%s""",
            (pay_id, current_user["khach_id"]),
        )
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy giao dịch của tài khoản này.")
        return {"success": True, "payment": row}
    except HTTPException:
        raise
    except Error as exc:
        raise HTTPException(status_code=500, detail=f"Không kiểm tra được trạng thái: {exc}") from exc
    finally:
        cursor.close()
