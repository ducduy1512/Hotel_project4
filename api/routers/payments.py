from datetime import timedelta
import json
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from mysql.connector import Error

from api.database import get_db
from api.schemas import PaymentCreate, PaymentUpdate
from api.peak_season_display import (
    enrich_peak_season_record,
    enrich_peak_season_records,
)

router = APIRouter(prefix="/api/payments", tags=["Payments"])

PAYMENT_METHODS = {"TIEN_MAT", "CHUYEN_KHOAN", "THE"}
PAYMENT_STATUSES = {"CHO_THANH_TOAN", "THANH_CONG", "THAT_BAI", "HOAN_TIEN"}
CENT = Decimal("0.01")


def money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(CENT)


def get_payment_by_id(cursor, payment_id: int):
    cursor.execute(
        """
        SELECT
            py.id,
            py.booking_id,
            py.khach_id,
            py.ngay_thanh_toan,
            py.so_tien,
            py.method,
            py.status,
            py.tien_phong_ap_dung,
            py.tien_phu_phi_mua_cao_diem,
            py.ap_dung_mua_cao_diem,
            py.chi_tiet_mua_cao_diem,
            b.tien_phong_du_kien,
            GREATEST(
                COALESCE(py.so_tien, 0)
                - COALESCE(py.tien_phong_ap_dung, 0)
                - COALESCE(py.tien_phu_phi_mua_cao_diem, 0),
                0
            ) AS tien_dich_vu,
            b.ap_dung_mua_cao_diem AS booking_ap_dung_mua_cao_diem,
            b.phong_id,
            p.so_phong,
            b.ngay_nhan,
            b.ngay_tra,
            b.trang_thai AS booking_trang_thai
        FROM pay py
        JOIN booking b ON b.id = py.booking_id
        JOIN phong p ON p.id = b.phong_id
        WHERE py.id = %s
        """,
        (payment_id,),
    )
    row = cursor.fetchone()
    if row and isinstance(row.get("chi_tiet_mua_cao_diem"), str):
        try:
            row["chi_tiet_mua_cao_diem"] = json.loads(row["chi_tiet_mua_cao_diem"])
        except ValueError:
            pass
    return enrich_peak_season_record(row)


def calculate_booking_totals(cursor, booking_id: int):
    """Tính tiền theo đúng quy tắc của Database: từng đêm + dịch vụ Booking."""
    cursor.execute(
        """
        SELECT
            b.id,
            b.phong_id,
            b.ngay_nhan,
            b.ngay_tra,
            b.trang_thai,
            b.tien_phong_du_kien,
            b.tien_phu_phi_mua_cao_diem,
            b.ap_dung_mua_cao_diem,
            b.chi_tiet_mua_cao_diem
        FROM booking b
        WHERE b.id = %s
        """,
        (booking_id,),
    )
    booking = cursor.fetchone()
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking không tồn tại.")
    if booking["trang_thai"] == "DA_HUY":
        raise HTTPException(status_code=409, detail="Booking đã hủy, không thể thanh toán.")

    room_total = money(booking["tien_phong_du_kien"])
    peak_surcharge = money(booking.get("tien_phu_phi_mua_cao_diem", 0))

    cursor.execute(
        """
        SELECT COALESCE(SUM(don_gia * so_luong), 0) AS tien_dich_vu
        FROM dichvu
        WHERE booking_id = %s
        """,
        (booking_id,),
    )
    service_row = cursor.fetchone()
    service_total = money(service_row["tien_dich_vu"] if service_row else 0)

    peak_detail = booking.get("chi_tiet_mua_cao_diem")
    if isinstance(peak_detail, str):
        try:
            peak_detail = json.loads(peak_detail)
        except ValueError:
            pass
    return {
        "tien_phong": room_total.quantize(CENT),
        "tien_phu_phi_mua_cao_diem": peak_surcharge.quantize(CENT),
        "ap_dung_mua_cao_diem": bool(booking.get("ap_dung_mua_cao_diem")),
        "chi_tiet_mua_cao_diem": peak_detail,
        "tien_dich_vu": service_total,
        "tong_tien": (room_total + peak_surcharge + service_total).quantize(CENT),
    }


def validate_payment_method(method: str) -> None:
    if method not in PAYMENT_METHODS:
        raise HTTPException(
            status_code=422,
            detail=f"Phương thức thanh toán hợp lệ: {sorted(PAYMENT_METHODS)}",
        )


def validate_payment_status(status: str) -> None:
    if status not in PAYMENT_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Trạng thái thanh toán hợp lệ: {sorted(PAYMENT_STATUSES)}",
        )


@router.get("/")
def get_payments(db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT
                py.id,
                py.booking_id,
                py.khach_id,
                py.ngay_thanh_toan,
                py.so_tien,
                py.method,
                py.status,
                py.tien_phong_ap_dung,
                py.tien_phu_phi_mua_cao_diem,
                py.ap_dung_mua_cao_diem,
                py.chi_tiet_mua_cao_diem,
                b.tien_phong_du_kien,
                GREATEST(
                COALESCE(py.so_tien, 0)
                - COALESCE(py.tien_phong_ap_dung, 0)
                - COALESCE(py.tien_phu_phi_mua_cao_diem, 0),
                0
            ) AS tien_dich_vu,
                b.ap_dung_mua_cao_diem AS booking_ap_dung_mua_cao_diem,
                b.phong_id,
                p.so_phong,
                b.ngay_nhan,
                b.ngay_tra,
                b.trang_thai AS booking_trang_thai
            FROM pay py
            JOIN booking b ON b.id = py.booking_id
            JOIN phong p ON p.id = b.phong_id
            ORDER BY py.id DESC
            """
        )
        payments = cursor.fetchall()
        enrich_peak_season_records(payments)
        return {"message": "Lấy danh sách thanh toán thành công", "total": len(payments), "payments": payments}
    except Error as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        cursor.close()


@router.get("/webhook-events")
def get_payment_webhook_events(
    limit: int = Query(default=100, ge=1, le=500),
    db=Depends(get_db),
):
    """ADMIN audit view for SePay callbacks, including unmatched/amount-mismatch transfers."""
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT id, transaction_id, gateway, account_number, payment_code,
                      transfer_type, transfer_amount, reference_code, transaction_date,
                      pay_id, processing_result, received_at, processed_at
               FROM sepay_webhook_events
               ORDER BY id DESC LIMIT %s""",
            (limit,),
        )
        rows = cursor.fetchall()
        return {"total": len(rows), "events": rows}
    except Error as exc:
        raise HTTPException(status_code=500, detail=f"Không đọc được nhật ký webhook: {exc}") from exc
    finally:
        cursor.close()


@router.get("/{payment_id:int}")
def get_payment(payment_id: int, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    try:
        payment = get_payment_by_id(cursor, payment_id)
        if payment is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy thanh toán.")
        return {"message": "Lấy thông tin thanh toán thành công", "payment": payment}
    except HTTPException:
        raise
    except Error as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        cursor.close()


@router.post("/", status_code=201)
def create_payment(data: PaymentCreate, db=Depends(get_db)):
    validate_payment_method(data.method)
    validate_payment_status(data.status)
    if data.status != "CHO_THANH_TOAN":
        raise HTTPException(
            status_code=422,
            detail="Giao dịch mới phải ở trạng thái CHO_THANH_TOAN. Hãy xác nhận sau khi đã có hóa đơn.",
        )

    cursor = db.cursor(dictionary=True)
    try:
        db.start_transaction()
        cursor.execute(
            "SELECT id, khach_id, trang_thai FROM booking WHERE id = %s FOR UPDATE",
            (data.booking_id,),
        )
        booking = cursor.fetchone()
        if booking is None:
            raise HTTPException(status_code=404, detail="Booking không tồn tại.")
        if booking["trang_thai"] == "DA_HUY":
            raise HTTPException(status_code=409, detail="Booking đã hủy, không thể tạo thanh toán.")

        totals = calculate_booking_totals(cursor, data.booking_id)
        supplied_amount = money(data.so_tien)
        if supplied_amount != totals["tong_tien"]:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Số tiền nhập không khớp tổng tiền Database. "
                    f"Số tiền đúng: {totals['tong_tien']} VNĐ."
                ),
            )

        cursor.execute(
            """
            SELECT id, status
            FROM pay
            WHERE booking_id = %s
              AND status IN ('CHO_THANH_TOAN', 'THANH_CONG')
            FOR UPDATE
            """,
            (data.booking_id,),
        )
        active_payment = cursor.fetchone()
        if active_payment:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Booking đã có giao dịch đang hoạt động (Pay ID {active_payment['id']}). "
                    "Không tạo thêm giao dịch trùng."
                ),
            )

        cursor.execute(
            """
            INSERT INTO pay (
                booking_id, khach_id, ngay_thanh_toan,
                so_tien, method, status
            )
            VALUES (%s, %s, %s, %s, %s, 'CHO_THANH_TOAN')
            """,
            (
                data.booking_id,
                booking["khach_id"],
                data.ngay_thanh_toan,
                supplied_amount,
                data.method,
            ),
        )
        new_id = cursor.lastrowid
        db.commit()

        payment = get_payment_by_id(cursor, new_id)
        return {
            "message": "Tạo giao dịch chờ thanh toán thành công",
            "id": new_id,
            "payment": payment,
            "calculation": totals,
        }
    except HTTPException:
        db.rollback()
        raise
    except Error as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"MySQL từ chối tạo thanh toán: {exc}") from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        cursor.close()


@router.put("/{payment_id:int}")
def update_payment(payment_id: int, data: PaymentUpdate, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    try:
        db.start_transaction()
        cursor.execute(
            """
            SELECT id, booking_id, khach_id, ngay_thanh_toan,
                   so_tien, method, status
            FROM pay
            WHERE id = %s
            FOR UPDATE
            """,
            (payment_id,),
        )
        existing = cursor.fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy thanh toán.")

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="Không có dữ liệu cập nhật.")

        # GUI hiện tại gửi lại số tiền/phương thức và tự đặt ngày = thời điểm hiện tại
        # khi bấm Cập nhật. Chỉ chấp nhận các giá trị tiền/phương thức không đổi;
        # không ghi đè ngày, số tiền hoặc phương thức đã lưu.
        if "so_tien" in update_data and update_data["so_tien"] is not None:
            if money(update_data["so_tien"]) != money(existing["so_tien"]):
                raise HTTPException(status_code=409, detail="Không được sửa số tiền của giao dịch đã tạo.")
        if "method" in update_data and update_data["method"] is not None:
            validate_payment_method(update_data["method"])
            if update_data["method"] != existing["method"]:
                raise HTTPException(status_code=409, detail="Không được sửa phương thức của giao dịch đã tạo.")

        new_status = update_data.get("status")
        if not new_status:
            raise HTTPException(
                status_code=422,
                detail="Chỉ cập nhật trạng thái thanh toán. Vui lòng chọn trạng thái mới.",
            )
        validate_payment_status(new_status)

        old_status = existing["status"]
        allowed_transitions = {
            "CHO_THANH_TOAN": {"THANH_CONG", "THAT_BAI"},
            "THAT_BAI": {"CHO_THANH_TOAN"},
            "THANH_CONG": {"HOAN_TIEN"},
            "HOAN_TIEN": set(),
        }
        if new_status != old_status and new_status not in allowed_transitions[old_status]:
            raise HTTPException(
                status_code=409,
                detail=f"Không thể chuyển trạng thái từ {old_status} sang {new_status}.",
            )

        if new_status == "THANH_CONG" and old_status != "THANH_CONG":
            cursor.execute(
                "SELECT id, tong_tien FROM hoadon WHERE pay_id = %s",
                (payment_id,),
            )
            invoice = cursor.fetchone()
            if invoice is None:
                raise HTTPException(
                    status_code=409,
                    detail="Chưa có hóa đơn cho giao dịch. Hãy tạo hóa đơn trước khi xác nhận thanh toán.",
                )
            if money(invoice["tong_tien"]) != money(existing["so_tien"]):
                raise HTTPException(status_code=409, detail="Số tiền thanh toán không khớp hóa đơn.")
            cursor.execute(
                "SELECT trang_thai FROM booking WHERE id = %s",
                (existing["booking_id"],),
            )
            booking_row = cursor.fetchone()
            if booking_row is None or booking_row["trang_thai"] == "DA_HUY":
                raise HTTPException(status_code=409, detail="Không thể thanh toán Booking đã hủy.")

        if new_status != old_status:
            cursor.execute(
                "UPDATE pay SET status = %s WHERE id = %s",
                (new_status, payment_id),
            )

        db.commit()
        updated = get_payment_by_id(cursor, payment_id)
        return {
            "message": "Cập nhật trạng thái thanh toán thành công",
            "payment": updated,
        }
    except HTTPException:
        db.rollback()
        raise
    except Error as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Database từ chối cập nhật: {exc}") from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        cursor.close()


@router.delete("/{payment_id:int}")
def delete_payment(payment_id: int, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    try:
        db.start_transaction()
        cursor.execute(
            "SELECT id, status FROM pay WHERE id = %s FOR UPDATE",
            (payment_id,),
        )
        payment = cursor.fetchone()
        if payment is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy thanh toán.")

        if payment["status"] != "THAT_BAI":
            raise HTTPException(
                status_code=409,
                detail="Chỉ được xóa giao dịch THAT_BAI. Giao dịch chờ, thành công hoặc hoàn tiền phải giữ lịch sử.",
            )

        cursor.execute("SELECT id FROM hoadon WHERE pay_id = %s", (payment_id,))
        if cursor.fetchone() is not None:
            raise HTTPException(
                status_code=409,
                detail="Giao dịch đã có hóa đơn; không được xóa lịch sử thanh toán.",
            )

        cursor.execute("DELETE FROM pay WHERE id = %s", (payment_id,))
        db.commit()
        return {"message": "Đã xóa giao dịch thất bại chưa lập hóa đơn", "id": payment_id}
    except HTTPException:
        db.rollback()
        raise
    except Error as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Không thể xóa thanh toán: {exc}") from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        cursor.close()
