import hashlib
import hmac
import secrets

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from mysql.connector import IntegrityError

from api.database import get_db


router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"]
)


# =====================================
# REQUEST MODELS
# =====================================

from api.schemas import RegisterRequest, LoginRequest


# =====================================
# PASSWORD HASHING
# =====================================

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        200000
    ).hex()

    return f"{salt}${password_hash}"


def verify_password(password: str, stored_password: str) -> bool:
    try:
        salt, saved_hash = stored_password.split("$", 1)

        check_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            200000
        ).hex()

        return hmac.compare_digest(check_hash, saved_hash)

    except (ValueError, AttributeError):
        return False


# =====================================
# CREATE USERS TABLE
# =====================================

def create_users_table(db):
    cursor = db.cursor()

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                full_name VARCHAR(100) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(30) NOT NULL DEFAULT 'staff',
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        db.commit()

    finally:
        cursor.close()


# =====================================
# REGISTER
# =====================================

@router.post("/register")
def register(data: RegisterRequest, db=Depends(get_db)):

    create_users_table(db)

    username = data.username.strip()
    full_name = data.full_name.strip()

    if not username or not full_name:
        raise HTTPException(
            status_code=400,
            detail="Vui lòng nhập đầy đủ thông tin."
        )

    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT id FROM users WHERE username = %s",
            (username,)
        )

        if cursor.fetchone():
            raise HTTPException(
                status_code=409,
                detail="Tên đăng nhập đã tồn tại."
            )

        password_hash = hash_password(data.password)

        cursor.execute("""
            INSERT INTO users
                (username, full_name, password_hash, role, is_active)
            VALUES
                (%s, %s, %s, %s, %s)
        """, (
            username,
            full_name,
            password_hash,
            "staff",
            True
        ))

        db.commit()

        return {
            "success": True,
            "message": "Đăng ký tài khoản thành công.",
            "user": {
                "id": cursor.lastrowid,
                "username": username,
                "full_name": full_name,
                "role": "staff"
            }
        }

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Tên đăng nhập đã tồn tại."
        )

    except Exception:
        db.rollback()
        raise

    finally:
        cursor.close()


# =====================================
# LOGIN
# =====================================

@router.post("/login")
def login(data: LoginRequest, db=Depends(get_db)):

    create_users_table(db)

    username = data.username.strip()

    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                id,
                username,
                full_name,
                password_hash,
                role,
                is_active
            FROM users
            WHERE username = %s
        """, (username,))

        user = cursor.fetchone()

    finally:
        cursor.close()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Tên đăng nhập hoặc mật khẩu không chính xác."
        )

    if not user["is_active"]:
        raise HTTPException(
            status_code=403,
            detail="Tài khoản đã bị khóa."
        )

    if not verify_password(data.password, user["password_hash"]):
        raise HTTPException(
            status_code=401,
            detail="Tên đăng nhập hoặc mật khẩu không chính xác."
        )

    return {
        "success": True,
        "message": "Đăng nhập thành công.",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "full_name": user["full_name"],
            "role": user["role"]
        }
    }