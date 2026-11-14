
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_db


router = APIRouter(
    prefix="/api/reports",
    tags=["Reports"]
)


# Hàm dùng chung để gọi stored procedure
def execute_procedure(db, procedure_name, params):
    cursor = db.cursor(dictionary=True)

    try:
        cursor.callproc(procedure_name, params)

        result_sets = []

        # Đọc toàn bộ kết quả trả về từ procedure
        for result_cursor in cursor.stored_results():
            rows = result_cursor.fetchall()
            result_sets.append(rows)
            result_cursor.close()

        return result_sets

    except Exception as e:
        raise e

    finally:
        cursor.close()


# =====================================================
# 1. LỊCH SỬ BOOKING THEO KHÁCH HÀNG
# =====================================================

@router.get("/booking-history/{khach_id}")
def get_booking_history(
    khach_id: int,
    db=Depends(get_db)
):
    if khach_id <= 0:
        raise HTTPException(
            status_code=400,
            detail="ID khách hàng phải lớn hơn 0"
        )

    try:
        result_sets = execute_procedure(
            db,
            "sp_lich_su_booking",
            [khach_id]
        )

        data = result_sets[0] if result_sets else []

        return {
            "message": "Lấy lịch sử booking thành công",
            "khach_id": khach_id,
            "total": len(data),
            "data": data
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Không thể lấy lịch sử booking. MySQL trả về: {str(e)}"
        )


# =====================================================
# 2. THỐNG KÊ DOANH THU THEO KHOẢNG THỜI GIAN
# =====================================================

@router.get("/revenue")
def get_revenue_statistics(
    tu_ngay: date = Query(..., description="Ngày bắt đầu (YYYY-MM-DD)"),
    den_ngay: date = Query(..., description="Ngày kết thúc (YYYY-MM-DD)"),
    db=Depends(get_db)
):
    if den_ngay < tu_ngay:
        raise HTTPException(
            status_code=400,
            detail="Ngày kết thúc phải lớn hơn hoặc bằng ngày bắt đầu"
        )

    try:
        result_sets = execute_procedure(
            db,
            "sp_thong_ke_doanh_thu",
            [tu_ngay, den_ngay]
        )

        data = result_sets[0] if result_sets else []

        return {
            "message": "Thống kê doanh thu thành công",
            "tu_ngay": tu_ngay,
            "den_ngay": den_ngay,
            "total": len(data),
            "data": data
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Không thể thống kê doanh thu. MySQL trả về: {str(e)}"
        )
