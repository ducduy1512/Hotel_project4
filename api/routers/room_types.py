
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from mysql.connector import Error, IntegrityError
from api.database import get_db


router = APIRouter(
    prefix="/api/room-types",
    tags=["Room Types"]
)


# ==============================
# SCHEMAS
# ==============================

class RoomTypeCreate(BaseModel):
    ten: str = Field(min_length=1, max_length=100)
    gia_co_ban: float = Field(gt=0)
    suc_chua: int = Field(gt=0)


class RoomTypeUpdate(BaseModel):
    ten: str = Field(min_length=1, max_length=100)
    gia_co_ban: float = Field(gt=0)
    suc_chua: int = Field(gt=0)


# ==============================
# GET: LẤY DANH SÁCH LOẠI PHÒNG
# ==============================

@router.get("/")
def get_room_types(db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT id, ten, gia_co_ban, suc_chua
            FROM loaiphong
            ORDER BY id
        """)

        return cursor.fetchall()

    except Error as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cursor.close()


# ==============================
# GET: LẤY CHI TIẾT LOẠI PHÒNG
# ==============================

@router.get("/{room_type_id}")
def get_room_type(
    room_type_id: int,
    db=Depends(get_db)
):
    cursor = db.cursor(dictionary=True)

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
                detail="Không tìm thấy loại phòng"
            )

        return room_type

    except HTTPException:
        raise

    except Error as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cursor.close()


# ==============================
# POST: THÊM LOẠI PHÒNG
# ==============================

@router.post("/", status_code=201)
def create_room_type(
    room_type: RoomTypeCreate,
    db=Depends(get_db)
):
    cursor = db.cursor()

    try:
        cursor.execute("""
            INSERT INTO loaiphong (
                ten,
                gia_co_ban,
                suc_chua
            )
            VALUES (%s, %s, %s)
        """, (
            room_type.ten.strip(),
            room_type.gia_co_ban,
            room_type.suc_chua
        ))

        # Lấy ID tự tăng của bản ghi vừa thêm
        new_id = cursor.lastrowid

        db.commit()

        # Trả ID trực tiếp trong Response
        return {
            "message": "Thêm loại phòng thành công",
            "id": new_id,
            "ten": room_type.ten.strip(),
            "gia_co_ban": room_type.gia_co_ban,
            "suc_chua": room_type.suc_chua
        }

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Tên loại phòng đã tồn tại."
        )

    except Error as e:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cursor.close()


# ==============================
# PUT: CẬP NHẬT LOẠI PHÒNG
# ==============================

@router.put("/{room_type_id}")
def update_room_type(
    room_type_id: int,
    room_type: RoomTypeUpdate,
    db=Depends(get_db)
):
    cursor = db.cursor(dictionary=True)

    try:
        # Kiểm tra loại phòng có tồn tại không
        cursor.execute("""
            SELECT id
            FROM loaiphong
            WHERE id = %s
        """, (room_type_id,))

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy loại phòng"
            )

        # Cập nhật thông tin
        cursor.execute("""
            UPDATE loaiphong
            SET ten = %s,
                gia_co_ban = %s,
                suc_chua = %s
            WHERE id = %s
        """, (
            room_type.ten.strip(),
            room_type.gia_co_ban,
            room_type.suc_chua,
            room_type_id
        ))

        db.commit()

        # Lấy dữ liệu sau khi cập nhật
        cursor.execute("""
            SELECT id, ten, gia_co_ban, suc_chua
            FROM loaiphong
            WHERE id = %s
        """, (room_type_id,))

        updated_room_type = cursor.fetchone()

        return {
            "message": "Cập nhật loại phòng thành công",
            "room_type": updated_room_type
        }

    except HTTPException:
        raise

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Tên loại phòng đã được sử dụng."
        )

    except Error as e:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cursor.close()


# ==============================
# DELETE: XÓA LOẠI PHÒNG
# ==============================

@router.delete("/{room_type_id}")
def delete_room_type(
    room_type_id: int,
    db=Depends(get_db)
):
    cursor = db.cursor()

    try:
        # Kiểm tra loại phòng có tồn tại không
        cursor.execute("""
            SELECT id
            FROM loaiphong
            WHERE id = %s
        """, (room_type_id,))

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy loại phòng"
            )

        # Xóa loại phòng
        cursor.execute("""
            DELETE FROM loaiphong
            WHERE id = %s
        """, (room_type_id,))

        db.commit()

        return {
            "message": "Xóa loại phòng thành công",
            "id": room_type_id
        }

    except HTTPException:
        raise

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Không thể xóa loại phòng vì đang có phòng sử dụng loại này."
        )

    except Error as e:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cursor.close()
