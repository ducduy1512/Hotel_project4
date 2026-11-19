"""Shared configuration and helpers for VietQR / SePay payment integration."""

import os
from pathlib import Path
from urllib.parse import urlencode
import re

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def get_qr_config() -> dict:
    """Return bank details or raise a clear error when QR is not configured."""
    bank_code = os.getenv("PAYMENT_BANK_CODE", "").strip()
    account_number = os.getenv("PAYMENT_BANK_ACCOUNT", "").strip().replace(" ", "")
    account_name = os.getenv("PAYMENT_ACCOUNT_NAME", "").strip()
    missing = [
        name for name, value in (
            ("PAYMENT_BANK_CODE", bank_code),
            ("PAYMENT_BANK_ACCOUNT", account_number),
            ("PAYMENT_ACCOUNT_NAME", account_name),
        ) if not value
    ]
    if missing:
        raise RuntimeError(
            "Chưa cấu hình tài khoản nhận QR. Hãy điền " + ", ".join(missing)
            + " trong file .env rồi khởi động lại API."
        )
    if not re.fullmatch(r"[A-Za-z0-9_-]{2,30}", bank_code):
        raise RuntimeError("PAYMENT_BANK_CODE không hợp lệ; hãy dùng mã ngân hàng VietQR/SePay.")
    if not re.fullmatch(r"[0-9]{4,19}", account_number):
        raise RuntimeError("PAYMENT_BANK_ACCOUNT phải gồm 4-19 chữ số.")
    return {
        "bank_code": bank_code,
        "account_number": account_number,
        "account_name": account_name,
        "qr_image_base_url": os.getenv("PAYMENT_QR_IMAGE_URL", "https://vietqr.app/img").strip(),
    }


def payment_code_for(pay_id: int) -> str:
    """Stable, unique transfer description associated with one Pay row."""
    return f"HTL{int(pay_id):08d}"


def build_vietqr_url(config: dict, amount: int, payment_code: str) -> str:
    params = {
        "acc": config["account_number"],
        "bank": config["bank_code"],
        "amount": str(int(amount)),
        "des": payment_code,
    }
    return f"{config['qr_image_base_url']}?{urlencode(params)}"
