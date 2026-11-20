-- HOTEL MANAGEMENT SYSTEM - SQL MODULE
-- Database: hotel_management_erd
-- ERD: 8 business tables + 3 support tables (users / QR / webhook audit)
-- Run files in this order:
-- 1) Hotel_Table.sql
-- 2) Hotel_InsertData.sql
-- 3) Hotel_Procedures.sql
-- 4) Hotel_Trigger.sql
-- 5) Hotel_Report.sql
-- 6) Hotel_TestCase.sql
-- MySQL 8.0.16+ is required for enforced CHECK constraints.

USE hotel_management_erd;
SET NAMES utf8mb4;

-- HOTEL TEST CASE / OBJECT INVENTORY
-- Run after: Hotel_Table.sql -> Hotel_InsertData.sql -> Hotel_Procedures.sql
--            -> Hotel_Trigger.sql -> Hotel_Report.sql

-- A. Object counts: 11 tables (8 ERD + 3 support), 15 procedures, 15 triggers, 10 views.
SELECT 'BASE_TABLES' AS object_type, COUNT(*) AS actual_count, 11 AS expected_count,
       IF(COUNT(*) = 11, 'PASS', 'CHECK') AS result
FROM information_schema.tables
WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE';

SELECT 'QR_SUPPORT_TABLES' AS object_type, COUNT(*) AS actual_count, 2 AS expected_count,
       IF(COUNT(*) = 2, 'PASS', 'CHECK') AS result
FROM information_schema.tables
WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE'
  AND table_name IN ('payment_qr', 'sepay_webhook_events');

SELECT 'STORED_PROCEDURES' AS object_type, COUNT(*) AS actual_count, 15 AS expected_count,
       IF(COUNT(*) = 15, 'PASS', 'CHECK') AS result
FROM information_schema.routines
WHERE routine_schema = DATABASE() AND routine_type = 'PROCEDURE';

SELECT 'TRIGGERS' AS object_type, COUNT(*) AS actual_count, 15 AS expected_count,
       IF(COUNT(*) = 15, 'PASS', 'CHECK') AS result
FROM information_schema.triggers
WHERE trigger_schema = DATABASE();

SELECT 'VIEWS' AS object_type, COUNT(*) AS actual_count, 10 AS expected_count,
       IF(COUNT(*) = 10, 'PASS', 'CHECK') AS result
FROM information_schema.views
WHERE table_schema = DATABASE();

-- B. Relationship inventory: expected 12 foreign keys including users + QR support relationships.
SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME,
       CONSTRAINT_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = DATABASE()
  AND REFERENCED_TABLE_NAME IS NOT NULL
ORDER BY TABLE_NAME, CONSTRAINT_NAME;

SELECT 'FOREIGN_KEY_COUNT' AS object_type, COUNT(*) AS actual_count,
       12 AS expected_count, IF(COUNT(*) = 12, 'PASS', 'CHECK') AS result
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = DATABASE() AND REFERENCED_TABLE_NAME IS NOT NULL;

SELECT 'SEPAY_TRANSACTION_ID_UNIQUE' AS test_case,
       IF(EXISTS (
           SELECT 1 FROM information_schema.STATISTICS
           WHERE TABLE_SCHEMA = DATABASE()
             AND TABLE_NAME = 'sepay_webhook_events'
             AND INDEX_NAME = 'uq_sepay_transaction_id'
             AND COLUMN_NAME = 'transaction_id'
             AND NON_UNIQUE = 0
       ), 'PASS', 'CHECK') AS result;

SELECT 'PAY_HOADON_ONE_TO_ONE' AS test_case,
       IF(EXISTS (
           SELECT 1 FROM information_schema.STATISTICS
           WHERE TABLE_SCHEMA = DATABASE()
             AND TABLE_NAME = 'hoadon'
             AND INDEX_NAME = 'uq_hoadon_pay_id'
             AND COLUMN_NAME = 'pay_id'
             AND NON_UNIQUE = 0
       ), 'PASS', 'CHECK') AS result;

-- B. ERD relationship integrity checks. Each invalid_count should be 0.
SELECT 'DICHVU_BOOKING_ROOM_MISMATCH' AS test_case, COUNT(*) AS invalid_count
FROM dichvu d JOIN booking b ON b.id = d.booking_id
WHERE d.phong_id IS NULL OR d.phong_id <> b.phong_id;

SELECT 'PAY_CUSTOMER_BOOKING_MISMATCH' AS test_case, COUNT(*) AS invalid_count
FROM pay py JOIN booking b ON b.id = py.booking_id
WHERE py.khach_id <> b.khach_id;

SELECT 'INVOICE_TOTAL_MISMATCH' AS test_case, COUNT(*) AS invalid_count
FROM hoadon h
WHERE h.tong_tien <> h.tien_phong + h.tien_phu_phi_mua_cao_diem + h.tien_dich_vu;

SELECT 'BOOKING_PEAK_PRICE_SNAPSHOT_MISSING' AS test_case, COUNT(*) AS invalid_count
FROM booking
WHERE chi_tiet_mua_cao_diem IS NULL
   OR JSON_TYPE(chi_tiet_mua_cao_diem) <> 'ARRAY';

SELECT 'PEAK_SEASON_RATE_INVALID' AS test_case, COUNT(*) AS invalid_count
FROM muacaodiem
WHERE he_so_gia NOT IN (0.10, 0.20, 0.30, 0.40, 0.50, 0.60);

SELECT 'BOOKING_ROOM_BASE_SNAPSHOT_MISMATCH' AS test_case, COUNT(*) AS invalid_count
FROM booking b
WHERE b.tien_phong_du_kien <> COALESCE((
    SELECT SUM(jt.gia_co_ban)
    FROM JSON_TABLE(
        b.chi_tiet_mua_cao_diem,
        '$[*]' COLUMNS (gia_co_ban DECIMAL(12,2) PATH '$.gia_co_ban')
    ) AS jt
), 0.00);

SELECT 'BOOKING_PEAK_FEE_SNAPSHOT_MISMATCH' AS test_case, COUNT(*) AS invalid_count
FROM booking b
WHERE b.tien_phu_phi_mua_cao_diem <> COALESCE((
    SELECT SUM(jt.phi_mua_cao_diem)
    FROM JSON_TABLE(
        b.chi_tiet_mua_cao_diem,
        '$[*]' COLUMNS (phi_mua_cao_diem DECIMAL(12,2) PATH '$.phi_mua_cao_diem')
    ) AS jt
), 0.00);

SELECT 'PAY_BOOKING_SNAPSHOT_MISMATCH' AS test_case, COUNT(*) AS invalid_count
FROM pay py
JOIN booking b ON b.id = py.booking_id
WHERE py.tien_phong_ap_dung <> b.tien_phong_du_kien
   OR py.tien_phu_phi_mua_cao_diem <> b.tien_phu_phi_mua_cao_diem
   OR py.ap_dung_mua_cao_diem <> b.ap_dung_mua_cao_diem
   OR NOT (py.chi_tiet_mua_cao_diem <=> b.chi_tiet_mua_cao_diem);

SELECT 'PAY_INVOICE_ROOM_SNAPSHOT_MISMATCH' AS test_case, COUNT(*) AS invalid_count
FROM pay py JOIN hoadon h ON h.pay_id = py.id
WHERE py.tien_phong_ap_dung <> h.tien_phong;

SELECT 'PAY_INVOICE_PEAK_FEE_MISMATCH' AS test_case, COUNT(*) AS invalid_count
FROM pay py JOIN hoadon h ON h.pay_id = py.id
WHERE py.tien_phu_phi_mua_cao_diem <> h.tien_phu_phi_mua_cao_diem;

SELECT 'PAY_AMOUNT_INVOICE_TOTAL_MISMATCH' AS test_case, COUNT(*) AS invalid_count
FROM pay py JOIN hoadon h ON h.pay_id = py.id
WHERE py.so_tien <> h.tong_tien;

SELECT 'PAY_SEASON_SNAPSHOT_MISSING' AS test_case, COUNT(*) AS invalid_count
FROM pay
WHERE chi_tiet_mua_cao_diem IS NULL
   OR JSON_TYPE(chi_tiet_mua_cao_diem) <> 'ARRAY';

SELECT 'INVOICE_PAY_MISSING' AS test_case, COUNT(*) AS invalid_count
FROM hoadon h LEFT JOIN pay py ON py.id = h.pay_id WHERE py.id IS NULL;

SELECT 'REFUNDED_OR_PENDING_PAY_WITHOUT_INVOICE' AS test_case, COUNT(*) AS invalid_count
FROM pay py LEFT JOIN hoadon h ON h.pay_id = py.id
WHERE py.status IN ('CHO_THANH_TOAN', 'THANH_CONG', 'HOAN_TIEN') AND h.id IS NULL;

SELECT 'OVERLAPPING_ACTIVE_BOOKINGS' AS test_case, COUNT(*) AS invalid_pair_count
FROM booking a JOIN booking b ON b.phong_id = a.phong_id AND a.id < b.id
WHERE a.trang_thai <> 'DA_HUY' AND b.trang_thai <> 'DA_HUY'
  AND a.ngay_nhan < b.ngay_tra AND a.ngay_tra > b.ngay_nhan;

SELECT 'OVERLAPPING_PEAK_SEASONS' AS test_case, COUNT(*) AS invalid_pair_count
FROM muacaodiem a JOIN muacaodiem b ON b.phong_id = a.phong_id AND a.id < b.id
WHERE a.tu_ngay <= b.den_ngay AND a.den_ngay >= b.tu_ngay;

-- C. Object inventory and summaries: these are convenient for screenshots in the report.
SHOW TABLES;
SHOW FULL TABLES WHERE Table_type = 'VIEW';
SHOW PROCEDURE STATUS WHERE Db = DATABASE();
SHOW TRIGGERS FROM hotel_management_erd;
SELECT trang_thai, COUNT(*) AS so_booking FROM booking GROUP BY trang_thai ORDER BY trang_thai;
SELECT status, COUNT(*) AS so_giao_dich FROM pay GROUP BY status ORDER BY status;

-- D. Manual negative tests: uncomment one at a time on a test database.
-- Expected SIGNAL 45000: room #1 overlaps Booking #1.
-- INSERT INTO booking(phong_id, khach_id, ngay_nhan, ngay_tra, trang_thai)
-- VALUES (1, 2, '2026-12-11', '2026-12-13', 'CHO_XAC_NHAN');
-- Expected SIGNAL 45000: Booking #1 belongs to Room #1, not Room #2.
-- INSERT INTO dichvu(ten, don_gia, so_luong, phong_id, booking_id)
-- VALUES ('Test mismatch', 10000, 1, 2, 1);
-- Expected SIGNAL 45000: Pay #1 is already successful; illegal state transition.
-- UPDATE pay SET status = 'THAT_BAI' WHERE id = 1;
