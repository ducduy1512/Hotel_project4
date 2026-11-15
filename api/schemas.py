
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# =========================================================
# ROOM TYPE
# =========================================================

class RoomTypeCreate(BaseModel):
    ten: str = Field(min_length=1, max_length=100)
    gia_co_ban: float = Field(gt=0)
    suc_chua: int = Field(gt=0)


class RoomTypeUpdate(BaseModel):
    ten: str = Field(min_length=1, max_length=100)
    gia_co_ban: float = Field(gt=0)
    suc_chua: int = Field(gt=0)


# =========================================================
# ROOM
# =========================================================

class RoomCreate(BaseModel):
    so_phong: str = Field(min_length=1, max_length=20)
    loai_phong_id: int = Field(gt=0)
    trang_thai: str = "SAN_SANG"


class RoomUpdate(BaseModel):
    so_phong: str = Field(min_length=1, max_length=20)
    loai_phong_id: int = Field(gt=0)
    trang_thai: str


# =========================================================
# CUSTOMER
# =========================================================

class CustomerCreate(BaseModel):
    ho_ten: str = Field(min_length=1, max_length=100)
    cccd: str = Field(min_length=1, max_length=20)
    sdt: str = Field(min_length=1, max_length=20)


class CustomerUpdate(BaseModel):
    ho_ten: str = Field(min_length=1, max_length=100)
    cccd: str = Field(min_length=1, max_length=20)
    sdt: str = Field(min_length=1, max_length=20)


# =========================================================
# BOOKING
# =========================================================

class BookingCreate(BaseModel):
    phong_id: int = Field(gt=0)
    khach_id: int = Field(gt=0)
    ngay_nhan: date
    ngay_tra: date


class BookingUpdate(BaseModel):
    phong_id: int = Field(gt=0)
    khach_id: int = Field(gt=0)
    ngay_nhan: date
    ngay_tra: date


# =========================================================
# SERVICE
# =========================================================

class ServiceCreate(BaseModel):
    ten: str = Field(min_length=1, max_length=255)
    don_gia: Decimal = Field(gt=0)
    so_luong: int = Field(gt=0)
    phong_id: Optional[int] = Field(default=None, gt=0)
    booking_id: Optional[int] = Field(default=None, gt=0)


class ServiceUpdate(BaseModel):
    ten: str = Field(min_length=1, max_length=255)
    don_gia: Decimal = Field(gt=0)
    so_luong: int = Field(gt=0)
    phong_id: Optional[int] = Field(default=None, gt=0)
    booking_id: Optional[int] = Field(default=None, gt=0)


# =========================================================
# PAYMENT
# =========================================================

class PaymentCreate(BaseModel):
    booking_id: int = Field(gt=0)
    ngay_thanh_toan: datetime
    so_tien: Decimal = Field(gt=0)
    method: str
    status: str = "CHO_THANH_TOAN"


class PaymentUpdate(BaseModel):
    ngay_thanh_toan: Optional[datetime] = None
    so_tien: Optional[Decimal] = Field(default=None, gt=0)
    method: Optional[str] = None
    status: Optional[str] = None


# =========================================================
# INVOICE
# =========================================================

class InvoiceCreate(BaseModel):
    booking_id: int = Field(gt=0)
    method: str


# =========================================================
# PEAK SEASON
# =========================================================

class PeakSeasonCreate(BaseModel):
    phong_id: int = Field(gt=0)
    tu_ngay: date
    den_ngay: date
    he_so_gia: float = Field(gt=0)


class PeakSeasonUpdate(BaseModel):
    phong_id: int = Field(gt=0)
    tu_ngay: date
    den_ngay: date
    he_so_gia: float = Field(gt=0)


# =========================================================
# AUTH
# =========================================================

class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=6, max_length=128)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)
