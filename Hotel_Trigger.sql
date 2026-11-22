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
-- Hotel_Six_Issues_Fix.sql is only for reconciling the uploaded legacy database dump.
-- MySQL 8.0.16+ is required for enforced CHECK constraints.

USE hotel_management_erd;
SET NAMES utf8mb4;

-- Remove duplicate/obsolete triggers left by the earlier peak-surcharge implementation.
-- The canonical triggers below protect immutable snapshots and rely on stored procedures
-- to create Pay + Invoice atomically; no AFTER trigger re-prices settled records.
DROP TRIGGER IF EXISTS `trg_booking_peak_before_insert`;
DROP TRIGGER IF EXISTS `trg_booking_peak_before_update`;
DROP TRIGGER IF EXISTS `trg_dichvu_after_insert`;
DROP TRIGGER IF EXISTS `trg_dichvu_after_update`;
DROP TRIGGER IF EXISTS `trg_dichvu_after_delete`;
DROP TRIGGER IF EXISTS `trg_loaiphong_after_update`;
DROP TRIGGER IF EXISTS `trg_muacaodiem_after_insert`;
DROP TRIGGER IF EXISTS `trg_muacaodiem_after_update`;
DROP TRIGGER IF EXISTS `trg_muacaodiem_after_delete`;
DROP TRIGGER IF EXISTS `trg_pay_peak_before_insert`;
DROP TRIGGER IF EXISTS `trg_pay_peak_before_update`;
DROP TRIGGER IF EXISTS `trg_pay_after_insert`;


-- 4. TRIGGERS (15 CANONICAL GUARD TRIGGERS; obsolete surcharge recalc triggers are removed)
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
        INSERT INTO dichvu
            (ten,don_gia,so_luong,phong_id,booking_id,loai_dichvu,nhom_dich_vu,don_vi_tinh,dang_hoat_dong)
        SELECT d.ten,d.don_gia,d.so_luong,NEW.phong_id,NEW.id,'MAC_DINH',d.nhom_dich_vu,d.don_vi_tinh,1
        FROM dichvu d
        WHERE d.phong_id=NEW.phong_id AND d.booking_id IS NULL
          AND d.loai_dichvu='MAC_DINH' AND d.dang_hoat_dong=1 AND d.don_gia=0;
    END IF;
    IF NEW.trang_thai='DANG_O' THEN
        UPDATE phong SET trang_thai='DANG_SU_DUNG' WHERE id=NEW.phong_id;
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
CREATE TRIGGER `trg_dichvu_before_insert` BEFORE INSERT ON `dichvu` FOR EACH ROW
BEGIN
    DECLARE v_booking_room_id INT DEFAULT NULL;
    DECLARE v_booking_status VARCHAR(30) DEFAULT NULL;
    DECLARE v_has_booking BOOLEAN DEFAULT TRUE;
    DECLARE v_has_invoice INT DEFAULT 0;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_has_booking=FALSE;
    IF NEW.ten IS NULL OR TRIM(NEW.ten)='' OR NEW.don_gia IS NULL OR NEW.don_gia<0
       OR NEW.so_luong IS NULL OR NEW.so_luong<=0
       OR NEW.nhom_dich_vu IS NULL OR TRIM(NEW.nhom_dich_vu)=''
       OR NEW.don_vi_tinh IS NULL OR TRIM(NEW.don_vi_tinh)='' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Thong tin dich vu khong hop le';
    END IF;
    IF NEW.booking_id IS NULL AND NEW.phong_id IS NULL THEN
        IF NEW.loai_dichvu<>'TUY_CHON' OR NEW.don_gia<=0 THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Danh muc chung phai la dich vu TUY_CHON co gia lon hon 0';
        END IF;
    ELSEIF NEW.booking_id IS NULL THEN
        IF NEW.loai_dichvu<>'MAC_DINH' OR NEW.don_gia<>0 THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Dich vu mac dinh cua phong phai co loai MAC_DINH va gia 0';
        END IF;
    ELSE
        SELECT phong_id,trang_thai INTO v_booking_room_id,v_booking_status FROM booking WHERE id=NEW.booking_id;
        IF NOT v_has_booking THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Booking khong ton tai'; END IF;
        IF v_booking_status IN ('DA_HUY','HOAN_THANH') THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Khong the them dich vu cho Booking da huy/hoan thanh'; END IF;
        IF (NEW.loai_dichvu='TUY_CHON' AND NEW.don_gia<=0) OR (NEW.loai_dichvu='MAC_DINH' AND NEW.don_gia<>0) THEN
            SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Gia dich vu khong khop loai dich vu';
        END IF;
        IF NEW.phong_id IS NULL THEN SET NEW.phong_id=v_booking_room_id;
        ELSEIF NEW.phong_id<>v_booking_room_id THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Phong cua dich vu khong khop voi phong cua Booking'; END IF;
        SELECT COUNT(*) INTO v_has_invoice FROM pay py JOIN hoadon hd ON hd.pay_id=py.id WHERE py.booking_id=NEW.booking_id;
        IF v_has_invoice>0 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Booking da co hoa don, khong the them dich vu'; END IF;
    END IF;
END$$
DELIMITER ;


DROP TRIGGER IF EXISTS `trg_dichvu_before_update`;
DELIMITER $$
CREATE TRIGGER `trg_dichvu_before_update` BEFORE UPDATE ON `dichvu` FOR EACH ROW
BEGIN
    DECLARE v_booking_room_id INT DEFAULT NULL;
    DECLARE v_booking_status VARCHAR(30) DEFAULT NULL;
    DECLARE v_has_booking BOOLEAN DEFAULT TRUE;
    DECLARE v_has_invoice INT DEFAULT 0;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_has_booking=FALSE;
    IF NEW.ten IS NULL OR TRIM(NEW.ten)='' OR NEW.don_gia IS NULL OR NEW.don_gia<0
       OR NEW.so_luong IS NULL OR NEW.so_luong<=0
       OR NEW.nhom_dich_vu IS NULL OR TRIM(NEW.nhom_dich_vu)=''
       OR NEW.don_vi_tinh IS NULL OR TRIM(NEW.don_vi_tinh)='' THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Thong tin dich vu khong hop le';
    END IF;
    IF OLD.booking_id IS NOT NULL AND NOT (NEW.booking_id <=> OLD.booking_id) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Khong duoc tach hoac chuyen dich vu da gan Booking';
    END IF;
    IF NEW.booking_id IS NULL AND NEW.phong_id IS NULL THEN
        IF NEW.loai_dichvu<>'TUY_CHON' OR NEW.don_gia<=0 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Danh muc chung phai la dich vu TUY_CHON co gia lon hon 0'; END IF;
    ELSEIF NEW.booking_id IS NULL THEN
        IF NEW.loai_dichvu<>'MAC_DINH' OR NEW.don_gia<>0 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Dich vu mac dinh cua phong phai co loai MAC_DINH va gia 0'; END IF;
    ELSE
        SELECT phong_id,trang_thai INTO v_booking_room_id,v_booking_status FROM booking WHERE id=NEW.booking_id;
        IF NOT v_has_booking THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Booking khong ton tai'; END IF;
        IF v_booking_status IN ('DA_HUY','HOAN_THANH') THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Khong duoc sua dich vu cua Booking da huy/hoan thanh'; END IF;
        IF (NEW.loai_dichvu='TUY_CHON' AND NEW.don_gia<=0) OR (NEW.loai_dichvu='MAC_DINH' AND NEW.don_gia<>0) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Gia dich vu khong khop loai dich vu'; END IF;
        IF NEW.phong_id IS NULL OR NEW.phong_id<>v_booking_room_id THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Phong cua dich vu phai khop voi phong cua Booking'; END IF;
        SELECT COUNT(*) INTO v_has_invoice FROM pay py JOIN hoadon hd ON hd.pay_id=py.id WHERE py.booking_id=NEW.booking_id;
        IF v_has_invoice>0 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Booking da co hoa don, khong duoc sua dich vu'; END IF;
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


-- 13. Validate invoice values against room price, peak-season rules and Booking services.
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
