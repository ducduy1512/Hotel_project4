"""Embedded SQLite database layer for Hotel Management.

The application creates data/hotel_management.db on first launch, importing the
schema, demo data, views and SQLite triggers exactly once. No MySQL server is used.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

PROJECT_DIR = Path(__file__).resolve().parent
SQLITE_DIR = PROJECT_DIR / "sqlite_database"
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = Path(os.getenv("HOTEL_SQLITE_PATH", str(DATA_DIR / "hotel_management.db"))).expanduser()
DB_CONFIG = {"database": str(DB_PATH), "engine": "SQLite"}

Error = sqlite3.Error
IntegrityError = sqlite3.IntegrityError

_init_lock = threading.Lock()
_initialized_path: set[str] = set()


def _read_sql(path: Path) -> str:
    if not path.exists():
        raise RuntimeError(f"Thiếu file database bắt buộc: {path}")
    return path.read_text(encoding="utf-8")


def initialize_database() -> None:
    """Create and seed the local DB once; never overwrite an existing DB."""
    key = str(DB_PATH.resolve())
    with _init_lock:
        if key in _initialized_path and DB_PATH.exists():
            return
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        if DB_PATH.exists() and DB_PATH.stat().st_size > 0:
            # Never overwrite a user's existing database. Detect an interrupted
            # or invalid first initialization and explain how to recover safely.
            try:
                check_conn = sqlite3.connect(DB_PATH, timeout=5)
                existing_tables = {r[0] for r in check_conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()}
                check_conn.close()
            except sqlite3.Error as exc:
                raise RuntimeError(f"File SQLite hiện có nhưng không đọc được: {DB_PATH}: {exc}") from exc
            required = {"booking", "dichvu", "hoadon", "khach", "loaiphong", "muacaodiem",
                        "pay", "payment_qr", "phong", "phong_muacaodiem", "sepay_webhook_events", "users"}
            missing = sorted(required - existing_tables)
            if missing:
                raise RuntimeError(
                    f"Database {DB_PATH} chưa khởi tạo đầy đủ (thiếu: {', '.join(missing)}). "
                    "Hãy sao lưu file rồi xóa database bị lỗi để project tự tạo lại."
                )
            _initialized_path.add(key)
            return
        conn = sqlite3.connect(DB_PATH, timeout=30)
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.executescript(_read_sql(SQLITE_DIR / "schema.sql"))
            # Import historical booking/payment rows before enabling FK checks;
            # the dump's insert sequence is not dependency ordered. Validate the
            # complete dataset immediately after all rows have been restored.
            conn.execute("PRAGMA foreign_keys=OFF")
            conn.executescript(_read_sql(SQLITE_DIR / "seed_data.sql"))
            conn.execute("PRAGMA foreign_keys=ON")
            conn.executescript(_read_sql(SQLITE_DIR / "views.sql"))
            conn.executescript(_read_sql(SQLITE_DIR / "triggers.sql"))
            conn.commit()
            violations = conn.execute("PRAGMA foreign_key_check").fetchall()
            if violations:
                raise RuntimeError(f"Dữ liệu khởi tạo vi phạm khóa ngoại: {violations[:5]}")
            _initialized_path.add(key)
        except Exception:
            conn.rollback()
            # Close before unlinking: Windows refuses to remove an open SQLite file.
            conn.close()
            if DB_PATH.exists():
                try:
                    DB_PATH.unlink()
                except OSError:
                    # Keep the original initialization exception as the useful one.
                    pass
            raise
        finally:
            try:
                conn.close()
            except Exception:
                pass


def _to_iso(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat(sep=" ") if isinstance(value, datetime) else value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def _translate_sql(sql: str) -> str:
    text = sql.strip()
    # MySQL row-lock suffixes: SQLite serializes writes with BEGIN IMMEDIATE.
    text = re.sub(r"\s+FOR\s+(?:UPDATE|SHARE)\b", "", text, flags=re.I)
    text = re.sub(r"\s+LOCK\s+IN\s+SHARE\s+MODE\b", "", text, flags=re.I)
    text = re.sub(r"DATE_ADD\(([^,()]+),\s*INTERVAL\s+1\s+DAY\)", r"date(\1, '+1 day')", text, flags=re.I)
    text = re.sub(r"DATEDIFF\(([^,()]+),\s*([^()]+)\)", r"CAST(julianday(\1)-julianday(\2) AS INTEGER)", text, flags=re.I)
    # MySQL ordered GROUP_CONCAT syntax used in a single report endpoint.
    text = re.sub(
        r"GROUP_CONCAT\(\s*DISTINCT\s+([\w.]+)\s+ORDER\s+BY\s+[\w.]+\s+SEPARATOR\s+'([^']*)'\s*\)",
        lambda m: f"REPLACE(GROUP_CONCAT(DISTINCT {m.group(1)}), ',', '{m.group(2)}')",
        text, flags=re.I | re.S,
    )
    text = re.sub(r"\bNOW\(\)", "CURRENT_TIMESTAMP", text, flags=re.I)
    text = re.sub(r"\bCURDATE\(\)", "date('now','localtime')", text, flags=re.I)
    text = re.sub(r"\bDATABASE\(\)", "'hotel_management_erd'", text, flags=re.I)
    # One route uses MySQL's upsert syntax for a room-season rate.
    text = re.sub(
        r"ON\s+DUPLICATE\s+KEY\s+UPDATE\s+he_so_phu_thu\s*=\s*VALUES\(he_so_phu_thu\)",
        "ON CONFLICT(phong_id, muacaodiem_id) DO UPDATE SET he_so_phu_thu=excluded.he_so_phu_thu",
        text, flags=re.I,
    )
    text = text.replace("%s", "?")
    return text


class _ResultCursor:
    def __init__(self, rows, dictionary=True):
        self._rows = list(rows or [])
        self._index = 0
        self._dictionary = dictionary
        self.with_rows = bool(self._rows)

    def fetchall(self):
        rows = self._rows[self._index:]
        self._index = len(self._rows)
        return rows

    def fetchone(self):
        if self._index >= len(self._rows):
            return None
        row = self._rows[self._index]
        self._index += 1
        return row

    def close(self):
        self._rows = []


class SQLiteCursor:
    def __init__(self, connection: "SQLiteConnection", dictionary: bool = False):
        self.connection = connection
        self.dictionary = dictionary
        self.raw = connection.raw.cursor()
        self._result_sets: list[list[Any]] = []
        self._result_index = 0
        self._current_rows = None
        self._call_row_index = 0
        self.with_rows = False
        self.description = None

    @property
    def lastrowid(self):
        return self.raw.lastrowid

    @property
    def rowcount(self):
        return self.raw.rowcount

    def _convert(self, row):
        if row is None:
            return None
        if isinstance(row, sqlite3.Row):
            return {key: row[key] for key in row.keys()} if self.dictionary else tuple(row)
        return row

    def execute(self, sql, params=None):
        call = re.match(r"^\s*CALL\s+(\w+)\s*\((.*)\)\s*;?\s*$", sql, flags=re.I | re.S)
        if call:
            values = params or ()
            self.callproc(call.group(1), values)
            self.with_rows = bool(self._result_sets)
            return self
        self._result_sets = []
        self._result_index = 0
        self._current_rows = None
        translated = _translate_sql(sql)
        adapted = tuple(_to_iso(v) for v in (params or ()))
        self.raw.execute(translated, adapted)
        self.description = self.raw.description
        self.with_rows = self.description is not None
        return self

    def executemany(self, sql, seq_of_params):
        self._result_sets = []
        self.raw.executemany(_translate_sql(sql), [tuple(_to_iso(v) for v in row) for row in seq_of_params])
        self.description = self.raw.description
        self.with_rows = self.description is not None
        return self

    def fetchone(self):
        if self._result_sets and self._result_index < len(self._result_sets):
            rows = self._result_sets[self._result_index]
            if self._call_row_index >= len(rows):
                return None
            row = rows[self._call_row_index]
            self._call_row_index += 1
            return row
        return self._convert(self.raw.fetchone())

    def fetchall(self):
        if self._result_sets and self._result_index < len(self._result_sets):
            rows = self._result_sets[self._result_index][self._call_row_index:]
            self._call_row_index = len(self._result_sets[self._result_index])
            return rows
        return [self._convert(row) for row in self.raw.fetchall()]

    def stored_results(self):
        results = self._result_sets[self._result_index:]
        self._result_index = len(self._result_sets)
        return [_ResultCursor(rows, self.dictionary) for rows in results]

    def nextset(self):
        if self._result_index < len(self._result_sets) - 1:
            self._result_index += 1
            self._call_row_index = 0
            self.with_rows = True
            return True
        self.with_rows = False
        return None

    def callproc(self, procedure_name, args=()):
        self._result_sets = _call_procedure(self.connection, procedure_name, list(args or []), self.dictionary)
        self._result_index = 0
        self._call_row_index = 0
        self.with_rows = bool(self._result_sets)
        if self._result_sets:
            self._current_rows = self._result_sets[0]
        return args

    def close(self):
        self.raw.close()


class SQLiteConnection:
    def __init__(self, raw: sqlite3.Connection):
        self.raw = raw

    def cursor(self, dictionary=False, **kwargs):
        return SQLiteCursor(self, dictionary=dictionary)

    def is_connected(self):
        try:
            self.raw.execute("SELECT 1")
            return True
        except sqlite3.Error:
            return False

    @property
    def in_transaction(self):
        return self.raw.in_transaction

    def start_transaction(self):
        if not self.raw.in_transaction:
            self.raw.execute("BEGIN IMMEDIATE")

    def commit(self):
        if self.raw.in_transaction:
            self.raw.commit()

    def rollback(self):
        if self.raw.in_transaction:
            self.raw.rollback()

    def close(self):
        self.raw.close()


def get_connection() -> SQLiteConnection:
    initialize_database()
    conn = sqlite3.connect(DB_PATH, timeout=30, isolation_level="DEFERRED", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.create_function("GREATEST", -1, lambda *values: max(v for v in values if v is not None) if any(v is not None for v in values) else None)
    conn.create_function("LEAST", -1, lambda *values: min(v for v in values if v is not None) if any(v is not None for v in values) else None)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute("PRAGMA journal_mode=WAL")
    return SQLiteConnection(conn)


def get_db():
    connection = get_connection()
    try:
        yield connection
    finally:
        connection.close()


def _rows(conn, sql, params=()):
    cur = conn.raw.execute(_translate_sql(sql), tuple(_to_iso(v) for v in params))
    return [dict(r) for r in cur.fetchall()]


def _one(conn, sql, params=()):
    rows = _rows(conn, sql, params)
    return rows[0] if rows else None


def _raise(message):
    raise sqlite3.IntegrityError(message)


def _season_snapshot(conn, room_id, checkin, checkout):
    room = _one(conn, "SELECT lp.gia_co_ban FROM phong p JOIN loaiphong lp ON lp.id=p.loai_phong_id WHERE p.id=?", (room_id,))
    if not room:
        _raise("Phong khong ton tai")
    base = Decimal(str(room["gia_co_ban"]))
    start = date.fromisoformat(str(checkin)[:10])
    end = date.fromisoformat(str(checkout)[:10])
    room_total = Decimal("0.00")
    surcharge_total = Decimal("0.00")
    applied = 0
    details = []
    day = start
    while day < end:
        season = _one(conn, """SELECT m.id, pm.he_so_phu_thu FROM muacaodiem m
            JOIN phong_muacaodiem pm ON pm.muacaodiem_id=m.id
            WHERE pm.phong_id=? AND ? BETWEEN m.tu_ngay AND m.den_ngay
            ORDER BY m.id DESC LIMIT 1""", (room_id, day.isoformat()))
        rate = Decimal(str(season["he_so_phu_thu"])) if season else Decimal("0.00")
        fee = (base * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if season:
            applied = 1
        room_total += base
        surcharge_total += fee
        details.append({"ngay": day.isoformat(), "mua_cao_diem_id": season["id"] if season else None,
                        "he_so_gia": float(rate), "gia_co_ban": float(base), "tien_dem": float(base),
                        "phi_mua_cao_diem": float(fee)})
        day += timedelta(days=1)
    return (float(room_total), float(surcharge_total), applied,
            json.dumps(details, ensure_ascii=False, separators=(",", ":")))


def _create_booking(conn, room_id, customer_id, checkin, checkout, selected_services=None):
    if not checkin or not checkout or str(checkout) <= str(checkin):
        _raise("Ngay nhan va ngay tra khong hop le")
    customer = _one(conn, "SELECT id FROM khach WHERE id=?", (customer_id,))
    room = _one(conn, "SELECT id,trang_thai FROM phong WHERE id=?", (room_id,))
    if not customer:
        _raise("Khach hang khong ton tai")
    if not room or room["trang_thai"] == "BAO_TRI":
        _raise("Phong khong ton tai hoac dang bao tri")
    conflict = _one(conn, """SELECT id FROM booking WHERE phong_id=? AND trang_thai<>'DA_HUY'
        AND ? < ngay_tra AND ? > ngay_nhan LIMIT 1""", (room_id, checkin, checkout))
    if conflict:
        _raise("Phong da duoc dat trong khoang thoi gian nay")
    room_total, surcharge, applied, detail = _season_snapshot(conn, room_id, checkin, checkout)
    cur = conn.raw.execute("""INSERT INTO booking(phong_id,khach_id,ngay_nhan,ngay_tra,trang_thai,
        tien_phong_du_kien,tien_phu_phi_mua_cao_diem,ap_dung_mua_cao_diem,chi_tiet_mua_cao_diem)
        VALUES(?,?,?,?,?,?,?,?,?)""", (room_id, customer_id, str(checkin), str(checkout),
        "CHO_XAC_NHAN", room_total, surcharge, applied, detail))
    booking_id = cur.lastrowid
    # SQLite after-insert trigger copies free default services. Customer booking
    # replaces that copy with exactly the services explicitly selected.
    if selected_services is not None:
        try:
            selected = json.loads(selected_services) if isinstance(selected_services, str) else selected_services
        except Exception:
            _raise("Danh sach dich vu phai la JSON ARRAY")
        if not isinstance(selected, list):
            _raise("Danh sach dich vu phai la JSON ARRAY")
        ids = [int(x.get("dichvu_id", 0)) for x in selected]
        if len(ids) != len(set(ids)):
            _raise("Khong duoc chon trung dich vu")
        conn.raw.execute("DELETE FROM dichvu WHERE booking_id=?", (booking_id,))
        days = (date.fromisoformat(str(checkout)[:10]) - date.fromisoformat(str(checkin)[:10])).days
        for item in selected:
            service = _one(conn, "SELECT * FROM dichvu WHERE id=? AND booking_id IS NULL AND dang_hoat_dong=1", (int(item.get("dichvu_id", 0)),))
            qty = int(item.get("so_luong", 0))
            if not service or qty <= 0:
                _raise("Dich vu khong hop le, khong thuoc phong hoac da ngung kinh doanh")
            allowed = ((service["loai_dichvu"] == "MAC_DINH" and service["phong_id"] == room_id) or
                       (service["loai_dichvu"] == "TUY_CHON" and service["phong_id"] is None and service["don_gia"] > 0))
            if not allowed:
                _raise("Dich vu khong hop le, khong thuoc phong hoac da ngung kinh doanh")
            if service["don_vi_tinh"] == "giường/đêm":
                qty *= days
            conn.raw.execute("""INSERT INTO dichvu(ten,don_gia,so_luong,phong_id,booking_id,loai_dichvu,nhom_dich_vu,don_vi_tinh,dang_hoat_dong)
                VALUES(?,?,?,?,?,?,?,?,1)""", (service["ten"],service["don_gia"],qty,room_id,booking_id,
                service["loai_dichvu"],service["nhom_dich_vu"],service["don_vi_tinh"]))
    return booking_id


def _create_invoice_payment(conn, booking_id, method):
    booking = _one(conn, "SELECT * FROM booking WHERE id=?", (booking_id,))
    if not booking:
        _raise("Booking khong ton tai")
    if booking["trang_thai"] == "DA_HUY":
        _raise("Khong the lap hoa don cho booking da huy")
    if method not in ("TIEN_MAT", "CHUYEN_KHOAN", "THE"):
        _raise("Phuong thuc thanh toan khong hop le")
    existing = _one(conn, "SELECT id FROM pay WHERE booking_id=? AND status IN ('CHO_THANH_TOAN','THANH_CONG')", (booking_id,))
    if existing:
        _raise("Booking da co giao dich dang cho hoac thanh toan thanh cong")
    room_total = float(booking["tien_phong_du_kien"] or 0)
    peak_total = float(booking["tien_phu_phi_mua_cao_diem"] or 0)
    service_total = float(_one(conn,"SELECT COALESCE(SUM(don_gia*so_luong),0) AS total FROM dichvu WHERE booking_id=?",(booking_id,))["total"] or 0)
    total = room_total + peak_total + service_total
    paycur = conn.raw.execute("""INSERT INTO pay(booking_id,khach_id,so_tien,ngay_thanh_toan,method,status,
        tien_phong_ap_dung,tien_phu_phi_mua_cao_diem,ap_dung_mua_cao_diem,chi_tiet_mua_cao_diem)
        VALUES(?,?,?,CURRENT_TIMESTAMP,?,'CHO_THANH_TOAN',?,?,?,?)""",
        (booking_id,booking["khach_id"],total,method,room_total,peak_total,booking["ap_dung_mua_cao_diem"],booking["chi_tiet_mua_cao_diem"]))
    pay_id = paycur.lastrowid
    invcur = conn.raw.execute("""INSERT INTO hoadon(pay_id,tien_phong,tien_phu_phi_mua_cao_diem,tien_dich_vu,tong_tien)
        VALUES(?,?,?,?,?)""",(pay_id,room_total,peak_total,service_total,total))
    return pay_id, invcur.lastrowid, {"booking_id":booking_id,"khach_id":booking["khach_id"],"pay_id":pay_id,
        "tien_phong":room_total,"tien_phu_phi_mua_cao_diem":peak_total,"tien_dich_vu":service_total,
        "tong_tien":total,"phuong_thuc":method,"trang_thai_thanh_toan":"CHO_THANH_TOAN"}


def _call_procedure(conn, name, args, dictionary):
    name = name.lower()
    result_sets = []
    own_tx = not conn.raw.in_transaction
    if own_tx:
        conn.raw.execute("BEGIN IMMEDIATE")
    try:
        if name == "sp_kiem_tra_phong_trong":
            start, end = args
            if not start or not end or str(end) <= str(start): _raise("Ngay tra phai sau ngay nhan")
            rows = _rows(conn, """SELECT p.id AS phong_id,p.so_phong,lp.ten AS loai_phong,lp.gia_co_ban,lp.suc_chua,p.trang_thai
                FROM phong p JOIN loaiphong lp ON p.loai_phong_id=lp.id WHERE p.trang_thai<>'BAO_TRI'
                AND NOT EXISTS(SELECT 1 FROM booking b WHERE b.phong_id=p.id AND b.trang_thai<>'DA_HUY'
                AND ? < b.ngay_tra AND ? > b.ngay_nhan) ORDER BY p.so_phong""", (start,end))
            result_sets = [rows]
        elif name in ("sp_tao_booking", "sp_tao_booking_customer"):
            room, customer, start, end = args[:4]
            selected = args[4] if name.endswith("customer") and len(args)>4 else None
            bid = _create_booking(conn, room, customer, start, end, selected)
            result_sets = [[{"booking_id":bid,"phong_id":room,"khach_id":customer,"ngay_nhan":str(start),"ngay_tra":str(end),"trang_thai":"CHO_XAC_NHAN"}]]
        elif name == "sp_huy_booking":
            bid=int(args[0]); b=_one(conn,"SELECT * FROM booking WHERE id=?",(bid,))
            if not b: _raise("Booking khong ton tai")
            if b["trang_thai"]=="DA_HUY": _raise("Booking da duoc huy truoc do")
            if b["trang_thai"] in ("DANG_O","HOAN_THANH"): _raise("Khong the huy booking dang o hoac da hoan thanh")
            pay=_one(conn,"SELECT status FROM pay WHERE booking_id=? AND status IN ('THANH_CONG','CHO_THANH_TOAN') LIMIT 1",(bid,))
            if pay and pay["status"]=="THANH_CONG": _raise("Booking da thanh toan thanh cong, can xu ly hoan tien truoc")
            if pay: _raise("Booking con giao dich cho thanh toan; hay huy/that bai giao dich truoc")
            conn.raw.execute("UPDATE booking SET trang_thai='DA_HUY' WHERE id=?",(bid,))
            result_sets=[[{"booking_id":bid,"trang_thai_moi":"DA_HUY"}]]
        elif name in ("sp_xac_nhan_booking","sp_nhan_phong","sp_tra_phong"):
            bid=int(args[0]); b=_one(conn,"SELECT trang_thai FROM booking WHERE id=?",(bid,))
            if not b: _raise("Booking khong ton tai")
            target={"sp_xac_nhan_booking":("CHO_XAC_NHAN","DA_XAC_NHAN"),"sp_nhan_phong":("DA_XAC_NHAN","DANG_O"),"sp_tra_phong":("DANG_O","HOAN_THANH")}[name]
            if b["trang_thai"]!=target[0]:
                msg={"sp_xac_nhan_booking":"Chi xac nhan Booking dang o trang thai CHO_XAC_NHAN","sp_nhan_phong":"Chi nhan phong cho booking da xac nhan","sp_tra_phong":"Booking khong o trang thai dang o"}[name]
                _raise(msg)
            conn.raw.execute("UPDATE booking SET trang_thai=? WHERE id=?",(target[1],bid))
            result_sets=[_rows(conn,"SELECT id AS booking_id,trang_thai FROM booking WHERE id=?",(bid,))]
        elif name == "sp_cap_nhat_booking":
            bid, room_id, customer_id, start, end = args
            current = _one(conn, "SELECT * FROM booking WHERE id=?", (bid,))
            if not current: _raise("Booking khong ton tai")
            if current["trang_thai"] not in ("CHO_XAC_NHAN", "DA_XAC_NHAN"):
                _raise("Chi duoc sua Booking dang cho hoac da xac nhan")
            if _one(conn, "SELECT id FROM pay WHERE booking_id=? LIMIT 1", (bid,)):
                _raise("Booking da co giao dich Pay, khong duoc doi phong hoac ngay")
            room = _one(conn, "SELECT trang_thai FROM phong WHERE id=?", (room_id,))
            if not room or room["trang_thai"] == "BAO_TRI": _raise("Phong moi khong ton tai hoac dang bao tri")
            if not _one(conn, "SELECT id FROM khach WHERE id=?", (customer_id,)): _raise("Khach hang khong ton tai")
            if not start or not end or str(end) <= str(start): _raise("Ngay nhan va ngay tra khong hop le")
            conflict = _one(conn, "SELECT id FROM booking WHERE phong_id=? AND id<>? AND trang_thai<>'DA_HUY' AND ?<ngay_tra AND ?>ngay_nhan LIMIT 1", (room_id,bid,start,end))
            if conflict: _raise("Cap nhat that bai: phong da co Booking trung lich")
            room_total, surcharge, applied, detail = _season_snapshot(conn, room_id, start, end)
            conn.raw.execute("""UPDATE booking SET phong_id=?,khach_id=?,ngay_nhan=?,ngay_tra=?,
                tien_phong_du_kien=?,tien_phu_phi_mua_cao_diem=?,ap_dung_mua_cao_diem=?,chi_tiet_mua_cao_diem=? WHERE id=?""",
                (room_id,customer_id,str(start),str(end),room_total,surcharge,applied,detail,bid))
            # A room change/date change requires the free room-default services to be refreshed.
            conn.raw.execute("DELETE FROM dichvu WHERE booking_id=? AND loai_dichvu='MAC_DINH' AND don_gia=0", (bid,))
            conn.raw.execute("""INSERT INTO dichvu(ten,don_gia,so_luong,phong_id,booking_id,loai_dichvu,nhom_dich_vu,don_vi_tinh,dang_hoat_dong)
                SELECT ten,don_gia,so_luong,?,?,'MAC_DINH',nhom_dich_vu,don_vi_tinh,1 FROM dichvu
                WHERE phong_id=? AND booking_id IS NULL AND loai_dichvu='MAC_DINH' AND dang_hoat_dong=1 AND don_gia=0""",(room_id,bid,room_id))
            result_sets=[_rows(conn,"SELECT id AS booking_id,phong_id,khach_id,ngay_nhan,ngay_tra,trang_thai,tien_phong_du_kien,tien_phu_phi_mua_cao_diem,ap_dung_mua_cao_diem,chi_tiet_mua_cao_diem FROM booking WHERE id=?",(bid,))]
        elif name == "sp_tinh_tien_va_tao_hoa_don":
            result_sets=[[_create_invoice_payment(conn,int(args[0]),str(args[1]))[2]]]
        elif name == "sp_lich_su_booking":
            cid=int(args[0])
            if not _one(conn,"SELECT id FROM khach WHERE id=?",(cid,)): _raise("Khach hang khong ton tai")
            rows=_rows(conn,"""SELECT k.id AS khach_id,k.ho_ten,k.cccd,k.sdt,b.id AS booking_id,p.so_phong,lp.ten AS loai_phong,
                b.ngay_nhan,b.ngay_tra,CAST(julianday(b.ngay_tra)-julianday(b.ngay_nhan) AS INTEGER) AS so_dem,
                b.trang_thai AS trang_thai_booking,COALESCE((SELECT SUM(h.tong_tien) FROM pay py JOIN hoadon h ON py.id=h.pay_id WHERE py.booking_id=b.id),0) AS tong_tien_hoa_don,
                (SELECT group_concat(py.id || ': ' || py.status, '; ') FROM pay py WHERE py.booking_id=b.id) AS lich_su_thanh_toan
                FROM khach k LEFT JOIN booking b ON k.id=b.khach_id LEFT JOIN phong p ON b.phong_id=p.id
                LEFT JOIN loaiphong lp ON p.loai_phong_id=lp.id WHERE k.id=? ORDER BY b.ngay_nhan DESC""",(cid,))
            result_sets=[rows]
        elif name == "sp_thong_ke_doanh_thu":
            start,end=args
            if str(end)<str(start): _raise("Ngay ket thuc phai lon hon hoac bang ngay bat dau")
            result_sets=[_rows(conn,"""SELECT ? AS tu_ngay,? AS den_ngay,
                COALESCE(SUM(CASE WHEN status='THANH_CONG' THEN so_tien ELSE 0 END),0) AS tong_tien_thanh_cong,
                COALESCE(SUM(CASE WHEN status='HOAN_TIEN' THEN so_tien ELSE 0 END),0) AS tong_tien_hoan,
                COALESCE(SUM(CASE WHEN status='THANH_CONG' THEN so_tien WHEN status='HOAN_TIEN' THEN -so_tien ELSE 0 END),0) AS doanh_thu_thuc_thu,
                COALESCE(SUM(status='THANH_CONG'),0) AS so_giao_dich_thanh_cong,
                COALESCE(SUM(status='HOAN_TIEN'),0) AS so_giao_dich_hoan_tien FROM pay
                WHERE ngay_thanh_toan>=? AND ngay_thanh_toan<date(?,'+1 day')""",(str(start),str(end),str(start),str(end))),
                _rows(conn,"""SELECT method AS phuong_thuc_thanh_toan,
                SUM(CASE WHEN status='THANH_CONG' THEN so_tien WHEN status='HOAN_TIEN' THEN -so_tien ELSE 0 END) AS doanh_thu_thuc_thu,
                COALESCE(SUM(status='THANH_CONG'),0) AS so_giao_dich_thanh_cong FROM pay
                WHERE ngay_thanh_toan>=? AND ngay_thanh_toan<date(?,'+1 day') GROUP BY method ORDER BY doanh_thu_thuc_thu DESC""",(str(start),str(end))),
                _rows(conn,"SELECT COUNT(*) AS so_booking_hoan_thanh FROM booking WHERE trang_thai='HOAN_THANH' AND ngay_tra>=? AND ngay_tra<date(?,'+1 day')",(str(start),str(end)))]
        elif name == "sp_them_khach_hang":
            vals=[str(x).strip() for x in args[:3]]
            if any(not x for x in vals): _raise("Ho ten, CCCD va so dien thoai khong duoc de trong")
            cur=conn.raw.execute("INSERT INTO khach(ho_ten,cccd,sdt) VALUES(?,?,?)",vals); kid=cur.lastrowid
            result_sets=[_rows(conn,"SELECT id AS khach_id,ho_ten,cccd,sdt FROM khach WHERE id=?",(kid,))]
        elif name == "sp_cap_nhat_thong_tin_phong":
            rid,room_no,type_id,status=args
            r=_one(conn,"SELECT id FROM phong WHERE id=?",(rid,))
            if not r: _raise("Phong khong ton tai")
            if not room_no or not str(room_no).strip(): _raise("So phong khong duoc de trong")
            if status not in ("SAN_SANG","BAO_TRI"): _raise("Chi duoc cap nhat SAN_SANG hoac BAO_TRI; DANG_SU_DUNG do Booking tu dong quan ly")
            if _one(conn,"SELECT id FROM booking WHERE phong_id=? AND trang_thai='DANG_O'",(rid,)): _raise("Phong dang co khach luu tru, khong the thay doi trang thai phong")
            if status=="BAO_TRI" and _one(conn,"SELECT id FROM booking WHERE phong_id=? AND trang_thai IN ('CHO_XAC_NHAN','DA_XAC_NHAN') AND ngay_tra>date('now','localtime')",(rid,)):
                _raise("Phong con Booking hien tai/tuong lai, can xu ly Booking truoc khi bao tri")
            conn.raw.execute("UPDATE phong SET so_phong=?,loai_phong_id=?,trang_thai=? WHERE id=?",(str(room_no).strip(),type_id,status,rid))
            result_sets=[_rows(conn,"SELECT id AS phong_id,so_phong,loai_phong_id,trang_thai FROM phong WHERE id=?",(rid,))]
        elif name == "sp_hoan_tien":
            pid=int(args[0]); p=_one(conn,"SELECT status FROM pay WHERE id=?",(pid,))
            if not p: _raise("Giao dich thanh toan khong ton tai")
            if p["status"]!="THANH_CONG": _raise("Chi hoan tien cho giao dich da THANH_CONG")
            conn.raw.execute("UPDATE pay SET status='HOAN_TIEN' WHERE id=?",(pid,))
            result_sets=[_rows(conn,"SELECT id AS pay_id,booking_id,so_tien,method,status AS trang_thai_thanh_toan FROM pay WHERE id=?",(pid,))]
        elif name == "sp_xac_nhan_thanh_toan":
            pid=int(args[0]); p=_one(conn,"SELECT status FROM pay WHERE id=?",(pid,))
            if not p: _raise("Giao dich thanh toan khong ton tai")
            if p["status"]!="CHO_THANH_TOAN": _raise("Chi xac nhan giao dich dang CHO_THANH_TOAN")
            conn.raw.execute("UPDATE pay SET status='THANH_CONG' WHERE id=?",(pid,))
            result_sets=[_rows(conn,"""SELECT py.id AS pay_id,py.booking_id,py.so_tien,py.method,py.status AS trang_thai_thanh_toan,
                b.trang_thai AS trang_thai_booking,hd.id AS hoadon_id,hd.tong_tien FROM pay py JOIN booking b ON b.id=py.booking_id
                LEFT JOIN hoadon hd ON hd.pay_id=py.id WHERE py.id=?""",(pid,))]
        else:
            _raise(f"Stored Procedure '{name}' chua duoc chuyen sang SQLite")
        if own_tx:
            conn.raw.commit()
        return result_sets
    except Exception:
        if own_tx:
            conn.raw.rollback()
        raise
