
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from database import Error, IntegrityError
from api.database import get_db


router = APIRouter(
    prefix="/api/room-types",
    tags=["Room Types"]
)


from api.schemas import RoomTypeCreate, RoomTypeUpdate


class DefaultRoomTypeService(BaseModel):
    """Một dịch vụ mặc định áp dụng đồng nhất cho các phòng cùng loại."""

    ten: str = Field(min_length=1, max_length=100)
    don_gia: Decimal = Field(ge=0)
    so_luong: int = Field(gt=0)


class RoomTypeDefaultServicesUpdate(BaseModel):
    # Mảng rỗng có nghĩa là Admin chủ động bỏ toàn bộ dịch vụ mặc định.
    services: list[DefaultRoomTypeService] = Field(default_factory=list, max_length=50)


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
# DỊCH VỤ MẶC ĐỊNH THEO LOẠI PHÒNG
# ==============================

@router.get("/{room_type_id}/default-services")
def get_room_type_default_services(
    room_type_id: int,
    db=Depends(get_db),
):
    """Đọc cấu hình dịch vụ mặc định đang được áp dụng trên các phòng cùng loại.

    HOTEL ERD hiện lưu dịch vụ mặc định trong dichvu với booking_id IS NULL
    và phong_id NOT NULL. Để không thêm bảng và không thay đổi ERD, cấu hình
    theo loại phòng được đồng bộ thành cùng một bộ dòng dichvu trên tất cả
    phòng thuộc loại đó. Các dòng dịch vụ đã gắn Booking không bị đụng đến.
    """
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT id, ten FROM loaiphong WHERE id = %s",
            (room_type_id,),
        )
        room_type = cursor.fetchone()
        if room_type is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy loại phòng.")

        cursor.execute(
            "SELECT COUNT(*) AS room_count FROM phong WHERE loai_phong_id = %s",
            (room_type_id,),
        )
        room_count = int((cursor.fetchone() or {}).get("room_count") or 0)

        cursor.execute(
            """
            SELECT
                d.ten,
                d.don_gia,
                MIN(d.so_luong) AS so_luong_min,
                MAX(d.so_luong) AS so_luong_max,
                COUNT(DISTINCT d.phong_id) AS so_phong_ap_dung
            FROM dichvu AS d
            INNER JOIN phong AS p ON p.id = d.phong_id
            WHERE p.loai_phong_id = %s
              AND d.booking_id IS NULL
              AND d.loai_dichvu = 'MAC_DINH'
              AND d.dang_hoat_dong = 1
            GROUP BY d.ten, d.don_gia
            ORDER BY d.ten, d.don_gia
            """,
            (room_type_id,),
        )
        services = cursor.fetchall()
        for item in services:
            item["so_luong_min"] = int(item["so_luong_min"] or 0)
            item["so_luong_max"] = int(item["so_luong_max"] or 0)
            item["so_phong_ap_dung"] = int(item["so_phong_ap_dung"] or 0)
            item["so_luong"] = item["so_luong_min"] or 1
            item["is_consistent"] = item["so_luong_min"] == item["so_luong_max"]

        return {
            "room_type": room_type,
            "room_count": room_count,
            "services": services,
            "is_consistent": all(item["is_consistent"] for item in services)
                and all(item["so_phong_ap_dung"] == room_count for item in services),
        }
    except HTTPException:
        raise
    except Error as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Không tải được dịch vụ mặc định của loại phòng: {exc}",
        ) from exc
    finally:
        cursor.close()


@router.put("/{room_type_id}/default-services")
def update_room_type_default_services(
    room_type_id: int,
    payload: RoomTypeDefaultServicesUpdate,
    db=Depends(get_db),
):
    """Thay thế đồng bộ dịch vụ mặc định trên mọi phòng thuộc một loại phòng.

    Chỉ xóa dichvu.booking_id IS NULL. Dịch vụ đã được sao chép vào Booking
    (booking_id IS NOT NULL) là snapshot lịch sử và luôn được giữ nguyên.
    """
    normalized_services = []
    seen = set()
    for item in payload.services:
        name = item.ten.strip()
        if not name:
            raise HTTPException(status_code=422, detail="Tên dịch vụ không được để trống.")
        if item.don_gia.as_tuple().exponent < -2:
            raise HTTPException(
                status_code=422,
                detail=f"Đơn giá dịch vụ '{name}' chỉ được có tối đa 2 chữ số thập phân.",
            )
        if item.don_gia != 0:
            raise HTTPException(
                status_code=422,
                detail=f"Dịch vụ mặc định '{name}' phải miễn phí (đơn giá bằng 0). Dịch vụ tính phí được quản lý trong Danh mục dịch vụ.",
            )
        key = name.casefold()
        if key in seen:
            raise HTTPException(
                status_code=422,
                detail=f"Dịch vụ '{name}' đang bị khai báo trùng trong cùng loại phòng.",
            )
        seen.add(key)
        normalized_services.append((name, item.don_gia, item.so_luong))

    cursor = db.cursor(dictionary=True)
    try:
        # Khóa loại phòng và danh sách phòng để tránh cấu hình một phần khi
        # có thao tác thêm/chuyển phòng đồng thời.
        cursor.execute(
            "SELECT id, ten FROM loaiphong WHERE id = %s FOR UPDATE",
            (room_type_id,),
        )
        room_type = cursor.fetchone()
        if room_type is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy loại phòng.")

        cursor.execute(
            "SELECT id FROM phong WHERE loai_phong_id = %s ORDER BY id FOR UPDATE",
            (room_type_id,),
        )
        room_ids = [int(row["id"]) for row in cursor.fetchall()]
        if not room_ids:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Loại phòng này chưa có phòng thực tế. Hãy tạo ít nhất một phòng "
                    "thuộc loại này trước khi cấu hình dịch vụ mặc định."
                ),
            )

        # Chỉ thay các dòng dịch vụ mẫu của phòng. Lịch sử Booking và hóa đơn
        # dùng các dòng booking_id IS NOT NULL nên không bị xóa/sửa.
        cursor.execute(
            """
            DELETE d
            FROM dichvu AS d
            INNER JOIN phong AS p ON p.id = d.phong_id
            WHERE p.loai_phong_id = %s
              AND d.booking_id IS NULL
              AND d.loai_dichvu = 'MAC_DINH'
            """,
            (room_type_id,),
        )

        if normalized_services:
            rows = [
                (name, price, quantity, room_id)
                for room_id in room_ids
                for name, price, quantity in normalized_services
            ]
            cursor.executemany(
                """
                INSERT INTO dichvu
                    (ten, don_gia, so_luong, phong_id, booking_id, loai_dichvu,
                     nhom_dich_vu, don_vi_tinh, dang_hoat_dong)
                VALUES (%s, %s, %s, %s, NULL, 'MAC_DINH', 'DO_DUNG', 'phần', 1)
                """,
                rows,
            )

        db.commit()
        return {
            "success": True,
            "message": (
                f"Đã đồng bộ {len(normalized_services)} dịch vụ mặc định "
                f"cho {len(room_ids)} phòng thuộc loại {room_type['ten']}."
            ),
            "room_type_id": room_type_id,
            "room_count": len(room_ids),
            "service_count": len(normalized_services),
            "assignment_count": len(room_ids) * len(normalized_services),
        }
    except HTTPException:
        db.rollback()
        raise
    except Error as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Không thể đồng bộ dịch vụ mặc định: {exc}",
        ) from exc
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
