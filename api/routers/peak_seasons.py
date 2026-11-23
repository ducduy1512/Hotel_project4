from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from mysql.connector import Error, IntegrityError
from api.database import get_db
from api.schemas import (
    PeakSeasonCreate, PeakSeasonUpdate, PeakSeasonBulkCreate,
    peak_surcharge_for_room_type,
)

router = APIRouter(prefix="/api/peak-seasons", tags=["Peak Seasons"])


def validate_dates(tu_ngay, den_ngay):
    if den_ngay <= tu_ngay:
        raise HTTPException(status_code=422, detail="Ngày kết thúc phải sau ngày bắt đầu.")


def _season_rows(cursor, season_id=None):
    sql = """
        SELECT m.id, m.tu_ngay, m.den_ngay,
               pm.phong_id, p.so_phong, lp.ten AS ten_loai_phong,
               pm.he_so_phu_thu AS he_so_gia,
               COUNT(*) OVER (PARTITION BY m.id) AS so_phong_ap_dung
        FROM muacaodiem m
        JOIN phong_muacaodiem pm ON pm.muacaodiem_id = m.id
        JOIN phong p ON p.id = pm.phong_id
        JOIN loaiphong lp ON lp.id = p.loai_phong_id
    """
    params = ()
    if season_id is not None:
        sql += " WHERE m.id = %s"
        params = (season_id,)
    sql += " ORDER BY m.id DESC, p.so_phong"
    cursor.execute(sql, params)
    return cursor.fetchall()


@router.get("/")
def get_peak_seasons(db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    try:
        return _season_rows(cursor)
    except Error as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        cursor.close()


@router.get("/{season_id}")
def get_peak_season(season_id: int, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    try:
        rows = _season_rows(cursor, season_id)
        if not rows:
            raise HTTPException(status_code=404, detail="Không tìm thấy mùa cao điểm.")
        first = rows[0]
        return {
            "id": first["id"], "tu_ngay": first["tu_ngay"], "den_ngay": first["den_ngay"],
            "rooms": [{"phong_id": r["phong_id"], "so_phong": r["so_phong"],
                       "ten_loai_phong": r["ten_loai_phong"], "he_so_gia": r["he_so_gia"]} for r in rows]
        }
    except HTTPException:
        raise
    except Error as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        cursor.close()


@router.post("/apply-all", status_code=201)
def create_peak_season_for_all_rooms(season: PeakSeasonBulkCreate, db=Depends(get_db)):
    """Create ONE season row and N room-rate links atomically."""
    validate_dates(season.tu_ngay, season.den_ngay)
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("""SELECT p.id, p.so_phong, lp.ten AS ten_loai_phong
            FROM phong p JOIN loaiphong lp ON lp.id=p.loai_phong_id
            ORDER BY p.id FOR UPDATE""")
        rooms = cursor.fetchall()
        if not rooms:
            raise HTTPException(status_code=409, detail="Khách sạn chưa có phòng.")
        # Rates are derived from each physical room's assigned room type.
        # The client cannot accidentally apply a different rate to a room.
        room_rate_by_id = {}
        for room in rooms:
            try:
                room_rate_by_id[int(room["id"])] = peak_surcharge_for_room_type(room["ten_loai_phong"])
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        cursor.execute("""SELECT m.id, p.so_phong FROM muacaodiem m
            JOIN phong_muacaodiem pm ON pm.muacaodiem_id=m.id
            JOIN phong p ON p.id=pm.phong_id
            WHERE m.tu_ngay <= %s AND m.den_ngay >= %s
            FOR UPDATE""", (season.den_ngay, season.tu_ngay))
        conflicts = cursor.fetchall()
        if conflicts:
            names = ", ".join(sorted({str(x["so_phong"]) for x in conflicts}))
            raise HTTPException(status_code=409, detail=f"Các phòng đã có mùa cao điểm trùng ngày: {names}.")
        cursor.execute("INSERT INTO muacaodiem (tu_ngay, den_ngay) VALUES (%s, %s)", (season.tu_ngay, season.den_ngay))
        season_id = cursor.lastrowid
        cursor.executemany("""INSERT INTO phong_muacaodiem (phong_id, muacaodiem_id, he_so_phu_thu)
            VALUES (%s, %s, %s)""", [(int(r["id"]), season_id, room_rate_by_id[int(r["id"])]) for r in rooms])
        db.commit()
        return {"message": f"Đã tạo 1 mùa cao điểm và liên kết với {len(rooms)} phòng.",
                "id": season_id, "total_rooms": len(rooms), "created_links": len(rooms),
                "tu_ngay": season.tu_ngay, "den_ngay": season.den_ngay,
                "room_rates": [{"phong_id": int(r["id"]), "so_phong": r["so_phong"],
                                "ten_loai_phong": r["ten_loai_phong"],
                                "he_so_gia": room_rate_by_id[int(r["id"])]} for r in rooms]}
    except HTTPException:
        db.rollback(); raise
    except IntegrityError as exc:
        db.rollback(); raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Error as exc:
        db.rollback(); raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        cursor.close()


@router.post("/", status_code=201)
def create_peak_season(season: PeakSeasonCreate, db=Depends(get_db)):
    validate_dates(season.tu_ngay, season.den_ngay)
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("""SELECT p.id, p.so_phong, lp.ten AS ten_loai_phong
            FROM phong p JOIN loaiphong lp ON lp.id=p.loai_phong_id
            WHERE p.id=%s FOR UPDATE""", (season.phong_id,))
        room = cursor.fetchone()
        if not room: raise HTTPException(status_code=404, detail="Phòng không tồn tại.")
        try:
            derived_rate = peak_surcharge_for_room_type(room["ten_loai_phong"])
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        cursor.execute("""SELECT m.id FROM muacaodiem m JOIN phong_muacaodiem pm ON pm.muacaodiem_id=m.id
            WHERE pm.phong_id=%s AND m.tu_ngay<=%s AND m.den_ngay>=%s LIMIT 1 FOR UPDATE""",
            (season.phong_id, season.den_ngay, season.tu_ngay))
        if cursor.fetchone(): raise HTTPException(status_code=409, detail="Phòng đã có mùa cao điểm trùng ngày.")
        cursor.execute("INSERT INTO muacaodiem (tu_ngay,den_ngay) VALUES (%s,%s)", (season.tu_ngay,season.den_ngay))
        sid=cursor.lastrowid
        cursor.execute("INSERT INTO phong_muacaodiem (phong_id,muacaodiem_id,he_so_phu_thu) VALUES (%s,%s,%s)",
                       (season.phong_id,sid,derived_rate))
        db.commit()
        return {"message":"Thêm mùa cao điểm thành công.","id":sid,
                "peak_season":{"id":sid,"phong_id":season.phong_id,"so_phong":room["so_phong"],
                               "tu_ngay":season.tu_ngay,"den_ngay":season.den_ngay,"he_so_gia":derived_rate,
                               "ten_loai_phong":room["ten_loai_phong"]}}
    except HTTPException:
        db.rollback(); raise
    except IntegrityError as exc:
        db.rollback(); raise HTTPException(status_code=409,detail=str(exc)) from exc
    except Error as exc:
        db.rollback(); raise HTTPException(status_code=500,detail=str(exc)) from exc
    finally: cursor.close()


@router.put("/{season_id}")
def update_peak_season(season_id: int, season: PeakSeasonUpdate, db=Depends(get_db)):
    validate_dates(season.tu_ngay, season.den_ngay)
    cursor=db.cursor(dictionary=True)
    try:
        cursor.execute("""SELECT p.id, p.so_phong, lp.ten AS ten_loai_phong
            FROM phong p JOIN loaiphong lp ON lp.id=p.loai_phong_id WHERE p.id=%s""",(season.phong_id,))
        room = cursor.fetchone()
        if not room: raise HTTPException(status_code=404,detail="Phòng không tồn tại.")
        try:
            derived_rate = peak_surcharge_for_room_type(room["ten_loai_phong"])
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        cursor.execute("SELECT id FROM muacaodiem WHERE id=%s FOR UPDATE",(season_id,))
        if not cursor.fetchone(): raise HTTPException(status_code=404,detail="Không tìm thấy mùa cao điểm.")
        cursor.execute("""SELECT m.id FROM muacaodiem m JOIN phong_muacaodiem pm ON pm.muacaodiem_id=m.id
            WHERE pm.phong_id=%s AND m.id<>%s AND m.tu_ngay<=%s AND m.den_ngay>=%s LIMIT 1""",
            (season.phong_id,season_id,season.den_ngay,season.tu_ngay))
        if cursor.fetchone(): raise HTTPException(status_code=409,detail="Khoảng ngày bị trùng với mùa cao điểm khác của phòng.")
        cursor.execute("UPDATE muacaodiem SET tu_ngay=%s,den_ngay=%s WHERE id=%s",(season.tu_ngay,season.den_ngay,season_id))
        cursor.execute("""INSERT INTO phong_muacaodiem (phong_id,muacaodiem_id,he_so_phu_thu)
            VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE he_so_phu_thu=VALUES(he_so_phu_thu)""",
            (season.phong_id,season_id,derived_rate))
        db.commit()
        return {"message":"Cập nhật mùa cao điểm/phụ thu thành công.","peak_season":{"id":season_id,"phong_id":season.phong_id,"tu_ngay":season.tu_ngay,"den_ngay":season.den_ngay,"he_so_gia":derived_rate,
                               "ten_loai_phong":room["ten_loai_phong"]}}
    except HTTPException:
        db.rollback(); raise
    except Error as exc:
        db.rollback(); raise HTTPException(status_code=409,detail=str(exc)) from exc
    finally: cursor.close()


@router.delete("/{season_id}")
def delete_peak_season(season_id: int, db=Depends(get_db)):
    cursor=db.cursor()
    try:
        cursor.execute("DELETE FROM muacaodiem WHERE id=%s",(season_id,))
        if cursor.rowcount == 0: raise HTTPException(status_code=404,detail="Không tìm thấy mùa cao điểm.")
        db.commit()
        return {"message":"Đã xóa mùa cao điểm và các liên kết phòng.","id":season_id}
    except HTTPException:
        db.rollback(); raise
    except Error as exc:
        db.rollback(); raise HTTPException(status_code=409,detail=str(exc)) from exc
    finally: cursor.close()
