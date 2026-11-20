from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from mysql.connector import Error

from api.database import get_db
from api.schemas import BookingUpdate
from api.peak_season_display import enrich_peak_season_record, enrich_peak_season_records


class BookingCreateRequest(BaseModel):
    """Payload đúng với bảng Booking trong ERD 8 bảng."""

    model_config = ConfigDict(extra="forbid")

    phong_id: int = Field(gt=0)
    khach_id: int = Field(gt=0)
    ngay_nhan: date
    ngay_tra: date

router = APIRouter(prefix="/api/bookings", tags=["Bookings"])


def validate_dates(ngay_nhan: date, ngay_tra: date) -> None:
    if ngay_tra <= ngay_nhan:
        raise HTTPException(
            status_code=422,
            detail="Ngày trả phòng phải sau ngày nhận phòng.",
        )


def read_procedure_rows(cursor):
    """Đọc hết mọi result set do stored procedure trả về."""
    rows = []
    for result_cursor in cursor.stored_results():
        try:
            rows.extend(result_cursor.fetchall())
        finally:
            result_cursor.close()
    return rows


def booking_select_sql(where_clause: str = "") -> str:
    return f"""
        SELECT
            b.id,
            b.phong_id,
            p.so_phong,
            b.khach_id,
            k.ho_ten,
            b.ngay_nhan,
            b.ngay_tra,
            b.trang_thai,
            b.tien_phong_du_kien,
            b.tien_phu_phi_mua_cao_diem,
            b.ap_dung_mua_cao_diem,
            b.chi_tiet_mua_cao_diem
        FROM booking b
        JOIN phong p ON p.id = b.phong_id
        JOIN khach k ON k.id = b.khach_id
        {where_clause}
    """


@router.get("/")
def get_bookings(db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(booking_select_sql("ORDER BY b.id DESC"))
        rows = cursor.fetchall()
        enrich_peak_season_records(rows)
        return rows
    except Error as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        cursor.close()


# Giữ cả hai URL: GUI hiện tại đang gọi /available-rooms; URL /search
# cũng được giữ để các client/API docs cũ không bị hỏng.
@router.get("/available-rooms")
@router.get("/available-rooms/search")
def get_available_rooms(
    ngay_nhan: date = Query(...),
    ngay_tra: date = Query(...),
    db=Depends(get_db),
):
    validate_dates(ngay_nhan, ngay_tra)
    cursor = db.cursor(dictionary=True)
    try:
        cursor.callproc(
            "sp_kiem_tra_phong_trong",
            [ngay_nhan, ngay_tra],
        )
        available_rooms = []
        for result_cursor in cursor.stored_results():
            try:
                available_rooms.extend(result_cursor.fetchall())
            finally:
                result_cursor.close()

        return {
            "ngay_nhan": ngay_nhan,
            "ngay_tra": ngay_tra,
            "total": len(available_rooms),
            "rooms": available_rooms,
        }
    except Error as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        cursor.close()


@router.get("/{booking_id}")
def get_booking(booking_id: int, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            booking_select_sql("WHERE b.id = %s"),
            (booking_id,),
        )
        booking = cursor.fetchone()
        if booking is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy Booking.")

        cursor.execute(
            """
            SELECT
                id AS dichvu_id,
                ten,
                don_gia,
                so_luong,
                don_gia * so_luong AS thanh_tien
            FROM dichvu
            WHERE booking_id = %s
            ORDER BY id
            """,
            (booking_id,),
        )
        booking["dich_vu"] = cursor.fetchall()
        enrich_peak_season_record(booking)
        return booking
    except HTTPException:
        raise
    except Error as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        cursor.close()


@router.post("/", status_code=201)
def create_booking(booking: BookingCreateRequest, db=Depends(get_db)):
    validate_dates(booking.ngay_nhan, booking.ngay_tra)

    # Dịch vụ mặc định được trg_booking_after_insert sao chép từ các dòng
    # dichvu có booking_id IS NULL. Dịch vụ phát sinh được thêm sau qua /api/services/.

    cursor = db.cursor(dictionary=True)
    try:
        # sp_tao_booking tự START TRANSACTION và COMMIT bên trong procedure.
        # Không mở transaction bên ngoài ở API vì nested START/COMMIT có thể
        # commit sớm transaction của API và làm rollback không còn hiệu lực.
        cursor.callproc(
            "sp_tao_booking",
            [
                booking.phong_id,
                booking.khach_id,
                booking.ngay_nhan,
                booking.ngay_tra,
            ],
        )
        procedure_rows = read_procedure_rows(cursor)
        procedure_result = procedure_rows[0] if procedure_rows else {}
        new_id = procedure_result.get("booking_id") if isinstance(
            procedure_result, dict
        ) else None

        if not new_id:
            # Fallback an toàn cho connector/procedure trả kết quả khác dạng.
            cursor.execute(
                """
                SELECT id
                FROM booking
                WHERE phong_id = %s
                  AND khach_id = %s
                  AND ngay_nhan = %s
                  AND ngay_tra = %s
                  AND trang_thai = 'CHO_XAC_NHAN'
                ORDER BY id DESC
                LIMIT 1
                """,
                (
                    booking.phong_id,
                    booking.khach_id,
                    booking.ngay_nhan,
                    booking.ngay_tra,
                ),
            )
            row = cursor.fetchone()
            new_id = row["id"] if row else None

        if not new_id:
            raise HTTPException(
                status_code=500,
                detail="Procedure đã chạy nhưng API không lấy được Booking ID.",
            )

        cursor.execute(
            booking_select_sql("WHERE b.id = %s"),
            (new_id,),
        )
        new_booking = cursor.fetchone()
        if new_booking is None:
            raise HTTPException(
                status_code=500,
                detail="Không tìm thấy Booking vừa tạo.",
            )

        cursor.execute(
            """
            SELECT
                id AS dichvu_id,
                ten,
                don_gia,
                so_luong,
                don_gia * so_luong AS thanh_tien
            FROM dichvu
            WHERE booking_id = %s
            ORDER BY id
            """,
            (new_id,),
        )
        services = cursor.fetchall()

        return {
            "message": "Tạo Booking thành công",
            "id": new_id,
            "booking": new_booking,
            "dich_vu": services,
            "tong_so_dich_vu": len(services),
        }
    except HTTPException:
        # Procedure có EXIT HANDLER tự rollback nếu phát sinh lỗi bên trong.
        raise
    except Error as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    finally:
        cursor.close()


@router.put("/{booking_id}")
def update_booking(
    booking_id: int,
    booking: BookingUpdate,
    db=Depends(get_db),
):
    validate_dates(booking.ngay_nhan, booking.ngay_tra)
    cursor = db.cursor(dictionary=True)
    try:
        db.start_transaction()
        cursor.execute(
            "SELECT id, trang_thai FROM booking WHERE id = %s FOR UPDATE",
            (booking_id,),
        )
        existing = cursor.fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy Booking.")

        if existing["trang_thai"] not in ("CHO_XAC_NHAN", "DA_XAC_NHAN"):
            raise HTTPException(
                status_code=409,
                detail="Chỉ được sửa Booking đang chờ hoặc đã xác nhận.",
            )

        cursor.execute(
            """
            UPDATE booking
            SET phong_id = %s,
                khach_id = %s,
                ngay_nhan = %s,
                ngay_tra = %s
            WHERE id = %s
            """,
            (
                booking.phong_id,
                booking.khach_id,
                booking.ngay_nhan,
                booking.ngay_tra,
                booking_id,
            ),
        )
        cursor.execute(
            booking_select_sql("WHERE b.id = %s"),
            (booking_id,),
        )
        updated = cursor.fetchone()
        db.commit()
        return {"message": "Cập nhật Booking thành công", "booking": updated}
    except HTTPException:
        db.rollback()
        raise
    except Error as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        cursor.close()


def run_booking_status_procedure(booking_id: int, procedure_name: str, success_message: str, db):
    """Gọi procedure chuyển trạng thái; procedure tự quản lý transaction."""
    cursor = db.cursor(dictionary=True)
    try:
        cursor.callproc(procedure_name, [booking_id])
        read_procedure_rows(cursor)
        cursor.execute(booking_select_sql("WHERE b.id = %s"), (booking_id,))
        booking = cursor.fetchone()
        if booking is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy Booking sau khi cập nhật.")
        return {"message": success_message, "id": booking_id,
                "booking": booking, "trang_thai": booking["trang_thai"]}
    except HTTPException:
        raise
    except Error as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    finally:
        cursor.close()


@router.post("/{booking_id}/confirm")
def confirm_booking(booking_id: int, db=Depends(get_db)):
    return run_booking_status_procedure(booking_id, "sp_xac_nhan_booking", "Xác nhận Booking thành công", db)


@router.post("/{booking_id}/check-in")
def check_in_booking(booking_id: int, db=Depends(get_db)):
    return run_booking_status_procedure(booking_id, "sp_nhan_phong", "Nhận phòng thành công", db)


@router.post("/{booking_id}/check-out")
def check_out_booking(booking_id: int, db=Depends(get_db)):
    return run_booking_status_procedure(booking_id, "sp_tra_phong", "Trả phòng thành công", db)


@router.delete("/{booking_id}")
def cancel_booking(booking_id: int, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM booking WHERE id = %s", (booking_id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy Booking.")

        # sp_huy_booking cũng tự quản lý transaction ở phía MySQL.
        cursor.callproc("sp_huy_booking", [booking_id])
        read_procedure_rows(cursor)

        cursor.execute(
            "SELECT id, trang_thai FROM booking WHERE id = %s",
            (booking_id,),
        )
        cancelled = cursor.fetchone()
        return {
            "message": "Hủy Booking thành công",
            "id": booking_id,
            "booking": cancelled,
        }
    except HTTPException:
        raise
    except Error as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    finally:
        cursor.close()
