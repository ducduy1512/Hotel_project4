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
(7,  7,  7,  '2026-12-21', '2026-12-24', 'DA_XAC_NHAN'), -- Phu phi mua cao diem +0.60
(8,  8,  8,  '2026-12-25', '2026-12-27', 'DA_XAC_NHAN'),
(9,  9,  9,  '2026-12-28', '2026-12-30', 'DA_XAC_NHAN'),
(10, 10, 10, '2026-12-05', '2026-12-07', 'DA_HUY'),
(11, 2,  3,  '2026-12-10', '2026-12-12', 'DA_HUY'),
(12, 1,  1,  '2026-12-20', '2026-12-23', 'DA_XAC_NHAN'), -- Phu phi mua cao diem +0.20
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

-- Classify the legacy sample rows before the service validation triggers are installed.
UPDATE dichvu
SET loai_dichvu = CASE WHEN don_gia > 0 THEN 'TUY_CHON' ELSE 'MAC_DINH' END,
    nhom_dich_vu = CASE
        WHEN LOWER(ten) LIKE '%an sang%' OR LOWER(ten) LIKE '%buffet%' THEN 'AN_SANG'
        WHEN LOWER(ten) LIKE '%giuong%' THEN 'GIUONG_PHU'
        WHEN LOWER(ten) LIKE '%giat ui%' THEN 'GIAT_UI'
        WHEN LOWER(ten) LIKE '%minibar%' THEN 'MINIBAR'
        WHEN LOWER(ten) LIKE '%xe%' OR LOWER(ten) LIKE '%dua don%' OR LOWER(ten) LIKE '%thue xe%' THEN 'DUA_DON'
        WHEN LOWER(ten) LIKE '%nuoc suoi%' OR LOWER(ten) LIKE '%tra va ca phe%' THEN 'DO_DUNG'
        ELSE 'KHAC' END,
    don_vi_tinh = CASE
        WHEN LOWER(ten) LIKE '%an sang%' OR LOWER(ten) LIKE '%buffet%' THEN 'suất'
        WHEN LOWER(ten) LIKE '%giat ui%' THEN 'món'
        WHEN LOWER(ten) LIKE '%minibar%' THEN 'lần'
        WHEN LOWER(ten) LIKE '%xe%' OR LOWER(ten) LIKE '%dua don%' OR LOWER(ten) LIKE '%thue xe%' THEN 'chuyến'
        WHEN LOWER(ten) LIKE '%nuoc suoi%' THEN 'chai'
        WHEN LOWER(ten) LIKE '%tra va ca phe%' THEN 'phần'
        ELSE 'lần' END;

-- Part C: Global paid optional-service catalog (not attached to a room or Booking).
INSERT INTO `dichvu`
    (`ten`, `don_gia`, `so_luong`, `loai_dichvu`, `nhom_dich_vu`, `don_vi_tinh`, `dang_hoat_dong`, `phong_id`, `booking_id`)
SELECT seed.ten, seed.don_gia, 1, 'TUY_CHON', seed.nhom_dich_vu, seed.don_vi_tinh, 1, NULL, NULL
FROM (
    SELECT 'Ăn sáng buffet' AS ten, 100000.00 AS don_gia, 'AN_SANG' AS nhom_dich_vu, 'suất/buổi' AS don_vi_tinh
    UNION ALL SELECT 'Giường phụ', 300000.00, 'GIUONG_PHU', 'giường/đêm'
    UNION ALL SELECT 'Giặt ủi quần áo thường', 25000.00, 'GIAT_UI', 'món'
    UNION ALL SELECT 'Giặt ủi áo sơ mi', 30000.00, 'GIAT_UI', 'áo'
    UNION ALL SELECT 'Giặt ủi vest/đầm', 80000.00, 'GIAT_UI', 'bộ'
    UNION ALL SELECT 'Minibar - Nước ngọt', 25000.00, 'MINIBAR', 'lon'
    UNION ALL SELECT 'Minibar - Nước trái cây', 35000.00, 'MINIBAR', 'chai'
    UNION ALL SELECT 'Minibar - Snack', 30000.00, 'MINIBAR', 'gói'
    UNION ALL SELECT 'Minibar - Chocolate', 45000.00, 'MINIBAR', 'thanh'
    UNION ALL SELECT 'Đưa đón sân bay một chiều', 650000.00, 'DUA_DON', 'chuyến'
    UNION ALL SELECT 'Đưa đón sân bay khứ hồi', 1200000.00, 'DUA_DON', 'chuyến'
    UNION ALL SELECT 'Trang trí sinh nhật cơ bản', 500000.00, 'TRANG_TRI', 'gói'
    UNION ALL SELECT 'Trang trí kỷ niệm / Honeymoon', 750000.00, 'TRANG_TRI', 'gói'
) AS seed;


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
(7,  7,  7200000.00, 200000.00, 7400000.00, '2026-11-13 14:55:00'), -- 3 dem Family: room 4.5tr + fee 2.7tr (+0.60) + 200k DV
(8,  8,  3000000.00, 100000.00, 3100000.00, '2026-11-13 15:55:00'),
(9,  9,  1600000.00,  80000.00, 1680000.00, '2026-11-14 16:55:00'),
(10, 12, 1800000.00,      0.00, 1800000.00, '2026-11-15 09:25:00'), -- 3 dem Standard: room 1.5tr + fee 300k (+0.20), no services
(11, 13, 1000000.00, 160000.00, 1160000.00, '2026-11-15 10:10:00'),
(12, 14, 1600000.00, 100000.00, 1700000.00, '2026-11-12 11:55:00'),
(13, 11, 1000000.00,  180000.00, 1180000.00, '2026-11-09 07:55:00'); -- Pay 11: giao dich hoan tien cua Booking 1



-- Luu y: du lieu mau duoc nap truoc khi tao trigger de giu nguyen cac giao dich lich su.
-- ============================================================================
