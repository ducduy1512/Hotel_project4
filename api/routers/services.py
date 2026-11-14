
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional

from api.database import get_db


router = APIRouter(
    prefix="/api/services",
    tags=["Services"]
)


# =========================
# SCHEMAS
# =========================

class ServiceCreate(BaseModel):
    ten: str = Field(..., min_length=1, max_length=255)
    don_gia: Decimal = Field(..., gt=0)
    so_luong: int = Field(..., gt=0)
    booking_id: int = Field(..., gt=0)


class ServiceUpdate(BaseModel):
    ten: Optional[str] = Field(None, min_length=1, max_length=255)
    don_gia: Optional[Decimal] = Field(None, gt=0)
    so_luong: Optional[int] = Field(None, gt=0)
    booking_id: Optional[int] = Field(None, gt=0)


# =========================
# HELPER
# =========================

def get_service_by_id(cursor, service_id: int):
    cursor.execute("""
        SELECT
            d.id,
            d.ten,
            d.don_gia,
            d.so_luong,
            d.booking_id
        FROM dichvu d
        WHERE d.id = %s
    """, (service_id,))

    return cursor.fetchone()


def check_booking_exists(cursor, booking_id: int):
    cursor.execute(
        "SELECT id FROM booking WHERE id = %s",
        (booking_id,)
    )

    if cursor.fetchone() is None:
        raise HTTPException(
            status_code=404,
            detail="Booking không tồn tại."
        )


# =========================
# GET ALL SERVICES
# =========================

@router.get("/")
def get_services(db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                d.id,
                d.ten,
                d.don_gia,
                d.so_luong,
                d.booking_id,
                b.phong_id,
                b.khach_id,
                b.ngay_nhan,
                b.ngay_tra,
                b.trang_thai AS booking_trang_thai
            FROM dichvu d
            LEFT JOIN booking b ON d.booking_id = b.id
            ORDER BY d.id DESC
        """)

        return {
            "message": "Lấy danh sách dịch vụ thành công",
            "total": cursor.rowcount,
            "services": cursor.fetchall()
        }

    finally:
        cursor.close()


# =========================
# GET SERVICE BY ID
# =========================

@router.get("/{service_id}")
def get_service(service_id: int, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)

    try:
        service = get_service_by_id(cursor, service_id)

        if service is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy dịch vụ."
            )

        return {
            "message": "Lấy thông tin dịch vụ thành công",
            "service": service
        }

    finally:
        cursor.close()


# =========================
# CREATE SERVICE
# =========================

@router.post("/", status_code=201)
def create_service(data: ServiceCreate, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)

    try:
        check_booking_exists(cursor, data.booking_id)

        cursor.execute("""
            INSERT INTO dichvu (
                ten,
                don_gia,
                so_luong,
                booking_id
            )
            VALUES (%s, %s, %s, %s)
        """, (
            data.ten.strip(),
            data.don_gia,
            data.so_luong,
            data.booking_id
        ))

        new_id = cursor.lastrowid
        db.commit()

        service = get_service_by_id(cursor, new_id)

        return {
            "message": "Thêm dịch vụ thành công",
            "id": new_id,
            "service": service
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Lỗi khi thêm dịch vụ: {str(e)}"
        )

    finally:
        cursor.close()


# =========================
# UPDATE SERVICE
# =========================

@router.put("/{service_id}")
def update_service(
    service_id: int,
    data: ServiceUpdate,
    db=Depends(get_db)
):
    cursor = db.cursor(dictionary=True)

    try:
        existing = get_service_by_id(cursor, service_id)

        if existing is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy dịch vụ."
            )

        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(
                status_code=400,
                detail="Không có thông tin nào được gửi để cập nhật."
            )

        if "ten" in update_data:
            update_data["ten"] = update_data["ten"].strip()

            if not update_data["ten"]:
                raise HTTPException(
                    status_code=422,
                    detail="Tên dịch vụ không được để trống."
                )

        if "booking_id" in update_data:
            check_booking_exists(cursor, update_data["booking_id"])

        allowed_fields = [
            "ten",
            "don_gia",
            "so_luong",
            "booking_id"
        ]

        set_clause = ", ".join(
            f"{field} = %s"
            for field in update_data
            if field in allowed_fields
        )

        values = [
            update_data[field]
            for field in update_data
            if field in allowed_fields
        ]

        values.append(service_id)

        cursor.execute(
            f"""
            UPDATE dichvu
            SET {set_clause}
            WHERE id = %s
            """,
            tuple(values)
        )

        db.commit()

        updated_service = get_service_by_id(cursor, service_id)

        return {
            "message": "Cập nhật dịch vụ thành công",
            "service": updated_service
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Lỗi khi cập nhật dịch vụ: {str(e)}"
        )

    finally:
        cursor.close()


# =========================
# DELETE SERVICE
# =========================

@router.delete("/{service_id}")
def delete_service(service_id: int, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)

    try:
        existing = get_service_by_id(cursor, service_id)

        if existing is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy dịch vụ."
            )

        cursor.execute(
            "DELETE FROM dichvu WHERE id = %s",
            (service_id,)
        )

        db.commit()

        return {
            "message": "Xóa dịch vụ thành công",
            "id": service_id
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Lỗi khi xóa dịch vụ: {str(e)}"
        )

    finally:
        cursor.close()
