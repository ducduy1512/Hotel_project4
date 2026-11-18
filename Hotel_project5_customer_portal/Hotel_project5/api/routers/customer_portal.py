"""Customer-only endpoints. All queries are restricted to the signed-in customer."""
from datetime import date
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from mysql.connector import Error
from pydantic import BaseModel, Field

from api.database import get_db
from api.routers.auth import require_customer

router = APIRouter(prefix="/api/customer", tags=["Customer Portal"])
PAYMENT_METHODS = {"TIEN_MAT", "CHUYEN_KHOAN", "THE"}


class CustomerServiceSelection(BaseModel):
    dichvu_id: int = Field(gt=0)
    so_luong: int = Field(gt=0)


class CustomerBookingCreate(BaseModel):
    phong_id: int = Field(gt=0)
    ngay_nhan: date
    ngay_tra: date
    # Danh sách dịch vụ mặc định khách chọn; [] = không lấy dịch vụ nào.
    dich_vu: list[CustomerServiceSelection] = Field(default_factory=list)


class CustomerPaymentRequest(BaseModel):
    method: str


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


@router.get("/available-rooms")
def available_rooms(
    ngay_nhan: date = Query(...),
    ngay_tra: date = Query(...),
    current_user=Depends(require_customer),
    db=Depends(get_db),
):
    if ngay_tra <= ngay_nhan:
        raise HTTPException(status_code=422, detail="Ngày trả phải sau ngày nhận.")
    cursor = db.cursor(dictionary=True)
    try:
        cursor.callproc("sp_kiem_tra_phong_trong", [ngay_nhan, ngay_tra])
        rooms = []
        for result_cursor in cursor.stored_results():
            try:
                rooms.extend(result_cursor.fetchall())
            finally:
                result_cursor.close()
        return {"ngay_nhan": ngay_nhan, "ngay_tra": ngay_tra, "total": len(rooms), "rooms": rooms}
    except Error as exc:
        raise HTTPException(status_code=400, detail=f"Không tìm được phòng: {exc}") from exc
    finally:
        cursor.close()


@router.get("/rooms/{room_id}/services")
def customer_room_services(
    room_id: int,
    current_user=Depends(require_customer),
    db=Depends(get_db),
):
    """Only expose default services for a room to the signed-in customer."""
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
            SELECT id AS dichvu_id, ten, don_gia, so_luong
            FROM dichvu
            WHERE phong_id = %s AND booking_id IS NULL
            ORDER BY ten, id
            """,
            (room_id,),
        )
        services = cursor.fetchall()
        return {"phong": room, "total": len(services), "services": services}
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
        # selected room-default services (including customer-selected quantities).
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
            SELECT id AS dichvu_id, ten, don_gia, so_luong,
                   don_gia * so_luong AS thanh_tien
            FROM dichvu
            WHERE booking_id = %s
            ORDER BY id
            """,
            (booking_id,),
        )
        chosen = cursor.fetchall()
        return {
            "success": True,
            "message": "Đặt phòng thành công. Dịch vụ đã được lưu theo lựa chọn của bạn.",
            "booking_id": booking_id,
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
                      b.ngay_nhan, b.ngay_tra, DATEDIFF(b.ngay_tra,b.ngay_nhan) AS so_dem,
                      b.trang_thai,
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
                      lp.gia_co_ban, DATEDIFF(b.ngay_tra,b.ngay_nhan) AS so_dem
               FROM booking b JOIN phong p ON p.id=b.phong_id
               JOIN loaiphong lp ON lp.id=p.loai_phong_id
               WHERE b.id=%s AND b.khach_id=%s""",
            (booking_id, current_user["khach_id"]),
        )
        detail = cursor.fetchone()
        cursor.execute(
            "SELECT id AS dichvu_id, ten, don_gia, so_luong, don_gia*so_luong AS thanh_tien FROM dichvu WHERE booking_id=%s ORDER BY id",
            (booking_id,),
        )
        detail["dich_vu"] = cursor.fetchall()
        cursor.execute(
            """SELECT py.id AS pay_id, py.so_tien, py.method, py.status,
                      py.ngay_thanh_toan, h.id AS hoa_don_id, h.tong_tien, h.ngay_lap
               FROM pay py LEFT JOIN hoadon h ON h.pay_id=py.id
               WHERE py.booking_id=%s ORDER BY py.id DESC""",
            (booking_id,),
        )
        detail["thanh_toan"] = cursor.fetchall()
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
            """SELECT h.id AS hoa_don_id, h.pay_id, h.tien_phong, h.tien_dich_vu,
                      h.tong_tien, h.ngay_lap, py.booking_id, py.so_tien,
                      py.method, py.status AS trang_thai_thanh_toan, py.ngay_thanh_toan,
                      p.so_phong, b.ngay_nhan, b.ngay_tra
               FROM hoadon h JOIN pay py ON py.id=h.pay_id
               JOIN booking b ON b.id=py.booking_id JOIN phong p ON p.id=b.phong_id
               WHERE b.khach_id=%s ORDER BY h.id DESC""",
            (current_user["khach_id"],),
        )
        rows = cursor.fetchall()
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
    cursor = db.cursor(dictionary=True)
    try:
        booking = _assert_booking_owner(cursor, booking_id, current_user["khach_id"])
        if booking["trang_thai"] not in ("DA_XAC_NHAN", "DANG_O", "HOAN_THANH"):
            raise HTTPException(status_code=409, detail="Booking cần được khách sạn xác nhận trước khi yêu cầu thanh toán.")
        # Nếu đã có hóa đơn cho lần thanh toán đang chờ/thành công, không tạo trùng.
        cursor.execute(
            """SELECT h.id AS hoa_don_id, py.id AS pay_id, py.status, py.method,
                      h.tien_phong, h.tien_dich_vu, h.tong_tien, h.ngay_lap
               FROM pay py LEFT JOIN hoadon h ON h.pay_id=py.id
               WHERE py.booking_id=%s AND py.status IN ('CHO_THANH_TOAN','THANH_CONG')
               ORDER BY py.id DESC LIMIT 1""",
            (booking_id,),
        )
        existing = cursor.fetchone()
        if existing:
            if existing.get("hoa_don_id"):
                return {"success": True, "message": "Booking đã có hóa đơn cho giao dịch hiện tại.", "invoice": existing}
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
            """SELECT h.id AS hoa_don_id, h.pay_id, h.tien_phong, h.tien_dich_vu,
                      h.tong_tien, h.ngay_lap, py.status, py.method
               FROM hoadon h JOIN pay py ON py.id=h.pay_id WHERE py.id=%s""",
            (pay_id,),
        )
        invoice = cursor.fetchone()
        if invoice is None:
            raise HTTPException(status_code=500, detail="Giao dịch được tạo nhưng chưa tìm thấy hóa đơn.")
        return {"success": True, "message": "Đã tạo yêu cầu thanh toán. Giao dịch đang chờ khách sạn xác nhận.", "invoice": invoice}
    except HTTPException:
        raise
    except Error as exc:
        raise HTTPException(status_code=409, detail=f"Không thể tạo yêu cầu thanh toán: {exc}") from exc
    finally:
        cursor.close()
