"""Public SePay webhook endpoint. It is intentionally separate from user auth routes."""

import hashlib
import hmac
import json
import os
import re
import time
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException, Request
from mysql.connector import Error, IntegrityError

from api.database import get_db

router = APIRouter(prefix="/api/webhooks", tags=["Payment Gateway Webhooks"])
PAYMENT_CODE_RE = re.compile(r"\bHTL\d{8,}\b", re.IGNORECASE)


def verify_sepay_auth(raw_body: bytes, headers) -> None:
    """Verify SePay HMAC-SHA256 (recommended) or API-key authentication."""
    mode = os.getenv("SEPAY_WEBHOOK_AUTH_MODE", "HMAC_SHA256").strip().upper()

    if mode == "HMAC_SHA256":
        secret = os.getenv("SEPAY_WEBHOOK_SECRET", "").strip()
        if not secret:
            raise HTTPException(status_code=503, detail="Chưa cấu hình SEPAY_WEBHOOK_SECRET.")
        signature = headers.get("X-SePay-Signature", "").strip()
        timestamp_text = headers.get("X-SePay-Timestamp", "").strip()
        try:
            timestamp = int(timestamp_text)
        except (TypeError, ValueError):
            raise HTTPException(status_code=401, detail="Thiếu timestamp xác thực SePay.")
        if abs(int(time.time()) - timestamp) > 300:
            raise HTTPException(status_code=401, detail="Webhook SePay đã quá thời hạn xác thực (5 phút).")
        signed_message = str(timestamp).encode("ascii") + b"." + raw_body
        digest = hmac.new(secret.encode("utf-8"), signed_message, hashlib.sha256).hexdigest()
        expected = f"sha256={digest}"
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=401, detail="Chữ ký HMAC của SePay không hợp lệ.")
        return

    if mode == "API_KEY":
        expected_key = os.getenv("SEPAY_WEBHOOK_API_KEY", "").strip()
        authorization = headers.get("Authorization", "").strip()
        if not expected_key:
            raise HTTPException(status_code=503, detail="Chưa cấu hình SEPAY_WEBHOOK_API_KEY.")
        if not authorization.startswith("Apikey ") or not hmac.compare_digest(
            authorization[7:].strip(), expected_key
        ):
            raise HTTPException(status_code=401, detail="API Key SePay không hợp lệ.")
        return

    raise HTTPException(
        status_code=503,
        detail="SEPAY_WEBHOOK_AUTH_MODE chỉ hỗ trợ HMAC_SHA256 hoặc API_KEY; không cho phép webhook không xác thực.",
    )


def extract_payment_code(payload: dict) -> str:
    direct_code = payload.get("code")
    if direct_code:
        candidate = str(direct_code).strip().upper()
        if PAYMENT_CODE_RE.fullmatch(candidate):
            return candidate
    text = " ".join(str(payload.get(key) or "") for key in ("content", "description")).upper()
    match = PAYMENT_CODE_RE.search(text)
    return match.group(0) if match else ""


def _to_decimal(value) -> Decimal:
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        raise HTTPException(status_code=422, detail="Số tiền giao dịch SePay không hợp lệ.")


@router.post("/sepay", status_code=200)
async def receive_sepay_webhook(request: Request, db=Depends(get_db)):
    raw_body = await request.body()
    verify_sepay_auth(raw_body, request.headers)

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Payload webhook phải là JSON hợp lệ.") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Payload webhook không đúng định dạng object.")

    transaction_id = payload.get("id")
    if transaction_id is None or str(transaction_id).strip() == "":
        raise HTTPException(status_code=422, detail="Webhook SePay thiếu mã giao dịch id.")
    transaction_id = str(transaction_id).strip()[:80]
    transfer_type = str(payload.get("transferType") or "").strip().lower()
    payment_code = extract_payment_code(payload)
    gateway = str(payload.get("gateway") or "")[:60]
    account_number = str(payload.get("accountNumber") or "").strip().replace(" ", "")[:64]
    reference_code = str(payload.get("referenceCode") or "")[:128]
    transaction_date = str(payload.get("transactionDate") or "")[:40]
    raw_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    transfer_amount = _to_decimal(payload.get("transferAmount", 0))
    expected_account = (
        os.getenv("SEPAY_WEBHOOK_ACCOUNT_NUMBER", "").strip().replace(" ", "")
        or os.getenv("PAYMENT_BANK_ACCOUNT", "").strip().replace(" ", "")
    )

    cursor = db.cursor(dictionary=True)
    try:
        db.start_transaction()
        try:
            cursor.execute(
                """INSERT INTO sepay_webhook_events
                   (transaction_id, gateway, account_number, payment_code, transfer_type,
                    transfer_amount, reference_code, transaction_date, processing_result, raw_payload)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'PROCESSING',%s)""",
                (transaction_id, gateway, account_number or None, payment_code or None,
                 transfer_type or None, transfer_amount, reference_code or None,
                 transaction_date or None, raw_json),
            )
            event_id = cursor.lastrowid
        except IntegrityError as exc:
            db.rollback()
            if getattr(exc, "errno", None) == 1062:
                return {"success": True, "duplicate": True, "message": "Giao dịch SePay đã được nhận trước đó."}
            raise

        def finish(result: str, pay_id=None):
            cursor.execute(
                """UPDATE sepay_webhook_events
                   SET processing_result=%s, pay_id=%s, processed_at=CURRENT_TIMESTAMP
                   WHERE id=%s""",
                (result, pay_id, event_id),
            )
            db.commit()
            return {"success": True, "result": result, "pay_id": pay_id}

        if transfer_type != "in":
            return finish("IGNORED_NOT_INCOMING")
        if not payment_code:
            return finish("UNMATCHED_NO_PAYMENT_CODE")
        if expected_account and account_number and account_number != expected_account:
            return finish("UNEXPECTED_RECEIVING_ACCOUNT")
        if expected_account and not account_number:
            return finish("MISSING_RECEIVING_ACCOUNT")

        cursor.execute(
            """SELECT q.pay_id, q.payment_code, py.so_tien, py.status,
                      py.method, h.tong_tien, b.trang_thai AS booking_status
               FROM payment_qr q
               JOIN pay py ON py.id=q.pay_id
               JOIN hoadon h ON h.pay_id=py.id
               JOIN booking b ON b.id=py.booking_id
               WHERE q.payment_code=%s
               FOR UPDATE""",
            (payment_code,),
        )
        payment = cursor.fetchone()
        if payment is None:
            return finish("UNMATCHED_PAYMENT_CODE")
        pay_id = int(payment["pay_id"])

        if payment["method"] != "CHUYEN_KHOAN":
            return finish("PAYMENT_METHOD_NOT_BANK_TRANSFER", pay_id)
        if payment["booking_status"] == "DA_HUY":
            return finish("BOOKING_CANCELLED", pay_id)
        if payment["status"] != "CHO_THANH_TOAN":
            return finish("PAYMENT_NOT_PENDING", pay_id)
        expected_amount = _to_decimal(payment["so_tien"])
        invoice_amount = _to_decimal(payment["tong_tien"])
        if transfer_amount != expected_amount or invoice_amount != expected_amount:
            return finish("AMOUNT_MISMATCH", pay_id)

        cursor.execute(
            "UPDATE pay SET status='THANH_CONG' WHERE id=%s AND status='CHO_THANH_TOAN'",
            (pay_id,),
        )
        if cursor.rowcount != 1:
            return finish("PAYMENT_NOT_PENDING", pay_id)

        cursor.execute(
            """UPDATE payment_qr
               SET sepay_transaction_id=%s, sepay_reference_code=%s,
                   received_amount=%s, received_account_number=%s,
                   received_at=CURRENT_TIMESTAMP
               WHERE pay_id=%s AND sepay_transaction_id IS NULL""",
            (transaction_id, reference_code or None, transfer_amount,
             account_number or None, pay_id),
        )
        if cursor.rowcount != 1:
            raise RuntimeError("Không thể ghi nhận mã giao dịch vào payment_qr.")
        return finish("PAID", pay_id)

    except HTTPException:
        db.rollback()
        raise
    except Error as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail=f"Không xử lý được webhook trong MySQL: {exc}") from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý webhook thanh toán: {exc}") from exc
    finally:
        cursor.close()
