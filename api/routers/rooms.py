
from fastapi import APIRouter, Depends, HTTPException
from mysql.connector import Error, IntegrityError
from api.database import get_db


router = APIRouter(
    prefix="/api/rooms",
    tags=["Rooms"]
)


from api.schemas import RoomCreate, RoomUpdate


# ==============================
# KIỂM TRA TRẠNG THÁI PHÒNG
# ==============================

# DANG_SU_DUNG là trạng thái do nghiệp vụ Booking/check-in quản lý.
# API quản trị phòng chỉ được đặt thủ công SAN_SANG hoặc BAO_TRI.
MANUAL_ROOM_STATUSES = {"SAN_SANG", "BAO_TRI"}


def validate_status(status: str):
    if status not in MANUAL_ROOM_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=(
                "Trạng thái cập nhật không hợp lệ. Chỉ chấp nhận SAN_SANG "
                "hoặc BAO_TRI. DANG_SU_DUNG được đồng bộ tự động từ Booking."
            ),
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
    """Cập nhật phòng thông qua Stored Procedure của Database.

    Không UPDATE trực tiếp bảng phong tại API. Procedure
    sp_cap_nhat_thong_tin_phong tự kiểm tra Booking đang lưu trú,
    Booking tương lai và quy tắc trạng thái phòng; procedure cũng tự
    START/COMMIT/ROLLBACK transaction nên API không mở transaction lồng.
    """
    cursor = db.cursor(dictionary=True)

    try:
        validate_status(room.trang_thai)

        # Kiểm tra phòng tồn tại để trả 404 rõ ràng trước khi gọi procedure.
        cursor.execute(
            "SELECT id FROM phong WHERE id = %s",
            (room_id,),
        )
        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy phòng.",
            )

        # Kiểm tra loại phòng tồn tại; FK trong Database vẫn là lớp bảo vệ cuối.
        cursor.execute(
            "SELECT id FROM loaiphong WHERE id = %s",
            (room.loai_phong_id,),
        )
        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Loại phòng không tồn tại.",
            )

        # Procedure tự quản lý transaction. Không gọi db.commit() bên ngoài.
        cursor.execute(
            "CALL sp_cap_nhat_thong_tin_phong(%s, %s, %s, %s)",
            (
                room_id,
                room.so_phong.strip(),
                room.loai_phong_id,
                room.trang_thai,
            ),
        )

        # Procedure có SELECT kết quả ở cuối. Đọc và giải phóng toàn bộ
        # result sets (bao gồm result set trạng thái CALL) trước truy vấn kế tiếp.
        while True:
            if cursor.with_rows:
                cursor.fetchall()
            if not cursor.nextset():
                break

        # Đọc lại dữ liệu thật sau khi Stored Procedure đã COMMIT.
        cursor.execute(
            """
            SELECT
                p.id,
                p.so_phong,
                p.loai_phong_id,
                lp.ten AS ten_loai_phong,
                p.trang_thai
            FROM phong p
            LEFT JOIN loaiphong lp ON lp.id = p.loai_phong_id
            WHERE p.id = %s
            """,
            (room_id,),
        )
        updated_room = cursor.fetchone()

        if updated_room is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy phòng sau khi cập nhật.",
            )

        return {
            "message": "Cập nhật phòng thành công thông qua sp_cap_nhat_thong_tin_phong.",
            "room": updated_room,
        }

    except HTTPException:
        raise

    except IntegrityError as exc:
        # Duplicate room number hoặc vi phạm khóa ngoại/UNIQUE.
        raise HTTPException(
            status_code=409,
            detail=(
                "Không thể cập nhật phòng vì số phòng đã được sử dụng "
                "hoặc dữ liệu vi phạm ràng buộc."
            ),
        ) from exc

    except Error as exc:
        # SIGNAL SQLSTATE '45000' từ Stored Procedure là lỗi nghiệp vụ,
        # ví dụ phòng đang có khách hoặc còn Booking hiện tại/tương lai.
        if getattr(exc, "sqlstate", None) == "45000" or getattr(exc, "errno", None) == 1644:
            raise HTTPException(
                status_code=409,
                detail=getattr(exc, "msg", None) or str(exc),
            ) from exc

        raise HTTPException(
            status_code=500,
            detail=f"Lỗi MySQL khi gọi sp_cap_nhat_thong_tin_phong: {exc}",
        ) from exc

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
