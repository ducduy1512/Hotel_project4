
"""
AUTHENTICATION - HOTEL PROJECT 5

Chức năng:
- Đăng ký tài khoản CUSTOMER.
- Đăng nhập ADMIN/CUSTOMER.
- Tạo và xác minh access token.
- Xác minh tài khoản còn hoạt động.
- Kiểm tra quyền ADMIN/CUSTOMER.

Bảng sử dụng:
- users
- khach

Không tự tạo bảng trong Python.
"""

import os
import json
import time
import base64
import hashlib
import hmac
import secrets
from pathlib import Path

from dotenv import load_dotenv
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)

from mysql.connector import Error, IntegrityError
from pydantic import BaseModel, Field

from api.database import get_db


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)


# =========================================================
# CONFIGURATION
# =========================================================

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

TOKEN_SECRET_VALUE = os.getenv("HOTEL_AUTH_SECRET", "").strip()
if len(TOKEN_SECRET_VALUE) < 32 or TOKEN_SECRET_VALUE.startswith("replace-this"):
    raise RuntimeError(
        "HOTEL_AUTH_SECRET chưa được cấu hình an toàn. "
        "Hãy đặt một chuỗi ngẫu nhiên riêng, tối thiểu 32 ký tự trong file .env."
    )
TOKEN_SECRET = TOKEN_SECRET_VALUE.encode("utf-8")

TOKEN_EXPIRE_SECONDS = 12 * 60 * 60

PBKDF2_ITERATIONS = 200_000

bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth"
)


# =========================================================
# REQUEST MODELS
# =========================================================

class RegisterRequest(BaseModel):

    username: str = Field(
        min_length=3,
        max_length=50
    )

    full_name: str = Field(
        min_length=2,
        max_length=100
    )

    cccd: str = Field(
        min_length=1,
        max_length=20
    )

    sdt: str = Field(
        min_length=1,
        max_length=20
    )

    password: str = Field(
        min_length=6,
        max_length=128
    )


class LoginRequest(BaseModel):

    username: str = Field(
        min_length=1,
        max_length=50
    )

    password: str = Field(
        min_length=1,
        max_length=128
    )


# =========================================================
# PASSWORD HASHING
# =========================================================

def hash_password(password: str) -> str:

    salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS
    ).hex()

    return f"{salt}${password_hash}"


def verify_password(
    password: str,
    stored_password: str
) -> bool:

    try:

        salt, saved_hash = stored_password.split("$", 1)

        check_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            PBKDF2_ITERATIONS
        ).hex()

        return hmac.compare_digest(
            check_hash,
            saved_hash
        )

    except (ValueError, AttributeError, TypeError):

        return False


# =========================================================
# TOKEN FUNCTIONS
# JWT HS256 - NO ADDITIONAL JWT PACKAGE REQUIRED
# =========================================================

def _b64url_encode(raw: bytes) -> str:

    return (
        base64.urlsafe_b64encode(raw)
        .rstrip(b"=")
        .decode("ascii")
    )


def _b64url_decode(value: str) -> bytes:

    padding = "=" * (-len(value) % 4)

    return base64.urlsafe_b64decode(
        value + padding
    )


def create_access_token(
    user: dict[str, Any]
) -> str:

    now = int(time.time())

    header = {
        "alg": "HS256",
        "typ": "JWT"
    }

    payload = {

        "sub": str(user["id"]),

        "username": user["username"],

        "full_name": user["full_name"],

        "role": str(user["role"]).upper(),

        "khach_id": user.get("khach_id"),

        "iat": now,

        "exp": now + TOKEN_EXPIRE_SECONDS
    }

    header_part = _b64url_encode(
        json.dumps(
            header,
            separators=(",", ":")
        ).encode("utf-8")
    )

    payload_part = _b64url_encode(
        json.dumps(
            payload,
            separators=(",", ":")
        ).encode("utf-8")
    )

    signing_input = (
        f"{header_part}.{payload_part}"
    ).encode("ascii")

    signature = hmac.new(
        TOKEN_SECRET,
        signing_input,
        hashlib.sha256
    ).digest()

    return (
        f"{header_part}."
        f"{payload_part}."
        f"{_b64url_encode(signature)}"
    )


def decode_access_token(
    token: str
) -> dict[str, Any]:

    try:

        parts = token.split(".")

        if len(parts) != 3:
            raise ValueError("Invalid token")

        header_part, payload_part, signature_part = parts

        signing_input = (
            f"{header_part}.{payload_part}"
        ).encode("ascii")

        expected_signature = hmac.new(
            TOKEN_SECRET,
            signing_input,
            hashlib.sha256
        ).digest()

        supplied_signature = _b64url_decode(
            signature_part
        )

        if not hmac.compare_digest(
            expected_signature,
            supplied_signature
        ):
            raise ValueError("Invalid signature")

        header = json.loads(
            _b64url_decode(header_part).decode("utf-8")
        )

        payload = json.loads(
            _b64url_decode(payload_part).decode("utf-8")
        )

        if header.get("alg") != "HS256":
            raise ValueError("Invalid algorithm")

        if int(payload.get("exp", 0)) <= int(time.time()):
            raise ValueError("Token expired")

        if not payload.get("sub"):
            raise ValueError("Missing user ID")

        if payload.get("role") not in (
            "ADMIN",
            "CUSTOMER"
        ):
            raise ValueError("Invalid role")

        return payload

    except Exception as exc:

        raise ValueError(
            "Token không hợp lệ hoặc đã hết hạn."
        ) from exc


# =========================================================
# GET CURRENT USER
# =========================================================

def get_current_user(

    credentials: HTTPAuthorizationCredentials | None =
        Depends(bearer_scheme),

    db=Depends(get_db)

):

    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
    ):

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bạn cần đăng nhập để tiếp tục.",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    try:

        token_data = decode_access_token(
            credentials.credentials
        )

        user_id = int(token_data["sub"])

    except (ValueError, TypeError, KeyError):

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn.",
            headers={
                "WWW-Authenticate": "Bearer"
            }
        )

    cursor = db.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                u.id,
                u.username,
                u.full_name,
                u.role,
                u.khach_id,
                u.is_active,

                k.ho_ten,
                k.cccd,
                k.sdt

            FROM users AS u

            LEFT JOIN khach AS k
                ON k.id = u.khach_id

            WHERE u.id = %s

            LIMIT 1
            """,
            (user_id,)
        )

        user = cursor.fetchone()

    except Error as exc:

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Không thể xác minh tài khoản trên MySQL."
        ) from exc

    finally:

        cursor.close()

    if not user:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản không còn tồn tại."
        )

    if not user["is_active"]:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị khóa."
        )

    user["role"] = str(user["role"]).upper()

    if user["role"] not in ("ADMIN", "CUSTOMER"):

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role tài khoản không hợp lệ."
        )

    return user


# =========================================================
# REQUIRE ADMIN
# =========================================================

def require_admin(
    current_user=Depends(get_current_user)
):

    if current_user["role"] != "ADMIN":

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chức năng này chỉ dành cho ADMIN."
        )

    return current_user


# =========================================================
# REQUIRE CUSTOMER
# =========================================================

def require_customer(
    current_user=Depends(get_current_user)
):

    if current_user["role"] != "CUSTOMER":

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chức năng này chỉ dành cho CUSTOMER."
        )

    if not current_user.get("khach_id"):

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản chưa được liên kết hồ sơ khách hàng."
        )

    return current_user


# =========================================================
# REGISTER CUSTOMER
# =========================================================

@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED
)
def register(
    data: RegisterRequest,
    db=Depends(get_db)
):

    username = data.username.strip()

    full_name = data.full_name.strip()

    cccd = data.cccd.strip()

    sdt = data.sdt.strip()

    if not all((username, full_name, cccd, sdt)):

        raise HTTPException(
            status_code=422,
            detail="Vui lòng nhập đầy đủ thông tin."
        )

    cursor = db.cursor(dictionary=True)

    try:

        # Bắt đầu transaction để tạo đồng thời khach và users.
        db.start_transaction()

        # Kiểm tra username
        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE username = %s
            LIMIT 1
            """,
            (username,)
        )

        if cursor.fetchone():

            raise HTTPException(
                status_code=409,
                detail="Tên đăng nhập đã tồn tại."
            )

        # Kiểm tra CCCD và số điện thoại
        cursor.execute(
            """
            SELECT id
            FROM khach
            WHERE cccd = %s
               OR sdt = %s
            LIMIT 1
            """,
            (cccd, sdt)
        )

        if cursor.fetchone():

            raise HTTPException(
                status_code=409,
                detail="CCCD hoặc số điện thoại đã được sử dụng."
            )

        # Tạo hồ sơ khách hàng
        cursor.execute(
            """
            INSERT INTO khach (
                ho_ten,
                cccd,
                sdt
            )
            VALUES (%s, %s, %s)
            """,
            (
                full_name,
                cccd,
                sdt
            )
        )

        khach_id = cursor.lastrowid

        # Mã hóa mật khẩu
        password_hash = hash_password(
            data.password
        )

        # Tạo tài khoản CUSTOMER
        # Không nhận role từ dữ liệu người dùng gửi lên.
        cursor.execute(
            """
            INSERT INTO users (
                username,
                full_name,
                password_hash,
                role,
                khach_id,
                is_active
            )
            VALUES (
                %s,
                %s,
                %s,
                'CUSTOMER',
                %s,
                1
            )
            """,
            (
                username,
                full_name,
                password_hash,
                khach_id
            )
        )

        user_id = cursor.lastrowid

        db.commit()

        return {

            "success": True,

            "message": "Đăng ký tài khoản CUSTOMER thành công.",

            "user": {

                "id": user_id,

                "username": username,

                "full_name": full_name,

                "role": "CUSTOMER",

                "khach_id": khach_id
            }
        }

    except HTTPException:

        db.rollback()
        raise

    except IntegrityError as exc:

        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Username, CCCD hoặc số điện thoại đã tồn tại."
        ) from exc

    except Error as exc:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Không thể tạo tài khoản. Hãy kiểm tra bảng users và khach."
        ) from exc

    except Exception:

        db.rollback()
        raise

    finally:

        cursor.close()


# =========================================================
# LOGIN
# =========================================================

@router.post("/login")
def login(
    data: LoginRequest,
    db=Depends(get_db)
):

    username = data.username.strip()

    cursor = db.cursor(dictionary=True)

    try:

        cursor.execute(
            """
            SELECT
                id,
                username,
                full_name,
                password_hash,
                role,
                khach_id,
                is_active

            FROM users

            WHERE username = %s

            LIMIT 1
            """,
            (username,)
        )

        user = cursor.fetchone()

    except Error as exc:

        raise HTTPException(
            status_code=503,
            detail="Không thể truy cập bảng users. Hãy chạy SQL migration trước."
        ) from exc

    finally:

        cursor.close()

    if (
        not user
        or not verify_password(
            data.password,
            user["password_hash"]
        )
    ):

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tên đăng nhập hoặc mật khẩu không chính xác."
        )

    if not user["is_active"]:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đã bị khóa."
        )

    role = str(user["role"]).upper()

    if role not in ("ADMIN", "CUSTOMER"):

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role tài khoản không hợp lệ."
        )

    if role == "CUSTOMER" and not user.get("khach_id"):

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản CUSTOMER chưa liên kết hồ sơ khách hàng."
        )

    user["role"] = role

    access_token = create_access_token(user)

    return {

        "success": True,

        "message": "Đăng nhập thành công.",

        "access_token": access_token,

        "token_type": "bearer",

        "expires_in": TOKEN_EXPIRE_SECONDS,

        "user": {

            "id": user["id"],

            "username": user["username"],

            "full_name": user["full_name"],

            "role": role,

            "khach_id": user.get("khach_id")
        }
    }


# =========================================================
# GET CURRENT ACCOUNT
# =========================================================

@router.get("/me")
def read_current_user(
    current_user=Depends(get_current_user)
):

    return {
        "success": True,
        "user": current_user
    }
