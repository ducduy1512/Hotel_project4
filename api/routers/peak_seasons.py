
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from mysql.connector import Error, IntegrityError

from api.database import get_db


router = APIRouter(
    prefix="/api/peak-seasons",
    tags=["Peak Seasons"]
)


# =====================================
# SCHEMAS
# =====================================

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


# =====================================
# VALIDATE DATA
# =====================================

def validate_dates(tu_ngay, den_ngay):
    if den_ngay <= tu_ngay:
        raise HTTPException(
            status_code=422,
            detail="Ngày kết thúc phải sau ngày bắt đầu."
        )


# =====================================
# GET: DANH SÁCH MÙA CAO ĐIỂM
# =====================================

@router.get("/")
def get_peak_seasons(db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                m.id,
                m.phong_id,
                p.so_phong,
                m.tu_ngay,
                m.den_ngay,
                m.he_so_gia
            FROM muacaodiem m
            JOIN phong p
                ON m.phong_id = p.id
            ORDER BY m.id DESC
        """)

        return cursor.fetchall()

    except Error as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cursor.close()


# =====================================
# GET: CHI TIẾT MÙA CAO ĐIỂM
# =====================================

@router.get("/{season_id}")
def get_peak_season(
    season_id: int,
    db=Depends(get_db)
):
    cursor = db.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                m.id,
                m.phong_id,
                p.so_phong,
                m.tu_ngay,
                m.den_ngay,
                m.he_so_gia
            FROM muacaodiem m
            JOIN phong p
                ON m.phong_id = p.id
            WHERE m.id = %s
        """, (season_id,))

        season = cursor.fetchone()

        if season is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy mùa cao điểm."
            )

        return season

    except HTTPException:
        raise

    except Error as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cursor.close()


# =====================================
# POST: THÊM MÙA CAO ĐIỂM
# =====================================

@router.post("/", status_code=201)
def create_peak_season(
    season: PeakSeasonCreate,
    db=Depends(get_db)
):
    validate_dates(season.tu_ngay, season.den_ngay)

    cursor = db.cursor(dictionary=True)

    try:
        # Kiểm tra phòng tồn tại
        cursor.execute("""
            SELECT id
            FROM phong
            WHERE id = %s
        """, (season.phong_id,))

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Phòng không tồn tại."
            )

        # Thêm mùa cao điểm
        cursor.execute("""
            INSERT INTO muacaodiem (
                phong_id,
                tu_ngay,
                den_ngay,
                he_so_gia
            )
            VALUES (%s, %s, %s, %s)
        """, (
            season.phong_id,
            season.tu_ngay,
            season.den_ngay,
            season.he_so_gia
        ))

        new_id = cursor.lastrowid

        db.commit()

        # Lấy lại dữ liệu vừa thêm
        cursor.execute("""
            SELECT
                m.id,
                m.phong_id,
                p.so_phong,
                m.tu_ngay,
                m.den_ngay,
                m.he_so_gia
            FROM muacaodiem m
            JOIN phong p
                ON m.phong_id = p.id
            WHERE m.id = %s
        """, (new_id,))

        new_season = cursor.fetchone()

        return {
            "message": "Thêm mùa cao điểm thành công",
            "id": new_id,
            "peak_season": new_season
        }

    except HTTPException:
        db.rollback()
        raise

    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=str(e)
        )

    except Error as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cursor.close()


# =====================================
# PUT: CẬP NHẬT MÙA CAO ĐIỂM
# =====================================

@router.put("/{season_id}")
def update_peak_season(
    season_id: int,
    season: PeakSeasonUpdate,
    db=Depends(get_db)
):
    validate_dates(season.tu_ngay, season.den_ngay)

    cursor = db.cursor(dictionary=True)

    try:
        # Kiểm tra mùa cao điểm tồn tại
        cursor.execute("""
            SELECT id
            FROM muacaodiem
            WHERE id = %s
        """, (season_id,))

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy mùa cao điểm."
            )

        # Kiểm tra phòng tồn tại
        cursor.execute("""
            SELECT id
            FROM phong
            WHERE id = %s
        """, (season.phong_id,))

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Phòng không tồn tại."
            )

        cursor.execute("""
            UPDATE muacaodiem
            SET
                phong_id = %s,
                tu_ngay = %s,
                den_ngay = %s,
                he_so_gia = %s
            WHERE id = %s
        """, (
            season.phong_id,
            season.tu_ngay,
            season.den_ngay,
            season.he_so_gia,
            season_id
        ))

        db.commit()

        cursor.execute("""
            SELECT
                m.id,
                m.phong_id,
                p.so_phong,
                m.tu_ngay,
                m.den_ngay,
                m.he_so_gia
            FROM muacaodiem m
            JOIN phong p
                ON m.phong_id = p.id
            WHERE m.id = %s
        """, (season_id,))

        updated_season = cursor.fetchone()

        return {
            "message": "Cập nhật mùa cao điểm thành công",
            "peak_season": updated_season
        }

    except HTTPException:
        db.rollback()
        raise

    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=str(e)
        )

    except Error as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        cursor.close()


# =====================================
# DELETE: XÓA MÙA CAO ĐIỂM
# =====================================

@router.delete("/{season_id}")
def delete_peak_season(
    season_id: int,
    db=Depends(get_db)
):
    cursor = db.cursor()

    try:
        cursor.execute("""
            SELECT id
            FROM muacaodiem
            WHERE id = %s
        """, (season_id,))

        if cursor.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Không tìm thấy mùa cao điểm."
            )

        cursor.execute("""
            DELETE FROM muacaodiem
            WHERE id = %s
        """, (season_id,))

        db.commit()

        return {
            "message": "Xóa mùa cao điểm thành công",
            "id": season_id
        }

    except HTTPException:
        db.rollback()
        raise

    except Error as e:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=str(e)
        )

    finally:
        cursor.close()
