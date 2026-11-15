from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_db


router = APIRouter(
    prefix="/api/reports",
    tags=["Reports"]
)


# =====================================================
# HELPER: GỌI STORED PROCEDURE
# =====================================================

def execute_procedure(db, procedure_name, params):
    cursor = db.cursor(dictionary=True)

    try:
        cursor.callproc(procedure_name, params)

        result_sets = []

        for result_cursor in cursor.stored_results():
            try:
                rows = result_cursor.fetchall()
                result_sets.append(rows)
            finally:
                result_cursor.close()

        return result_sets

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
# 2. CHI TIẾT BOOKING THEO KHOẢNG THỜI GIAN
# =====================================================

def get_revenue_details(db, tu_ngay, den_ngay):
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                b.id AS booking_id,
                ph.so_phong,
                kh.ho_ten,
                b.ngay_nhan,
                b.ngay_tra,

                SUM(
                    CASE
                        WHEN p.status = 'THANH_CONG'
                            THEN COALESCE(h.tong_tien, p.so_tien)

                        WHEN p.status = 'HOAN_TIEN'
                            THEN -COALESCE(h.tong_tien, p.so_tien)

                        ELSE 0
                    END
                ) AS tong_tien,

                GROUP_CONCAT(
                    DISTINCT p.status
                    ORDER BY p.status
                    SEPARATOR ', '
                ) AS trang_thai

            FROM pay p

            INNER JOIN booking b
                ON p.booking_id = b.id

            INNER JOIN phong ph
                ON b.phong_id = ph.id

            INNER JOIN khach kh
                ON b.khach_id = kh.id

            LEFT JOIN hoadon h
                ON p.id = h.pay_id

            WHERE
                p.ngay_thanh_toan >= %s
                AND p.ngay_thanh_toan < DATE_ADD(%s, INTERVAL 1 DAY)

            GROUP BY
                b.id,
                ph.so_phong,
                kh.ho_ten,
                b.ngay_nhan,
                b.ngay_tra

            ORDER BY
                MAX(p.ngay_thanh_toan) DESC,
                b.id DESC
        """, (tu_ngay, den_ngay))

        return cursor.fetchall()

    finally:
        cursor.close()


# =====================================================
# 3. THỐNG KÊ DOANH THU
# =====================================================

@router.get("/revenue")
def get_revenue_statistics(
    tu_ngay: date = Query(
        ...,
        description="Ngày bắt đầu (YYYY-MM-DD)"
    ),
    den_ngay: date = Query(
        ...,
        description="Ngày kết thúc (YYYY-MM-DD)"
    ),
    db=Depends(get_db)
):
    if den_ngay < tu_ngay:
        raise HTTPException(
            status_code=400,
            detail="Ngày kết thúc phải lớn hơn hoặc bằng ngày bắt đầu"
        )

    try:
        # Lấy số liệu thống kê từ stored procedure hiện tại
        result_sets = execute_procedure(
            db,
            "sp_thong_ke_doanh_thu",
            [tu_ngay, den_ngay]
        )

        data = result_sets[0] if result_sets else []

        # Lấy danh sách booking chi tiết
        details = get_revenue_details(
            db,
            tu_ngay,
            den_ngay
        )

        return {
            "message": "Thống kê doanh thu thành công",
            "tu_ngay": tu_ngay,
            "den_ngay": den_ngay,

            # Dữ liệu tổng hợp từ stored procedure
            "total": len(data),
            "data": data,

            # Dữ liệu chi tiết cho GUI
            "total_details": len(details),
            "details": details
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Không thể thống kê doanh thu. MySQL trả về: {str(e)}"
        )