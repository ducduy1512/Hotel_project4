
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

from api.schemas import BookingCreate, BookingUpdate


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
# POST: TẠO BOOKING KÈM DỊCH VỤ KHÁCH LỰA CHỌN
# Sử dụng:
# - Stored procedure sp_tao_booking
# - Bảng dichvu_catalog
# - Bảng loaiphong_dichvu
# - Bảng booking_dichvu
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

    cursor = None
    transaction_started = False

    try:
        # =================================================
        # 1. BẮT ĐẦU TRANSACTION
        # =================================================

        db.start_transaction()
        transaction_started = True

        cursor = db.cursor(dictionary=True)

        # =================================================
        # 2. KIỂM TRA PHÒNG VÀ LẤY LOẠI PHÒNG
        # =================================================

        cursor.execute("""
            SELECT
                p.id,
                p.so_phong,
                p.loai_phong_id,
                lp.ten AS ten_loai_phong
            FROM phong p
            JOIN loaiphong lp
                ON lp.id = p.loai_phong_id
            WHERE p.id = %s
            FOR UPDATE
        """, (booking.phong_id,))

        room = cursor.fetchone()

        if room is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy phòng."
            )

        # =================================================
        # 3. KIỂM TRA CÁC DỊCH VỤ KHÁCH LỰA CHỌN
        # =================================================

        selected_services = booking.dich_vu or []

        service_ids = [
            item.dichvu_id
            for item in selected_services
        ]

        # Không cho chọn trùng dịch vụ
        if len(service_ids) != len(set(service_ids)):
            raise HTTPException(
                status_code=400,
                detail="Không được chọn trùng dịch vụ."
            )

        services_to_insert = []

        for item in selected_services:

            cursor.execute("""
                SELECT
                    dc.id AS dichvu_id,
                    dc.ten,
                    lpd.don_gia
                FROM loaiphong_dichvu lpd
                JOIN dichvu_catalog dc
                    ON dc.id = lpd.dichvu_id
                WHERE lpd.loaiphong_id = %s
                  AND dc.id = %s
                  AND dc.trang_thai = 'DANG_HOAT_DONG'
            """, (
                room["loai_phong_id"],
                item.dichvu_id
            ))

            service = cursor.fetchone()

            if service is None:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Dịch vụ ID {item.dichvu_id} "
                        "không khả dụng cho loại phòng này."
                    )
                )

            services_to_insert.append({
                "dichvu_id": service["dichvu_id"],
                "ten": service["ten"],
                "don_gia": service["don_gia"],
                "so_luong": item.so_luong
            })

        # =================================================
        # 4. GỌI STORED PROCEDURE TẠO BOOKING
        # =================================================

        cursor.callproc(
            "sp_tao_booking",
            [
                booking.phong_id,
                booking.khach_id,
                booking.ngay_nhan,
                booking.ngay_tra
            ]
        )

        # Đọc và đóng tất cả result set của procedure
        close_procedure_results(cursor)

        # Lấy ID booking vừa tạo
        cursor.execute("""
            SELECT LAST_INSERT_ID() AS new_id
        """)

        id_result = cursor.fetchone()

        new_id = (
            id_result["new_id"]
            if id_result
            else None
        )

        if not new_id:
            raise HTTPException(
                status_code=500,
                detail="Không lấy được ID booking mới."
            )

        # =================================================
        # 5. LƯU DỊCH VỤ KHÁCH ĐÃ CHỌN
        # =================================================

        for service in services_to_insert:

            cursor.execute("""
                INSERT INTO booking_dichvu (
                    booking_id,
                    dichvu_id,
                    ten_dich_vu,
                    don_gia,
                    so_luong,
                    nguon
                )
                VALUES (
                    %s, %s, %s, %s, %s, 'DAT_TRUOC'
                )
            """, (
                new_id,
                service["dichvu_id"],
                service["ten"],
                service["don_gia"],
                service["so_luong"]
            ))

        # =================================================
        # 6. LẤY THÔNG TIN BOOKING
        # =================================================

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
                detail="Không tìm thấy booking vừa tạo."
            )

        # =================================================
        # 7. LẤY DANH SÁCH DỊCH VỤ BOOKING
        # =================================================

        cursor.execute("""
            SELECT
                id,
                dichvu_id,
                ten_dich_vu,
                don_gia,
                so_luong,
                nguon
            FROM booking_dichvu
            WHERE booking_id = %s
            ORDER BY id
        """, (new_id,))

        booking_services = cursor.fetchall()

        # =================================================
        # 8. COMMIT - CHỈ KHI TẤT CẢ ĐỀU THÀNH CÔNG
        # =================================================

        db.commit()
        transaction_started = False

        # =================================================
        # 9. TRẢ KẾT QUẢ
        # =================================================

        return {
            "message": "Tạo booking thành công",
            "id": new_id,
            "booking": new_booking,
            "dich_vu": booking_services,
            "tong_so_dich_vu": len(booking_services)
        }

    except HTTPException:
        if transaction_started:
            db.rollback()
            transaction_started = False
        raise

    except Error as e:
        if transaction_started:
            db.rollback()
            transaction_started = False

        raise HTTPException(
            status_code=409,
            detail=str(e)
        )

    except Exception as e:
        if transaction_started:
            db.rollback()
            transaction_started = False

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        if cursor is not None:
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

    # Bắt đầu transaction trước khi thực hiện các thao tác database
    db.start_transaction()

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
