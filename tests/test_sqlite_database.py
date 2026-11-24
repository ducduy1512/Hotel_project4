from __future__ import annotations

import sqlite3

import database


def _fresh_database(monkeypatch, tmp_path):
    db_path = tmp_path / "hotel_test.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    database._initialized_path.discard(str(db_path.resolve()))
    database.initialize_database()
    return db_path


def test_database_initializes_schema_seed_and_integrity(monkeypatch, tmp_path):
    db_path = _fresh_database(monkeypatch, tmp_path)
    conn = sqlite3.connect(db_path)
    try:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        views = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='view'")}
        triggers = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
        expected_tables = {
            "booking", "dichvu", "hoadon", "khach", "loaiphong", "muacaodiem",
            "pay", "payment_qr", "phong", "phong_muacaodiem", "sepay_webhook_events", "users",
        }
        assert expected_tables.issubset(tables)
        assert len(views) == 10
        assert len(triggers) == 17
        assert conn.execute("SELECT COUNT(*) FROM booking").fetchone()[0] == 26
        assert conn.execute("SELECT COUNT(*) FROM dichvu").fetchone()[0] == 176
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        conn.close()


def test_database_does_not_overwrite_existing_user_data(monkeypatch, tmp_path):
    db_path = _fresh_database(monkeypatch, tmp_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("UPDATE khach SET ho_ten='SQLite Keep Test' WHERE id=1")
        conn.commit()
    finally:
        conn.close()

    # Simulate a new application process using the same existing DB file.
    database._initialized_path.discard(str(db_path.resolve()))
    database.initialize_database()
    conn = sqlite3.connect(db_path)
    try:
        name = conn.execute("SELECT ho_ten FROM khach WHERE id=1").fetchone()[0]
        assert name == "SQLite Keep Test"
    finally:
        conn.close()


def test_business_flow_create_booking_payment_invoice(monkeypatch, tmp_path):
    db_path = _fresh_database(monkeypatch, tmp_path)
    conn = database.get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id FROM phong WHERE trang_thai='SAN_SANG' ORDER BY id LIMIT 1")
        room_id = cursor.fetchone()["id"]
        cursor.execute("SELECT id FROM khach ORDER BY id LIMIT 1")
        customer_id = cursor.fetchone()["id"]

        cursor.callproc("sp_tao_booking", [room_id, customer_id, "2027-02-10", "2027-02-12"])
        created = []
        for result in cursor.stored_results():
            created.extend(result.fetchall())
            result.close()
        booking_id = created[0]["booking_id"]

        cursor.callproc("sp_tinh_tien_va_tao_hoa_don", [booking_id, "CHUYEN_KHOAN"])
        created_payment = []
        for result in cursor.stored_results():
            created_payment.extend(result.fetchall())
            result.close()
        assert created_payment[0]["pay_id"] > 0

        pay_id = created_payment[0]["pay_id"]
        cursor.execute("SELECT tong_tien FROM hoadon WHERE pay_id=?", (pay_id,))
        invoice = cursor.fetchone()
        assert invoice is not None

        cursor.execute("UPDATE pay SET status='THANH_CONG' WHERE id=?", (pay_id,))
        conn.commit()
        cursor.execute("SELECT trang_thai FROM booking WHERE id=?", (booking_id,))
        assert cursor.fetchone()["trang_thai"] == "DA_XAC_NHAN"
    finally:
        cursor.close()
        conn.close()
