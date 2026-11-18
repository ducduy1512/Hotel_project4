"""Service endpoints mapped to the 8-table HOTEL ERD.

The ERD has one service table only:
- dichvu.booking_id IS NULL: default service attached to a room.
- dichvu.booking_id IS NOT NULL: service used by a Booking.

There is no dichvu_catalog or loaiphong_dichvu table in hotel_management_erd.
"""

from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, HTTPException
from mysql.connector import Error

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


def _validate_service_values(ten: str, don_gia, so_luong: int):
    name = (ten or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="Tên dịch vụ không được để trống.")
    if len(name) > 100:
        raise HTTPException(
            status_code=422,
            detail="Tên dịch vụ tối đa 100 ký tự theo cột dichvu.ten.",
        )

    try:
        price = Decimal(str(don_gia))
    except (InvalidOperation, TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Đơn giá dịch vụ không hợp lệ.")

    if not price.is_finite() or price < 0:
        raise HTTPException(status_code=422, detail="Đơn giá dịch vụ phải lớn hơn hoặc bằng 0.")
    if price.as_tuple().exponent < -2:
        raise HTTPException(status_code=422, detail="Đơn giá chỉ được có tối đa 2 chữ số thập phân.")

    if so_luong is None or int(so_luong) <= 0:
        raise HTTPException(status_code=422, detail="Số lượng dịch vụ phải lớn hơn 0.")

    return name, price, int(so_luong)


def _raise_database_error(exc: Error):
    """Map database constraints/triggers to a client-visible conflict."""
    sqlstate = getattr(exc, "sqlstate", None)
    errno = getattr(exc, "errno", None)
    detail = getattr(exc, "msg", None) or str(exc)

    if sqlstate in {"45000", "23000"} or errno in {1062, 1451, 1452, 1644, 3819}:
        raise HTTPException(status_code=409, detail=detail) from exc
    raise HTTPException(status_code=500, detail="Lỗi cơ sở dữ liệu khi xử lý dịch vụ.") from exc


def _read_procedure_result(cursor):
    """Read all result sets from sp_them_dichvu_booking and return first row."""
    first_row = None
    for result_cursor in cursor.stored_results():
        try:
            rows = result_cursor.fetchall()
            if rows and first_row is None:
                first_row = rows[0]
        finally:
            result_cursor.close()
    return first_row


@router.get("/")
def get_services():
    """List services consumed by Bookings (the scope shown in the Tkinter page)."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                d.id,
                d.ten,
                d.don_gia,
                d.so_luong,
                d.phong_id,
                d.booking_id,
                p.so_phong,
                b.trang_thai AS trang_thai_booking,
                b.ngay_nhan,
                b.ngay_tra
            FROM dichvu d
            JOIN booking b ON b.id = d.booking_id
            JOIN phong p ON p.id = d.phong_id
            ORDER BY d.id DESC
            """
        )
        return cursor.fetchall()
    except Error as exc:
        _raise_database_error(exc)
    finally:
        close_db(cursor, conn)


@router.get("/rooms/{room_id}/options")
def get_room_service_options(room_id: int):
    """Return room-default services stored as dichvu rows with NULL booking_id."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT id, so_phong, loai_phong_id
            FROM phong
            WHERE id = %s
            """,
            (room_id,),
        )
        room = cursor.fetchone()
        if room is None:
            raise HTTPException(status_code=404, detail="Phòng không tồn tại.")

        cursor.execute(
            """
            SELECT
                id AS dichvu_id,
                ten,
                don_gia,
                so_luong
            FROM dichvu
            WHERE phong_id = %s
              AND booking_id IS NULL
            ORDER BY ten, id
            """,
            (room_id,),
        )
        services = cursor.fetchall()
        return {
            "message": "Lấy dịch vụ mặc định của phòng thành công.",
            "phong": room,
            "total": len(services),
            "data": services,
        }
    except HTTPException:
        raise
    except Error as exc:
        _raise_database_error(exc)
    finally:
        close_db(cursor, conn)


@router.post("/", status_code=201)
def create_service(service: ServiceCreate):
    """Create either a room-default service or a Booking-consumption service."""
    ten, don_gia, so_luong = _validate_service_values(
        service.ten, service.don_gia, service.so_luong
    )
    if service.booking_id is None and service.phong_id is None:
        raise HTTPException(
            status_code=422,
            detail="Dịch vụ phải thuộc một Booking hoặc một phòng.",
        )

    conn = get_connection()
    cursor = conn.cursor()
    try:
        if service.booking_id is not None:
            # If a caller sends both identifiers, reject a mismatched room.
            # The procedure remains authoritative and locks/rechecks the Booking.
            if service.phong_id is not None:
                cursor.execute(
                    "SELECT phong_id FROM booking WHERE id = %s",
                    (service.booking_id,),
                )
                booking_row = cursor.fetchone()
                if booking_row is None:
                    raise HTTPException(status_code=404, detail="Booking không tồn tại.")
                if int(booking_row[0]) != service.phong_id:
                    raise HTTPException(
                        status_code=409,
                        detail="Phòng được gửi lên không khớp với phòng của Booking.",
                    )

            # The stored procedure owns its transaction (START TRANSACTION/COMMIT).
            # Do not wrap it in another API transaction.
            cursor.callproc(
                "sp_them_dichvu_booking",
                [service.booking_id, ten, don_gia, so_luong],
            )
            row = _read_procedure_result(cursor)
            if row is None:
                raise HTTPException(
                    status_code=500,
                    detail="Stored Procedure đã chạy nhưng không trả về mã dịch vụ.",
                )
            # The procedure's first result column is dichvu_id.
            service_id = row.get("dichvu_id") if isinstance(row, dict) else row[0]
            return {
                "message": "Thêm dịch vụ vào Booking thành công.",
                "id": int(service_id),
                "booking_id": service.booking_id,
            }

        # A default room service has booking_id = NULL. The insert trigger checks
        # values and requires a non-null room_id.
        cursor.execute(
            "SELECT id FROM phong WHERE id = %s FOR UPDATE",
            (service.phong_id,),
        )
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Phòng không tồn tại.")

        cursor.execute(
            """
            INSERT INTO dichvu (ten, don_gia, so_luong, phong_id, booking_id)
            VALUES (%s, %s, %s, %s, NULL)
            """,
            (ten, don_gia, so_luong, service.phong_id),
        )
        service_id = cursor.lastrowid
        conn.commit()
        return {
            "message": "Thêm dịch vụ mặc định cho phòng thành công.",
            "id": service_id,
            "phong_id": service.phong_id,
        }
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
    """Update service values without reassigning its room/Booking relationship."""
    ten, don_gia, so_luong = _validate_service_values(
        service.ten, service.don_gia, service.so_luong
    )

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT id, phong_id, booking_id
            FROM dichvu
            WHERE id = %s
            FOR UPDATE
            """,
            (service_id,),
        )
        current = cursor.fetchone()
        if current is None:
            raise HTTPException(status_code=404, detail="Dịch vụ không tồn tại.")

        old_booking_id = current["booking_id"]
        old_room_id = current["phong_id"]

        # A service already tied to a Booking cannot be detached or moved to
        # another Booking. The database trigger enforces the same rule.
        if old_booking_id is not None:
            if service.booking_id != old_booking_id:
                raise HTTPException(
                    status_code=409,
                    detail="Không được chuyển hoặc tách dịch vụ đã gắn với Booking.",
                )
            if service.phong_id is not None and service.phong_id != old_room_id:
                raise HTTPException(
                    status_code=409,
                    detail="Không được đổi phòng của dịch vụ thuộc Booking.",
                )
        else:
            # Room-default rows remain room-default rows; the GUI page manages
            # Booking services only, but the API preserves this data type.
            if service.booking_id is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Không được chuyển dịch vụ mặc định của phòng sang Booking.",
                )
            if service.phong_id is not None and service.phong_id != old_room_id:
                raise HTTPException(
                    status_code=409,
                    detail="Không hỗ trợ chuyển dịch vụ mặc định sang phòng khác.",
                )

        cursor.execute(
            """
            UPDATE dichvu
            SET ten = %s,
                don_gia = %s,
                so_luong = %s
            WHERE id = %s
            """,
            (ten, don_gia, so_luong, service_id),
        )
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
    """Delete a service only when database triggers permit the operation."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM dichvu WHERE id = %s", (service_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Dịch vụ không tồn tại.")
        conn.commit()
        return {"message": "Xóa dịch vụ thành công.", "id": service_id}
    except HTTPException:
        conn.rollback()
        raise
    except Error as exc:
        conn.rollback()
        _raise_database_error(exc)
    finally:
        close_db(cursor, conn)
