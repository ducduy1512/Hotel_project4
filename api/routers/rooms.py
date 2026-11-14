
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from mysql.connector import Error, IntegrityError
from api.database import get_db


router = APIRouter(
    prefix="/api/rooms",
    tags=["Rooms"]
)


# ==============================
# SCHEMAS
# ==============================

class RoomCreate(BaseModel):
    so_phong: str = Field(min_length=1, max_length=20)
    loai_phong_id: int = Field(gt=0)
    trang_thai: str = "SAN_SANG"


class RoomUpdate(BaseModel):
    so_phong: str = Field(min_length=1, max_length=20)
    loai_phong_id: int = Field(gt=0)
    trang_thai: str


# ==============================
# KIỂM TRA TRẠNG THÁI PHÒNG
# ==============================

VALID_STATUSES = [
    "SAN_SANG",
    "DANG_SU_DUNG",
    "BAO_TRI"
]


def validate_status(status: str):
    if status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail="Trạng thái không hợp lệ. Chỉ chấp nhận: SAN_SANG, DANG_SU_DUNG, BAO_TRI."
        )


# ==============================
# GET: DANH SÁCH PHÒNG
# ==============================

@router.get("/")
def get_rooms(db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                p.id,
                p.so_phong,
                p.loai_phong_id,
                lp.ten AS ten_loai_phong,
                p.trang_thai
            FROM phong p
            LEFT JOIN loaiphong lp
                ON p.loai_phong_id = lp.id
            ORDER BY p.id
        """)

        return cursor.fetchall()

    except Error as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()


# ==============================
# GET: CHI TIẾT PHÒNG
# ==============================

@router.get("/{room_id}")
def get_room(room_id: int, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                p.id,
                p.so_phong,
                p.loai_phong_id,
                lp.ten AS ten_loai_phong,
                p.trang_thai
            FROM phong p
            LEFT JOIN loaiphong lp
                ON p.loai_phong_id = lp.id
            WHERE p.id = %s
        """, (room_id,))

        room = cursor.fetchone()

        if room is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy phòng."
            )

        return room

    except HTTPException:
        raise

    except Error as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()


# ==============================
# POST: THÊM PHÒNG
# ==============================

@router.post("/", status_code=201)
def create_room(room: RoomCreate, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)

    try:
        validate_status(room.trang_thai)

        # Kiểm tra loại phòng tồn tại
        cursor.execute("""
            SELECT id
            FROM loaiphong
            WHERE id = %s
        """, (room.loai_phong_id,))

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Loại phòng không tồn tại."
            )

        cursor.execute("""
            INSERT INTO phong (
                so_phong,
                loai_phong_id,
                trang_thai
            )
            VALUES (%s, %s, %s)
        """, (
            room.so_phong.strip(),
            room.loai_phong_id,
            room.trang_thai
        ))

        new_id = cursor.lastrowid
        db.commit()

        cursor.execute("""
            SELECT
                p.id,
                p.so_phong,
                p.loai_phong_id,
                lp.ten AS ten_loai_phong,
                p.trang_thai
            FROM phong p
            LEFT JOIN loaiphong lp
                ON p.loai_phong_id = lp.id
            WHERE p.id = %s
        """, (new_id,))

        new_room = cursor.fetchone()

        return {
            "message": "Thêm phòng thành công",
            "id": new_id,
            "room": new_room
        }

    except HTTPException:
        db.rollback()
        raise

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Số phòng đã tồn tại hoặc dữ liệu vi phạm ràng buộc."
        )

    except Error as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()


# ==============================
# PUT: CẬP NHẬT PHÒNG
# ==============================

@router.put("/{room_id}")
def update_room(
    room_id: int,
    room: RoomUpdate,
    db=Depends(get_db)
):
    cursor = db.cursor(dictionary=True)

    try:
        validate_status(room.trang_thai)

        # Kiểm tra phòng tồn tại
        cursor.execute("""
            SELECT id
            FROM phong
            WHERE id = %s
        """, (room_id,))

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy phòng."
            )

        # Kiểm tra loại phòng tồn tại
        cursor.execute("""
            SELECT id
            FROM loaiphong
            WHERE id = %s
        """, (room.loai_phong_id,))

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Loại phòng không tồn tại."
            )

        cursor.execute("""
            UPDATE phong
            SET so_phong = %s,
                loai_phong_id = %s,
                trang_thai = %s
            WHERE id = %s
        """, (
            room.so_phong.strip(),
            room.loai_phong_id,
            room.trang_thai,
            room_id
        ))

        db.commit()

        cursor.execute("""
            SELECT
                p.id,
                p.so_phong,
                p.loai_phong_id,
                lp.ten AS ten_loai_phong,
                p.trang_thai
            FROM phong p
            LEFT JOIN loaiphong lp
                ON p.loai_phong_id = lp.id
            WHERE p.id = %s
        """, (room_id,))

        updated_room = cursor.fetchone()

        return {
            "message": "Cập nhật phòng thành công",
            "room": updated_room
        }

    except HTTPException:
        raise

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Số phòng đã được sử dụng hoặc dữ liệu vi phạm ràng buộc."
        )

    except Error as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()


# ==============================
# DELETE: XÓA PHÒNG
# ==============================

@router.delete("/{room_id}")
def delete_room(room_id: int, db=Depends(get_db)):
    cursor = db.cursor()

    try:
        cursor.execute("""
            SELECT id
            FROM phong
            WHERE id = %s
        """, (room_id,))

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy phòng."
            )

        cursor.execute("""
            DELETE FROM phong
            WHERE id = %s
        """, (room_id,))

        db.commit()

        return {
            "message": "Xóa phòng thành công",
            "id": room_id
        }

    except HTTPException:
        raise

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Không thể xóa phòng vì đang có booking hoặc dữ liệu liên quan."
        )

    except Error as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        cursor.close()
