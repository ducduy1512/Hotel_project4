from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from database import get_connection

router = APIRouter(
    prefix="/api/services",
    tags=["Services"]
)


from api.schemas import ServiceCreate, ServiceUpdate


@router.get("/")
def get_services():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT id, ten, don_gia, so_luong, phong_id, booking_id
        FROM dichvu
        ORDER BY id
    """)

    data = cursor.fetchall()
    cursor.close()
    conn.close()

    return data


@router.post("/")
def create_service(service: ServiceCreate):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        phong_id = service.phong_id

        if service.booking_id is not None:
            cursor.execute(
                "SELECT phong_id FROM booking WHERE id = %s",
                (service.booking_id,)
            )
            booking = cursor.fetchone()

            if booking is None:
                raise HTTPException(
                    status_code=404,
                    detail="Booking khong ton tai"
                )

            if phong_id is not None and phong_id != booking[0]:
                raise HTTPException(
                    status_code=400,
                    detail="Phong khong khop voi booking"
                )

            phong_id = booking[0]

        if phong_id is None:
            raise HTTPException(
                status_code=400,
                detail="Phai chon phong hoac booking"
            )

        cursor.execute("""
            INSERT INTO dichvu
            (ten, don_gia, so_luong, phong_id, booking_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            service.ten,
            service.don_gia,
            service.so_luong,
            phong_id,
            service.booking_id
        ))

        conn.commit()

        return {
            "message": "Them dich vu thanh cong",
            "id": cursor.lastrowid
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()


@router.put("/{service_id}")
def update_service(service_id: int, service: ServiceUpdate):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        phong_id = service.phong_id

        if service.booking_id is not None:
            cursor.execute(
                "SELECT phong_id FROM booking WHERE id = %s",
                (service.booking_id,)
            )
            booking = cursor.fetchone()

            if booking is None:
                raise HTTPException(
                    status_code=404,
                    detail="Booking khong ton tai"
                )

            if phong_id is not None and phong_id != booking[0]:
                raise HTTPException(
                    status_code=400,
                    detail="Phong khong khop voi booking"
                )

            phong_id = booking[0]

        if phong_id is None:
            raise HTTPException(
                status_code=400,
                detail="Phai chon phong hoac booking"
            )

        cursor.execute("""
            UPDATE dichvu
            SET ten = %s,
                don_gia = %s,
                so_luong = %s,
                phong_id = %s,
                booking_id = %s
            WHERE id = %s
        """, (
            service.ten,
            service.don_gia,
            service.so_luong,
            phong_id,
            service.booking_id,
            service_id
        ))

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Dich vu khong ton tai"
            )

        conn.commit()

        return {"message": "Cap nhat dich vu thanh cong"}

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()


@router.delete("/{service_id}")
def delete_service(service_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "DELETE FROM dichvu WHERE id = %s",
            (service_id,)
        )

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Dich vu khong ton tai"
            )

        conn.commit()

        return {"message": "Xoa dich vu thanh cong"}

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
        conn.close()
