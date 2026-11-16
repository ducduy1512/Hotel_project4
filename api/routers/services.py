
from fastapi import APIRouter, HTTPException
from database import get_connection

from api.schemas import (
    ServiceCreate,
    ServiceUpdate,
    ServiceCatalogCreate,
    ServiceCatalogUpdate,
    RoomTypeDefaultServicesUpdate,
)

router = APIRouter(
    prefix="/api/services",
    tags=["Services"]
)


# =========================================================
# HELPER
# =========================================================

def close_db(cursor, conn):
    try:
        if cursor:
            cursor.close()
    finally:
        if conn:
            conn.close()


# =========================================================
# 1. SERVICE CATALOG
# Bảng: dichvu_catalog
# =========================================================

@router.get("/catalog")
def get_service_catalog():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                id,
                ten,
                don_gia,
                trang_thai,
                mo_ta
            FROM dichvu_catalog
            ORDER BY ten
        """)

        return cursor.fetchall()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        close_db(cursor, conn)


@router.post("/catalog")
def create_service_catalog(service: ServiceCatalogCreate):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        ten = service.ten.strip()

        if not ten:
            raise HTTPException(
                status_code=400,
                detail="Ten dich vu khong duoc de trong"
            )

        cursor.execute("""
            INSERT INTO dichvu_catalog (
                ten,
                don_gia,
                trang_thai,
                mo_ta
            )
            VALUES (%s, %s, 'DANG_HOAT_DONG', %s)
        """, (
            ten,
            service.don_gia,
            service.mo_ta
        ))

        service_id = cursor.lastrowid
        conn.commit()

        return {
            "message": "Them danh muc dich vu thanh cong",
            "id": service_id
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        close_db(cursor, conn)


@router.put("/catalog/{service_id}")
def update_service_catalog(
    service_id: int,
    service: ServiceCatalogUpdate
):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        ten = service.ten.strip()

        if not ten:
            raise HTTPException(
                status_code=400,
                detail="Ten dich vu khong duoc de trong"
            )

        if service.trang_thai not in (
            "DANG_HOAT_DONG",
            "NGUNG_HOAT_DONG"
        ):
            raise HTTPException(
                status_code=400,
                detail="Trang thai dich vu khong hop le"
            )

        cursor.execute("""
            UPDATE dichvu_catalog
            SET ten = %s,
                don_gia = %s,
                trang_thai = %s,
                mo_ta = %s
            WHERE id = %s
        """, (
            ten,
            service.don_gia,
            service.trang_thai,
            service.mo_ta,
            service_id
        ))

        if cursor.rowcount == 0:
            cursor.execute("""
                SELECT id
                FROM dichvu_catalog
                WHERE id = %s
            """, (service_id,))

            if cursor.fetchone() is None:
                raise HTTPException(
                    status_code=404,
                    detail="Danh muc dich vu khong ton tai"
                )

        conn.commit()

        return {
            "message": "Cap nhat danh muc dich vu thanh cong"
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        close_db(cursor, conn)


# =========================================================
# 2. DEFAULT SERVICES BY ROOM TYPE
# Bảng: loaiphong_dichvu
# =========================================================

@router.get("/room-types/{room_type_id}/defaults")
def get_room_type_default_services(room_type_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT id, ten, gia_co_ban, suc_chua
            FROM loaiphong
            WHERE id = %s
        """, (room_type_id,))

        room_type = cursor.fetchone()

        if room_type is None:
            raise HTTPException(
                status_code=404,
                detail="Loai phong khong ton tai"
            )

        cursor.execute("""
            SELECT
                lpd.id AS mapping_id,
                dc.id AS dichvu_id,
                dc.ten,
                lpd.don_gia,
                lpd.so_luong_mac_dinh,
                dc.trang_thai,
                dc.mo_ta
            FROM loaiphong_dichvu lpd
            JOIN dichvu_catalog dc
                ON dc.id = lpd.dichvu_id
            WHERE lpd.loaiphong_id = %s
            ORDER BY dc.ten
        """, (room_type_id,))

        return {
            "room_type": room_type,
            "dich_vu": cursor.fetchall()
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        close_db(cursor, conn)


@router.put("/room-types/{room_type_id}/defaults")
def update_room_type_default_services(
    room_type_id: int,
    data: RoomTypeDefaultServicesUpdate
):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Check room type
        cursor.execute("""
            SELECT id
            FROM loaiphong
            WHERE id = %s
        """, (room_type_id,))

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Loai phong khong ton tai"
            )

        # Check duplicate service IDs
        service_ids = [
            item.dichvu_id
            for item in data.dich_vu
        ]

        if len(service_ids) != len(set(service_ids)):
            raise HTTPException(
                status_code=400,
                detail="Khong duoc chon trung dich vu"
            )

        # Validate all services before changing mappings
        for item in data.dich_vu:
            cursor.execute("""
                SELECT id
                FROM dichvu_catalog
                WHERE id = %s
                  AND trang_thai = 'DANG_HOAT_DONG'
            """, (item.dichvu_id,))

            if cursor.fetchone() is None:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Dich vu ID {item.dichvu_id} "
                        "khong ton tai hoac da ngung hoat dong"
                    )
                )

        # Replace old default-service configuration
        cursor.execute("""
            DELETE FROM loaiphong_dichvu
            WHERE loaiphong_id = %s
        """, (room_type_id,))

        for item in data.dich_vu:
            cursor.execute("""
                INSERT INTO loaiphong_dichvu (
                    loaiphong_id,
                    dichvu_id,
                    don_gia,
                    so_luong_mac_dinh
                )
                VALUES (%s, %s, %s, %s)
            """, (
                room_type_id,
                item.dichvu_id,
                item.don_gia,
                item.so_luong_mac_dinh
            ))

        conn.commit()

        return {
            "message": "Cap nhat dich vu mac dinh thanh cong",
            "room_type_id": room_type_id,
            "total_services": len(data.dich_vu)
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        close_db(cursor, conn)


# =========================================================
# 3. SERVICES AVAILABLE FOR A ROOM
# =========================================================

@router.get("/rooms/{room_id}/options")
def get_room_service_options(room_id: int):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                p.id AS phong_id,
                p.so_phong,
                p.loai_phong_id,
                lp.ten AS ten_loai_phong
            FROM phong p
            JOIN loaiphong lp
                ON lp.id = p.loai_phong_id
            WHERE p.id = %s
        """, (room_id,))

        room = cursor.fetchone()

        if room is None:
            raise HTTPException(
                status_code=404,
                detail="Phong khong ton tai"
            )

        cursor.execute("""
            SELECT
                dc.id AS dichvu_id,
                dc.ten,
                dc.mo_ta,
                lpd.don_gia,
                lpd.so_luong_mac_dinh
            FROM loaiphong_dichvu lpd
            JOIN dichvu_catalog dc
                ON dc.id = lpd.dichvu_id
            WHERE lpd.loaiphong_id = %s
              AND dc.trang_thai = 'DANG_HOAT_DONG'
            ORDER BY dc.ten
        """, (room["loai_phong_id"],))

        services = cursor.fetchall()

        return {
            "message": "Lay danh sach dich vu thanh cong",
            "phong": room,
            "total": len(services),
            "data": services
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        close_db(cursor, conn)


# =========================================================
# 4. LEGACY SERVICE API
# Giữ lại để tương thích với giao diện cũ.
# Bảng: dichvu
# =========================================================

@router.get("/")
def get_services():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                id,
                ten,
                don_gia,
                so_luong,
                phong_id,
                booking_id
            FROM dichvu
            ORDER BY id
        """)

        return cursor.fetchall()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        close_db(cursor, conn)


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
            INSERT INTO dichvu (
                ten,
                don_gia,
                so_luong,
                phong_id,
                booking_id
            )
            VALUES (%s, %s, %s, %s, %s)
        """, (
            service.ten,
            service.don_gia,
            service.so_luong,
            phong_id,
            service.booking_id
        ))

        service_id = cursor.lastrowid
        conn.commit()

        return {
            "message": "Them dich vu thanh cong",
            "id": service_id
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        close_db(cursor, conn)


@router.put("/{service_id}")
def update_service(
    service_id: int,
    service: ServiceUpdate
):
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
            cursor.execute(
                "SELECT id FROM dichvu WHERE id = %s",
                (service_id,)
            )

            if cursor.fetchone() is None:
                raise HTTPException(
                    status_code=404,
                    detail="Dich vu khong ton tai"
                )

        conn.commit()

        return {
            "message": "Cap nhat dich vu thanh cong"
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        close_db(cursor, conn)


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

        return {
            "message": "Xoa dich vu thanh cong"
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        close_db(cursor, conn)
