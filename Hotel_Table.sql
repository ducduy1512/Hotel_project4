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

-- ============================================================================
-- HOTEL MANAGEMENT DATABASE - VERSION 2 (ERD ALIGNED)
-- MySQL 8.0.16+
-- Schema: hotel_management_erd
-- 8 ERD TABLES + users AUTH TABLE | 15 STORED PROCEDURES | 10 VIEWS | 15 TRIGGERS
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
--   8. hoadon     (id, pay_id, tien_phong, tien_dich_vu, tong_tien, ngay_lap)
-- Includes:
--   - Full DDL (Tables, Primary Keys, Unique Keys, Foreign Keys, Check Constraints)
--   - Complete, mathematically consistent sample dataset (all statuses covered)
--   - 15 Stored Procedures, 10 Views, 15 Triggers enforcing ERD relationships and business rules
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
  CONSTRAINT `chk_he_so_gia` CHECK (`he_so_gia` > 0),
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


-- 1.8 Table: hoadon (HoaDon: id, tienPhong, tienDichVu, tongTien)
-- Relationship: Pay (1) -- [Xuat hoa don] -- (1) HoaDon
CREATE TABLE `hoadon` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `pay_id` INT NOT NULL,
  `tien_phong` DECIMAL(12,2) NOT NULL,
  `tien_dich_vu` DECIMAL(12,2) NOT NULL,
  `tong_tien` DECIMAL(12,2) NOT NULL,
  `ngay_lap` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_hoadon_pay_id` (`pay_id`),
  CONSTRAINT `fk_hoadon_pay` FOREIGN KEY (`pay_id`) REFERENCES `pay` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_hoadon_tien` CHECK (
    `tien_phong` >= 0
    AND `tien_dich_vu` >= 0
    AND `tong_tien` >= 0
    AND `tong_tien` = (`tien_phong` + `tien_dich_vu`)
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
