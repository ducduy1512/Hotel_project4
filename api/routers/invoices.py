
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.database import get_db


router = APIRouter(
    prefix="/api/invoices",
    tags=["Invoices"]
)


# =========================
# SCHEMAS
# =========================

class InvoiceCreate(BaseModel):
    booking_id: int = Field(..., gt=0)
    method: str


# =========================
# CONSTANTS
# =========================

PAYMENT_METHODS = [
    "TIEN_MAT",
    "CHUYEN_KHOAN",
    "THE"
]


# =========================
# HELPER
# =========================

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
            b.ngay_tra
        FROM hoadon h
        JOIN pay p ON h.pay_id = p.id
        JOIN booking b ON p.booking_id = b.id
        WHERE h.id = %s
    """, (invoice_id,))

    return cursor.fetchone()


# =========================
# GET ALL INVOICES
# =========================

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
                b.ngay_tra
            FROM hoadon h
            JOIN pay p ON h.pay_id = p.id
            JOIN booking b ON p.booking_id = b.id
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


# =========================
# GET INVOICE BY ID
# =========================

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


# =========================
# CREATE INVOICE
# CALL STORED PROCEDURE
# =========================

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

        # Kiểm tra booking tồn tại trước khi gọi procedure
        cursor.execute(
            "SELECT id FROM booking WHERE id = %s",
            (data.booking_id,)
        )

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Booking không tồn tại."
            )

        # Gọi procedure:
        # IN p_booking_id INT
        # IN p_method VARCHAR(30)
        cursor.callproc(
            "sp_tinh_tien_va_tao_hoa_don",
            [
                data.booking_id,
                data.method
            ]
        )

        # Lấy kết quả SELECT cuối cùng từ procedure
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
                    "Procedure đã chạy nhưng không trả về kết quả. "
                    "Hãy kiểm tra lại stored procedure trong MySQL."
                )
            )

        # Lấy hóa đơn vừa được procedure tạo
        pay_id = procedure_result["pay_id"]

        cursor.execute("""
            SELECT
                h.id AS invoice_id,
                h.pay_id,
                h.tien_phong,
                h.tien_dich_vu,
                h.tong_tien,
                h.ngay_lap,
                p.booking_id,
                p.ngay_thanh_toan,
                p.method,
                p.status AS payment_status
            FROM hoadon h
            JOIN pay p ON h.pay_id = p.id
            WHERE h.pay_id = %s
        """, (pay_id,))

        invoice = cursor.fetchone()

        if invoice is None:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Procedure đã tạo thanh toán nhưng không tìm thấy "
                    "hóa đơn tương ứng."
                )
            )

        return {
            "message": "Tính tiền và tạo hóa đơn thành công",
            "booking_id": procedure_result["booking_id"],
            "pay_id": procedure_result["pay_id"],
            "invoice": invoice,
            "calculation": {
                "tien_phong": procedure_result["tien_phong"],
                "tien_dich_vu": procedure_result["tien_dich_vu"],
                "tong_tien": procedure_result["tong_tien"]
            },
            "phuong_thuc": procedure_result["phuong_thuc"],
            "trang_thai_thanh_toan": (
                procedure_result["trang_thai_thanh_toan"]
            )
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=409,
            detail=(
                "Không thể tính tiền hoặc tạo hóa đơn. "
                f"MySQL trả về: {str(e)}"
            )
        )

    finally:
        cursor.close()


# =========================
# UPDATE INVOICE
# PROTECT FINANCIAL DATA
# =========================

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


# =========================
# DELETE INVOICE
# PROTECT FINANCIAL DATA
# =========================

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
