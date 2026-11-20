
from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


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
    # Phòng mới chỉ có thể sẵn sàng hoặc bảo trì.
    # DANG_SU_DUNG do Booking/check-in tự đồng bộ.
    trang_thai: Literal["SAN_SANG", "BAO_TRI"] = "SAN_SANG"


class RoomUpdate(BaseModel):
    so_phong: str = Field(min_length=1, max_length=20)
    loai_phong_id: int = Field(gt=0)
    # Phù hợp với sp_cap_nhat_thong_tin_phong trong SQL V2.
    trang_thai: Literal["SAN_SANG", "BAO_TRI"]


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


class BookingServiceSelection(BaseModel):
    dichvu_id: int = Field(gt=0)
    so_luong: int = Field(default=1, gt=0)


class BookingCreate(BaseModel):
    phong_id: int = Field(gt=0)
    khach_id: int = Field(gt=0)
    ngay_nhan: date
    ngay_tra: date

    # Khách có thể chọn nhiều dịch vụ hoặc không chọn dịch vụ nào.
    dich_vu: list[BookingServiceSelection] = Field(default_factory=list)



class BookingUpdate(BaseModel):
    phong_id: int = Field(gt=0)
    khach_id: int = Field(gt=0)
    ngay_nhan: date
    ngay_tra: date


# =========================================================
# SERVICE
# =========================================================

class ServiceCreate(BaseModel):
    # Khớp bảng dichvu: ten VARCHAR(100), don_gia >= 0, so_luong > 0.
    ten: str = Field(min_length=1, max_length=100)
    don_gia: Decimal = Field(ge=0)
    so_luong: int = Field(gt=0)
    phong_id: Optional[int] = Field(default=None, gt=0)
    booking_id: Optional[int] = Field(default=None, gt=0)


class ServiceUpdate(BaseModel):
    ten: str = Field(min_length=1, max_length=100)
    don_gia: Decimal = Field(ge=0)
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

PEAK_SEASON_RATES = {0.6, 0.5, 0.4, 0.3, 0.2, 0.1}


def validate_peak_surcharge_rate(value: float) -> float:
    from decimal import Decimal
    allowed = {Decimal("0.6"), Decimal("0.5"), Decimal("0.4"),
               Decimal("0.3"), Decimal("0.2"), Decimal("0.1")}
    if Decimal(str(value)) not in allowed:
        raise ValueError("Hệ số phụ thu phải là một trong các mức 0.6, 0.5, 0.4, 0.3, 0.2 hoặc 0.1.")
    return float(value)


class PeakSeasonCreate(BaseModel):
    phong_id: int = Field(gt=0)
    tu_ngay: date
    den_ngay: date
    he_so_gia: float

    @field_validator("he_so_gia")
    @classmethod
    def validate_rate(cls, value):
        return validate_peak_surcharge_rate(value)


class PeakSeasonUpdate(BaseModel):
    phong_id: int = Field(gt=0)
    tu_ngay: date
    den_ngay: date
    he_so_gia: float

    @field_validator("he_so_gia")
    @classmethod
    def validate_rate(cls, value):
        return validate_peak_surcharge_rate(value)


# =========================================================
# AUTH
# =========================================================

class RegisterRequest(BaseModel):
    class Config:
        extra = "forbid"

    username: str = Field(min_length=3, max_length=50)
    full_name: str = Field(min_length=2, max_length=100)
    cccd: str = Field(min_length=9, max_length=20)
    sdt: str = Field(min_length=9, max_length=20)
    password: str = Field(min_length=6, max_length=128)


class CustomerPortalBookingCreate(BaseModel):
    phong_id: int = Field(gt=0)
    ngay_nhan: date
    ngay_tra: date


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)
