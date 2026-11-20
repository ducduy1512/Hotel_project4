-- ============================================================================
-- HOTEL PROJECT: PEAK-SEASON SURCHARGE MIGRATION (MySQL 8.0.46)
-- ============================================================================
-- Purpose:
--   Change he_so_gia from a multiplier (legacy 1.20/1.60) to a surcharge rate
--   selected from 0.60, 0.50, 0.40, 0.30, 0.20, 0.10.
--   Invoice total = base room + peak-season surcharge + services.
--
-- IMPORTANT:
--   1) BACK UP hotel_management_erd before running this script.
--   2) Run this script ONCE against the existing database created from the
--      previous Hotel SQL version (the schema shown in hotel_management_full).
--   3) This migration preserves pay.so_tien and hoadon.tong_tien. For each old
--      multiplier snapshot, it splits the former room amount into base room
--      and surcharge instead of changing the amount paid/owed.
--   4) Do not run this migration on a fresh database created by the updated
--      Hotel_Complete.sql; that file already contains the new design.
-- ============================================================================

USE `hotel_management_erd`;

-- 1. Add the separate surcharge amount to each accounting level.
ALTER TABLE `booking`
    ADD COLUMN `tien_phu_phi_mua_cao_diem` DECIMAL(12,2) NOT NULL DEFAULT 0.00
    AFTER `tien_phong_du_kien`;

ALTER TABLE `pay`
    ADD COLUMN `tien_phu_phi_mua_cao_diem` DECIMAL(12,2) NOT NULL DEFAULT 0.00
    AFTER `tien_phong_ap_dung`;

ALTER TABLE `hoadon`
    ADD COLUMN `tien_phu_phi_mua_cao_diem` DECIMAL(12,2) NOT NULL DEFAULT 0.00
    AFTER `tien_phong`;

-- 2. Remove old rules that assume the surcharge is folded into room price.
--    The new CHECK is installed before data migration; each invoice update is
--    made atomically with room and fee fields so the three-part sum remains true.
ALTER TABLE `hoadon` DROP CHECK `chk_hoadon_tien`;
ALTER TABLE `hoadon`
    ADD CONSTRAINT `chk_hoadon_tien` CHECK (
        `tien_phong` >= 0
        AND `tien_phu_phi_mua_cao_diem` >= 0
        AND `tien_dich_vu` >= 0
        AND `tong_tien` >= 0
        AND `tong_tien` = (`tien_phong` + `tien_phu_phi_mua_cao_diem` + `tien_dich_vu`)
    );

-- 3. Temporarily remove triggers that protect old snapshots and old rate values.
DROP TRIGGER IF EXISTS `trg_booking_before_insert`;
DROP TRIGGER IF EXISTS `trg_booking_before_update`;
DROP TRIGGER IF EXISTS `trg_muacaodiem_before_insert`;
DROP TRIGGER IF EXISTS `trg_muacaodiem_before_update`;
DROP TRIGGER IF EXISTS `trg_pay_before_insert`;
DROP TRIGGER IF EXISTS `trg_pay_before_update`;
DROP TRIGGER IF EXISTS `trg_hoadon_before_insert`;
DROP TRIGGER IF EXISTS `trg_hoadon_before_update`;

-- 4. Convert legacy multipliers: 1.20 -> +0.20, 1.60 -> +0.60.
ALTER TABLE `muacaodiem` DROP CHECK `chk_he_so_gia`;
UPDATE `muacaodiem`
SET `he_so_gia` = ROUND(`he_so_gia` - 1.00, 2)
WHERE `he_so_gia` > 1.00;
ALTER TABLE `muacaodiem`
    ADD CONSTRAINT `chk_he_so_gia` CHECK (
        `he_so_gia` IN (0.10, 0.20, 0.30, 0.40, 0.50, 0.60)
    );

-- 5. Rebuild immutable snapshots, keeping the historical nightly base price
--    and rate from each old snapshot whenever available.
DROP PROCEDURE IF EXISTS `sp_backfill_peak_surcharge_snapshots`;
DELIMITER $$
CREATE PROCEDURE `sp_backfill_peak_surcharge_snapshots`()
BEGIN
    DECLARE v_done TINYINT DEFAULT 0;
    DECLARE v_booking_id INT;
    DECLARE v_room_id INT;
    DECLARE v_start DATE;
    DECLARE v_end DATE;
    DECLARE v_old_detail JSON;
    DECLARE v_item JSON;
    DECLARE v_new_detail JSON;
    DECLARE v_idx INT DEFAULT 0;
    DECLARE v_len INT DEFAULT 0;
    DECLARE v_room_rate DECIMAL(12,2) DEFAULT 0.00;
    DECLARE v_base DECIMAL(12,2) DEFAULT 0.00;
    DECLARE v_old_factor DECIMAL(4,2) DEFAULT 0.00;
    DECLARE v_rate DECIMAL(4,2) DEFAULT 0.00;
    DECLARE v_season_id INT DEFAULT NULL;
    DECLARE v_fee DECIMAL(12,2) DEFAULT 0.00;
    DECLARE v_room_total DECIMAL(12,2) DEFAULT 0.00;
    DECLARE v_peak_total DECIMAL(12,2) DEFAULT 0.00;
    DECLARE v_has_peak TINYINT DEFAULT 0;
    DECLARE v_day DATE;
    DECLARE v_night_date VARCHAR(10);

    DECLARE booking_cursor CURSOR FOR
        SELECT `id`, `phong_id`, `ngay_nhan`, `ngay_tra`, `chi_tiet_mua_cao_diem`
        FROM `booking` ORDER BY `id`;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_done = 1;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION
    BEGIN
        ROLLBACK;
        RESIGNAL;
    END;

    START TRANSACTION;
    OPEN booking_cursor;
    booking_loop: LOOP
        FETCH booking_cursor INTO v_booking_id, v_room_id, v_start, v_end, v_old_detail;
        IF v_done = 1 THEN LEAVE booking_loop; END IF;

        SELECT lp.`gia_co_ban` INTO v_room_rate
        FROM `phong` p JOIN `loaiphong` lp ON lp.`id` = p.`loai_phong_id`
        WHERE p.`id` = v_room_id;

        SET v_room_total = 0.00;
        SET v_peak_total = 0.00;
        SET v_has_peak = 0;
        SET v_new_detail = JSON_ARRAY();
        SET v_len = IF(JSON_TYPE(v_old_detail) = 'ARRAY', COALESCE(JSON_LENGTH(v_old_detail), 0), 0);

        IF v_len > 0 THEN
            SET v_idx = 0;
            WHILE v_idx < v_len DO
                SET v_item = JSON_EXTRACT(v_old_detail, CONCAT('$[', v_idx, ']'));
                SET v_base = COALESCE(
                    CAST(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(v_item, '$.gia_co_ban')), 'null') AS DECIMAL(12,2)),
                    v_room_rate
                );
                SET v_old_factor = COALESCE(
                    CAST(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(v_item, '$.he_so_gia')), 'null') AS DECIMAL(4,2)),
                    0.00
                );
                SET v_season_id = CAST(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(v_item, '$.mua_cao_diem_id')), 'null') AS UNSIGNED);
                SET v_night_date = COALESCE(
                    JSON_UNQUOTE(JSON_EXTRACT(v_item, '$.ngay')),
                    DATE_FORMAT(DATE_ADD(v_start, INTERVAL v_idx DAY), '%Y-%m-%d')
                );

                IF v_season_id IS NULL THEN
                    SET v_rate = 0.00;
                ELSEIF v_old_factor > 1.00 THEN
                    SET v_rate = ROUND(v_old_factor - 1.00, 2);
                ELSE
                    SET v_rate = v_old_factor;
                END IF;

                IF v_rate NOT IN (0.00, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60) THEN
                    SIGNAL SQLSTATE '45000'
                        SET MESSAGE_TEXT = 'Snapshot cu co he so khong the chuyen doi; kiem tra booking truoc khi tiep tuc';
                END IF;

                SET v_fee = ROUND(v_base * v_rate, 2);
                SET v_room_total = v_room_total + v_base;
                SET v_peak_total = v_peak_total + v_fee;
                IF v_rate > 0 THEN SET v_has_peak = 1; END IF;

                SET v_new_detail = JSON_ARRAY_APPEND(v_new_detail, '$', JSON_OBJECT(
                    'ngay', v_night_date,
                    'mua_cao_diem_id', IF(v_rate > 0, v_season_id, NULL),
                    'he_so_gia', v_rate,
                    'gia_co_ban', v_base,
                    'tien_dem', v_base,
                    'phi_mua_cao_diem', v_fee
                ));
                SET v_idx = v_idx + 1;
            END WHILE;
        ELSE
            -- Older records without a usable snapshot: rebuild from the current
            -- room rate and current rate calendar for the booked date range.
            SET v_day = v_start;
            WHILE v_day < v_end DO
                SET v_season_id = NULL;
                SET v_rate = 0.00;
                SELECT MAX(m.`id`), COALESCE(MAX(m.`he_so_gia`), 0.00)
                INTO v_season_id, v_rate
                FROM `muacaodiem` m
                WHERE m.`phong_id` = v_room_id
                  AND v_day BETWEEN m.`tu_ngay` AND m.`den_ngay`;

                SET v_fee = ROUND(v_room_rate * v_rate, 2);
                SET v_room_total = v_room_total + v_room_rate;
                SET v_peak_total = v_peak_total + v_fee;
                IF v_rate > 0 THEN SET v_has_peak = 1; ELSE SET v_season_id = NULL; END IF;

                SET v_new_detail = JSON_ARRAY_APPEND(v_new_detail, '$', JSON_OBJECT(
                    'ngay', DATE_FORMAT(v_day, '%Y-%m-%d'),
                    'mua_cao_diem_id', v_season_id,
                    'he_so_gia', v_rate,
                    'gia_co_ban', v_room_rate,
                    'tien_dem', v_room_rate,
                    'phi_mua_cao_diem', v_fee
                ));
                SET v_day = DATE_ADD(v_day, INTERVAL 1 DAY);
            END WHILE;
        END IF;

        UPDATE `booking`
        SET `tien_phong_du_kien` = v_room_total,
            `tien_phu_phi_mua_cao_diem` = v_peak_total,
            `ap_dung_mua_cao_diem` = v_has_peak,
            `chi_tiet_mua_cao_diem` = v_new_detail
        WHERE `id` = v_booking_id;
    END LOOP;
    CLOSE booking_cursor;

    -- Copy the immutable Booking breakdown to Pay; never alter so_tien/status.
    UPDATE `pay` py
    JOIN `booking` b ON b.`id` = py.`booking_id`
    SET py.`tien_phong_ap_dung` = b.`tien_phong_du_kien`,
        py.`tien_phu_phi_mua_cao_diem` = b.`tien_phu_phi_mua_cao_diem`,
        py.`ap_dung_mua_cao_diem` = b.`ap_dung_mua_cao_diem`,
        py.`chi_tiet_mua_cao_diem` = b.`chi_tiet_mua_cao_diem`;

    -- Split each old invoice room amount into base room + surcharge. The total
    -- and service amount remain untouched, preserving every historical invoice.
    UPDATE `hoadon` h
    JOIN `pay` py ON py.`id` = h.`pay_id`
    SET h.`tien_phong` = py.`tien_phong_ap_dung`,
        h.`tien_phu_phi_mua_cao_diem` = py.`tien_phu_phi_mua_cao_diem`;

    COMMIT;
END$$
DELIMITER ;
CALL `sp_backfill_peak_surcharge_snapshots`();
DROP PROCEDURE IF EXISTS `sp_backfill_peak_surcharge_snapshots`;


-- 6. Install the revised invoice calculation procedure.
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

-- 7. Install triggers using the additive surcharge model.
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

-- 8. Refresh accounting/detail views to expose the separate surcharge.
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

-- 9. Reconciliation checks. These queries should return zero rows / matching totals.
SELECT `id`, `tong_tien`, `tien_phong`, `tien_phu_phi_mua_cao_diem`, `tien_dich_vu`
FROM `hoadon`
WHERE `tong_tien` <> (`tien_phong` + `tien_phu_phi_mua_cao_diem` + `tien_dich_vu`);

SELECT py.`id` AS pay_id, py.`so_tien`, h.`tong_tien`
FROM `pay` py JOIN `hoadon` h ON h.`pay_id` = py.`id`
WHERE py.`so_tien` <> h.`tong_tien`;

SELECT `id`, `phong_id`, `tu_ngay`, `den_ngay`, `he_so_gia`
FROM `muacaodiem` ORDER BY `id`;

-- Example calculation: 1,000,000 + 50,000 + (1,000,000 x 0.20) = 1,250,000.
SELECT CAST(1000000.00 AS DECIMAL(12,2)) AS tien_phong,
       CAST(50000.00 AS DECIMAL(12,2)) AS tien_dich_vu,
       ROUND(1000000.00 * 0.20, 2) AS tien_phu_phi_mua_cao_diem,
       1000000.00 + 50000.00 + ROUND(1000000.00 * 0.20, 2) AS tong_tien;

-- End of migration.
