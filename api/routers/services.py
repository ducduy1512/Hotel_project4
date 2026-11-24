"""Quản lý dịch vụ mặc định, danh mục dịch vụ tính phí và dịch vụ Booking.

Giữ một bảng dichvu theo ERD 8 bảng:
- MAC_DINH + phong_id: dịch vụ miễn phí gắn với một phòng.
- TUY_CHON + phong_id NULL + booking_id NULL: danh mục bổ sung toàn cục.
- booking_id NOT NULL: snapshot dịch vụ đã được khách chọn cho Booking.
"""
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, HTTPException
from database import Error

from database import get_connection
from api.schemas import ServiceCreate, ServiceUpdate

router = APIRouter(prefix="/api/services", tags=["Services"])


def close_db(cursor, conn):
    try:
        if cursor is not None:
            cursor.close()
    finally:
        if conn is not None and conn.is_connected():
            conn.close()


def _validate_service_values(ten, don_gia, so_luong, nhom_dich_vu, don_vi_tinh):
    name = (ten or "").strip()
    group = (nhom_dich_vu or "").strip().upper()
    unit = (don_vi_tinh or "").strip()
    if not name or len(name) > 100:
        raise HTTPException(status_code=422, detail="Tên dịch vụ phải có từ 1 đến 100 ký tự.")
    if not group or len(group) > 50:
        raise HTTPException(status_code=422, detail="Nhóm dịch vụ không hợp lệ.")
    if not unit or len(unit) > 40:
        raise HTTPException(status_code=422, detail="Đơn vị tính phải có từ 1 đến 40 ký tự.")
    try:
        price = Decimal(str(don_gia))
    except (InvalidOperation, TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Đơn giá dịch vụ không hợp lệ.")
    if not price.is_finite() or price < 0 or price.as_tuple().exponent < -2:
        raise HTTPException(status_code=422, detail="Đơn giá phải không âm và tối đa 2 chữ số thập phân.")
    if so_luong is None or int(so_luong) <= 0:
        raise HTTPException(status_code=422, detail="Số lượng phải lớn hơn 0.")
    return name, price, int(so_luong), group, unit


def _raise_database_error(exc: Error):
    sqlstate = getattr(exc, "sqlstate", None)
    errno = getattr(exc, "errno", None)
    detail = getattr(exc, "msg", None) or str(exc)
    if sqlstate in {"45000", "23000"} or errno in {1062, 1451, 1452, 1644, 3819}:
        raise HTTPException(status_code=409, detail=detail) from exc
    raise HTTPException(status_code=500, detail="Lỗi cơ sở dữ liệu khi xử lý dịch vụ.") from exc


@router.get("/")
def get_services():
    """Liệt kê danh mục chung, dịch vụ phòng và dịch vụ đã gắn Booking."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT d.id, d.ten, d.don_gia, d.so_luong, d.phong_id, d.booking_id,
                   d.loai_dichvu, d.nhom_dich_vu, d.don_vi_tinh, d.dang_hoat_dong,
                   p.so_phong, b.trang_thai AS trang_thai_booking,
                   b.ngay_nhan, b.ngay_tra,
                   CASE
                     WHEN d.booking_id IS NOT NULL THEN 'BOOKING'
                     WHEN d.phong_id IS NOT NULL THEN 'PHONG'
                     ELSE 'DANH_MUC_CHUNG'
                   END AS pham_vi
            FROM dichvu d
            LEFT JOIN phong p ON p.id = d.phong_id
            LEFT JOIN booking b ON b.id = d.booking_id
            WHERE d.booking_id IS NULL
            ORDER BY d.loai_dichvu, d.nhom_dich_vu, d.ten, d.id DESC
        """)
        return cursor.fetchall()
    except Error as exc:
        _raise_database_error(exc)
    finally:
        close_db(cursor, conn)


@router.get("/rooms/{room_id}/options")
def get_room_service_options(room_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, so_phong, loai_phong_id FROM phong WHERE id=%s", (room_id,))
        room = cursor.fetchone()
        if room is None:
            raise HTTPException(status_code=404, detail="Phòng không tồn tại.")
        cursor.execute("""
            SELECT id AS dichvu_id, ten, don_gia, so_luong, loai_dichvu,
                   nhom_dich_vu, don_vi_tinh
            FROM dichvu
            WHERE phong_id=%s AND booking_id IS NULL AND loai_dichvu='MAC_DINH' AND dang_hoat_dong=1
            ORDER BY ten, id
        """, (room_id,))
        services = cursor.fetchall()
        return {"message": "Lấy dịch vụ mặc định của phòng thành công.", "phong": room,
                "total": len(services), "data": services}
    except HTTPException:
        raise
    except Error as exc:
        _raise_database_error(exc)
    finally:
        close_db(cursor, conn)


@router.post("/", status_code=201)
def create_service(service: ServiceCreate):
    name, price, quantity, group, unit = _validate_service_values(
        service.ten, service.don_gia, service.so_luong,
        service.nhom_dich_vu, service.don_vi_tinh,
    )
    kind = service.loai_dichvu
    if service.booking_id is not None:
        if price <= 0:
            raise HTTPException(status_code=422, detail="Dịch vụ bổ sung trong Booking phải có đơn giá lớn hơn 0.")
        if service.phong_id is not None:
            raise HTTPException(status_code=422, detail="Không cần gửi phòng_id khi thêm dịch vụ vào Booking.")
    elif kind == "TUY_CHON":
        if service.phong_id is not None or price <= 0:
            raise HTTPException(status_code=422, detail="Danh mục tính phí phải có phòng_id và booking_id để trống, đơn giá lớn hơn 0.")
    else:
        if service.phong_id is None or price != 0:
            raise HTTPException(status_code=422, detail="Dịch vụ mặc định phải gắn với phòng và có đơn giá bằng 0.")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        if service.booking_id is not None:
            cursor.execute("""
                INSERT INTO dichvu
                    (ten, don_gia, so_luong, phong_id, booking_id, loai_dichvu,
                     nhom_dich_vu, don_vi_tinh, dang_hoat_dong)
                SELECT %s, %s, %s, b.phong_id, b.id, 'TUY_CHON', %s, %s, 1
                FROM booking b WHERE b.id=%s
            """, (name, price, quantity, group, unit, service.booking_id))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Booking không tồn tại.")
            service_id = cursor.lastrowid
            conn.commit()
            return {"message": "Thêm dịch vụ vào Booking thành công.", "id": service_id,
                    "booking_id": service.booking_id}

        if kind == "MAC_DINH":
            cursor.execute("SELECT id FROM phong WHERE id=%s FOR UPDATE", (service.phong_id,))
            if cursor.fetchone() is None:
                raise HTTPException(status_code=404, detail="Phòng không tồn tại.")

        cursor.execute("""
            INSERT INTO dichvu
                (ten, don_gia, so_luong, phong_id, booking_id, loai_dichvu,
                 nhom_dich_vu, don_vi_tinh, dang_hoat_dong)
            VALUES (%s, %s, %s, %s, NULL, %s, %s, %s, %s)
        """, (name, price, quantity, service.phong_id, kind, group, unit, int(service.dang_hoat_dong)))
        service_id = cursor.lastrowid
        conn.commit()
        return {"message": "Đã thêm dịch vụ vào danh mục.", "id": service_id,
                "loai_dichvu": kind, "phong_id": service.phong_id}
    except HTTPException:
        conn.rollback()
        raise
    except Error as exc:
        conn.rollback()
        _raise_database_error(exc)
    finally:
        close_db(cursor, conn)


@router.put("/{service_id}")
def update_service(service_id: int, service: ServiceUpdate):
    name, price, quantity, group, unit = _validate_service_values(
        service.ten, service.don_gia, service.so_luong,
        service.nhom_dich_vu, service.don_vi_tinh,
    )
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM dichvu WHERE id=%s FOR UPDATE", (service_id,))
        current = cursor.fetchone()
        if current is None:
            raise HTTPException(status_code=404, detail="Dịch vụ không tồn tại.")
        old_booking_id, old_room_id = current["booking_id"], current["phong_id"]
        if old_booking_id is not None:
            if service.booking_id != old_booking_id or service.phong_id not in (None, old_room_id):
                raise HTTPException(status_code=409, detail="Không được chuyển/tách dịch vụ đã gắn Booking.")
            if ((service.loai_dichvu == "TUY_CHON" and price <= 0)
                    or (service.loai_dichvu == "MAC_DINH" and price != 0)):
                raise HTTPException(status_code=422, detail="Giá dịch vụ trong Booking không khớp loại dịch vụ.")
        elif old_room_id is not None:
            if service.booking_id is not None or service.phong_id not in (None, old_room_id):
                raise HTTPException(status_code=409, detail="Không được chuyển dịch vụ mặc định sang đối tượng khác.")
            if service.loai_dichvu != "MAC_DINH" or price != 0:
                raise HTTPException(status_code=422, detail="Dịch vụ mặc định phải giữ loại MAC_DINH và giá 0.")
        else:
            if service.booking_id is not None or service.phong_id is not None or service.loai_dichvu != "TUY_CHON" or price <= 0:
                raise HTTPException(status_code=422, detail="Danh mục chung phải là TUY_CHON, không gắn phòng/Booking và giá lớn hơn 0.")

        cursor.execute("""
            UPDATE dichvu
            SET ten=%s, don_gia=%s, so_luong=%s, loai_dichvu=%s,
                nhom_dich_vu=%s, don_vi_tinh=%s, dang_hoat_dong=%s
            WHERE id=%s
        """, (name, price, quantity, service.loai_dichvu, group, unit,
              int(service.dang_hoat_dong), service_id))
        conn.commit()
        return {"message": "Cập nhật dịch vụ thành công.", "id": service_id}
    except HTTPException:
        conn.rollback()
        raise
    except Error as exc:
        conn.rollback()
        _raise_database_error(exc)
    finally:
        close_db(cursor, conn)


@router.delete("/{service_id}")
def delete_service(service_id: int):
    """Danh mục dùng chung được ngừng cung cấp (soft delete) để giữ lịch sử giá."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, phong_id, booking_id FROM dichvu WHERE id=%s FOR UPDATE", (service_id,))
        row = cursor.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Dịch vụ không tồn tại.")
        if row["booking_id"] is None and row["phong_id"] is None:
            cursor.execute("UPDATE dichvu SET dang_hoat_dong=0 WHERE id=%s", (service_id,))
            message = "Đã ngừng cung cấp dịch vụ trong danh mục; Booking cũ được giữ nguyên."
        else:
            cursor.execute("DELETE FROM dichvu WHERE id=%s", (service_id,))
            message = "Đã xóa dịch vụ." 
        conn.commit()
        return {"message": message, "id": service_id}
    except HTTPException:
        conn.rollback()
        raise
    except Error as exc:
        conn.rollback()
        _raise_database_error(exc)
    finally:
        close_db(cursor, conn)
