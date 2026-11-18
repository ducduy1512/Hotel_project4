-- ================================================================
-- CUSTOMER SERVICE SELECTION MIGRATION
-- MySQL 8.0.16+
-- Run this in the SAME database configured by DB_NAME in the API .env.
-- Does not DROP/CREATE the database or modify existing customer data.
-- ================================================================

-- 4.2B Customer booking with explicit service selection.
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


