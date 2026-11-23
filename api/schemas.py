
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
    # MAC_DINH: gắn với phòng và miễn phí; TUY_CHON: danh mục chung hoặc dịch vụ Booking.
    ten: str = Field(min_length=1, max_length=100)
    don_gia: Decimal = Field(ge=0)
    so_luong: int = Field(gt=0)
    phong_id: Optional[int] = Field(default=None, gt=0)
    booking_id: Optional[int] = Field(default=None, gt=0)
    loai_dichvu: Literal["MAC_DINH", "TUY_CHON"] = "MAC_DINH"
    nhom_dich_vu: str = Field(default="KHAC", min_length=1, max_length=50)
    don_vi_tinh: str = Field(default="lần", min_length=1, max_length=40)
    dang_hoat_dong: bool = True


class ServiceUpdate(BaseModel):
    ten: str = Field(min_length=1, max_length=100)
    don_gia: Decimal = Field(ge=0)
    so_luong: int = Field(gt=0)
    phong_id: Optional[int] = Field(default=None, gt=0)
    booking_id: Optional[int] = Field(default=None, gt=0)
    loai_dichvu: Literal["MAC_DINH", "TUY_CHON"] = "MAC_DINH"
    nhom_dich_vu: str = Field(default="KHAC", min_length=1, max_length=50)
    don_vi_tinh: str = Field(default="lần", min_length=1, max_length=40)
    dang_hoat_dong: bool = True


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

PEAK_SEASON_RATES = {0.6, 0.5, 0.4, 0.35, 0.3, 0.25, 0.2, 0.1}

# Phu thu duoc xac dinh theo LOAI PHONG cua tung PHONG vat ly.
ROOM_TYPE_PEAK_SURCHARGES = {
    "standard": 0.20,
    "deluxe": 0.25,
    "vip": 0.30,
    "family": 0.35,
}


def peak_surcharge_for_room_type(room_type_name: str) -> float:
    key = str(room_type_name or "").strip().casefold()
    try:
        return ROOM_TYPE_PEAK_SURCHARGES[key]
    except KeyError as exc:
        raise ValueError(
            f"Chua cau hinh phu thu mua cao diem cho loai phong '{room_type_name}'."
        ) from exc


def validate_peak_surcharge_rate(value: float) -> float:
    from decimal import Decimal
    allowed = {Decimal("0.6"), Decimal("0.5"), Decimal("0.4"),
               Decimal("0.35"), Decimal("0.3"), Decimal("0.25"), Decimal("0.2"), Decimal("0.1")}
    if Decimal(str(value)) not in allowed:
        raise ValueError("Tỷ lệ phụ thu không hợp lệ. Các mức hệ thống hỗ trợ gồm 0.6, 0.5, 0.4, 0.35, 0.3, 0.25, 0.2 và 0.1.")
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


class PeakSeasonRoomRate(BaseModel):
    """One room's rate within a shared peak-season date range."""
    phong_id: int = Field(gt=0)
    he_so_gia: float

    @field_validator("he_so_gia")
    @classmethod
    def validate_rate(cls, value):
        return validate_peak_surcharge_rate(value)


class PeakSeasonBulkCreate(BaseModel):
    """Create linked muacaodiem rows for every current room in one operation."""
    tu_ngay: date
    den_ngay: date
    room_rates: list[PeakSeasonRoomRate] = Field(default_factory=list)


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
