-- HOTEL MANAGEMENT SYSTEM - SQL MODULE
-- Database: hotel_management_erd
-- ERD: 8 business tables + supplementary users authentication table
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

-- 5. VIEWS (10 VIEWS FOR REPORTING AND APPLICATION SCREENS)
-- ============================================================================

-- 5.1 Room information with room type and current status.
CREATE OR REPLACE VIEW `v_thong_tin_phong` AS
SELECT p.id AS phong_id,
       p.so_phong,
       lp.id AS loai_phong_id,
       lp.ten AS loai_phong,
       lp.gia_co_ban,
       lp.suc_chua,
       p.trang_thai,
       CASE
           WHEN EXISTS (
               SELECT 1 FROM booking b
               WHERE b.phong_id = p.id AND b.trang_thai = 'DANG_O'
           ) THEN 1 ELSE 0
       END AS co_khach_dang_o
FROM phong p
JOIN loaiphong lp ON lp.id = p.loai_phong_id;


-- 5.2 Booking details with customer, room, service and payment summaries.
CREATE OR REPLACE VIEW `v_chi_tiet_booking` AS
SELECT b.id AS booking_id,
       b.trang_thai AS trang_thai_booking,
       b.ngay_nhan,
       b.ngay_tra,
       DATEDIFF(b.ngay_tra, b.ngay_nhan) AS so_dem,
       k.id AS khach_id,
       k.ho_ten,
       k.cccd,
       k.sdt,
       p.id AS phong_id,
       p.so_phong,
       lp.ten AS loai_phong,
       lp.gia_co_ban,
       COALESCE((
           SELECT SUM(d.don_gia * d.so_luong)
           FROM dichvu d WHERE d.booking_id = b.id
       ), 0) AS tong_tien_dich_vu,
       COALESCE((
           SELECT SUM(hd.tong_tien)
           FROM pay py JOIN hoadon hd ON hd.pay_id = py.id
           WHERE py.booking_id = b.id
       ), 0) AS tong_tien_hoa_don,
       COALESCE((
           SELECT SUM(CASE
               WHEN py.status = 'THANH_CONG' THEN py.so_tien
               WHEN py.status = 'HOAN_TIEN' THEN -py.so_tien
               ELSE 0 END)
           FROM pay py WHERE py.booking_id = b.id
       ), 0) AS tien_thuc_thu
FROM booking b
JOIN khach k ON k.id = b.khach_id
JOIN phong p ON p.id = b.phong_id
JOIN loaiphong lp ON lp.id = p.loai_phong_id;


-- 5.3 Rooms currently occupied and their in-house customers.
CREATE OR REPLACE VIEW `v_phong_dang_su_dung` AS
SELECT p.id AS phong_id,
       p.so_phong,
       lp.ten AS loai_phong,
       b.id AS booking_id,
       b.ngay_nhan,
       b.ngay_tra,
       k.id AS khach_id,
       k.ho_ten,
       k.sdt
FROM phong p
JOIN booking b ON b.phong_id = p.id AND b.trang_thai = 'DANG_O'
JOIN khach k ON k.id = b.khach_id
JOIN loaiphong lp ON lp.id = p.loai_phong_id;


-- 5.4 Rooms marked for maintenance.
CREATE OR REPLACE VIEW `v_phong_bao_tri` AS
SELECT p.id AS phong_id,
       p.so_phong,
       lp.ten AS loai_phong,
       lp.gia_co_ban,
       lp.suc_chua,
       p.trang_thai
FROM phong p
JOIN loaiphong lp ON lp.id = p.loai_phong_id
WHERE p.trang_thai = 'BAO_TRI';


-- 5.5 Itemized services consumed under each Booking.
CREATE OR REPLACE VIEW `v_dich_vu_booking` AS
SELECT d.id AS dichvu_id,
       d.booking_id,
       b.trang_thai AS trang_thai_booking,
       k.ho_ten,
       p.so_phong,
       d.ten AS ten_dich_vu,
       d.don_gia,
       d.so_luong,
       (d.don_gia * d.so_luong) AS thanh_tien
FROM dichvu d
JOIN booking b ON b.id = d.booking_id
JOIN khach k ON k.id = b.khach_id
JOIN phong p ON p.id = b.phong_id;


-- 5.6 Invoice details with associated payment, Booking, customer and room.
CREATE OR REPLACE VIEW `v_chi_tiet_hoa_don` AS
SELECT hd.id AS hoadon_id,
       hd.ngay_lap,
       hd.tien_phong,
       hd.tien_dich_vu,
       hd.tong_tien,
       py.id AS pay_id,
       py.ngay_thanh_toan,
       py.method,
       py.status AS trang_thai_thanh_toan,
       py.so_tien,
       b.id AS booking_id,
       b.trang_thai AS trang_thai_booking,
       k.id AS khach_id,
       k.ho_ten,
       p.so_phong
FROM hoadon hd
JOIN pay py ON py.id = hd.pay_id
JOIN booking b ON b.id = py.booking_id
JOIN khach k ON k.id = b.khach_id
JOIN phong p ON p.id = b.phong_id;


-- 5.7 Monthly cash revenue: successful receipts less refunds.
CREATE OR REPLACE VIEW `v_doanh_thu_theo_thang` AS
SELECT YEAR(py.ngay_thanh_toan) AS nam,
       MONTH(py.ngay_thanh_toan) AS thang,
       SUM(CASE WHEN py.status = 'THANH_CONG' THEN py.so_tien ELSE 0 END) AS tong_thanh_toan_thanh_cong,
       SUM(CASE WHEN py.status = 'HOAN_TIEN' THEN py.so_tien ELSE 0 END) AS tong_tien_hoan,
       SUM(CASE
           WHEN py.status = 'THANH_CONG' THEN py.so_tien
           WHEN py.status = 'HOAN_TIEN' THEN -py.so_tien
           ELSE 0 END) AS doanh_thu_thuc_thu,
       SUM(py.status = 'THANH_CONG') AS so_giao_dich_thanh_cong,
       SUM(py.status = 'HOAN_TIEN') AS so_giao_dich_hoan_tien
FROM pay py
GROUP BY YEAR(py.ngay_thanh_toan), MONTH(py.ngay_thanh_toan);


-- 5.8 Booking counts by status.
CREATE OR REPLACE VIEW `v_thong_ke_trang_thai_booking` AS
SELECT b.trang_thai,
       COUNT(*) AS so_luong_booking
FROM booking b
GROUP BY b.trang_thai;


-- 5.9 Customer profile and booking/payment history aggregates.
CREATE OR REPLACE VIEW `v_thong_tin_khach_hang` AS
SELECT k.id AS khach_id,
       k.ho_ten,
       k.cccd,
       k.sdt,
       COALESCE(bs.tong_booking, 0) AS tong_booking,
       COALESCE(bs.booking_hoan_thanh, 0) AS booking_hoan_thanh,
       COALESCE(bs.booking_da_huy, 0) AS booking_da_huy,
       bs.lan_dat_gan_nhat,
       COALESCE(ps.doanh_thu_thuc_thu, 0) AS doanh_thu_thuc_thu
FROM khach k
LEFT JOIN (
    SELECT b.khach_id,
           COUNT(*) AS tong_booking,
           SUM(b.trang_thai = 'HOAN_THANH') AS booking_hoan_thanh,
           SUM(b.trang_thai = 'DA_HUY') AS booking_da_huy,
           MAX(b.ngay_nhan) AS lan_dat_gan_nhat
    FROM booking b
    GROUP BY b.khach_id
) bs ON bs.khach_id = k.id
LEFT JOIN (
    SELECT py.khach_id,
           SUM(CASE
               WHEN py.status = 'THANH_CONG' THEN py.so_tien
               WHEN py.status = 'HOAN_TIEN' THEN -py.so_tien
               ELSE 0 END) AS doanh_thu_thuc_thu
    FROM pay py
    GROUP BY py.khach_id
) ps ON ps.khach_id = k.id;


-- 5.10 Peak-season configurations by room.
CREATE OR REPLACE VIEW `v_thong_ke_mua_cao_diem` AS
SELECT m.id AS mua_cao_diem_id,
       p.id AS phong_id,
       p.so_phong,
       lp.ten AS loai_phong,
       m.tu_ngay,
       m.den_ngay,
       DATEDIFF(m.den_ngay, m.tu_ngay) + 1 AS so_ngay_ap_dung,
       m.he_so_gia,
       lp.gia_co_ban,
       ROUND(lp.gia_co_ban * m.he_so_gia, 2) AS gia_mot_dem_mua_cao_diem
FROM muacaodiem m
JOIN phong p ON p.id = m.phong_id
JOIN loaiphong lp ON lp.id = p.loai_phong_id;


-- ============================================================================
