-- ============================================================================
-- HOTEL MANAGEMENT DATABASE - VERSION 2 (ERD ALIGNED)
-- MySQL 8.0.16+
-- Schema: hotel_management_erd
-- 8 ERD TABLES + users AUTH TABLE | 18 STORED PROCEDURES | 10 VIEWS | 15 TRIGGERS
-- Main ERD relationships:
--   LoaiPhong 1-N Phong
--   Phong 1-N Booking; Khach 1-N Booking
--   Phong 1-N DichVu; Booking 1-N DichVu
--   Phong 1-N MuaCaoDiem
--   Booking 1-N Pay; Khach 1-N Pay; Pay 1-1 HoaDon
-- Notes:
--   * Room occupancy status is synchronized from Booking check-in/check-out.
--   * A service linked to a Booking must reference that Booking's room.
--   * A payment is created pending, then can become successful only with a matching invoice.
--   * One invoice belongs to exactly one Pay; one Booking may have multiple payment attempts.
--   * Sample data is loaded before triggers so existing historical records are preserved.
-- ============================================================================

-- ============================================================================
-- HOTEL MANAGEMENT DATABASE - VERSION 2 (BASED ON 8-ENTITY ERD)
-- Target: MySQL 8.0.16+
-- Schema: hotel_management_erd
-- Business ERD entities (8):
--   1. loaiphong  (id, ten, gia_co_ban, suc_chua)
--   2. phong      (id, so_phong, loai_phong_id, trang_thai)
--   3. khach      (id, ho_ten, cccd, sdt)
--   4. booking    (id, phong_id, khach_id, ngay_nhan, ngay_tra, trang_thai)
--   5. dichvu     (id, ten, don_gia, so_luong, phong_id, booking_id)
--   6. muacaodiem (id, phong_id, tu_ngay, den_ngay, he_so_gia)
--   7. pay        (id, booking_id, khach_id, ngay_thanh_toan, so_tien, method, status)
--   8. hoadon     (id, pay_id, tien_phong, tien_phu_phi_mua_cao_diem, tien_dich_vu, tong_tien, ngay_lap)
-- Includes:
--   - Full DDL (Tables, Primary Keys, Unique Keys, Foreign Keys, Check Constraints)
--   - Complete, mathematically consistent sample dataset (all statuses covered)
--   - 18 Stored Procedures, 10 Views, 15 Triggers enforcing ERD relationships and business rules
-- ============================================================================

DROP DATABASE IF EXISTS `hotel_management_erd`;
CREATE DATABASE `hotel_management_erd`
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `hotel_management_erd`;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================================
-- 1. TABLE DEFINITIONS (DDL)
-- ============================================================================

-- 1.1 Table: loaiphong (LoaiPhong: id, ten, giaCoBan, sucChua)
CREATE TABLE `loaiphong` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `ten` VARCHAR(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `gia_co_ban` DECIMAL(12,2) NOT NULL,
  `suc_chua` INT NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_loaiphong_ten` (`ten`),
  CONSTRAINT `chk_gia_phong` CHECK (`gia_co_ban` >= 0),
  CONSTRAINT `chk_suc_chua` CHECK (`suc_chua` > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- 1.2 Table: phong (Phong: id, soPhong, loaiPhong, trangThai)
-- Relationship: LoaiPhong (1) -- [In] -- (N) Phong
CREATE TABLE `phong` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `so_phong` VARCHAR(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `loai_phong_id` INT NOT NULL,
  `trang_thai` VARCHAR(30) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'SAN_SANG',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_phong_so_phong` (`so_phong`),
  KEY `fk_phong_loaiphong` (`loai_phong_id`),
  CONSTRAINT `fk_phong_loaiphong` FOREIGN KEY (`loai_phong_id`) REFERENCES `loaiphong` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_trang_thai_phong` CHECK (`trang_thai` IN ('SAN_SANG', 'DANG_SU_DUNG', 'BAO_TRI'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- 1.3 Table: khach (Khach: id, hoTen, CCCD, SDT)
CREATE TABLE `khach` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `ho_ten` VARCHAR(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `cccd` VARCHAR(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `sdt` VARCHAR(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_khach_cccd` (`cccd`),
  UNIQUE KEY `uq_khach_sdt` (`sdt`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- 1.4 Table: booking (includes immutable nightly room-price/peak-season snapshot)
-- Relationships: Phong (1) -- [In] -- (N) Booking; Khach (1) -- [Tao] -- (N) Booking
CREATE TABLE `booking` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `phong_id` INT NOT NULL,
  `khach_id` INT NOT NULL,
  `ngay_nhan` DATE NOT NULL,
  `ngay_tra` DATE NOT NULL,
  `trang_thai` VARCHAR(30) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'CHO_XAC_NHAN',
  `tien_phong_du_kien` DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  `tien_phu_phi_mua_cao_diem` DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  `ap_dung_mua_cao_diem` TINYINT(1) NOT NULL DEFAULT 0,
  `chi_tiet_mua_cao_diem` JSON DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_booking_phong` (`phong_id`),
  KEY `fk_booking_khach` (`khach_id`),
  KEY `idx_booking_ngay` (`ngay_nhan`, `ngay_tra`),
  CONSTRAINT `fk_booking_khach` FOREIGN KEY (`khach_id`) REFERENCES `khach` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_booking_phong` FOREIGN KEY (`phong_id`) REFERENCES `phong` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_ngay_booking` CHECK (`ngay_tra` > `ngay_nhan`),
  CONSTRAINT `chk_trang_thai_booking` CHECK (`trang_thai` IN ('CHO_XAC_NHAN', 'DA_XAC_NHAN', 'DANG_O', 'DA_HUY', 'HOAN_THANH'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- 1.5 Table: dichvu (DichVu: id, ten, donGia, soLuong)
-- Relationships:
--   Phong (1) -- [In] -- (N) DichVu   (booking_id IS NULL: default services included with room)
--   Booking (1) -- [Dung] -- (N) DichVu (booking_id IS NOT NULL: services used in booking)
CREATE TABLE `dichvu` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `ten` VARCHAR(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `don_gia` DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  `so_luong` INT NOT NULL DEFAULT 1,
  `phong_id` INT DEFAULT NULL,
  `booking_id` INT DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_dichvu_phong` (`phong_id`),
  KEY `fk_dichvu_booking` (`booking_id`),
  CONSTRAINT `fk_dichvu_phong` FOREIGN KEY (`phong_id`) REFERENCES `phong` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_dichvu_booking` FOREIGN KEY (`booking_id`) REFERENCES `booking` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_dichvu_gia` CHECK (`don_gia` >= 0),
  CONSTRAINT `chk_dichvu_soluong` CHECK (`so_luong` > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- 1.6 Table: muacaodiem (MuaCaoDiem: id, tuNgay, denNgay, heSoGia)
-- Relationship: Phong (1) -- [Ap dung] -- (N) MuaCaoDiem
CREATE TABLE `muacaodiem` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `phong_id` INT NOT NULL,
  `tu_ngay` DATE NOT NULL,
  `den_ngay` DATE NOT NULL,
  `he_so_gia` DECIMAL(4,2) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_muacaodiem_phong` (`phong_id`),
  CONSTRAINT `fk_muacaodiem_phong` FOREIGN KEY (`phong_id`) REFERENCES `phong` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_he_so_gia` CHECK (`he_so_gia` IN (0.10, 0.20, 0.30, 0.40, 0.50, 0.60)),
  CONSTRAINT `chk_ngay_caodiem` CHECK (`den_ngay` >= `tu_ngay`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- 1.7 Table: pay (includes immutable applied room-price/peak-season snapshot)
-- Relationships: Booking (1) -- [Thanh toan] -- (N) Pay; Khach (1) -- [Thuc hien] -- (N) Pay
CREATE TABLE `pay` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `booking_id` INT NOT NULL,
  `khach_id` INT NOT NULL,
  `ngay_thanh_toan` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `so_tien` DECIMAL(12,2) NOT NULL,
  `method` VARCHAR(30) COLLATE utf8mb4_unicode_ci NOT NULL,
  `status` VARCHAR(30) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'CHO_THANH_TOAN',
  `tien_phong_ap_dung` DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  `tien_phu_phi_mua_cao_diem` DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  `ap_dung_mua_cao_diem` TINYINT(1) NOT NULL DEFAULT 0,
  `chi_tiet_mua_cao_diem` JSON DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_pay_booking` (`booking_id`),
  KEY `fk_pay_khach` (`khach_id`),
  CONSTRAINT `fk_pay_booking` FOREIGN KEY (`booking_id`) REFERENCES `booking` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_pay_khach` FOREIGN KEY (`khach_id`) REFERENCES `khach` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_pay_method` CHECK (`method` IN ('TIEN_MAT', 'CHUYEN_KHOAN', 'THE')),
  CONSTRAINT `chk_pay_sotien` CHECK (`so_tien` >= 0),
  CONSTRAINT `chk_pay_status` CHECK (`status` IN ('CHO_THANH_TOAN', 'THANH_CONG', 'THAT_BAI', 'HOAN_TIEN'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- 1.8 Table: hoadon (HoaDon: tien phong + phu phi mua cao diem + tien dich vu)
-- Relationship: Pay (1) -- [Xuat hoa don] -- (1) HoaDon
CREATE TABLE `hoadon` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `pay_id` INT NOT NULL,
  `tien_phong` DECIMAL(12,2) NOT NULL,
  `tien_phu_phi_mua_cao_diem` DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  `tien_dich_vu` DECIMAL(12,2) NOT NULL,
  `tong_tien` DECIMAL(12,2) NOT NULL,
  `ngay_lap` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_hoadon_pay_id` (`pay_id`),
  CONSTRAINT `fk_hoadon_pay` FOREIGN KEY (`pay_id`) REFERENCES `pay` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_hoadon_tien` CHECK (
    `tien_phong` >= 0
    AND `tien_phu_phi_mua_cao_diem` >= 0
    AND `tien_dich_vu` >= 0
    AND `tong_tien` >= 0
    AND `tong_tien` = (`tien_phong` + `tien_phu_phi_mua_cao_diem` + `tien_dich_vu`)
  )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- 1.9 QR transfer and SePay webhook audit tables (supporting tables; not ERD business entities).
CREATE TABLE `payment_qr` (
  `pay_id` INT NOT NULL,
  `payment_code` VARCHAR(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `sepay_transaction_id` VARCHAR(80) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sepay_reference_code` VARCHAR(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `received_amount` DECIMAL(12,2) DEFAULT NULL,
  `received_account_number` VARCHAR(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `received_at` DATETIME DEFAULT NULL,
  PRIMARY KEY (`pay_id`),
  UNIQUE KEY `uq_payment_qr_code` (`payment_code`),
  UNIQUE KEY `uq_payment_qr_sepay_transaction` (`sepay_transaction_id`),
  CONSTRAINT `fk_payment_qr_pay` FOREIGN KEY (`pay_id`) REFERENCES `pay` (`id`)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `chk_payment_qr_amount` CHECK (`received_amount` IS NULL OR `received_amount` >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `sepay_webhook_events` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `transaction_id` VARCHAR(80) COLLATE utf8mb4_unicode_ci NOT NULL,
  `gateway` VARCHAR(60) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `account_number` VARCHAR(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `payment_code` VARCHAR(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `transfer_type` VARCHAR(16) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `transfer_amount` DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  `reference_code` VARCHAR(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `transaction_date` VARCHAR(40) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_id` INT DEFAULT NULL,
  `processing_result` VARCHAR(40) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'RECEIVED',
  `raw_payload` JSON NOT NULL,
  `received_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `processed_at` DATETIME DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_sepay_transaction_id` (`transaction_id`),
  KEY `idx_sepay_payment_code` (`payment_code`),
  KEY `idx_sepay_pay_id` (`pay_id`),
  KEY `idx_sepay_result` (`processing_result`),
  CONSTRAINT `fk_sepay_event_pay` FOREIGN KEY (`pay_id`) REFERENCES `pay` (`id`)
    ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `chk_sepay_transfer_amount` CHECK (`transfer_amount` >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;


-- 1.10 Supplementary authentication table (outside the 8-table business ERD).
-- This table stores application accounts and maps CUSTOMER accounts to khach.
-- Public registration always creates role CUSTOMER; ADMIN is provisioned by SQL.
CREATE TABLE `users` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(50) COLLATE utf8mb4_unicode_ci NOT NULL,
  `full_name` VARCHAR(100) COLLATE utf8mb4_unicode_ci NOT NULL,
  `password_hash` VARCHAR(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` ENUM('ADMIN', 'CUSTOMER') NOT NULL DEFAULT 'CUSTOMER',
  `khach_id` INT DEFAULT NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_users_username` (`username`),
  UNIQUE KEY `uq_users_khach_id` (`khach_id`),
  CONSTRAINT `fk_users_khach` FOREIGN KEY (`khach_id`)
    REFERENCES `khach` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Initial ADMIN account for first startup.
-- Username: admin | Password: Admin@123
-- Change this password before putting the application into real use.
INSERT INTO `users`
  (`username`, `full_name`, `password_hash`, `role`, `khach_id`, `is_active`)
VALUES
  ('admin', 'Quản trị viên',
   'd9438c8f7c2a0b5e6d1f932a4b7c8d90$8f0a1af0e5463f1f110d102e74a1ccf3c8d05ddc1bc7c11c54829d8a8a805532',
   'ADMIN', NULL, 1);


-- ============================================================================
-- 2. SAMPLE DATASET (100% CONSISTENT WITH CONSTRAINTS & TRIGGERS)
-- ============================================================================

-- 2.1 loaiphong (4 room types)
INSERT INTO `loaiphong` (`id`, `ten`, `gia_co_ban`, `suc_chua`) VALUES
(1, 'Standard',  500000.00, 2),
(2, 'Deluxe',    800000.00, 4),
(3, 'VIP',      1200000.00, 3),
(4, 'Family',   1500000.00, 6);

-- 2.2 phong (11 rooms covering SAN_SANG, DANG_SU_DUNG, BAO_TRI)
INSERT INTO `phong` (`id`, `so_phong`, `loai_phong_id`, `trang_thai`) VALUES
(1,  '101', 1, 'SAN_SANG'),
(2,  '102', 1, 'SAN_SANG'),
(3,  '201', 2, 'SAN_SANG'),
(4,  '202', 2, 'SAN_SANG'),
(5,  '301', 3, 'SAN_SANG'),
(6,  '302', 3, 'SAN_SANG'),
(7,  '401', 4, 'SAN_SANG'),
(8,  '402', 4, 'DANG_SU_DUNG'), -- Dang co Booking 15 luu tru
(9,  '501', 2, 'SAN_SANG'),
(10, '502', 1, 'BAO_TRI'),      -- Phong dang bao tri
(11, '601', 1, 'SAN_SANG');

-- 2.3 khach (10 guests)
INSERT INTO `khach` (`id`, `ho_ten`, `cccd`, `sdt`) VALUES
(1,  'Nguyen Van An',    '079201000001', '0901000001'),
(2,  'Tran Thi Binh',    '079201000002', '0901000002'),
(3,  'Le Hoang Nam',     '079201000003', '0901000003'),
(4,  'Pham Thu Ha',      '079201000004', '0901000004'),
(5,  'Hoang Minh Duc',   '079201000005', '0901000005'),
(6,  'Vo Ngoc Anh',      '079201000006', '0901000006'),
(7,  'Dang Quoc Bao',    '079201000007', '0901000007'),
(8,  'Bui Thanh Truc',   '079201000008', '0901000008'),
(9,  'Do Minh Khang',    '079201000009', '0901000009'),
(10, 'Nguyen Thao Vy',   '079201000010', '0901000010');

-- 2.4 muacaodiem (Peak season rules per room)
INSERT INTO `muacaodiem` (`id`, `phong_id`, `tu_ngay`, `den_ngay`, `he_so_gia`) VALUES
(1, 1, '2026-12-20', '2026-12-31', 0.20),
(2, 3, '2026-12-20', '2026-12-31', 0.30),
(3, 5, '2026-12-20', '2026-12-31', 0.50),
(4, 7, '2026-12-20', '2026-12-31', 0.60);

-- 2.5 booking (17 bookings covering all 5 statuses: CHO_XAC_NHAN, DA_XAC_NHAN, DANG_O, DA_HUY, HOAN_THANH)
INSERT INTO `booking` (`id`, `phong_id`, `khach_id`, `ngay_nhan`, `ngay_tra`, `trang_thai`) VALUES
(1,  1,  1,  '2026-12-10', '2026-12-12', 'DA_XAC_NHAN'),
(2,  2,  2,  '2026-12-04', '2026-12-06', 'DA_XAC_NHAN'),
(3,  3,  3,  '2026-12-07', '2026-12-10', 'DA_XAC_NHAN'),
(4,  4,  4,  '2026-12-11', '2026-12-13', 'DA_XAC_NHAN'),
(5,  5,  5,  '2026-12-14', '2026-12-16', 'DA_XAC_NHAN'),
(6,  6,  6,  '2026-12-17', '2026-12-20', 'DA_XAC_NHAN'),
(7,  7,  7,  '2026-12-21', '2026-12-24', 'DA_XAC_NHAN'), -- Ap dung phu thu mua cao diem 0.60
(8,  8,  8,  '2026-12-25', '2026-12-27', 'DA_XAC_NHAN'),
(9,  9,  9,  '2026-12-28', '2026-12-30', 'DA_XAC_NHAN'),
(10, 10, 10, '2026-12-05', '2026-12-07', 'DA_HUY'),
(11, 2,  3,  '2026-12-10', '2026-12-12', 'DA_HUY'),
(12, 1,  1,  '2026-12-20', '2026-12-23', 'DA_XAC_NHAN'), -- Ap dung phu thu mua cao diem 0.20
(13, 4,  1,  '2026-12-20', '2026-12-28', 'DA_HUY'),
(14, 11, 2,  '2026-12-15', '2026-12-17', 'DA_XAC_NHAN'),
(15, 8,  5,  '2026-11-15', '2026-11-18', 'DANG_O'),      -- Khach dang o phong 402
(16, 9,  6,  '2026-11-10', '2026-11-12', 'HOAN_THANH'),  -- Booking da tra phong & hoan thanh
(17, 11, 7,  '2026-12-22', '2026-12-25', 'CHO_XAC_NHAN');

-- 2.6 dichvu
-- Part A: Default room services (booking_id IS NULL -> Phong 1 - In - N DichVu)
INSERT INTO `dichvu` (`id`, `ten`, `don_gia`, `so_luong`, `phong_id`, `booking_id`) VALUES
(1,  'Nuoc suoi mien phi',      0.00, 2, 1,  NULL),
(2,  'Tra va ca phe mien phi',  0.00, 2, 1,  NULL),
(3,  'Nuoc suoi mien phi',      0.00, 2, 2,  NULL),
(4,  'Nuoc suoi mien phi',      0.00, 2, 3,  NULL),
(5,  'Tra va ca phe mien phi',  0.00, 2, 3,  NULL),
(6,  'Nuoc suoi mien phi',      0.00, 2, 4,  NULL),
(7,  'Nuoc suoi mien phi',      0.00, 4, 5,  NULL),
(8,  'Tra va ca phe mien phi',  0.00, 4, 5,  NULL),
(9,  'Nuoc suoi mien phi',      0.00, 4, 6,  NULL),
(10, 'Nuoc suoi mien phi',      0.00, 4, 7,  NULL),
(11, 'Nuoc suoi mien phi',      0.00, 4, 8,  NULL),
(12, 'Nuoc suoi mien phi',      0.00, 2, 9,  NULL),
(13, 'Nuoc suoi mien phi',      0.00, 2, 11, NULL);

-- Part B: Booking services (booking_id IS NOT NULL -> Booking 1 - Dung - N DichVu)
INSERT INTO `dichvu` (`id`, `ten`, `don_gia`, `so_luong`, `phong_id`, `booking_id`) VALUES
-- Booking 1 (tien_dich_vu = 180,000)
(14, 'Nuoc suoi mien phi',          0.00, 2, 1,  1),
(15, 'Tra va ca phe mien phi',      0.00, 2, 1,  1),
(16, 'An sang',                 50000.00, 2, 1,  1),
(17, 'Giat ui',                 80000.00, 1, 1,  1),
-- Booking 2 (tien_dich_vu = 150,000)
(18, 'Nuoc suoi mien phi',          0.00, 2, 2,  2),
(19, 'Thue xe',                150000.00, 1, 2,  2),
-- Booking 3 (tien_dich_vu = 350,000)
(20, 'Nuoc suoi mien phi',          0.00, 2, 3,  3),
(21, 'Tra va ca phe mien phi',      0.00, 2, 3,  3),
(22, 'An sang',                 50000.00, 3, 3,  3),
(23, 'Minibar',                100000.00, 2, 3,  3),
-- Booking 4 (tien_dich_vu = 160,000)
(24, 'Nuoc suoi mien phi',          0.00, 2, 4,  4),
(25, 'Giat ui',                 80000.00, 2, 4,  4),
-- Booking 5 (tien_dich_vu = 550,000)
(26, 'Nuoc suoi mien phi',          0.00, 4, 5,  5),
(27, 'Tra va ca phe mien phi',      0.00, 4, 5,  5),
(28, 'An sang',                 50000.00, 5, 5,  5),
(29, 'Spa',                    300000.00, 1, 5,  5),
-- Booking 6 (tien_dich_vu = 150,000)
(30, 'Nuoc suoi mien phi',          0.00, 4, 6,  6),
(31, 'Thue xe',                150000.00, 1, 6,  6),
-- Booking 7 (tien_dich_vu = 200,000)
(32, 'Nuoc suoi mien phi',          0.00, 4, 7,  7),
(33, 'Minibar',                100000.00, 2, 7,  7),
-- Booking 8 (tien_dich_vu = 100,000)
(34, 'Nuoc suoi mien phi',          0.00, 4, 8,  8),
(35, 'An sang',                 50000.00, 2, 8,  8),
-- Booking 9 (tien_dich_vu = 80,000)
(36, 'Nuoc suoi mien phi',          0.00, 2, 9,  9),
(37, 'Giat ui',                 80000.00, 1, 9,  9),
-- Booking 12 (tien_dich_vu = 0)
(38, 'Nuoc suoi mien phi',          0.00, 2, 1,  12),
(39, 'Tra va ca phe mien phi',      0.00, 2, 1,  12),
-- Booking 14 (tien_dich_vu = 160,000)
(40, 'Nuoc suoi mien phi',          0.00, 2, 11, 14),
(41, 'Giat ui',                 80000.00, 2, 11, 14),
-- Booking 15 (DANG_O - chua xuat hoa don)
(42, 'Nuoc suoi mien phi',          0.00, 4, 8,  15),
(43, 'Spa',                    300000.00, 1, 8,  15),
-- Booking 16 (HOAN_THANH - tien_dich_vu = 100,000)
(44, 'Nuoc suoi mien phi',          0.00, 2, 9,  16),
(45, 'An sang',                 50000.00, 2, 9,  16),
-- Booking 17 (CHO_XAC_NHAN)
(46, 'Nuoc suoi mien phi',          0.00, 2, 11, 17);

-- 2.7 pay (14 payment records; khach_id always matches booking.khach_id)
INSERT INTO `pay` (`id`, `booking_id`, `khach_id`, `ngay_thanh_toan`, `so_tien`, `method`, `status`) VALUES
(1,  1,  1,  '2026-11-10 09:00:00', 1180000.00, 'TIEN_MAT',     'THANH_CONG'),
(2,  2,  2,  '2026-11-10 10:00:00', 1150000.00, 'CHUYEN_KHOAN', 'THANH_CONG'),
(3,  3,  3,  '2026-11-11 11:00:00', 2750000.00, 'THE',          'THANH_CONG'),
(4,  4,  4,  '2026-11-11 12:00:00', 1760000.00, 'TIEN_MAT',     'THANH_CONG'),
(5,  5,  5,  '2026-11-12 13:00:00', 2950000.00, 'CHUYEN_KHOAN', 'THANH_CONG'),
(6,  6,  6,  '2026-11-12 14:00:00', 3750000.00, 'THE',          'THANH_CONG'),
(7,  7,  7,  '2026-11-13 15:00:00', 7400000.00, 'CHUYEN_KHOAN', 'THANH_CONG'),
(8,  8,  8,  '2026-11-13 16:00:00', 3100000.00, 'TIEN_MAT',     'THANH_CONG'),
(9,  9,  9,  '2026-11-14 17:00:00', 1680000.00, 'THE',          'THANH_CONG'),
(10, 10, 10, '2026-11-14 18:00:00',       0.00, 'TIEN_MAT',     'THAT_BAI'),
(11, 1,  1,  '2026-11-09 08:00:00', 1180000.00, 'TIEN_MAT',     'HOAN_TIEN'),
(12, 12, 1,  '2026-11-15 09:30:00', 1800000.00, 'TIEN_MAT',     'THANH_CONG'),
(13, 14, 2,  '2026-11-15 10:15:00', 1160000.00, 'TIEN_MAT',     'THANH_CONG'),
(14, 16, 6,  '2026-11-12 12:00:00', 1700000.00, 'CHUYEN_KHOAN', 'THANH_CONG');

-- 2.8 hoadon (13 invoices; Pay failed #10 has no invoice, refunded Pay #11 retains its invoice)
INSERT INTO `hoadon` (`id`, `pay_id`, `tien_phong`, `tien_dich_vu`, `tong_tien`, `ngay_lap`) VALUES
(1,  1,  1000000.00, 180000.00, 1180000.00, '2026-11-10 08:55:00'),
(2,  2,  1000000.00, 150000.00, 1150000.00, '2026-11-10 09:55:00'),
(3,  3,  2400000.00, 350000.00, 2750000.00, '2026-11-11 10:55:00'),
(4,  4,  1600000.00, 160000.00, 1760000.00, '2026-11-11 11:55:00'),
(5,  5,  2400000.00, 550000.00, 2950000.00, '2026-11-12 12:55:00'),
(6,  6,  3600000.00, 150000.00, 3750000.00, '2026-11-12 13:55:00'),
(7,  7,  7200000.00, 200000.00, 7400000.00, '2026-11-13 14:55:00'), -- Sau backfill: 4.5tr tien phong + 2.7tr phu phi + 200k DV
(8,  8,  3000000.00, 100000.00, 3100000.00, '2026-11-13 15:55:00'),
(9,  9,  1600000.00,  80000.00, 1680000.00, '2026-11-14 16:55:00'),
(10, 12, 1800000.00,      0.00, 1800000.00, '2026-11-15 09:25:00'), -- Sau backfill: 1.5tr tien phong + 300k phu phi + 0 DV
(11, 13, 1000000.00, 160000.00, 1160000.00, '2026-11-15 10:10:00'),
(12, 14, 1600000.00, 100000.00, 1700000.00, '2026-11-12 11:55:00'),
(13, 11, 1000000.00,  180000.00, 1180000.00, '2026-11-09 07:55:00'); -- Pay 11: giao dich hoan tien cua Booking 1



-- Luu y: du lieu mau duoc nap truoc khi tao trigger de giu nguyen cac giao dich lich su.
-- ============================================================================
-- 3. STORED PROCEDURES (18 PERSISTENT PROCEDURES; backfill helper is temporary)
-- ============================================================================

-- 3.1 Kiểm tra phòng trống theo khoảng ngày
DROP PROCEDURE IF EXISTS `sp_kiem_tra_phong_trong`;
DELIMITER $$
CREATE PROCEDURE `sp_kiem_tra_phong_trong`(
    IN p_ngay_nhan DATE,
    IN p_ngay_tra DATE
)
BEGIN
    IF p_ngay_nhan IS NULL OR p_ngay_tra IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Ngay nhan va ngay tra khong duoc de trong';
    END IF;

    IF p_ngay_tra <= p_ngay_nhan THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Ngay tra phai sau ngay nhan';
    END IF;

    SELECT
        p.id AS phong_id,
        p.so_phong,
        lp.ten AS loai_phong,
        lp.gia_co_ban,
        lp.suc_chua,
        p.trang_thai
    FROM phong p
    JOIN loaiphong lp ON p.loai_phong_id = lp.id
    WHERE p.trang_thai <> 'BAO_TRI'
      AND NOT EXISTS (
          SELECT 1
          FROM booking b
          WHERE b.phong_id = p.id
            AND b.trang_thai <> 'DA_HUY'
            AND p_ngay_nhan < b.ngay_tra
            AND p_ngay_tra > b.ngay_nhan
      )
    ORDER BY p.so_phong;
END$$
DELIMITER ;


-- 3.2 Tạo booking mới (Trigger trg_booking_after_insert sẽ tự copy dịch vụ mặc định của phòng)
DROP PROCEDURE IF EXISTS `sp_tao_booking`;
DELIMITER $$
CREATE PROCEDURE `sp_tao_booking`(
    IN p_phong_id INT,
    IN p_khach_id INT,
    IN p_ngay_nhan DATE,
    IN p_ngay_tra DATE
)
BEGIN
    DECLARE v_dem INT DEFAULT 0;
    DECLARE v_trang_thai_phong VARCHAR(30) DEFAULT NULL;
    DECLARE v_booking_id INT;
    DECLARE v_khach_check INT;
    DECLARE v_not_found BOOLEAN DEFAULT FALSE;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_not_found = TRUE;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    IF p_ngay_nhan IS NULL OR p_ngay_tra IS NULL OR p_ngay_tra <= p_ngay_nhan THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Ngay nhan va ngay tra khong hop le';
    END IF;

    SELECT id INTO v_khach_check FROM khach WHERE id = p_khach_id FOR SHARE;
    IF v_not_found THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Khach hang khong ton tai';
    END IF;

    SET v_not_found = FALSE;
    SELECT trang_thai INTO v_trang_thai_phong
    FROM phong
    WHERE id = p_phong_id
    FOR UPDATE;

    IF v_not_found OR v_trang_thai_phong IS NULL OR v_trang_thai_phong = 'BAO_TRI' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Phong khong ton tai hoac dang bao tri';
    END IF;

    SELECT COUNT(*) INTO v_dem
    FROM booking
    WHERE phong_id = p_phong_id
      AND trang_thai <> 'DA_HUY'
      AND p_ngay_nhan < ngay_tra
      AND p_ngay_tra > ngay_nhan;

    IF v_dem > 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Phong da duoc dat trong khoang thoi gian nay';
    END IF;

    INSERT INTO booking (phong_id, khach_id, ngay_nhan, ngay_tra, trang_thai)
    VALUES (p_phong_id, p_khach_id, p_ngay_nhan, p_ngay_tra, 'CHO_XAC_NHAN');

    SET v_booking_id = LAST_INSERT_ID();

    COMMIT;

    SELECT v_booking_id AS booking_id,
           p_phong_id AS phong_id,
           p_khach_id AS khach_id,
           p_ngay_nhan AS ngay_nhan,
           p_ngay_tra AS ngay_tra,
           'CHO_XAC_NHAN' AS trang_thai;
END$$
DELIMITER ;


-- 3.2B Customer booking with explicit service selection.
-- p_dich_vu is a JSON array:
-- [{"dichvu_id": 1, "so_luong": 2}, ...]
-- IDs must refer to default services of the selected room (booking_id IS NULL).
-- An empty array means the customer opts out of all default services.
DROP PROCEDURE IF EXISTS `sp_tao_booking_customer`;
DELIMITER $$
CREATE PROCEDURE `sp_tao_booking_customer`(
    IN p_phong_id INT,
    IN p_khach_id INT,
    IN p_ngay_nhan DATE,
    IN p_ngay_tra DATE,
    IN p_dich_vu JSON
)
BEGIN
    DECLARE v_dem INT DEFAULT 0;
    DECLARE v_trang_thai_phong VARCHAR(30) DEFAULT NULL;
    DECLARE v_booking_id INT DEFAULT NULL;
    DECLARE v_not_found BOOLEAN DEFAULT FALSE;
    DECLARE v_selected_count INT DEFAULT 0;
    DECLARE v_distinct_count INT DEFAULT 0;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_not_found = TRUE;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    IF p_ngay_nhan IS NULL OR p_ngay_tra IS NULL OR p_ngay_tra <= p_ngay_nhan THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Ngay nhan va ngay tra khong hop le';
    END IF;

    IF p_dich_vu IS NULL OR JSON_TYPE(p_dich_vu) <> 'ARRAY' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Danh sach dich vu phai la JSON ARRAY';
    END IF;

    SELECT id INTO v_dem FROM khach WHERE id = p_khach_id FOR SHARE;
    IF v_dem IS NULL OR v_dem = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Khach hang khong ton tai';
    END IF;

    SET v_not_found = FALSE;
    SELECT trang_thai INTO v_trang_thai_phong
    FROM phong WHERE id = p_phong_id FOR UPDATE;

    IF v_not_found OR v_trang_thai_phong IS NULL OR v_trang_thai_phong = 'BAO_TRI' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Phong khong ton tai hoac dang bao tri';
    END IF;

    SELECT COUNT(*) INTO v_dem
    FROM booking
    WHERE phong_id = p_phong_id
      AND trang_thai <> 'DA_HUY'
      AND p_ngay_nhan < ngay_tra
      AND p_ngay_tra > ngay_nhan;

    IF v_dem > 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Phong da duoc dat trong khoang thoi gian nay';
    END IF;

    SELECT COUNT(*), COUNT(DISTINCT x.dichvu_id)
    INTO v_selected_count, v_distinct_count
    FROM JSON_TABLE(
        p_dich_vu, '$[*]' COLUMNS(
            dichvu_id INT PATH '$.dichvu_id' ERROR ON EMPTY ERROR ON ERROR,
            so_luong INT PATH '$.so_luong' ERROR ON EMPTY ERROR ON ERROR
        )
    ) AS x;

    IF v_selected_count <> v_distinct_count THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Khong duoc chon trung dich vu';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM JSON_TABLE(
            p_dich_vu, '$[*]' COLUMNS(
                dichvu_id INT PATH '$.dichvu_id' ERROR ON EMPTY ERROR ON ERROR,
                so_luong INT PATH '$.so_luong' ERROR ON EMPTY ERROR ON ERROR
            )
        ) AS x
        LEFT JOIN dichvu d
          ON d.id = x.dichvu_id
         AND d.phong_id = p_phong_id
         AND d.booking_id IS NULL
        WHERE d.id IS NULL OR x.so_luong <= 0
    ) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Dich vu khong thuoc danh sach mac dinh cua phong hoac so luong khong hop le';
    END IF;

    INSERT INTO booking (phong_id, khach_id, ngay_nhan, ngay_tra, trang_thai)
    VALUES (p_phong_id, p_khach_id, p_ngay_nhan, p_ngay_tra, 'CHO_XAC_NHAN');

    SET v_booking_id = LAST_INSERT_ID();

    -- trg_booking_after_insert first copies all room defaults.
    -- Replace those copies with exactly the customer's selected services.
    DELETE FROM dichvu WHERE booking_id = v_booking_id;

    INSERT INTO dichvu (ten, don_gia, so_luong, phong_id, booking_id)
    SELECT d.ten, d.don_gia, x.so_luong, p_phong_id, v_booking_id
    FROM JSON_TABLE(
        p_dich_vu, '$[*]' COLUMNS(
            dichvu_id INT PATH '$.dichvu_id' ERROR ON EMPTY ERROR ON ERROR,
            so_luong INT PATH '$.so_luong' ERROR ON EMPTY ERROR ON ERROR
        )
    ) AS x
    JOIN dichvu d
      ON d.id = x.dichvu_id
     AND d.phong_id = p_phong_id
     AND d.booking_id IS NULL;

    COMMIT;

    SELECT v_booking_id AS booking_id,
           p_phong_id AS phong_id,
           p_khach_id AS khach_id,
           p_ngay_nhan AS ngay_nhan,
           p_ngay_tra AS ngay_tra,
           'CHO_XAC_NHAN' AS trang_thai,
           v_selected_count AS so_dich_vu_da_chon;
END$$
DELIMITER ;


-- 3.3 Hủy booking
DROP PROCEDURE IF EXISTS `sp_huy_booking`;
DELIMITER $$
CREATE PROCEDURE `sp_huy_booking`(
    IN p_booking_id INT
)
BEGIN
    DECLARE v_dem INT DEFAULT 0;
    DECLARE v_trang_thai VARCHAR(30);

    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    SELECT COUNT(*) INTO v_dem FROM booking WHERE id = p_booking_id;
    IF v_dem = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Booking khong ton tai';
    END IF;

    SELECT trang_thai INTO v_trang_thai
    FROM booking
    WHERE id = p_booking_id
    FOR UPDATE;

    IF v_trang_thai = 'DA_HUY' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Booking da duoc huy truoc do';
    END IF;

    IF v_trang_thai IN ('DANG_O', 'HOAN_THANH') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Khong the huy booking dang o hoac da hoan thanh';
    END IF;

    SELECT COUNT(*) INTO v_dem
    FROM pay
    WHERE booking_id = p_booking_id
      AND status = 'THANH_CONG';

    IF v_dem > 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Booking da thanh toan thanh cong, can xu ly hoan tien truoc';
    END IF;

    SELECT COUNT(*) INTO v_dem
    FROM pay
    WHERE booking_id = p_booking_id
      AND status = 'CHO_THANH_TOAN';

    IF v_dem > 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Booking con giao dich cho thanh toan; hay huy/that bai giao dich truoc';
    END IF;

    UPDATE booking SET trang_thai = 'DA_HUY' WHERE id = p_booking_id;

    COMMIT;

    SELECT id AS booking_id, trang_thai AS trang_thai_moi
    FROM booking
    WHERE id = p_booking_id;
END$$
DELIMITER ;


-- 3.4 Nhận phòng (Check-in)
DROP PROCEDURE IF EXISTS `sp_nhan_phong`;
DELIMITER $$
CREATE PROCEDURE `sp_nhan_phong`(IN p_booking_id INT)
BEGIN
    DECLARE v_status VARCHAR(30) DEFAULT NULL;
    DECLARE v_not_found BOOLEAN DEFAULT FALSE;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_not_found = TRUE;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    SELECT trang_thai INTO v_status
    FROM booking
    WHERE id = p_booking_id
    FOR UPDATE;

    IF v_not_found THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Booking khong ton tai';
    END IF;

    IF v_status <> 'DA_XAC_NHAN' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Chi nhan phong cho booking da xac nhan';
    END IF;

    -- Trigger trg_booking_after_update sẽ tự động đổi phong.trang_thai sang DANG_SU_DUNG
    UPDATE booking SET trang_thai = 'DANG_O' WHERE id = p_booking_id;

    COMMIT;

    SELECT p_booking_id AS booking_id, 'DANG_O' AS trang_thai;
END$$
DELIMITER ;


-- 3.5 Trả phòng (Check-out)
DROP PROCEDURE IF EXISTS `sp_tra_phong`;
DELIMITER $$
CREATE PROCEDURE `sp_tra_phong`(IN p_booking_id INT)
BEGIN
    DECLARE v_status VARCHAR(30) DEFAULT NULL;
    DECLARE v_not_found BOOLEAN DEFAULT FALSE;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_not_found = TRUE;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    SELECT trang_thai INTO v_status
    FROM booking
    WHERE id = p_booking_id
    FOR UPDATE;

    IF v_not_found THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Booking khong ton tai';
    END IF;

    IF v_status <> 'DANG_O' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Booking khong o trang thai dang o';
    END IF;

    -- Trigger trg_booking_after_update sẽ tự động giải phóng phong.trang_thai về SAN_SANG
    UPDATE booking SET trang_thai = 'HOAN_THANH' WHERE id = p_booking_id;

    COMMIT;

    SELECT p_booking_id AS booking_id, 'HOAN_THANH' AS trang_thai;
END$$
DELIMITER ;


-- 3.6 Thêm dịch vụ cho booking
DROP PROCEDURE IF EXISTS `sp_them_dichvu_booking`;
DELIMITER $$
CREATE PROCEDURE `sp_them_dichvu_booking`(
    IN p_booking_id INT,
    IN p_ten VARCHAR(100),
    IN p_don_gia DECIMAL(12,2),
    IN p_so_luong INT
)
BEGIN
    DECLARE v_phong_id INT DEFAULT NULL;
    DECLARE v_status VARCHAR(30) DEFAULT NULL;
    DECLARE v_not_found BOOLEAN DEFAULT FALSE;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_not_found = TRUE;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    SELECT phong_id, trang_thai INTO v_phong_id, v_status
    FROM booking
    WHERE id = p_booking_id
    FOR UPDATE;

    IF v_not_found THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Booking khong ton tai';
    END IF;

    IF v_status NOT IN ('CHO_XAC_NHAN', 'DA_XAC_NHAN', 'DANG_O') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Khong the them dich vu cho booking da huy hoac hoan thanh';
    END IF;

    INSERT INTO dichvu (ten, don_gia, so_luong, phong_id, booking_id)
    VALUES (p_ten, p_don_gia, p_so_luong, v_phong_id, p_booking_id);

    COMMIT;

    SELECT LAST_INSERT_ID() AS dichvu_id,
           p_booking_id AS booking_id,
           p_ten AS ten_dich_vu,
           p_don_gia AS don_gia,
           p_so_luong AS so_luong,
           (p_don_gia * p_so_luong) AS thanh_tien;
END$$
DELIMITER ;


-- 3.7 Tính tiền (gồm hệ số mùa cao điểm + dịch vụ) và tạo giao dịch thanh toán + hóa đơn
DROP PROCEDURE IF EXISTS `sp_tinh_tien_va_tao_hoa_don`;
DELIMITER $$
CREATE PROCEDURE `sp_tinh_tien_va_tao_hoa_don`(
    IN p_booking_id INT,
    IN p_method VARCHAR(30)
)
BEGIN
    DECLARE v_dem INT DEFAULT 0;
    DECLARE v_khach_id INT;
    DECLARE v_tien_phong DECIMAL(12,2) DEFAULT 0;
    DECLARE v_phu_phi_mua_cao_diem DECIMAL(12,2) DEFAULT 0;
    DECLARE v_tien_dich_vu DECIMAL(12,2) DEFAULT 0;
    DECLARE v_tong_tien DECIMAL(12,2) DEFAULT 0;
    DECLARE v_pay_id INT;
    DECLARE v_booking_status VARCHAR(30);
    DECLARE v_not_found BOOLEAN DEFAULT FALSE;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_not_found = TRUE;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
    SELECT b.khach_id, b.trang_thai, b.tien_phong_du_kien,
           b.tien_phu_phi_mua_cao_diem
    INTO v_khach_id, v_booking_status, v_tien_phong, v_phu_phi_mua_cao_diem
    FROM booking b WHERE b.id = p_booking_id FOR UPDATE;

    IF v_not_found THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Booking khong ton tai';
    END IF;
    IF v_booking_status = 'DA_HUY' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Khong the lap hoa don cho booking da huy';
    END IF;
    IF p_method IS NULL OR p_method NOT IN ('TIEN_MAT', 'CHUYEN_KHOAN', 'THE') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Phuong thuc thanh toan khong hop le';
    END IF;

    SELECT COUNT(*) INTO v_dem FROM pay
    WHERE booking_id = p_booking_id AND status IN ('CHO_THANH_TOAN', 'THANH_CONG');
    IF v_dem > 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Booking da co giao dich dang cho hoac thanh toan thanh cong';
    END IF;

    SELECT COALESCE(SUM(don_gia * so_luong), 0)
    INTO v_tien_dich_vu FROM dichvu WHERE booking_id = p_booking_id;

    SET v_tong_tien = v_tien_phong + v_phu_phi_mua_cao_diem + v_tien_dich_vu;

    INSERT INTO pay (booking_id, khach_id, so_tien, ngay_thanh_toan, method, status)
    VALUES (p_booking_id, v_khach_id, v_tong_tien, NOW(), p_method, 'CHO_THANH_TOAN');
    SET v_pay_id = LAST_INSERT_ID();

    INSERT INTO hoadon (pay_id, tien_phong, tien_phu_phi_mua_cao_diem, tien_dich_vu, tong_tien)
    VALUES (v_pay_id, v_tien_phong, v_phu_phi_mua_cao_diem, v_tien_dich_vu, v_tong_tien);

    COMMIT;
    SELECT p_booking_id AS booking_id, v_khach_id AS khach_id, v_pay_id AS pay_id,
           v_tien_phong AS tien_phong,
           v_phu_phi_mua_cao_diem AS tien_phu_phi_mua_cao_diem,
           v_tien_dich_vu AS tien_dich_vu, v_tong_tien AS tong_tien,
           p_method AS phuong_thuc, 'CHO_THANH_TOAN' AS trang_thai_thanh_toan;
END$$
DELIMITER ;

-- 3.8 Lịch sử đặt phòng theo khách hàng
DROP PROCEDURE IF EXISTS `sp_lich_su_booking`;
DELIMITER $$
CREATE PROCEDURE `sp_lich_su_booking`(
    IN p_khach_id INT
)
BEGIN
    DECLARE v_dem INT DEFAULT 0;

    SELECT COUNT(*) INTO v_dem FROM khach WHERE id = p_khach_id;
    IF v_dem = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Khach hang khong ton tai';
    END IF;

    SELECT
        k.id AS khach_id,
        k.ho_ten,
        k.cccd,
        k.sdt,
        b.id AS booking_id,
        p.so_phong,
        lp.ten AS loai_phong,
        b.ngay_nhan,
        b.ngay_tra,
        DATEDIFF(b.ngay_tra, b.ngay_nhan) AS so_dem,
        b.trang_thai AS trang_thai_booking,
        COALESCE(
            (
                SELECT SUM(h.tong_tien)
                FROM pay py
                JOIN hoadon h ON py.id = h.pay_id
                WHERE py.booking_id = b.id
            ), 0
        ) AS tong_tien_hoa_don,
        (
            SELECT GROUP_CONCAT(CONCAT(py.id, ': ', py.status) ORDER BY py.id SEPARATOR '; ')
            FROM pay py
            WHERE py.booking_id = b.id
        ) AS lich_su_thanh_toan
    FROM khach k
    LEFT JOIN booking b ON k.id = b.khach_id
    LEFT JOIN phong p ON b.phong_id = p.id
    LEFT JOIN loaiphong lp ON p.loai_phong_id = lp.id
    WHERE k.id = p_khach_id
    ORDER BY b.ngay_nhan DESC;
END$$
DELIMITER ;


-- 3.9 Thống kê doanh thu theo khoảng thời gian
DROP PROCEDURE IF EXISTS `sp_thong_ke_doanh_thu`;
DELIMITER $$
CREATE PROCEDURE `sp_thong_ke_doanh_thu`(
    IN p_tu_ngay DATE,
    IN p_den_ngay DATE
)
BEGIN
    IF p_tu_ngay IS NULL OR p_den_ngay IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Ngay bat dau va ngay ket thuc khong duoc de trong';
    END IF;

    IF p_den_ngay < p_tu_ngay THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Ngay ket thuc phai lon hon hoac bang ngay bat dau';
    END IF;

    SELECT
        p_tu_ngay AS tu_ngay,
        p_den_ngay AS den_ngay,
        COALESCE(SUM(CASE WHEN status = 'THANH_CONG' THEN so_tien ELSE 0 END), 0) AS tong_tien_thanh_cong,
        COALESCE(SUM(CASE WHEN status = 'HOAN_TIEN' THEN so_tien ELSE 0 END), 0) AS tong_tien_hoan,
        COALESCE(SUM(
            CASE
                WHEN status = 'THANH_CONG' THEN so_tien
                WHEN status = 'HOAN_TIEN' THEN -so_tien
                ELSE 0
            END
        ), 0) AS doanh_thu_thuc_thu,
        COALESCE(SUM(status = 'THANH_CONG'), 0) AS so_giao_dich_thanh_cong,
        COALESCE(SUM(status = 'HOAN_TIEN'), 0) AS so_giao_dich_hoan_tien
    FROM pay
    WHERE ngay_thanh_toan >= p_tu_ngay
      AND ngay_thanh_toan < DATE_ADD(p_den_ngay, INTERVAL 1 DAY);

    SELECT
        method AS phuong_thuc_thanh_toan,
        SUM(
            CASE
                WHEN status = 'THANH_CONG' THEN so_tien
                WHEN status = 'HOAN_TIEN' THEN -so_tien
                ELSE 0
            END
        ) AS doanh_thu_thuc_thu,
        COALESCE(SUM(status = 'THANH_CONG'), 0) AS so_giao_dich_thanh_cong
    FROM pay
    WHERE ngay_thanh_toan >= p_tu_ngay
      AND ngay_thanh_toan < DATE_ADD(p_den_ngay, INTERVAL 1 DAY)
    GROUP BY method
    ORDER BY doanh_thu_thuc_thu DESC;

    SELECT COUNT(*) AS so_booking_hoan_thanh
    FROM booking
    WHERE trang_thai = 'HOAN_THANH'
      AND ngay_tra >= p_tu_ngay
      AND ngay_tra < DATE_ADD(p_den_ngay, INTERVAL 1 DAY);
END$$
DELIMITER ;



-- ----------------------------------------------------------------------------
-- 3.10 Them khach hang
-- ----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS `sp_them_khach_hang`;
DELIMITER $$
CREATE PROCEDURE `sp_them_khach_hang`(
    IN p_ho_ten VARCHAR(100),
    IN p_cccd VARCHAR(20),
    IN p_sdt VARCHAR(20)
)
BEGIN
    IF p_ho_ten IS NULL OR TRIM(p_ho_ten) = ''
       OR p_cccd IS NULL OR TRIM(p_cccd) = ''
       OR p_sdt IS NULL OR TRIM(p_sdt) = '' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Ho ten, CCCD va so dien thoai khong duoc de trong';
    END IF;

    INSERT INTO khach (ho_ten, cccd, sdt)
    VALUES (TRIM(p_ho_ten), TRIM(p_cccd), TRIM(p_sdt));

    SELECT LAST_INSERT_ID() AS khach_id,
           TRIM(p_ho_ten) AS ho_ten,
           TRIM(p_cccd) AS cccd,
           TRIM(p_sdt) AS sdt;
END$$
DELIMITER ;


-- ----------------------------------------------------------------------------
-- 3.11 Cap nhat thong tin phong (khong cho sua trang thai DANG_SU_DUNG thu cong)
-- ----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS `sp_cap_nhat_thong_tin_phong`;
DELIMITER $$
CREATE PROCEDURE `sp_cap_nhat_thong_tin_phong`(
    IN p_phong_id INT,
    IN p_so_phong VARCHAR(20),
    IN p_loai_phong_id INT,
    IN p_trang_thai VARCHAR(30)
)
BEGIN
    DECLARE v_dem INT DEFAULT 0;
    DECLARE v_room_id INT DEFAULT NULL;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    SELECT id INTO v_room_id
    FROM phong
    WHERE id = p_phong_id
    FOR UPDATE;

    IF v_room_id IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Phong khong ton tai';
    END IF;

    IF p_so_phong IS NULL OR TRIM(p_so_phong) = '' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'So phong khong duoc de trong';
    END IF;

    IF p_trang_thai IS NULL OR p_trang_thai NOT IN ('SAN_SANG', 'BAO_TRI') THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Chi duoc cap nhat SAN_SANG hoac BAO_TRI; DANG_SU_DUNG do Booking tu dong quan ly';
    END IF;

    SELECT COUNT(*) INTO v_dem
    FROM booking
    WHERE phong_id = p_phong_id
      AND trang_thai = 'DANG_O';

    IF v_dem > 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Phong dang co khach luu tru, khong the thay doi trang thai phong';
    END IF;

    IF p_trang_thai = 'BAO_TRI' THEN
        SELECT COUNT(*) INTO v_dem
        FROM booking
        WHERE phong_id = p_phong_id
          AND trang_thai IN ('CHO_XAC_NHAN', 'DA_XAC_NHAN')
          AND ngay_tra > CURDATE();

        IF v_dem > 0 THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Phong con Booking hien tai/tuong lai, can xu ly Booking truoc khi bao tri';
        END IF;
    END IF;

    UPDATE phong
    SET so_phong = TRIM(p_so_phong),
        loai_phong_id = p_loai_phong_id,
        trang_thai = p_trang_thai
    WHERE id = p_phong_id;

    COMMIT;

    SELECT id AS phong_id, so_phong, loai_phong_id, trang_thai
    FROM phong
    WHERE id = p_phong_id;
END$$
DELIMITER ;


-- ----------------------------------------------------------------------------
-- 3.12 Xac nhan Booking (danh cho quan tri vien)
-- ----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS `sp_xac_nhan_booking`;
DELIMITER $$
CREATE PROCEDURE `sp_xac_nhan_booking`(IN p_booking_id INT)
BEGIN
    DECLARE v_status VARCHAR(30) DEFAULT NULL;
    DECLARE v_not_found BOOLEAN DEFAULT FALSE;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_not_found = TRUE;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;

    SELECT trang_thai INTO v_status
    FROM booking
    WHERE id = p_booking_id
    FOR UPDATE;

    IF v_not_found THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Booking khong ton tai';
    END IF;

    IF v_status <> 'CHO_XAC_NHAN' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Chi xac nhan Booking dang o trang thai CHO_XAC_NHAN';
    END IF;

    UPDATE booking
    SET trang_thai = 'DA_XAC_NHAN'
    WHERE id = p_booking_id;

    COMMIT;

    SELECT id AS booking_id, trang_thai
    FROM booking
    WHERE id = p_booking_id;
END$$
DELIMITER ;


-- ----------------------------------------------------------------------------
-- 3.13 Xem chi tiet Booking (3 result sets: thong tin, dich vu, thanh toan)
-- ----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS `sp_xem_chi_tiet_booking`;
DELIMITER $$
CREATE PROCEDURE `sp_xem_chi_tiet_booking`(IN p_booking_id INT)
BEGIN
    IF NOT EXISTS (SELECT 1 FROM booking WHERE id = p_booking_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Booking khong ton tai';
    END IF;

    -- Result set 1: Booking and the immutable room/peak-season snapshot.
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
           b.tien_phong_du_kien,
           b.tien_phu_phi_mua_cao_diem,
           b.ap_dung_mua_cao_diem,
           b.chi_tiet_mua_cao_diem
    FROM booking b
    JOIN khach k ON k.id = b.khach_id
    JOIN phong p ON p.id = b.phong_id
    JOIN loaiphong lp ON lp.id = p.loai_phong_id
    WHERE b.id = p_booking_id;

    -- Result set 2: selected services.
    SELECT d.id AS dichvu_id,
           d.ten,
           d.don_gia,
           d.so_luong,
           (d.don_gia * d.so_luong) AS thanh_tien
    FROM dichvu d
    WHERE d.booking_id = p_booking_id
    ORDER BY d.id;

    -- Result set 3: payment and invoice with surcharge kept separate.
    SELECT py.id AS pay_id,
           py.ngay_thanh_toan,
           py.so_tien,
           py.tien_phong_ap_dung,
           py.tien_phu_phi_mua_cao_diem AS pay_tien_phu_phi_mua_cao_diem,
           py.method,
           py.status,
           hd.id AS hoadon_id,
           hd.tien_phong,
           hd.tien_phu_phi_mua_cao_diem AS hoadon_tien_phu_phi_mua_cao_diem,
           hd.tien_dich_vu,
           hd.tong_tien,
           hd.ngay_lap
    FROM pay py
    LEFT JOIN hoadon hd ON hd.pay_id = py.id
    WHERE py.booking_id = p_booking_id
    ORDER BY py.id;
END$$
DELIMITER ;

-- ----------------------------------------------------------------------------
-- 3.14 Thong ke so phong theo trang thai
-- ----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS `sp_thong_ke_phong`;
DELIMITER $$
CREATE PROCEDURE `sp_thong_ke_phong`()
BEGIN
    SELECT 'SAN_SANG' AS trang_thai, COUNT(*) AS so_luong
    FROM phong WHERE trang_thai = 'SAN_SANG'
    UNION ALL
    SELECT 'DANG_SU_DUNG', COUNT(*)
    FROM phong WHERE trang_thai = 'DANG_SU_DUNG'
    UNION ALL
    SELECT 'BAO_TRI', COUNT(*)
    FROM phong WHERE trang_thai = 'BAO_TRI';
END$$
DELIMITER ;


-- ----------------------------------------------------------------------------
-- 3.15 Cap nhat dich vu (trigger se tu kiem tra Booking va hoa don)
-- ----------------------------------------------------------------------------
DROP PROCEDURE IF EXISTS `sp_cap_nhat_dich_vu`;
DELIMITER $$
CREATE PROCEDURE `sp_cap_nhat_dich_vu`(
    IN p_dichvu_id INT,
    IN p_ten VARCHAR(100),
    IN p_don_gia DECIMAL(12,2),
    IN p_so_luong INT
)
BEGIN
    IF p_ten IS NULL OR TRIM(p_ten) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Ten dich vu khong duoc de trong';
    END IF;

    IF p_don_gia IS NULL OR p_don_gia < 0 OR p_so_luong IS NULL OR p_so_luong <= 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Don gia hoac so luong dich vu khong hop le';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM dichvu WHERE id = p_dichvu_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Dich vu khong ton tai';
    END IF;

    UPDATE dichvu
    SET ten = TRIM(p_ten),
        don_gia = p_don_gia,
        so_luong = p_so_luong
    WHERE id = p_dichvu_id;

    SELECT id AS dichvu_id, ten, don_gia, so_luong,
           don_gia * so_luong AS thanh_tien
    FROM dichvu
    WHERE id = p_dichvu_id;
END$$
DELIMITER ;


-- Backfill immutable nightly room and peak-surcharge snapshots for seed rows.
DELIMITER $$
-- Refund a successful payment through the guarded Pay status transition.
DROP PROCEDURE IF EXISTS `sp_hoan_tien`;
DELIMITER $$
CREATE PROCEDURE `sp_hoan_tien`(IN p_pay_id INT)
BEGIN
    DECLARE v_status VARCHAR(30) DEFAULT NULL;
    DECLARE v_not_found BOOLEAN DEFAULT FALSE;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_not_found = TRUE;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
    SELECT status INTO v_status
    FROM pay
    WHERE id = p_pay_id
    FOR UPDATE;

    IF v_not_found THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Giao dich thanh toan khong ton tai';
    END IF;
    IF v_status <> 'THANH_CONG' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Chi hoan tien cho giao dich da THANH_CONG';
    END IF;

    UPDATE pay SET status = 'HOAN_TIEN' WHERE id = p_pay_id;
    COMMIT;

    SELECT id AS pay_id, booking_id, so_tien, method,
           status AS trang_thai_thanh_toan
    FROM pay WHERE id = p_pay_id;
END$$
DELIMITER ;

-- Confirm a pending payment; triggers validate invoice and confirm the Booking.
DROP PROCEDURE IF EXISTS `sp_xac_nhan_thanh_toan`;
DELIMITER $$
CREATE PROCEDURE `sp_xac_nhan_thanh_toan`(IN p_pay_id INT)
BEGIN
    DECLARE v_status VARCHAR(30) DEFAULT NULL;
    DECLARE v_not_found BOOLEAN DEFAULT FALSE;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_not_found = TRUE;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
    SELECT status INTO v_status
    FROM pay
    WHERE id = p_pay_id
    FOR UPDATE;

    IF v_not_found THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Giao dich thanh toan khong ton tai';
    END IF;
    IF v_status <> 'CHO_THANH_TOAN' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Chi xac nhan giao dich dang CHO_THANH_TOAN';
    END IF;

    UPDATE pay SET status = 'THANH_CONG' WHERE id = p_pay_id;
    COMMIT;

    SELECT py.id AS pay_id, py.booking_id, py.so_tien, py.method,
           py.status AS trang_thai_thanh_toan,
           b.trang_thai AS trang_thai_booking,
           hd.id AS hoadon_id, hd.tong_tien
    FROM pay py
    JOIN booking b ON b.id = py.booking_id
    LEFT JOIN hoadon hd ON hd.pay_id = py.id
    WHERE py.id = p_pay_id;
END$$
DELIMITER ;

DROP PROCEDURE IF EXISTS `sp_backfill_peak_price_snapshots`$$
CREATE PROCEDURE `sp_backfill_peak_price_snapshots`()
BEGIN
    DECLARE v_done BOOLEAN DEFAULT FALSE;
    DECLARE v_booking_id INT;
    DECLARE v_room_id INT;
    DECLARE v_start DATE;
    DECLARE v_end DATE;
    DECLARE v_rate DECIMAL(12,2);
    DECLARE v_day DATE;
    DECLARE v_factor DECIMAL(4,2);
    DECLARE v_season_id INT;
    DECLARE v_room_total DECIMAL(12,2);
    DECLARE v_peak_fee DECIMAL(12,2);
    DECLARE v_flag TINYINT(1);
    DECLARE v_detail JSON;
    DECLARE booking_cursor CURSOR FOR
        SELECT id, phong_id, ngay_nhan, ngay_tra FROM booking;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_done = TRUE;

    OPEN booking_cursor;
    booking_loop: LOOP
        FETCH booking_cursor INTO v_booking_id, v_room_id, v_start, v_end;
        IF v_done THEN LEAVE booking_loop; END IF;
        SELECT lp.gia_co_ban INTO v_rate
        FROM phong p JOIN loaiphong lp ON lp.id=p.loai_phong_id
        WHERE p.id=v_room_id;
        SET v_day=v_start; SET v_room_total=0.00; SET v_peak_fee=0.00;
        SET v_flag=0; SET v_detail=JSON_ARRAY();
        WHILE v_day < v_end DO
            SET v_season_id=NULL; SET v_factor=0.00;
            SELECT MAX(id), COALESCE(MAX(he_so_gia),0.00)
            INTO v_season_id, v_factor
            FROM muacaodiem
            WHERE phong_id=v_room_id AND v_day BETWEEN tu_ngay AND den_ngay;
            IF v_season_id IS NOT NULL THEN SET v_flag=1; END IF;
            SET v_room_total=v_room_total+v_rate;
            SET v_peak_fee=v_peak_fee+ROUND(v_rate*v_factor,2);
            SET v_detail=JSON_ARRAY_APPEND(v_detail,'$',JSON_OBJECT(
                'ngay',DATE_FORMAT(v_day,'%Y-%m-%d'),'mua_cao_diem_id',v_season_id,
                'he_so_gia',v_factor,'gia_co_ban',v_rate,'tien_dem',v_rate,
                'phi_mua_cao_diem',ROUND(v_rate*v_factor,2)));
            SET v_day=DATE_ADD(v_day,INTERVAL 1 DAY);
        END WHILE;
        UPDATE booking SET tien_phong_du_kien=v_room_total,
            tien_phu_phi_mua_cao_diem=v_peak_fee,
            ap_dung_mua_cao_diem=v_flag, chi_tiet_mua_cao_diem=v_detail
        WHERE id=v_booking_id;
    END LOOP;
    CLOSE booking_cursor;

    UPDATE pay py
    JOIN booking b ON b.id=py.booking_id
    SET py.tien_phong_ap_dung=b.tien_phong_du_kien,
        py.tien_phu_phi_mua_cao_diem=b.tien_phu_phi_mua_cao_diem,
        py.ap_dung_mua_cao_diem=b.ap_dung_mua_cao_diem,
        py.chi_tiet_mua_cao_diem=b.chi_tiet_mua_cao_diem;

    UPDATE hoadon h
    JOIN pay py ON py.id=h.pay_id
    SET h.tien_phong=py.tien_phong_ap_dung,
        h.tien_phu_phi_mua_cao_diem=py.tien_phu_phi_mua_cao_diem;
END$$
DELIMITER ;
CALL `sp_backfill_peak_price_snapshots`();
DROP PROCEDURE IF EXISTS `sp_backfill_peak_price_snapshots`;


-- ============================================================================
-- 4. TRIGGERS (15 TRIGGERS - REVISED TO PROTECT ERD BUSINESS RULES)
-- ============================================================================

-- ----------------------------------------------------------------------------
-- GROUP A: BOOKING - PHONG - DICHVU
-- ----------------------------------------------------------------------------

-- 1. Validate Booking insert: date range, room status, overlap and check-in state.
DROP TRIGGER IF EXISTS `trg_booking_before_insert`;
DELIMITER $$
CREATE TRIGGER `trg_booking_before_insert`
BEFORE INSERT ON `booking`
FOR EACH ROW
BEGIN
    DECLARE v_room_status VARCHAR(30) DEFAULT NULL;
    DECLARE v_dem INT DEFAULT 0;
    DECLARE v_gia_co_ban DECIMAL(12,2) DEFAULT 0.00;
    DECLARE v_ngay DATE;
    DECLARE v_he_so DECIMAL(4,2) DEFAULT 0.00;
    DECLARE v_mua_id INT DEFAULT NULL;
    DECLARE v_tien_phong DECIMAL(12,2) DEFAULT 0.00;
    DECLARE v_phu_phi_mua_cao_diem DECIMAL(12,2) DEFAULT 0.00;
    DECLARE v_co_mua_cao_diem TINYINT(1) DEFAULT 0;
    DECLARE v_chi_tiet JSON;

    IF NEW.ngay_nhan IS NULL OR NEW.ngay_tra IS NULL
       OR NEW.ngay_tra <= NEW.ngay_nhan THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Ngay nhan va ngay tra khong hop le';
    END IF;

    IF NEW.trang_thai NOT IN ('CHO_XAC_NHAN', 'DA_XAC_NHAN', 'DANG_O', 'DA_HUY', 'HOAN_THANH') THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Trang thai Booking khong hop le';
    END IF;

    -- Lock the room row so concurrent booking requests for the same room serialize.
    SELECT trang_thai INTO v_room_status
    FROM phong
    WHERE id = NEW.phong_id
    FOR UPDATE;

    IF v_room_status IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Phong khong ton tai';
    END IF;

    IF NEW.trang_thai <> 'DA_HUY' AND v_room_status = 'BAO_TRI' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Phong dang bao tri, khong the dat';
    END IF;

    IF NEW.trang_thai <> 'DA_HUY' THEN
        SELECT COUNT(*) INTO v_dem
        FROM booking b
        WHERE b.phong_id = NEW.phong_id
          AND b.trang_thai <> 'DA_HUY'
          AND NEW.ngay_nhan < b.ngay_tra
          AND NEW.ngay_tra > b.ngay_nhan;

        IF v_dem > 0 THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Phong da co Booking trung khoang thoi gian';
        END IF;
    END IF;

    -- Lock in the nightly room-price breakdown at Booking creation.
    SELECT lp.gia_co_ban INTO v_gia_co_ban
    FROM phong p JOIN loaiphong lp ON lp.id = p.loai_phong_id
    WHERE p.id = NEW.phong_id;
    SET v_ngay = NEW.ngay_nhan;
    SET v_chi_tiet = JSON_ARRAY();
    WHILE v_ngay < NEW.ngay_tra DO
        SET v_mua_id = NULL;
        SET v_he_so = 0.00;
        SELECT MAX(m.id), COALESCE(MAX(m.he_so_gia), 0.00)
        INTO v_mua_id, v_he_so
        FROM muacaodiem m
        WHERE m.phong_id = NEW.phong_id
          AND v_ngay BETWEEN m.tu_ngay AND m.den_ngay;
        IF v_mua_id IS NOT NULL THEN SET v_co_mua_cao_diem = 1; END IF;
        SET v_tien_phong = v_tien_phong + v_gia_co_ban;
        SET v_phu_phi_mua_cao_diem = v_phu_phi_mua_cao_diem + ROUND(v_gia_co_ban * v_he_so, 2);
        SET v_chi_tiet = JSON_ARRAY_APPEND(
            v_chi_tiet, '$',
            JSON_OBJECT('ngay', DATE_FORMAT(v_ngay, '%Y-%m-%d'),
                        'mua_cao_diem_id', v_mua_id,
                        'he_so_gia', v_he_so,
                        'gia_co_ban', v_gia_co_ban,
                        'tien_dem', v_gia_co_ban,
                        'phi_mua_cao_diem', ROUND(v_gia_co_ban * v_he_so, 2))
        );
        SET v_ngay = DATE_ADD(v_ngay, INTERVAL 1 DAY);
    END WHILE;
    SET NEW.tien_phong_du_kien = v_tien_phong;
    SET NEW.tien_phu_phi_mua_cao_diem = v_phu_phi_mua_cao_diem;
    SET NEW.ap_dung_mua_cao_diem = v_co_mua_cao_diem;
    SET NEW.chi_tiet_mua_cao_diem = v_chi_tiet;

    IF NEW.trang_thai = 'DANG_O' THEN
        IF v_room_status = 'DANG_SU_DUNG' THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Phong dang co khach su dung';
        END IF;

        SELECT COUNT(*) INTO v_dem
        FROM booking b
        WHERE b.phong_id = NEW.phong_id
          AND b.trang_thai = 'DANG_O';

        IF v_dem > 0 THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Phong da co Booking dang luu tru';
        END IF;
    END IF;
END$$
DELIMITER ;


-- 2. Copy default room services to a new Booking; synchronize direct DANG_O inserts.
DROP TRIGGER IF EXISTS `trg_booking_after_insert`;
DELIMITER $$
CREATE TRIGGER `trg_booking_after_insert`
AFTER INSERT ON `booking`
FOR EACH ROW
BEGIN
    IF NEW.trang_thai <> 'DA_HUY' THEN
        INSERT INTO dichvu (ten, don_gia, so_luong, phong_id, booking_id)
        SELECT d.ten, d.don_gia, d.so_luong, NEW.phong_id, NEW.id
        FROM dichvu d
        WHERE d.phong_id = NEW.phong_id
          AND d.booking_id IS NULL;
    END IF;

    IF NEW.trang_thai = 'DANG_O' THEN
        UPDATE phong
        SET trang_thai = 'DANG_SU_DUNG'
        WHERE id = NEW.phong_id;
    END IF;
END$$
DELIMITER ;


-- 3. Validate Booking update: legal status flow, no overlap, payment and invoice consistency.
DROP TRIGGER IF EXISTS `trg_booking_before_update`;
DELIMITER $$
CREATE TRIGGER `trg_booking_before_update`
BEFORE UPDATE ON `booking`
FOR EACH ROW
BEGIN
    DECLARE v_room_status VARCHAR(30) DEFAULT NULL;
    DECLARE v_dem INT DEFAULT 0;
    DECLARE v_changed_room_or_dates BOOLEAN DEFAULT FALSE;
    DECLARE v_gia_co_ban DECIMAL(12,2) DEFAULT 0.00;
    DECLARE v_ngay DATE;
    DECLARE v_he_so DECIMAL(4,2) DEFAULT 0.00;
    DECLARE v_mua_id INT DEFAULT NULL;
    DECLARE v_tien_phong DECIMAL(12,2) DEFAULT 0.00;
    DECLARE v_phu_phi_mua_cao_diem DECIMAL(12,2) DEFAULT 0.00;
    DECLARE v_co_mua_cao_diem TINYINT(1) DEFAULT 0;
    DECLARE v_chi_tiet JSON;

    IF NEW.ngay_nhan IS NULL OR NEW.ngay_tra IS NULL
       OR NEW.ngay_tra <= NEW.ngay_nhan THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Ngay nhan va ngay tra khong hop le';
    END IF;

    SET v_changed_room_or_dates =
        (NEW.phong_id <> OLD.phong_id)
        OR (NEW.ngay_nhan <> OLD.ngay_nhan)
        OR (NEW.ngay_tra <> OLD.ngay_tra);

    IF NOT v_changed_room_or_dates AND (
        NEW.tien_phong_du_kien <> OLD.tien_phong_du_kien
        OR NEW.tien_phu_phi_mua_cao_diem <> OLD.tien_phu_phi_mua_cao_diem
        OR NEW.ap_dung_mua_cao_diem <> OLD.ap_dung_mua_cao_diem
        OR NOT (NEW.chi_tiet_mua_cao_diem <=> OLD.chi_tiet_mua_cao_diem)
    ) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Snapshot gia Booking khong duoc sua truc tiep';
    END IF;

    -- Cancelled and completed Bookings are historical records and cannot be altered.
    IF OLD.trang_thai IN ('DA_HUY', 'HOAN_THANH')
       AND (NEW.phong_id <> OLD.phong_id
            OR NEW.khach_id <> OLD.khach_id
            OR NEW.ngay_nhan <> OLD.ngay_nhan
            OR NEW.ngay_tra <> OLD.ngay_tra
            OR NEW.trang_thai <> OLD.trang_thai) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Booking da huy/hoan thanh khong duoc thay doi';
    END IF;

    -- Legal Booking status transitions.
    IF NEW.trang_thai <> OLD.trang_thai THEN
        IF OLD.trang_thai = 'CHO_XAC_NHAN'
           AND NEW.trang_thai NOT IN ('DA_XAC_NHAN', 'DA_HUY') THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Chuyen trang thai Booking khong hop le';
        ELSEIF OLD.trang_thai = 'DA_XAC_NHAN'
           AND NEW.trang_thai NOT IN ('DANG_O', 'DA_HUY') THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Chuyen trang thai Booking khong hop le';
        ELSEIF OLD.trang_thai = 'DANG_O'
           AND NEW.trang_thai <> 'HOAN_THANH' THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Booking dang o chi duoc chuyen sang HOAN_THANH';
        ELSEIF OLD.trang_thai IN ('DA_HUY', 'HOAN_THANH') THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Booking da ket thuc, khong the mo lai';
        END IF;
    END IF;

    -- Room/date changes after issuing an invoice would invalidate the bill.
    IF v_changed_room_or_dates THEN
        SELECT COUNT(*) INTO v_dem
        FROM pay py
        WHERE py.booking_id = OLD.id;

        IF v_dem > 0 THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Booking da co giao dich Pay, khong duoc doi phong hoac ngay';
        END IF;
    END IF;

    -- A customer cannot be replaced after a payment record has been created.
    IF NEW.khach_id <> OLD.khach_id THEN
        SELECT COUNT(*) INTO v_dem
        FROM pay
        WHERE booking_id = OLD.id;

        IF v_dem > 0 THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Booking da co giao dich, khong duoc doi khach hang';
        END IF;
    END IF;

    -- Cancellation is blocked while a payment is pending or successful.
    IF NEW.trang_thai = 'DA_HUY' AND OLD.trang_thai <> 'DA_HUY' THEN
        SELECT COUNT(*) INTO v_dem
        FROM pay
        WHERE booking_id = OLD.id
          AND status IN ('CHO_THANH_TOAN', 'THANH_CONG');

        IF v_dem > 0 THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Can xu ly giao dich dang cho/thanh cong truoc khi huy Booking';
        END IF;
    END IF;

    -- Lock the affected room on room/date changes to serialize overlap checks.
    IF v_changed_room_or_dates
       OR (NEW.trang_thai = 'DANG_O' AND OLD.trang_thai <> 'DANG_O') THEN
        SELECT trang_thai INTO v_room_status
        FROM phong
        WHERE id = NEW.phong_id
        FOR UPDATE;

        IF v_room_status IS NULL OR v_room_status = 'BAO_TRI' THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Phong moi khong ton tai hoac dang bao tri';
        END IF;
    END IF;

    IF NEW.trang_thai = 'DANG_O'
       AND (OLD.trang_thai <> 'DANG_O' OR NEW.phong_id <> OLD.phong_id) THEN
        IF v_room_status = 'DANG_SU_DUNG' THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Phong dang duoc su dung boi khach khac';
        END IF;

        SELECT COUNT(*) INTO v_dem
        FROM booking b
        WHERE b.phong_id = NEW.phong_id
          AND b.id <> OLD.id
          AND b.trang_thai = 'DANG_O';

        IF v_dem > 0 THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Phong da co Booking khac dang luu tru';
        END IF;
    END IF;

    -- Keep the non-overlap rule when dates or room are changed.
    IF NEW.trang_thai <> 'DA_HUY' THEN
        SELECT COUNT(*) INTO v_dem
        FROM booking b
        WHERE b.phong_id = NEW.phong_id
          AND b.id <> OLD.id
          AND b.trang_thai <> 'DA_HUY'
          AND NEW.ngay_nhan < b.ngay_tra
          AND NEW.ngay_tra > b.ngay_nhan;

        IF v_dem > 0 THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Cap nhat that bai: phong da co Booking trung lich';
        END IF;
    END IF;

    -- Recalculate snapshot only when the Booking dates/room are changed.
    IF v_changed_room_or_dates THEN
        SELECT lp.gia_co_ban INTO v_gia_co_ban
        FROM phong p JOIN loaiphong lp ON lp.id = p.loai_phong_id
        WHERE p.id = NEW.phong_id;
        SET v_ngay = NEW.ngay_nhan;
        SET v_chi_tiet = JSON_ARRAY();
        WHILE v_ngay < NEW.ngay_tra DO
            SET v_mua_id = NULL;
            SET v_he_so = 0.00;
            SELECT MAX(m.id), COALESCE(MAX(m.he_so_gia), 0.00)
            INTO v_mua_id, v_he_so
            FROM muacaodiem m
            WHERE m.phong_id = NEW.phong_id
              AND v_ngay BETWEEN m.tu_ngay AND m.den_ngay;
            IF v_mua_id IS NOT NULL THEN SET v_co_mua_cao_diem = 1; END IF;
            SET v_tien_phong = v_tien_phong + v_gia_co_ban;
            SET v_phu_phi_mua_cao_diem = v_phu_phi_mua_cao_diem + ROUND(v_gia_co_ban * v_he_so, 2);
            SET v_chi_tiet = JSON_ARRAY_APPEND(
                v_chi_tiet, '$',
                JSON_OBJECT('ngay', DATE_FORMAT(v_ngay, '%Y-%m-%d'),
                            'mua_cao_diem_id', v_mua_id,
                            'he_so_gia', v_he_so,
                            'gia_co_ban', v_gia_co_ban,
                            'tien_dem', v_gia_co_ban,
                            'phi_mua_cao_diem', ROUND(v_gia_co_ban * v_he_so, 2))
            );
            SET v_ngay = DATE_ADD(v_ngay, INTERVAL 1 DAY);
        END WHILE;
        SET NEW.tien_phong_du_kien = v_tien_phong;
        SET NEW.tien_phu_phi_mua_cao_diem = v_phu_phi_mua_cao_diem;
        SET NEW.ap_dung_mua_cao_diem = v_co_mua_cao_diem;
        SET NEW.chi_tiet_mua_cao_diem = v_chi_tiet;
    END IF;
END$$
DELIMITER ;


-- 4. Synchronize room status and service.room_id when a Booking changes.
DROP TRIGGER IF EXISTS `trg_booking_after_update`;
DELIMITER $$
CREATE TRIGGER `trg_booking_after_update`
AFTER UPDATE ON `booking`
FOR EACH ROW
BEGIN
    DECLARE v_dem INT DEFAULT 0;

    IF NEW.phong_id <> OLD.phong_id THEN
        UPDATE dichvu
        SET phong_id = NEW.phong_id
        WHERE booking_id = NEW.id
          AND phong_id <> NEW.phong_id;
    END IF;

    -- Release the old room on check-out or when an in-house Booking moves rooms.
    IF OLD.trang_thai = 'DANG_O'
       AND (NEW.trang_thai <> 'DANG_O' OR NEW.phong_id <> OLD.phong_id) THEN
        SELECT COUNT(*) INTO v_dem
        FROM booking
        WHERE phong_id = OLD.phong_id
          AND id <> NEW.id
          AND trang_thai = 'DANG_O';

        UPDATE phong
        SET trang_thai = IF(v_dem > 0, 'DANG_SU_DUNG', 'SAN_SANG')
        WHERE id = OLD.phong_id
          AND trang_thai <> 'BAO_TRI';
    END IF;

    -- Occupy the new/current room on check-in or when an in-house Booking moves.
    IF NEW.trang_thai = 'DANG_O'
       AND (OLD.trang_thai <> 'DANG_O' OR NEW.phong_id <> OLD.phong_id) THEN
        UPDATE phong
        SET trang_thai = 'DANG_SU_DUNG'
        WHERE id = NEW.phong_id;
    END IF;
END$$
DELIMITER ;


-- ----------------------------------------------------------------------------
-- GROUP B: PEAK-SEASON CONFIGURATION
-- ----------------------------------------------------------------------------

-- 5. Validate peak-season INSERT and prevent overlapping periods for the same room.
DROP TRIGGER IF EXISTS `trg_muacaodiem_before_insert`;
DELIMITER $$
CREATE TRIGGER `trg_muacaodiem_before_insert`
BEFORE INSERT ON `muacaodiem`
FOR EACH ROW
BEGIN
    DECLARE v_room_id INT DEFAULT NULL;
    DECLARE v_dem INT DEFAULT 0;

    IF NEW.tu_ngay IS NULL OR NEW.den_ngay IS NULL OR NEW.den_ngay < NEW.tu_ngay THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Khoang ngay mua cao diem khong hop le';
    END IF;

    IF NEW.he_so_gia IS NULL OR NEW.he_so_gia NOT IN (0.10, 0.20, 0.30, 0.40, 0.50, 0.60) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'He so phu thu phai la 0.1, 0.2, 0.3, 0.4, 0.5 hoac 0.6';
    END IF;

    SELECT id INTO v_room_id
    FROM phong
    WHERE id = NEW.phong_id
    FOR UPDATE;

    IF v_room_id IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Phong ap dung mua cao diem khong ton tai';
    END IF;

    SELECT COUNT(*) INTO v_dem
    FROM muacaodiem
    WHERE phong_id = NEW.phong_id
      AND NEW.tu_ngay <= den_ngay
      AND NEW.den_ngay >= tu_ngay;

    IF v_dem > 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Khoang ngay mua cao diem bi trung lap voi cau hinh da co';
    END IF;
END$$
DELIMITER ;


-- 6. Validate peak-season UPDATE and exclude the current row from overlap checks.
DROP TRIGGER IF EXISTS `trg_muacaodiem_before_update`;
DELIMITER $$
CREATE TRIGGER `trg_muacaodiem_before_update`
BEFORE UPDATE ON `muacaodiem`
FOR EACH ROW
BEGIN
    DECLARE v_room_id INT DEFAULT NULL;
    DECLARE v_dem INT DEFAULT 0;

    IF NEW.tu_ngay IS NULL OR NEW.den_ngay IS NULL OR NEW.den_ngay < NEW.tu_ngay THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Khoang ngay mua cao diem khong hop le';
    END IF;

    IF NEW.he_so_gia IS NULL OR NEW.he_so_gia NOT IN (0.10, 0.20, 0.30, 0.40, 0.50, 0.60) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'He so phu thu phai la 0.1, 0.2, 0.3, 0.4, 0.5 hoac 0.6';
    END IF;

    SELECT id INTO v_room_id
    FROM phong
    WHERE id = NEW.phong_id
    FOR UPDATE;

    IF v_room_id IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Phong ap dung mua cao diem khong ton tai';
    END IF;

    SELECT COUNT(*) INTO v_dem
    FROM muacaodiem
    WHERE phong_id = NEW.phong_id
      AND id <> OLD.id
      AND NEW.tu_ngay <= den_ngay
      AND NEW.den_ngay >= tu_ngay;

    IF v_dem > 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Cap nhat that bai: khoang ngay mua cao diem bi trung lap';
    END IF;
END$$
DELIMITER ;


-- ----------------------------------------------------------------------------
-- GROUP C: SERVICES
-- ----------------------------------------------------------------------------

-- 7. A Booking service must belong to the same room as its Booking.
DROP TRIGGER IF EXISTS `trg_dichvu_before_insert`;
DELIMITER $$
CREATE TRIGGER `trg_dichvu_before_insert`
BEFORE INSERT ON `dichvu`
FOR EACH ROW
BEGIN
    DECLARE v_booking_room_id INT DEFAULT NULL;
    DECLARE v_booking_status VARCHAR(30) DEFAULT NULL;
    DECLARE v_has_booking BOOLEAN DEFAULT TRUE;
    DECLARE v_has_invoice INT DEFAULT 0;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_has_booking = FALSE;

    IF NEW.ten IS NULL OR TRIM(NEW.ten) = '' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Ten dich vu khong duoc de trong';
    END IF;

    IF NEW.don_gia IS NULL OR NEW.don_gia < 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Don gia dich vu khong duoc am';
    END IF;

    IF NEW.so_luong IS NULL OR NEW.so_luong <= 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'So luong dich vu phai lon hon 0';
    END IF;

    IF NEW.booking_id IS NULL THEN
        IF NEW.phong_id IS NULL THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Dich vu mac dinh phai thuoc mot phong';
        END IF;
    ELSE
        SELECT phong_id, trang_thai
        INTO v_booking_room_id, v_booking_status
        FROM booking
        WHERE id = NEW.booking_id;

        IF NOT v_has_booking THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Booking khong ton tai';
        END IF;

        IF v_booking_status IN ('DA_HUY', 'HOAN_THANH') THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Khong the them dich vu cho Booking da huy/hoan thanh';
        END IF;

        IF NEW.phong_id IS NULL THEN
            SET NEW.phong_id = v_booking_room_id;
        ELSEIF NEW.phong_id <> v_booking_room_id THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Phong cua dich vu khong khop voi phong cua Booking';
        END IF;

        SELECT COUNT(*) INTO v_has_invoice
        FROM pay py
        JOIN hoadon hd ON hd.pay_id = py.id
        WHERE py.booking_id = NEW.booking_id;

        IF v_has_invoice > 0 THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Booking da co hoa don, khong the them dich vu';
        END IF;
    END IF;
END$$
DELIMITER ;


-- 8. Prevent invalid service reassignment, price changes after invoicing and room mismatch.
DROP TRIGGER IF EXISTS `trg_dichvu_before_update`;
DELIMITER $$
CREATE TRIGGER `trg_dichvu_before_update`
BEFORE UPDATE ON `dichvu`
FOR EACH ROW
BEGIN
    DECLARE v_booking_room_id INT DEFAULT NULL;
    DECLARE v_booking_status VARCHAR(30) DEFAULT NULL;
    DECLARE v_has_booking BOOLEAN DEFAULT TRUE;
    DECLARE v_has_invoice INT DEFAULT 0;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_has_booking = FALSE;

    IF NEW.ten IS NULL OR TRIM(NEW.ten) = '' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Ten dich vu khong duoc de trong';
    END IF;

    IF NEW.don_gia IS NULL OR NEW.don_gia < 0
       OR NEW.so_luong IS NULL OR NEW.so_luong <= 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Don gia hoac so luong dich vu khong hop le';
    END IF;

    -- Once used by a Booking, the service cannot be detached or reassigned.
    IF OLD.booking_id IS NOT NULL AND NOT (NEW.booking_id <=> OLD.booking_id) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Khong duoc tach hoac chuyen dich vu da gan Booking';
    END IF;

    IF NEW.booking_id IS NULL THEN
        IF NEW.phong_id IS NULL THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Dich vu mac dinh phai thuoc mot phong';
        END IF;
    ELSE
        SELECT phong_id, trang_thai
        INTO v_booking_room_id, v_booking_status
        FROM booking
        WHERE id = NEW.booking_id;

        IF NOT v_has_booking THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Booking khong ton tai';
        END IF;

        IF v_booking_status IN ('DA_HUY', 'HOAN_THANH') THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Khong duoc sua dich vu cua Booking da huy/hoan thanh';
        END IF;

        IF NEW.phong_id IS NULL OR NEW.phong_id <> v_booking_room_id THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Phong cua dich vu phai khop voi phong cua Booking';
        END IF;

        SELECT COUNT(*) INTO v_has_invoice
        FROM pay py
        JOIN hoadon hd ON hd.pay_id = py.id
        WHERE py.booking_id = NEW.booking_id;

        IF v_has_invoice > 0 THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Booking da co hoa don, khong duoc sua dich vu';
        END IF;
    END IF;
END$$
DELIMITER ;


-- 9. Preserve service history after cancellation, completion or invoice issuance.
DROP TRIGGER IF EXISTS `trg_dichvu_before_delete`;
DELIMITER $$
CREATE TRIGGER `trg_dichvu_before_delete`
BEFORE DELETE ON `dichvu`
FOR EACH ROW
BEGIN
    DECLARE v_booking_status VARCHAR(30) DEFAULT NULL;
    DECLARE v_has_booking BOOLEAN DEFAULT TRUE;
    DECLARE v_has_invoice INT DEFAULT 0;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_has_booking = FALSE;

    IF OLD.booking_id IS NOT NULL THEN
        SELECT trang_thai INTO v_booking_status
        FROM booking
        WHERE id = OLD.booking_id;

        IF NOT v_has_booking THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Booking cua dich vu khong ton tai';
        END IF;

        IF v_booking_status IN ('DA_HUY', 'HOAN_THANH') THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Khong duoc xoa dich vu cua Booking da huy/hoan thanh';
        END IF;

        SELECT COUNT(*) INTO v_has_invoice
        FROM pay py
        JOIN hoadon hd ON hd.pay_id = py.id
        WHERE py.booking_id = OLD.booking_id;

        IF v_has_invoice > 0 THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Booking da co hoa don, khong duoc xoa dich vu';
        END IF;
    END IF;
END$$
DELIMITER ;


-- ----------------------------------------------------------------------------
-- GROUP D: PAYMENTS AND INVOICES
-- ----------------------------------------------------------------------------

-- 10. New payment attempts must start pending and belong to the Booking's customer.
DROP TRIGGER IF EXISTS `trg_pay_before_insert`;
DELIMITER $$
CREATE TRIGGER `trg_pay_before_insert`
BEFORE INSERT ON `pay`
FOR EACH ROW
BEGIN
    DECLARE v_booking_customer_id INT DEFAULT NULL;
    DECLARE v_booking_status VARCHAR(30) DEFAULT NULL;
    DECLARE v_booking_room_total DECIMAL(12,2) DEFAULT 0.00;
    DECLARE v_booking_peak_fee DECIMAL(12,2) DEFAULT 0.00;
    DECLARE v_booking_peak_flag TINYINT(1) DEFAULT 0;
    DECLARE v_booking_peak_detail JSON DEFAULT NULL;
    DECLARE v_service_total DECIMAL(12,2) DEFAULT 0.00;
    DECLARE v_has_booking BOOLEAN DEFAULT TRUE;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_has_booking = FALSE;

    IF NEW.so_tien IS NULL OR NEW.so_tien < 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'So tien thanh toan khong duoc am';
    END IF;
    IF NEW.status <> 'CHO_THANH_TOAN' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Giao dich moi phai bat dau o trang thai CHO_THANH_TOAN';
    END IF;

    SELECT khach_id, trang_thai, tien_phong_du_kien,
           tien_phu_phi_mua_cao_diem, ap_dung_mua_cao_diem, chi_tiet_mua_cao_diem
    INTO v_booking_customer_id, v_booking_status, v_booking_room_total,
         v_booking_peak_fee, v_booking_peak_flag, v_booking_peak_detail
    FROM booking WHERE id = NEW.booking_id;
    IF NOT v_has_booking THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Booking khong ton tai';
    END IF;
    IF v_booking_status = 'DA_HUY' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Khong the tao giao dich cho Booking da huy';
    END IF;
    IF NEW.khach_id <> v_booking_customer_id THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Khach thanh toan khong khop voi khach dat Booking';
    END IF;

    SELECT COALESCE(SUM(don_gia * so_luong), 0)
    INTO v_service_total FROM dichvu WHERE booking_id = NEW.booking_id;
    IF NEW.so_tien <> (v_booking_room_total + v_booking_peak_fee + v_service_total) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'So tien Pay phai bang tien phong + phu phi cao diem + dich vu Booking';
    END IF;

    SET NEW.tien_phong_ap_dung = v_booking_room_total;
    SET NEW.tien_phu_phi_mua_cao_diem = v_booking_peak_fee;
    SET NEW.ap_dung_mua_cao_diem = v_booking_peak_flag;
    SET NEW.chi_tiet_mua_cao_diem = v_booking_peak_detail;
END$$
DELIMITER ;


DROP TRIGGER IF EXISTS `trg_pay_before_update`;
DELIMITER $$
CREATE TRIGGER `trg_pay_before_update`
BEFORE UPDATE ON `pay`
FOR EACH ROW
BEGIN
    DECLARE v_booking_customer_id INT DEFAULT NULL;
    DECLARE v_booking_status VARCHAR(30) DEFAULT NULL;
    DECLARE v_invoice_count INT DEFAULT 0;
    DECLARE v_invoice_total DECIMAL(12,2) DEFAULT NULL;
    DECLARE v_has_booking BOOLEAN DEFAULT TRUE;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_has_booking = FALSE;

    IF NEW.booking_id <> OLD.booking_id
       OR NEW.khach_id <> OLD.khach_id
       OR NEW.ngay_thanh_toan <> OLD.ngay_thanh_toan
       OR NEW.so_tien <> OLD.so_tien
       OR NEW.method <> OLD.method
       OR NEW.tien_phong_ap_dung <> OLD.tien_phong_ap_dung
       OR NEW.tien_phu_phi_mua_cao_diem <> OLD.tien_phu_phi_mua_cao_diem
       OR NEW.ap_dung_mua_cao_diem <> OLD.ap_dung_mua_cao_diem
       OR NOT (NEW.chi_tiet_mua_cao_diem <=> OLD.chi_tiet_mua_cao_diem) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Thong tin co dinh cua giao dich khong duoc thay doi';
    END IF;

    SELECT khach_id, trang_thai
    INTO v_booking_customer_id, v_booking_status
    FROM booking
    WHERE id = NEW.booking_id;

    IF NOT v_has_booking THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Booking cua giao dich khong ton tai';
    END IF;

    IF NEW.khach_id <> v_booking_customer_id THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Khach hang cua Pay khong khop voi Booking';
    END IF;

    IF NEW.status <> OLD.status THEN
        IF OLD.status = 'CHO_THANH_TOAN'
           AND NEW.status NOT IN ('THANH_CONG', 'THAT_BAI') THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Chuyen trang thai thanh toan khong hop le';
        ELSEIF OLD.status = 'THAT_BAI'
           AND NEW.status <> 'CHO_THANH_TOAN' THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Giao dich that bai chi duoc thu lai bang trang thai CHO_THANH_TOAN';
        ELSEIF OLD.status = 'THANH_CONG'
           AND NEW.status <> 'HOAN_TIEN' THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Giao dich thanh cong chi duoc chuyen sang HOAN_TIEN';
        ELSEIF OLD.status = 'HOAN_TIEN' THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Giao dich da hoan tien la trang thai cuoi';
        END IF;
    END IF;

    IF NEW.status = 'THANH_CONG' AND OLD.status <> 'THANH_CONG' THEN
        IF v_booking_status = 'DA_HUY' THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Khong the thanh toan Booking da huy';
        END IF;

        SELECT COUNT(*), MAX(tong_tien)
        INTO v_invoice_count, v_invoice_total
        FROM hoadon
        WHERE pay_id = NEW.id;

        IF v_invoice_count = 0 THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Can co hoa don truoc khi xac nhan thanh toan';
        END IF;

        IF NEW.so_tien <> v_invoice_total THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'So tien Pay khong khop tong tien hoa don';
        END IF;
    END IF;

    IF NEW.status = 'HOAN_TIEN' AND OLD.status <> 'THANH_CONG' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Chi duoc hoan tien cho giao dich da thanh cong';
    END IF;
END$$
DELIMITER ;


-- 12. A successful payment automatically confirms a Booking waiting for confirmation.
DROP TRIGGER IF EXISTS `trg_pay_after_update`;
DELIMITER $$
CREATE TRIGGER `trg_pay_after_update`
AFTER UPDATE ON `pay`
FOR EACH ROW
BEGIN
    IF NEW.status = 'THANH_CONG' AND OLD.status <> 'THANH_CONG' THEN
        UPDATE booking
        SET trang_thai = 'DA_XAC_NHAN'
        WHERE id = NEW.booking_id
          AND trang_thai = 'CHO_XAC_NHAN';
    END IF;
END$$
DELIMITER ;


-- 13. Validate invoice values against immutable Booking/Pay price snapshots and Booking services.
DROP TRIGGER IF EXISTS `trg_hoadon_before_insert`;
DELIMITER $$
CREATE TRIGGER `trg_hoadon_before_insert`
BEFORE INSERT ON `hoadon`
FOR EACH ROW
BEGIN
    DECLARE v_pay_amount DECIMAL(12,2) DEFAULT NULL;
    DECLARE v_pay_status VARCHAR(30) DEFAULT NULL;
    DECLARE v_booking_id INT DEFAULT NULL;
    DECLARE v_booking_status VARCHAR(30) DEFAULT NULL;
    DECLARE v_room_id INT DEFAULT NULL;
    DECLARE v_ngay_nhan DATE DEFAULT NULL;
    DECLARE v_ngay_tra DATE DEFAULT NULL;
    DECLARE v_ngay_hien_tai DATE DEFAULT NULL;
    DECLARE v_gia_co_ban DECIMAL(12,2) DEFAULT 0;
    DECLARE v_he_so DECIMAL(6,2) DEFAULT 1;
    DECLARE v_calc_tien_phong DECIMAL(12,2) DEFAULT 0;
    DECLARE v_calc_phu_phi DECIMAL(12,2) DEFAULT 0;
    DECLARE v_calc_tien_dv DECIMAL(12,2) DEFAULT 0;
    DECLARE v_has_pay BOOLEAN DEFAULT TRUE;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_has_pay = FALSE;

    IF NEW.tien_phong IS NULL OR NEW.tien_phu_phi_mua_cao_diem IS NULL
       OR NEW.tien_dich_vu IS NULL OR NEW.tong_tien IS NULL
       OR NEW.tien_phong < 0 OR NEW.tien_phu_phi_mua_cao_diem < 0 OR NEW.tien_dich_vu < 0
       OR NEW.tong_tien <> (NEW.tien_phong + NEW.tien_phu_phi_mua_cao_diem + NEW.tien_dich_vu) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Thanh phan tien hoa don khong hop le';
    END IF;

    SELECT py.so_tien, py.status, py.booking_id,
           b.trang_thai, b.phong_id, b.ngay_nhan, b.ngay_tra,
           lp.gia_co_ban
    INTO v_pay_amount, v_pay_status, v_booking_id,
         v_booking_status, v_room_id, v_ngay_nhan, v_ngay_tra,
         v_gia_co_ban
    FROM pay py
    JOIN booking b ON b.id = py.booking_id
    JOIN phong p ON p.id = b.phong_id
    JOIN loaiphong lp ON lp.id = p.loai_phong_id
    WHERE py.id = NEW.pay_id;

    IF NOT v_has_pay THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Giao dich Pay khong ton tai';
    END IF;

    IF v_pay_status <> 'CHO_THANH_TOAN' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Chi lap hoa don cho giao dich dang CHO_THANH_TOAN';
    END IF;

    IF v_booking_status = 'DA_HUY' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Khong the lap hoa don cho Booking da huy';
    END IF;

    SELECT py.tien_phong_ap_dung, py.tien_phu_phi_mua_cao_diem
    INTO v_calc_tien_phong, v_calc_phu_phi
    FROM pay py WHERE py.id = NEW.pay_id;

    SELECT COALESCE(SUM(d.don_gia * d.so_luong), 0)
    INTO v_calc_tien_dv
    FROM dichvu d
    WHERE d.booking_id = v_booking_id;

    IF NEW.tien_phong <> v_calc_tien_phong THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Tien phong hoa don khong khop snapshot gia Booking/Pay';
    END IF;

    IF NEW.tien_phu_phi_mua_cao_diem <> v_calc_phu_phi THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Phu phi mua cao diem hoa don khong khop snapshot Booking/Pay';
    END IF;

    IF NEW.tien_dich_vu <> v_calc_tien_dv THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Tien dich vu hoa don khong khop dich vu cua Booking';
    END IF;

    IF NEW.tong_tien <> v_pay_amount THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Tong tien hoa don khong khop so tien Pay';
    END IF;
END$$
DELIMITER ;


-- 14. A pending invoice can be corrected only while it still matches its source data.
DROP TRIGGER IF EXISTS `trg_hoadon_before_update`;
DELIMITER $$
CREATE TRIGGER `trg_hoadon_before_update`
BEFORE UPDATE ON `hoadon`
FOR EACH ROW
BEGIN
    DECLARE v_pay_amount DECIMAL(12,2) DEFAULT NULL;
    DECLARE v_pay_status VARCHAR(30) DEFAULT NULL;
    DECLARE v_booking_id INT DEFAULT NULL;
    DECLARE v_room_id INT DEFAULT NULL;
    DECLARE v_ngay_nhan DATE DEFAULT NULL;
    DECLARE v_ngay_tra DATE DEFAULT NULL;
    DECLARE v_ngay_hien_tai DATE DEFAULT NULL;
    DECLARE v_gia_co_ban DECIMAL(12,2) DEFAULT 0;
    DECLARE v_he_so DECIMAL(6,2) DEFAULT 1;
    DECLARE v_calc_tien_phong DECIMAL(12,2) DEFAULT 0;
    DECLARE v_calc_phu_phi DECIMAL(12,2) DEFAULT 0;
    DECLARE v_calc_tien_dv DECIMAL(12,2) DEFAULT 0;
    DECLARE v_has_pay BOOLEAN DEFAULT TRUE;

    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_has_pay = FALSE;

    IF NEW.pay_id <> OLD.pay_id THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Khong duoc thay doi pay_id cua hoa don';
    END IF;

    IF NEW.tien_phong IS NULL OR NEW.tien_phu_phi_mua_cao_diem IS NULL
       OR NEW.tien_dich_vu IS NULL OR NEW.tong_tien IS NULL
       OR NEW.tien_phong < 0 OR NEW.tien_phu_phi_mua_cao_diem < 0 OR NEW.tien_dich_vu < 0
       OR NEW.tong_tien <> (NEW.tien_phong + NEW.tien_phu_phi_mua_cao_diem + NEW.tien_dich_vu) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Tong tien hoa don khong hop le';
    END IF;

    SELECT py.so_tien, py.status, py.booking_id,
           b.phong_id, b.ngay_nhan, b.ngay_tra, lp.gia_co_ban
    INTO v_pay_amount, v_pay_status, v_booking_id,
         v_room_id, v_ngay_nhan, v_ngay_tra, v_gia_co_ban
    FROM pay py
    JOIN booking b ON b.id = py.booking_id
    JOIN phong p ON p.id = b.phong_id
    JOIN loaiphong lp ON lp.id = p.loai_phong_id
    WHERE py.id = OLD.pay_id;

    IF NOT v_has_pay THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Giao dich Pay cua hoa don khong ton tai';
    END IF;

    IF v_pay_status <> 'CHO_THANH_TOAN' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Chi duoc sua hoa don khi Pay dang CHO_THANH_TOAN';
    END IF;

    SELECT py.tien_phong_ap_dung, py.tien_phu_phi_mua_cao_diem
    INTO v_calc_tien_phong, v_calc_phu_phi
    FROM pay py WHERE py.id = NEW.pay_id;

    SELECT COALESCE(SUM(d.don_gia * d.so_luong), 0)
    INTO v_calc_tien_dv
    FROM dichvu d
    WHERE d.booking_id = v_booking_id;

    IF NEW.tien_phong <> v_calc_tien_phong
       OR NEW.tien_phu_phi_mua_cao_diem <> v_calc_phu_phi
       OR NEW.tien_dich_vu <> v_calc_tien_dv
       OR NEW.tong_tien <> v_pay_amount THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Hoa don khong khop voi tien phong, dich vu hoac Pay';
    END IF;
END$$
DELIMITER ;


-- 15. Prevent deletion of invoices for successful or refunded payments.
DROP TRIGGER IF EXISTS `trg_hoadon_before_delete`;
DELIMITER $$
CREATE TRIGGER `trg_hoadon_before_delete`
BEFORE DELETE ON `hoadon`
FOR EACH ROW
BEGIN
    DECLARE v_pay_status VARCHAR(30) DEFAULT NULL;
    DECLARE v_has_pay BOOLEAN DEFAULT TRUE;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_has_pay = FALSE;

    SELECT status INTO v_pay_status
    FROM pay
    WHERE id = OLD.pay_id;

    IF NOT v_has_pay THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Khong tim thay giao dich cua hoa don';
    END IF;

    IF v_pay_status IN ('THANH_CONG', 'HOAN_TIEN') THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Khong duoc xoa hoa don da thanh toan hoac hoan tien';
    END IF;
END$$
DELIMITER ;


-- ============================================================================
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
       b.tien_phong_du_kien,
       b.tien_phu_phi_mua_cao_diem,
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
       hd.tien_phu_phi_mua_cao_diem,
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
       ROUND(lp.gia_co_ban * m.he_so_gia, 2) AS phu_phi_mua_cao_diem_moi_dem
FROM muacaodiem m
JOIN phong p ON p.id = m.phong_id
JOIN loaiphong lp ON lp.id = p.loai_phong_id;


-- ============================================================================
-- 6. POST-CREATION CHECKS AND EXAMPLE CALLS
-- ============================================================================
-- Object inventory:
-- SHOW TABLES;
-- SHOW FULL TABLES WHERE Table_type = 'VIEW';
-- SHOW PROCEDURE STATUS WHERE Db = 'hotel_management_erd';
-- SHOW TRIGGERS FROM hotel_management_erd;
--
-- Example view queries:
-- SELECT * FROM v_thong_tin_phong;
-- SELECT * FROM v_chi_tiet_booking;
-- SELECT * FROM v_phong_dang_su_dung;
-- SELECT * FROM v_phong_bao_tri;
-- SELECT * FROM v_dich_vu_booking;
-- SELECT * FROM v_chi_tiet_hoa_don;
-- SELECT * FROM v_doanh_thu_theo_thang;
-- SELECT * FROM v_thong_ke_trang_thai_booking;
-- SELECT * FROM v_thong_tin_khach_hang;
-- SELECT * FROM v_thong_ke_mua_cao_diem;
--
-- Example procedure calls (use valid IDs and dates for your test database):
-- CALL sp_kiem_tra_phong_trong('2026-12-20', '2026-12-23');
-- CALL sp_tao_booking(3, 2, '2027-01-10', '2027-01-12');
-- CALL sp_xac_nhan_booking(<booking_id>);
-- CALL sp_nhan_phong(<booking_id>);
-- CALL sp_them_dichvu_booking(<booking_id>, 'An sang', 50000, 2);
-- CALL sp_tinh_tien_va_tao_hoa_don(<booking_id>, 'CHUYEN_KHOAN');
-- UPDATE pay SET status = 'THANH_CONG' WHERE id = <pay_id>;
-- CALL sp_tra_phong(<booking_id>);
-- CALL sp_huy_booking(<booking_id>);
-- CALL sp_lich_su_booking(<khach_id>);
-- CALL sp_thong_ke_doanh_thu('2026-11-01', '2026-11-30');
-- CALL sp_them_khach_hang('Khach Moi', '079299999999', '0909999999');
-- CALL sp_cap_nhat_thong_tin_phong(1, '101', 1, 'SAN_SANG');
-- CALL sp_xem_chi_tiet_booking(<booking_id>);
-- CALL sp_thong_ke_phong();
-- CALL sp_cap_nhat_dich_vu(<dichvu_id>, 'Giat ui', 80000, 2);
--
-- IMPORTANT:
-- 1) This script drops and recreates hotel_management_erd. Back up existing data first.
-- 2) Run the complete script in MySQL Workbench with support for DELIMITER commands.
-- 3) CHECK constraints are enforced in MySQL 8.0.16 and later.
