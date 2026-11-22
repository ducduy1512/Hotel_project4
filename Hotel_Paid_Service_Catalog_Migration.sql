-- ============================================================================
-- HOTEL MANAGEMENT - PAID OPTIONAL SERVICE CATALOG MIGRATION
-- Target: MySQL 8.0+ / database hotel_management_erd
-- Run ONCE on an existing database after taking a backup.
-- Does not add a ninth table; extends the existing `dichvu` table.
-- ============================================================================

USE hotel_management_erd;
SET NAMES utf8mb4;

-- 1. Add service classification, group, unit and active status.
ALTER TABLE dichvu
    ADD COLUMN loai_dichvu ENUM('MAC_DINH','TUY_CHON') NOT NULL DEFAULT 'MAC_DINH' AFTER so_luong,
    ADD COLUMN nhom_dich_vu VARCHAR(50) NOT NULL DEFAULT 'KHAC' AFTER loai_dichvu,
    ADD COLUMN don_vi_tinh VARCHAR(40) NOT NULL DEFAULT 'lần' AFTER nhom_dich_vu,
    ADD COLUMN dang_hoat_dong TINYINT(1) NOT NULL DEFAULT 1 AFTER don_vi_tinh;

-- Remove old validators temporarily: the old UPDATE trigger blocks edits to
-- already-invoiced Booking rows, and the old INSERT trigger forbids global rows.
DROP TRIGGER IF EXISTS trg_dichvu_before_insert;
DROP TRIGGER IF EXISTS trg_dichvu_before_update;

-- 2. Backfill existing records without changing historical price/quantity.
UPDATE dichvu
SET loai_dichvu = CASE WHEN don_gia > 0 THEN 'TUY_CHON' ELSE 'MAC_DINH' END,
    nhom_dich_vu = CASE
        WHEN LOWER(ten) LIKE '%an sang%' OR LOWER(ten) LIKE '%buffet%' THEN 'AN_SANG'
        WHEN LOWER(ten) LIKE '%giuong%' THEN 'GIUONG_PHU'
        WHEN LOWER(ten) LIKE '%giat ui%' THEN 'GIAT_UI'
        WHEN LOWER(ten) LIKE '%minibar%' OR LOWER(ten) LIKE '%nuoc ngot%' THEN 'MINIBAR'
        WHEN LOWER(ten) LIKE '%xe%' OR LOWER(ten) LIKE '%dua don%' OR LOWER(ten) LIKE '%thue xe%' THEN 'DUA_DON'
        WHEN LOWER(ten) LIKE '%trang tri%' OR LOWER(ten) LIKE '%sinh nhat%' OR LOWER(ten) LIKE '%honeymoon%' THEN 'TRANG_TRI'
        WHEN LOWER(ten) LIKE '%nuoc suoi%' OR LOWER(ten) LIKE '%tra va ca phe%' THEN 'DO_DUNG'
        ELSE 'KHAC'
    END,
    don_vi_tinh = CASE
        WHEN LOWER(ten) LIKE '%an sang%' OR LOWER(ten) LIKE '%buffet%' THEN 'suất'
        WHEN LOWER(ten) LIKE '%giat ui%' THEN 'món'
        WHEN LOWER(ten) LIKE '%minibar%' THEN 'lần'
        WHEN LOWER(ten) LIKE '%xe%' OR LOWER(ten) LIKE '%dua don%' OR LOWER(ten) LIKE '%thue xe%' THEN 'chuyến'
        WHEN LOWER(ten) LIKE '%nuoc suoi%' THEN 'chai'
        WHEN LOWER(ten) LIKE '%tra va ca phe%' THEN 'phần'
        ELSE 'lần'
    END;

-- 3. Register the new paid optional catalog entries (idempotent by name).
INSERT INTO dichvu
    (ten, don_gia, so_luong, phong_id, booking_id, loai_dichvu, nhom_dich_vu, don_vi_tinh, dang_hoat_dong)
SELECT seed.ten, seed.don_gia, 1, NULL, NULL, 'TUY_CHON', seed.nhom_dich_vu, seed.don_vi_tinh, 1
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
) AS seed
WHERE NOT EXISTS (
    SELECT 1 FROM dichvu existing
    WHERE existing.ten = seed.ten
      AND existing.phong_id IS NULL
      AND existing.booking_id IS NULL
);

-- 4. Booking creation only copies free room-default rows, never the global catalog.
DROP TRIGGER IF EXISTS trg_booking_after_insert;
DELIMITER $$
CREATE TRIGGER trg_booking_after_insert
AFTER INSERT ON booking
FOR EACH ROW
BEGIN
    IF NEW.trang_thai <> 'DA_HUY' THEN
        INSERT INTO dichvu
            (ten, don_gia, so_luong, phong_id, booking_id, loai_dichvu,
             nhom_dich_vu, don_vi_tinh, dang_hoat_dong)
        SELECT d.ten, d.don_gia, d.so_luong, NEW.phong_id, NEW.id,
               'MAC_DINH', d.nhom_dich_vu, d.don_vi_tinh, 1
        FROM dichvu d
        WHERE d.phong_id = NEW.phong_id
          AND d.booking_id IS NULL
          AND d.loai_dichvu = 'MAC_DINH'
          AND d.dang_hoat_dong = 1
          AND d.don_gia = 0;
    END IF;

    IF NEW.trang_thai = 'DANG_O' THEN
        UPDATE phong SET trang_thai = 'DANG_SU_DUNG' WHERE id = NEW.phong_id;
    END IF;
END$$
DELIMITER ;

-- 5. Validate the three legal service-row shapes.
DROP TRIGGER IF EXISTS trg_dichvu_before_insert;
DELIMITER $$
CREATE TRIGGER trg_dichvu_before_insert
BEFORE INSERT ON dichvu
FOR EACH ROW
BEGIN
    DECLARE v_booking_room_id INT DEFAULT NULL;
    DECLARE v_booking_status VARCHAR(30) DEFAULT NULL;
    DECLARE v_has_booking BOOLEAN DEFAULT TRUE;
    DECLARE v_has_invoice INT DEFAULT 0;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_has_booking = FALSE;

    IF NEW.ten IS NULL OR TRIM(NEW.ten) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Ten dich vu khong duoc de trong';
    END IF;
    IF NEW.don_gia IS NULL OR NEW.don_gia < 0 OR NEW.so_luong IS NULL OR NEW.so_luong <= 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Don gia hoac so luong dich vu khong hop le';
    END IF;
    IF NEW.loai_dichvu NOT IN ('MAC_DINH','TUY_CHON')
       OR NEW.nhom_dich_vu IS NULL OR TRIM(NEW.nhom_dich_vu) = ''
       OR NEW.don_vi_tinh IS NULL OR TRIM(NEW.don_vi_tinh) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Thong tin phan loai dich vu khong hop le';
    END IF;

    IF NEW.booking_id IS NULL AND NEW.phong_id IS NULL THEN
        -- Global catalog entry: paid optional service only.
        IF NEW.loai_dichvu <> 'TUY_CHON' OR NEW.don_gia <= 0 THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Danh muc chung phai la dich vu TUY_CHON co gia lon hon 0';
        END IF;
    ELSEIF NEW.booking_id IS NULL THEN
        -- Room default: free service assigned to exactly one room.
        IF NEW.loai_dichvu <> 'MAC_DINH' OR NEW.don_gia <> 0 THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Dich vu mac dinh cua phong phai co loai MAC_DINH va gia 0';
        END IF;
    ELSE
        SELECT phong_id, trang_thai INTO v_booking_room_id, v_booking_status
        FROM booking WHERE id = NEW.booking_id;
        IF NOT v_has_booking THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Booking khong ton tai';
        END IF;
        IF v_booking_status IN ('DA_HUY','HOAN_THANH') THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Khong the them dich vu cho Booking da huy/hoan thanh';
        END IF;
        IF NEW.loai_dichvu = 'TUY_CHON' AND NEW.don_gia <= 0 THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Dich vu TUY_CHON trong Booking phai co gia lon hon 0';
        END IF;
        IF NEW.loai_dichvu = 'MAC_DINH' AND NEW.don_gia <> 0 THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Dich vu MAC_DINH trong Booking phai co gia 0';
        END IF;
        IF NEW.phong_id IS NULL THEN
            SET NEW.phong_id = v_booking_room_id;
        ELSEIF NEW.phong_id <> v_booking_room_id THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Phong cua dich vu khong khop voi phong cua Booking';
        END IF;
        SELECT COUNT(*) INTO v_has_invoice
        FROM pay py JOIN hoadon hd ON hd.pay_id = py.id
        WHERE py.booking_id = NEW.booking_id;
        IF v_has_invoice > 0 THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Booking da co hoa don, khong the them dich vu';
        END IF;
    END IF;
END$$
DELIMITER ;

DROP TRIGGER IF EXISTS trg_dichvu_before_update;
DELIMITER $$
CREATE TRIGGER trg_dichvu_before_update
BEFORE UPDATE ON dichvu
FOR EACH ROW
BEGIN
    DECLARE v_booking_room_id INT DEFAULT NULL;
    DECLARE v_booking_status VARCHAR(30) DEFAULT NULL;
    DECLARE v_has_booking BOOLEAN DEFAULT TRUE;
    DECLARE v_has_invoice INT DEFAULT 0;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_has_booking = FALSE;

    IF NEW.ten IS NULL OR TRIM(NEW.ten) = ''
       OR NEW.don_gia IS NULL OR NEW.don_gia < 0
       OR NEW.so_luong IS NULL OR NEW.so_luong <= 0
       OR NEW.nhom_dich_vu IS NULL OR TRIM(NEW.nhom_dich_vu) = ''
       OR NEW.don_vi_tinh IS NULL OR TRIM(NEW.don_vi_tinh) = '' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Thong tin dich vu khong hop le';
    END IF;
    IF OLD.booking_id IS NOT NULL AND NOT (NEW.booking_id <=> OLD.booking_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Khong duoc tach hoac chuyen dich vu da gan Booking';
    END IF;

    IF NEW.booking_id IS NULL AND NEW.phong_id IS NULL THEN
        IF NEW.loai_dichvu <> 'TUY_CHON' OR NEW.don_gia <= 0 THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Danh muc chung phai la dich vu TUY_CHON co gia lon hon 0';
        END IF;
    ELSEIF NEW.booking_id IS NULL THEN
        IF NEW.loai_dichvu <> 'MAC_DINH' OR NEW.don_gia <> 0 THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Dich vu mac dinh cua phong phai co loai MAC_DINH va gia 0';
        END IF;
    ELSE
        SELECT phong_id, trang_thai INTO v_booking_room_id, v_booking_status
        FROM booking WHERE id = NEW.booking_id;
        IF NOT v_has_booking THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Booking khong ton tai';
        END IF;
        IF v_booking_status IN ('DA_HUY','HOAN_THANH') THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Khong duoc sua dich vu cua Booking da huy/hoan thanh';
        END IF;
        IF (NEW.loai_dichvu = 'TUY_CHON' AND NEW.don_gia <= 0)
           OR (NEW.loai_dichvu = 'MAC_DINH' AND NEW.don_gia <> 0) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Gia dich vu khong khop loai dich vu';
        END IF;
        IF NEW.phong_id IS NULL OR NEW.phong_id <> v_booking_room_id THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Phong cua dich vu phai khop voi phong cua Booking';
        END IF;
        SELECT COUNT(*) INTO v_has_invoice
        FROM pay py JOIN hoadon hd ON hd.pay_id = py.id
        WHERE py.booking_id = NEW.booking_id;
        IF v_has_invoice > 0 THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Booking da co hoa don, khong duoc sua dich vu';
        END IF;
    END IF;
END$$
DELIMITER ;

-- 6. Customer can choose room-default services plus any active global paid add-ons.
-- Quantity submitted for unit 'giường/đêm' is beds per night; this procedure
-- stores beds x nights as the immutable Booking quantity.
DROP PROCEDURE IF EXISTS sp_tao_booking_customer;
DELIMITER $$
CREATE PROCEDURE sp_tao_booking_customer(
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
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Ngay nhan va ngay tra khong hop le';
    END IF;
    IF p_dich_vu IS NULL OR JSON_TYPE(p_dich_vu) <> 'ARRAY' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Danh sach dich vu phai la JSON ARRAY';
    END IF;
    SELECT id INTO v_dem FROM khach WHERE id = p_khach_id FOR SHARE;
    IF v_dem IS NULL OR v_dem = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Khach hang khong ton tai';
    END IF;
    SET v_not_found = FALSE;
    SELECT trang_thai INTO v_trang_thai_phong FROM phong WHERE id = p_phong_id FOR UPDATE;
    IF v_not_found OR v_trang_thai_phong IS NULL OR v_trang_thai_phong = 'BAO_TRI' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Phong khong ton tai hoac dang bao tri';
    END IF;
    SELECT COUNT(*) INTO v_dem FROM booking
    WHERE phong_id = p_phong_id AND trang_thai <> 'DA_HUY'
      AND p_ngay_nhan < ngay_tra AND p_ngay_tra > ngay_nhan;
    IF v_dem > 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Phong da duoc dat trong khoang thoi gian nay';
    END IF;

    SELECT COUNT(*), COUNT(DISTINCT x.dichvu_id)
    INTO v_selected_count, v_distinct_count
    FROM JSON_TABLE(p_dich_vu, '$[*]' COLUMNS(
        dichvu_id INT PATH '$.dichvu_id' ERROR ON EMPTY ERROR ON ERROR,
        so_luong INT PATH '$.so_luong' ERROR ON EMPTY ERROR ON ERROR
    )) AS x;
    IF v_selected_count <> v_distinct_count THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Khong duoc chon trung dich vu';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM JSON_TABLE(p_dich_vu, '$[*]' COLUMNS(
            dichvu_id INT PATH '$.dichvu_id' ERROR ON EMPTY ERROR ON ERROR,
            so_luong INT PATH '$.so_luong' ERROR ON EMPTY ERROR ON ERROR
        )) AS x
        LEFT JOIN dichvu d ON d.id = x.dichvu_id
          AND d.booking_id IS NULL AND d.dang_hoat_dong = 1
          AND ((d.loai_dichvu = 'MAC_DINH' AND d.phong_id = p_phong_id)
            OR (d.loai_dichvu = 'TUY_CHON' AND d.phong_id IS NULL AND d.don_gia > 0))
        WHERE d.id IS NULL OR x.so_luong <= 0
    ) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Dich vu khong hop le, khong thuoc phong hoac da ngung kinh doanh';
    END IF;

    INSERT INTO booking (phong_id, khach_id, ngay_nhan, ngay_tra, trang_thai)
    VALUES (p_phong_id, p_khach_id, p_ngay_nhan, p_ngay_tra, 'CHO_XAC_NHAN');
    SET v_booking_id = LAST_INSERT_ID();

    -- AFTER INSERT copies default services. Replace them with exactly what the
    -- Customer selected and copy current catalog price/name/unit into Booking.
    DELETE FROM dichvu WHERE booking_id = v_booking_id;
    INSERT INTO dichvu
        (ten, don_gia, so_luong, phong_id, booking_id, loai_dichvu,
         nhom_dich_vu, don_vi_tinh, dang_hoat_dong)
    SELECT d.ten, d.don_gia,
           CASE WHEN d.don_vi_tinh = 'giường/đêm'
                THEN x.so_luong * DATEDIFF(p_ngay_tra, p_ngay_nhan)
                ELSE x.so_luong END,
           p_phong_id, v_booking_id, d.loai_dichvu, d.nhom_dich_vu,
           d.don_vi_tinh, 1
    FROM JSON_TABLE(p_dich_vu, '$[*]' COLUMNS(
        dichvu_id INT PATH '$.dichvu_id' ERROR ON EMPTY ERROR ON ERROR,
        so_luong INT PATH '$.so_luong' ERROR ON EMPTY ERROR ON ERROR
    )) AS x
    JOIN dichvu d ON d.id = x.dichvu_id AND d.booking_id IS NULL
      AND d.dang_hoat_dong = 1
      AND ((d.loai_dichvu = 'MAC_DINH' AND d.phong_id = p_phong_id)
        OR (d.loai_dichvu = 'TUY_CHON' AND d.phong_id IS NULL));

    COMMIT;
    SELECT v_booking_id AS booking_id, p_phong_id AS phong_id,
           p_khach_id AS khach_id, p_ngay_nhan AS ngay_nhan,
           p_ngay_tra AS ngay_tra, 'CHO_XAC_NHAN' AS trang_thai,
           v_selected_count AS so_dich_vu_da_chon;
END$$
DELIMITER ;

-- 7. Keep the legacy Add Service Stored Procedure compatible, now marking the
-- inserted Booking item as a paid optional service.
DROP PROCEDURE IF EXISTS sp_them_dichvu_booking;
DELIMITER $$
CREATE PROCEDURE sp_them_dichvu_booking(
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
    BEGIN ROLLBACK; RESIGNAL; END;
    START TRANSACTION;
    SELECT phong_id, trang_thai INTO v_phong_id, v_status
    FROM booking WHERE id = p_booking_id FOR UPDATE;
    IF v_not_found THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Booking khong ton tai'; END IF;
    IF v_status NOT IN ('CHO_XAC_NHAN','DA_XAC_NHAN','DANG_O') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Khong the them dich vu cho booking da huy hoac hoan thanh';
    END IF;
    INSERT INTO dichvu
        (ten, don_gia, so_luong, phong_id, booking_id, loai_dichvu,
         nhom_dich_vu, don_vi_tinh, dang_hoat_dong)
    VALUES (p_ten, p_don_gia, p_so_luong, v_phong_id, p_booking_id,
            'TUY_CHON', 'KHAC', 'lần', 1);
    COMMIT;
    SELECT LAST_INSERT_ID() AS dichvu_id, p_booking_id AS booking_id,
           p_ten AS ten_dich_vu, p_don_gia AS don_gia,
           p_so_luong AS so_luong, (p_don_gia*p_so_luong) AS thanh_tien;
END$$
DELIMITER ;

-- 8. Extend the Booking service view with category and unit while preserving its name.
CREATE OR REPLACE VIEW v_dich_vu_booking AS
SELECT d.id AS dichvu_id, d.booking_id,
       b.trang_thai AS trang_thai_booking, k.ho_ten, p.so_phong,
       d.ten AS ten_dich_vu, d.don_gia, d.so_luong,
       d.loai_dichvu, d.nhom_dich_vu, d.don_vi_tinh,
       (d.don_gia * d.so_luong) AS thanh_tien
FROM dichvu d
JOIN booking b ON b.id = d.booking_id
JOIN khach k ON k.id = b.khach_id
JOIN phong p ON p.id = b.phong_id;

-- Payment and Invoice sums intentionally remain unchanged:
-- they already include SUM(don_gia * so_luong) for all selected Booking services.
-- Room defaults have a zero price; inactive global catalog rows are not copied.

SELECT loai_dichvu, nhom_dich_vu, ten, don_gia, don_vi_tinh, dang_hoat_dong
FROM dichvu
WHERE phong_id IS NULL AND booking_id IS NULL
ORDER BY nhom_dich_vu, ten;
