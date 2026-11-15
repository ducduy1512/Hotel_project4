
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.database import get_db


router = APIRouter(
    prefix="/api/invoices",
    tags=["Invoices"]
)


from api.schemas import InvoiceCreate


PAYMENT_METHODS = [
    "TIEN_MAT",
    "CHUYEN_KHOAN",
    "THE"
]


# =====================================================
# HELPER: LẤY HÓA ĐƠN THEO ID
# =====================================================

def get_invoice_by_id(cursor, invoice_id: int):
    cursor.execute("""
        SELECT
            h.id,
            h.pay_id,
            h.tien_phong,
            h.tien_dich_vu,
            h.tong_tien,
            h.ngay_lap,

            p.booking_id,
            p.ngay_thanh_toan,
            p.so_tien,
            p.method,
            p.status AS payment_status,

            b.phong_id,
            b.khach_id,
            b.ngay_nhan,
            b.ngay_tra,

            k.ho_ten,
            k.cccd,
            k.sdt,

            ph.so_phong

        FROM hoadon h
        JOIN pay p ON h.pay_id = p.id
        JOIN booking b ON p.booking_id = b.id
        JOIN khach k ON b.khach_id = k.id
        JOIN phong ph ON b.phong_id = ph.id

        WHERE h.id = %s
    """, (invoice_id,))

    return cursor.fetchone()


# =====================================================
# GET ALL INVOICES
# =====================================================

@router.get("/")
def get_invoices(db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                h.id,
                h.pay_id,
                h.tien_phong,
                h.tien_dich_vu,
                h.tong_tien,
                h.ngay_lap,

                p.booking_id,
                p.ngay_thanh_toan,
                p.so_tien,
                p.method,
                p.status AS payment_status,

                b.phong_id,
                b.khach_id,
                b.ngay_nhan,
                b.ngay_tra,

                k.ho_ten,
                k.cccd,
                k.sdt,

                ph.so_phong

            FROM hoadon h
            JOIN pay p ON h.pay_id = p.id
            JOIN booking b ON p.booking_id = b.id
            JOIN khach k ON b.khach_id = k.id
            JOIN phong ph ON b.phong_id = ph.id

            ORDER BY h.id DESC
        """)

        invoices = cursor.fetchall()

        return {
            "message": "Lấy danh sách hóa đơn thành công",
            "total": len(invoices),
            "invoices": invoices
        }

    finally:
        cursor.close()


# =====================================================
# GET INVOICE BY ID
# =====================================================

@router.get("/{invoice_id}")
def get_invoice(invoice_id: int, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)

    try:
        invoice = get_invoice_by_id(cursor, invoice_id)

        if invoice is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy hóa đơn."
            )

        return {
            "message": "Lấy thông tin hóa đơn thành công",
            "invoice": invoice
        }

    finally:
        cursor.close()


# =====================================================
# CREATE INVOICE
# =====================================================

@router.post("/", status_code=201)
def create_invoice(data: InvoiceCreate, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)

    try:
        if data.method not in PAYMENT_METHODS:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Phương thức thanh toán không hợp lệ. "
                    f"Các giá trị hợp lệ: {PAYMENT_METHODS}"
                )
            )

        cursor.execute(
            "SELECT id FROM booking WHERE id = %s",
            (data.booking_id,)
        )

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Booking không tồn tại."
            )

        cursor.callproc(
            "sp_tinh_tien_va_tao_hoa_don",
            [
                data.booking_id,
                data.method
            ]
        )

        procedure_result = None

        for result_cursor in cursor.stored_results():
            rows = result_cursor.fetchall()

            if rows:
                procedure_result = rows[0]

            result_cursor.close()

        if procedure_result is None:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Procedure không trả về kết quả. "
                    "Hãy kiểm tra stored procedure trong MySQL."
                )
            )

        pay_id = procedure_result["pay_id"]

        invoice = get_invoice_by_id(
            cursor,
            procedure_result.get("invoice_id", 0)
        ) if procedure_result.get("invoice_id") else None

        if invoice is None:
            cursor.execute("""
                SELECT id
                FROM hoadon
                WHERE pay_id = %s
            """, (pay_id,))

            invoice_row = cursor.fetchone()

            if invoice_row:
                invoice = get_invoice_by_id(
                    cursor,
                    invoice_row["id"]
                )

        if invoice is None:
            raise HTTPException(
                status_code=500,
                detail="Không tìm thấy hóa đơn vừa được tạo."
            )

        return {
            "message": "Tính tiền và tạo hóa đơn thành công",
            "booking_id": procedure_result["booking_id"],
            "pay_id": pay_id,
            "invoice": invoice,
            "calculation": {
                "tien_phong": procedure_result["tien_phong"],
                "tien_dich_vu": procedure_result["tien_dich_vu"],
                "tong_tien": procedure_result["tong_tien"]
            },
            "phuong_thuc": procedure_result.get("phuong_thuc"),
            "trang_thai_thanh_toan": procedure_result.get(
                "trang_thai_thanh_toan"
            )
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail=(
                "Không thể tính tiền hoặc tạo hóa đơn. "
                f"MySQL trả về: {str(e)}"
            )
        )

    finally:
        cursor.close()


# =====================================================
# PROTECT FINANCIAL DATA
# =====================================================

@router.put("/{invoice_id}")
def update_invoice(invoice_id: int):
    raise HTTPException(
        status_code=409,
        detail=(
            "Không cho phép sửa trực tiếp hóa đơn. "
            "Hóa đơn được tạo tự động bởi "
            "sp_tinh_tien_va_tao_hoa_don."
        )
    )


@router.delete("/{invoice_id}")
def delete_invoice(invoice_id: int):
    raise HTTPException(
        status_code=409,
        detail=(
            "Không cho phép xóa trực tiếp hóa đơn. "
            "Hóa đơn liên kết với khoản thanh toán. "
            "Hãy sử dụng nghiệp vụ điều chỉnh hoặc hủy riêng."
        )
    )
