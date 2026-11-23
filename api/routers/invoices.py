import json
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from mysql.connector import Error

from api.database import get_db
from api.routers.payments import calculate_booking_totals, money
from api.schemas import InvoiceCreate
from api.peak_season_display import (
    enrich_peak_season_record,
    enrich_peak_season_records,
)

router = APIRouter(prefix="/api/invoices", tags=["Invoices"])
PAYMENT_METHODS = {"TIEN_MAT", "CHUYEN_KHOAN", "THE"}


def read_procedure_rows(cursor):
    rows = []
    for result_cursor in cursor.stored_results():
        try:
            rows.extend(result_cursor.fetchall())
        finally:
            result_cursor.close()
    return rows


def get_invoice_by_id(cursor, invoice_id: int):
    cursor.execute(
        """
        SELECT
            h.id,
            h.pay_id,
            h.tien_phong,
            h.tien_phu_phi_mua_cao_diem,
            h.tien_dich_vu,
            h.tong_tien,
            h.ngay_lap,
            py.booking_id,
            py.khach_id,
            py.ngay_thanh_toan,
            py.so_tien,
            py.tien_phong_ap_dung,
            py.tien_phu_phi_mua_cao_diem AS pay_tien_phu_phi_mua_cao_diem,
            py.ap_dung_mua_cao_diem,
            py.chi_tiet_mua_cao_diem,
            b.ap_dung_mua_cao_diem AS booking_ap_dung_mua_cao_diem,
            b.chi_tiet_mua_cao_diem AS booking_chi_tiet_mua_cao_diem,
            py.method,
            py.status AS payment_status,
            b.phong_id,
            b.ngay_nhan,
            b.ngay_tra,
            k.ho_ten,
            k.cccd,
            k.sdt,
            p.so_phong
        FROM hoadon h
        JOIN pay py ON py.id = h.pay_id
        JOIN booking b ON b.id = py.booking_id
        JOIN khach k ON k.id = b.khach_id
        JOIN phong p ON p.id = b.phong_id
        WHERE h.id = %s
        """,
        (invoice_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return None

    # Pay snapshot is preferred because it is the immutable payment-time copy.
    # For older Pay rows where this field was not populated, fall back to the
    # Booking snapshot (also persisted by the database when the booking was made).
    if not row.get("chi_tiet_mua_cao_diem"):
        row["chi_tiet_mua_cao_diem"] = row.get("booking_chi_tiet_mua_cao_diem")
    if not row.get("ap_dung_mua_cao_diem") and row.get("booking_ap_dung_mua_cao_diem"):
        row["ap_dung_mua_cao_diem"] = row["booking_ap_dung_mua_cao_diem"]
    try:
        stored_peak_fee = Decimal(str(row.get("tien_phu_phi_mua_cao_diem") or 0))
    except Exception:
        stored_peak_fee = Decimal("0")
    if stored_peak_fee > 0:
        row["ap_dung_mua_cao_diem"] = 1

    if isinstance(row.get("chi_tiet_mua_cao_diem"), str):
        try:
            row["chi_tiet_mua_cao_diem"] = json.loads(row["chi_tiet_mua_cao_diem"])
        except ValueError:
            pass
    row.pop("booking_ap_dung_mua_cao_diem", None)
    row.pop("booking_chi_tiet_mua_cao_diem", None)

    # Hóa đơn chỉ liệt kê các dịch vụ đã gắn với chính Booking này và có
    # đơn giá lớn hơn 0. Dịch vụ mặc định miễn phí vẫn được lưu trong Booking
    # nhưng không xuất hiện như một khoản phải thanh toán.
    cursor.execute(
        """
        SELECT
            id AS dichvu_id,
            ten,
            don_gia,
            so_luong,
            don_vi_tinh,
            nhom_dich_vu,
            loai_dichvu,
            ROUND(don_gia * so_luong, 2) AS thanh_tien
        FROM dichvu
        WHERE booking_id = %s
          AND don_gia > 0
        ORDER BY id
        """,
        (row["booking_id"],),
    )
    row["dich_vu_tinh_phi"] = cursor.fetchall()
    return enrich_peak_season_record(row)


def invoice_response(cursor, invoice_id: int, message: str):
    invoice = get_invoice_by_id(cursor, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=500, detail="Không tìm thấy hóa đơn vừa xử lý.")
    return {
        "message": message,
        "booking_id": invoice["booking_id"],
        "pay_id": invoice["pay_id"],
        "invoice": invoice,
        "calculation": {
            "tien_phong": invoice["tien_phong"],
            "tien_phu_phi_mua_cao_diem": invoice["tien_phu_phi_mua_cao_diem"],
            "tien_dich_vu": invoice["tien_dich_vu"],
            "tong_tien": invoice["tong_tien"],
        },
        "phuong_thuc": invoice["method"],
        "trang_thai_thanh_toan": invoice["payment_status"],
    }


@router.get("/")
def get_invoices(db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                h.id,
                h.pay_id,
                h.tien_phong,
                h.tien_phu_phi_mua_cao_diem,
                h.tien_dich_vu,
                h.tong_tien,
                h.ngay_lap,
                py.booking_id,
                py.khach_id,
                py.ngay_thanh_toan,
                py.so_tien,
                py.tien_phong_ap_dung,
                py.tien_phu_phi_mua_cao_diem AS pay_tien_phu_phi_mua_cao_diem,
                py.ap_dung_mua_cao_diem,
                py.chi_tiet_mua_cao_diem,
                b.ap_dung_mua_cao_diem AS booking_ap_dung_mua_cao_diem,
                b.chi_tiet_mua_cao_diem AS booking_chi_tiet_mua_cao_diem,
                py.method,
                py.status AS payment_status,
                b.phong_id,
                b.ngay_nhan,
                b.ngay_tra,
                k.ho_ten,
                k.cccd,
                k.sdt,
                p.so_phong
            FROM hoadon h
            JOIN pay py ON py.id = h.pay_id
            JOIN booking b ON b.id = py.booking_id
            JOIN khach k ON k.id = b.khach_id
            JOIN phong p ON p.id = b.phong_id
            ORDER BY h.id DESC
            """
        )
        invoices = cursor.fetchall()
        for invoice in invoices:
            if not invoice.get("chi_tiet_mua_cao_diem"):
                invoice["chi_tiet_mua_cao_diem"] = invoice.get("booking_chi_tiet_mua_cao_diem")
            if not invoice.get("ap_dung_mua_cao_diem") and invoice.get("booking_ap_dung_mua_cao_diem"):
                invoice["ap_dung_mua_cao_diem"] = invoice["booking_ap_dung_mua_cao_diem"]
            try:
                if Decimal(str(invoice.get("tien_phu_phi_mua_cao_diem") or 0)) > 0:
                    invoice["ap_dung_mua_cao_diem"] = 1
            except Exception:
                pass
            invoice.pop("booking_ap_dung_mua_cao_diem", None)
            invoice.pop("booking_chi_tiet_mua_cao_diem", None)
        enrich_peak_season_records(invoices)
        return {"message": "Lấy danh sách hóa đơn thành công", "total": len(invoices), "invoices": invoices}
    except Error as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        cursor.close()


@router.get("/eligible-bookings")
def get_bookings_eligible_for_invoice(db=Depends(get_db)):
    """Danh sách Booking chưa bị hủy và chưa có hóa đơn.

    Booking có thể ở trạng thái CHO_XAC_NHAN, DA_XAC_NHAN, DANG_O
    hoặc HOAN_THANH; procedure lập hóa đơn sẽ kiểm tra điều kiện nghiệp vụ
    cuối cùng trước khi ghi Pay và HoaDon.
    """
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                b.id,
                b.phong_id,
                p.so_phong,
                b.khach_id,
                k.ho_ten,
                b.ngay_nhan,
                b.ngay_tra,
                b.trang_thai
            FROM booking b
            JOIN phong p ON p.id = b.phong_id
            JOIN khach k ON k.id = b.khach_id
            WHERE b.trang_thai <> 'DA_HUY'
              AND NOT EXISTS (
                  SELECT 1
                  FROM pay py
                  JOIN hoadon hd ON hd.pay_id = py.id
                  WHERE py.booking_id = b.id
              )
            ORDER BY b.id DESC
            """
        )
        bookings = cursor.fetchall()
        return {
            "message": "Lấy danh sách Booking đủ điều kiện lập hóa đơn thành công",
            "total": len(bookings),
            "bookings": bookings,
        }
    except Error as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        cursor.close()


@router.get("/{invoice_id}")
def get_invoice(invoice_id: int, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    try:
        invoice = get_invoice_by_id(cursor, invoice_id)
        if invoice is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy hóa đơn.")
        return {"message": "Lấy thông tin hóa đơn thành công", "invoice": invoice}
    except HTTPException:
        raise
    except Error as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        cursor.close()


@router.post("/", status_code=201)
def create_invoice(data: InvoiceCreate, db=Depends(get_db)):
    if data.method not in PAYMENT_METHODS:
        raise HTTPException(
            status_code=422,
            detail=f"Phương thức thanh toán hợp lệ: {sorted(PAYMENT_METHODS)}",
        )

    cursor = db.cursor(dictionary=True)
    transaction_started = False
    try:
        # Khóa Booking để tránh hai yêu cầu cùng lúc lập hai giao dịch/hóa đơn.
        db.start_transaction()
        transaction_started = True
        cursor.execute(
            "SELECT id, trang_thai FROM booking WHERE id = %s FOR UPDATE",
            (data.booking_id,),
        )
        booking = cursor.fetchone()
        if booking is None:
            raise HTTPException(status_code=404, detail="Booking không tồn tại.")
        if booking["trang_thai"] == "DA_HUY":
            raise HTTPException(status_code=409, detail="Không thể lập hóa đơn cho Booking đã hủy.")

        # Lặp lại yêu cầu sau khi đã thanh toán thành công: trả hóa đơn hiện tại,
        # không tạo thêm Pay/HoaDon.
        cursor.execute(
            """
            SELECT h.id
            FROM pay py
            JOIN hoadon h ON h.pay_id = py.id
            WHERE py.booking_id = %s
              AND py.status = 'THANH_CONG'
            ORDER BY py.id DESC
            LIMIT 1
            """,
            (data.booking_id,),
        )
        successful_invoice = cursor.fetchone()
        if successful_invoice:
            db.commit()
            transaction_started = False
            return invoice_response(
                cursor,
                successful_invoice["id"],
                "Booking đã thanh toán; trả về hóa đơn hiện có.",
            )

        cursor.execute(
            """
            SELECT id, so_tien, method
            FROM pay
            WHERE booking_id = %s
              AND status = 'CHO_THANH_TOAN'
            ORDER BY id DESC
            FOR UPDATE
            """,
            (data.booking_id,),
        )
        pending_payments = cursor.fetchall()

        if len(pending_payments) > 1:
            raise HTTPException(
                status_code=409,
                detail="Booking có nhiều giao dịch đang chờ. Cần xử lý dữ liệu thanh toán trước.",
            )

        if pending_payments:
            pending = pending_payments[0]
            if pending["method"] != data.method:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Giao dịch Pay {pending['id']} đã dùng phương thức "
                        f"{pending['method']}; không thể lập hóa đơn với phương thức {data.method}."
                    ),
                )

            cursor.execute(
                "SELECT id FROM hoadon WHERE pay_id = %s",
                (pending["id"],),
            )
            existing_invoice = cursor.fetchone()
            if existing_invoice:
                db.commit()
                transaction_started = False
                return invoice_response(
                    cursor,
                    existing_invoice["id"],
                    "Hóa đơn cho giao dịch đang chờ đã tồn tại.",
                )

            totals = calculate_booking_totals(cursor, data.booking_id)
            if money(pending["so_tien"]) != totals["tong_tien"]:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Số tiền Pay không khớp với tổng tiền tính từ Booking. "
                        f"Tổng đúng hiện tại: {totals['tong_tien']} VNĐ."
                    ),
                )

            cursor.execute(
                """
                INSERT INTO hoadon (
                    pay_id, tien_phong, tien_phu_phi_mua_cao_diem,
                    tien_dich_vu, tong_tien
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    pending["id"],
                    totals["tien_phong"],
                    totals["tien_phu_phi_mua_cao_diem"],
                    totals["tien_dich_vu"],
                    totals["tong_tien"],
                ),
            )
            invoice_id = cursor.lastrowid
            db.commit()
            transaction_started = False
            return invoice_response(
                cursor,
                invoice_id,
                "Lập hóa đơn thành công cho giao dịch Pay đang chờ.",
            )

        # Không có Pay đang chờ: nhả transaction của API rồi gọi procedure.
        # sp_tinh_tien_va_tao_hoa_don tự START TRANSACTION/COMMIT trong MySQL.
        db.rollback()
        transaction_started = False
        cursor.callproc(
            "sp_tinh_tien_va_tao_hoa_don",
            [data.booking_id, data.method],
        )
        procedure_rows = read_procedure_rows(cursor)
        procedure_result = procedure_rows[0] if procedure_rows else {}
        pay_id = (
            procedure_result.get("pay_id")
            if isinstance(procedure_result, dict)
            else None
        )

        if not pay_id:
            cursor.execute(
                """
                SELECT id
                FROM pay
                WHERE booking_id = %s
                ORDER BY id DESC
                LIMIT 1
                """,
                (data.booking_id,),
            )
            payment_row = cursor.fetchone()
            pay_id = payment_row["id"] if payment_row else None

        if not pay_id:
            raise HTTPException(
                status_code=500,
                detail="Stored Procedure không trả về Pay ID và không tìm thấy giao dịch mới.",
            )

        cursor.execute("SELECT id FROM hoadon WHERE pay_id = %s", (pay_id,))
        invoice_row = cursor.fetchone()
        if invoice_row is None:
            raise HTTPException(
                status_code=500,
                detail="Procedure đã tạo giao dịch nhưng không tìm thấy hóa đơn.",
            )

        return invoice_response(
            cursor,
            invoice_row["id"],
            "Tính tiền và tạo Pay/HoaDon thành công bằng Stored Procedure.",
        )

    except HTTPException:
        if transaction_started:
            db.rollback()
        raise
    except Error as exc:
        if transaction_started:
            db.rollback()
        raise HTTPException(status_code=409, detail=f"MySQL từ chối lập hóa đơn: {exc}") from exc
    except Exception as exc:
        if transaction_started:
            db.rollback()
        raise HTTPException(status_code=500, detail=f"Không thể lập hóa đơn: {exc}") from exc
    finally:
        cursor.close()


@router.put("/{invoice_id}")
def update_invoice(invoice_id: int):
    raise HTTPException(
        status_code=409,
        detail="Không cho phép sửa trực tiếp hóa đơn. Hóa đơn là chứng từ tài chính được kiểm soát bởi Database.",
    )


@router.delete("/{invoice_id}")
def delete_invoice(invoice_id: int):
    raise HTTPException(
        status_code=409,
        detail="Không cho phép xóa trực tiếp hóa đơn. Cần xử lý theo quy trình điều chỉnh/hủy riêng.",
    )
