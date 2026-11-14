
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from mysql.connector import Error

from api.database import get_db


router = APIRouter(
    prefix="/api/bookings",
    tags=["Bookings"]
)


# ==================================================
# SCHEMAS
# ==================================================

class BookingCreate(BaseModel):
    phong_id: int = Field(gt=0)
    khach_id: int = Field(gt=0)
    ngay_nhan: date
    ngay_tra: date


class BookingUpdate(BaseModel):
    phong_id: int = Field(gt=0)
    khach_id: int = Field(gt=0)
    ngay_nhan: date
    ngay_tra: date


# ==================================================
# VALIDATE DATES
# ==================================================

def validate_dates(ngay_nhan, ngay_tra):
    if ngay_tra <= ngay_nhan:
        raise HTTPException(
            status_code=422,
            detail="Ngày trả phòng phải sau ngày nhận phòng."
        )


# ==================================================
# HELPER: ĐÓNG CÁC RESULT SET CỦA PROCEDURE
# ==================================================

def close_procedure_results(cursor):
    for result in cursor.stored_results():
        result.fetchall()
        result.close()


# ==================================================
# GET: DANH SÁCH BOOKING
# ==================================================

@router.get("/")
def get_bookings(db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                b.id,
                b.phong_id,
                p.so_phong,
                b.khach_id,
                k.ho_ten,
                b.ngay_nhan,
                b.ngay_tra,
                b.trang_thai
            FROM booking b
            JOIN phong p
                ON b.phong_id = p.id
            JOIN khach k
                ON b.khach_id = k.id
            ORDER BY b.id DESC
        """)

        return cursor.fetchall()

    except Error as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cursor.close()


# ==================================================
# GET: KIỂM TRA PHÒNG TRỐNG
# Đặt trước GET /{booking_id} để tránh xung đột URL
# ==================================================

@router.get("/available-rooms/search")
def get_available_rooms(
    ngay_nhan: date = Query(...),
    ngay_tra: date = Query(...),
    db=Depends(get_db)
):
    validate_dates(ngay_nhan, ngay_tra)

    cursor = db.cursor(dictionary=True)

    try:
        cursor.callproc(
            "sp_kiem_tra_phong_trong",
            [ngay_nhan, ngay_tra]
        )

        available_rooms = []

        for result in cursor.stored_results():
            rows = result.fetchall()

            if result.description:
                columns = [
                    column[0]
                    for column in result.description
                ]

                available_rooms.extend([
                    dict(zip(columns, row))
                    for row in rows
                ])

            result.close()

        return {
            "ngay_nhan": ngay_nhan,
            "ngay_tra": ngay_tra,
            "total": len(available_rooms),
            "rooms": available_rooms
        }

    except Error as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    finally:
        cursor.close()


# ==================================================
# GET: CHI TIẾT BOOKING
# ==================================================

@router.get("/{booking_id}")
def get_booking(
    booking_id: int,
    db=Depends(get_db)
):
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                b.id,
                b.phong_id,
                p.so_phong,
                b.khach_id,
                k.ho_ten,
                b.ngay_nhan,
                b.ngay_tra,
                b.trang_thai
            FROM booking b
            JOIN phong p
                ON b.phong_id = p.id
            JOIN khach k
                ON b.khach_id = k.id
            WHERE b.id = %s
        """, (booking_id,))

        booking = cursor.fetchone()

        if booking is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy booking."
            )

        return booking

    except HTTPException:
        raise

    except Error as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cursor.close()


# ==================================================
# POST: TẠO BOOKING
# Sử dụng stored procedure sp_tao_booking
# Lấy ID bằng LAST_INSERT_ID()
# ==================================================

@router.post("/", status_code=201)
def create_booking(
    booking: BookingCreate,
    db=Depends(get_db)
):
    validate_dates(
        booking.ngay_nhan,
        booking.ngay_tra
    )

    cursor = db.cursor(dictionary=True)

    try:
        # Gọi stored procedure tạo booking
        cursor.callproc(
            "sp_tao_booking",
            [
                booking.phong_id,
                booking.khach_id,
                booking.ngay_nhan,
                booking.ngay_tra
            ]
        )

        # Đóng các Result Set do procedure trả về
        close_procedure_results(cursor)

        # Lấy ID tự tăng trên chính kết nối hiện tại
        cursor.execute("SELECT LAST_INSERT_ID() AS new_id")

        id_result = cursor.fetchone()
        new_id = id_result["new_id"] if id_result else None

        if not new_id:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Không lấy được ID booking. "
                    "Hãy kiểm tra stored procedure sp_tao_booking."
                )
            )

        # Lưu giao dịch
        db.commit()

        # Lấy thông tin booking vừa tạo
        cursor.execute("""
            SELECT
                b.id,
                b.phong_id,
                p.so_phong,
                b.khach_id,
                k.ho_ten,
                b.ngay_nhan,
                b.ngay_tra,
                b.trang_thai
            FROM booking b
            JOIN phong p
                ON b.phong_id = p.id
            JOIN khach k
                ON b.khach_id = k.id
            WHERE b.id = %s
        """, (new_id,))

        new_booking = cursor.fetchone()

        if new_booking is None:
            raise HTTPException(
                status_code=500,
                detail="Không tìm thấy booking vừa được tạo."
            )

        return {
            "message": "Tạo booking thành công",
            "id": new_id,
            "booking": new_booking
        }

    except HTTPException:
        db.rollback()
        raise

    except Error as e:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail=str(e)
        )

    finally:
        cursor.close()


# ==================================================
# PUT: CẬP NHẬT BOOKING
# ==================================================

@router.put("/{booking_id}")
def update_booking(
    booking_id: int,
    booking: BookingUpdate,
    db=Depends(get_db)
):
    validate_dates(
        booking.ngay_nhan,
        booking.ngay_tra
    )

    cursor = db.cursor(dictionary=True)

    try:
        # Kiểm tra booking tồn tại
        cursor.execute("""
            SELECT id, trang_thai
            FROM booking
            WHERE id = %s
        """, (booking_id,))

        existing_booking = cursor.fetchone()

        if existing_booking is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy booking."
            )

        # Không cho sửa booking đã hủy hoặc hoàn thành
        if existing_booking["trang_thai"] not in (
            "CHO_XAC_NHAN",
            "DA_XAC_NHAN"
        ):
            raise HTTPException(
                status_code=409,
                detail="Không thể cập nhật booking đã hủy hoặc hoàn thành."
            )

        # Kiểm tra phòng tồn tại
        cursor.execute("""
            SELECT id
            FROM phong
            WHERE id = %s
        """, (booking.phong_id,))

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy phòng."
            )

        # Kiểm tra khách hàng tồn tại
        cursor.execute("""
            SELECT id
            FROM khach
            WHERE id = %s
        """, (booking.khach_id,))

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy khách hàng."
            )

        # Cập nhật booking
        cursor.execute("""
            UPDATE booking
            SET
                phong_id = %s,
                khach_id = %s,
                ngay_nhan = %s,
                ngay_tra = %s
            WHERE id = %s
        """, (
            booking.phong_id,
            booking.khach_id,
            booking.ngay_nhan,
            booking.ngay_tra,
            booking_id
        ))

        db.commit()

        # Lấy thông tin sau cập nhật
        cursor.execute("""
            SELECT
                b.id,
                b.phong_id,
                p.so_phong,
                b.khach_id,
                k.ho_ten,
                b.ngay_nhan,
                b.ngay_tra,
                b.trang_thai
            FROM booking b
            JOIN phong p
                ON b.phong_id = p.id
            JOIN khach k
                ON b.khach_id = k.id
            WHERE b.id = %s
        """, (booking_id,))

        updated_booking = cursor.fetchone()

        return {
            "message": "Cập nhật booking thành công",
            "booking": updated_booking
        }

    except HTTPException:
        db.rollback()
        raise

    except Error as e:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail=str(e)
        )

    finally:
        cursor.close()


# ==================================================
# DELETE: HỦY BOOKING
# Không xóa bản ghi trực tiếp
# Sử dụng stored procedure sp_huy_booking
# ==================================================

@router.delete("/{booking_id}")
def cancel_booking(
    booking_id: int,
    db=Depends(get_db)
):
    cursor = db.cursor(dictionary=True)

    try:
        # Kiểm tra booking tồn tại
        cursor.execute("""
            SELECT id
            FROM booking
            WHERE id = %s
        """, (booking_id,))

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy booking."
            )

        # Gọi procedure hủy booking
        cursor.callproc(
            "sp_huy_booking",
            [booking_id]
        )

        close_procedure_results(cursor)

        db.commit()

        # Lấy trạng thái sau khi hủy
        cursor.execute("""
            SELECT
                id,
                trang_thai
            FROM booking
            WHERE id = %s
        """, (booking_id,))

        cancelled_booking = cursor.fetchone()

        return {
            "message": "Hủy booking thành công",
            "id": booking_id,
            "booking": cancelled_booking
        }

    except HTTPException:
        db.rollback()
        raise

    except Error as e:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail=str(e)
        )

    finally:
        cursor.close()
