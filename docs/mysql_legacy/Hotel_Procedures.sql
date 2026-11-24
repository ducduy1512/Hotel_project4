-- LEGACY MYSQL SCRIPT: current application uses SQLite. Do not execute this script to start the SQLite edition.
-- See README.md and sqlite_database/ for the active database setup.
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


-- Customer booking with explicit service selection.
-- p_dich_vu is a JSON array:
-- [{"dichvu_id": 1, "so_luong": 2}, ...]
-- IDs must refer to default services of the selected room (booking_id IS NULL).
-- An empty array means the customer opts out of all default services.
-- Customer can choose room-default services plus any active global paid add-ons.
-- JSON: [{"dichvu_id":1,"so_luong":2}]. Quantity for giường/đêm = beds per night.
DROP PROCEDURE IF EXISTS `sp_tao_booking_customer`;
DELIMITER $$
CREATE PROCEDURE `sp_tao_booking_customer`(
    IN p_phong_id INT, IN p_khach_id INT,
    IN p_ngay_nhan DATE, IN p_ngay_tra DATE, IN p_dich_vu JSON
)
BEGIN
    DECLARE v_dem INT DEFAULT 0;
    DECLARE v_trang_thai_phong VARCHAR(30) DEFAULT NULL;
    DECLARE v_booking_id INT DEFAULT NULL;
    DECLARE v_not_found BOOLEAN DEFAULT FALSE;
    DECLARE v_selected_count INT DEFAULT 0;
    DECLARE v_distinct_count INT DEFAULT 0;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_not_found = TRUE;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;

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
    IF v_dem > 0 THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Phong da duoc dat trong khoang thoi gian nay'; END IF;

    SELECT COUNT(*), COUNT(DISTINCT x.dichvu_id) INTO v_selected_count, v_distinct_count
    FROM JSON_TABLE(p_dich_vu, '$[*]' COLUMNS(
        dichvu_id INT PATH '$.dichvu_id' ERROR ON EMPTY ERROR ON ERROR,
        so_luong INT PATH '$.so_luong' ERROR ON EMPTY ERROR ON ERROR
    )) AS x;
    IF v_selected_count <> v_distinct_count THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Khong duoc chon trung dich vu';
    END IF;
    IF EXISTS (
        SELECT 1 FROM JSON_TABLE(p_dich_vu, '$[*]' COLUMNS(
            dichvu_id INT PATH '$.dichvu_id' ERROR ON EMPTY ERROR ON ERROR,
            so_luong INT PATH '$.so_luong' ERROR ON EMPTY ERROR ON ERROR
        )) AS x
        LEFT JOIN dichvu d ON d.id=x.dichvu_id AND d.booking_id IS NULL AND d.dang_hoat_dong=1
          AND ((d.loai_dichvu='MAC_DINH' AND d.phong_id=p_phong_id)
            OR (d.loai_dichvu='TUY_CHON' AND d.phong_id IS NULL AND d.don_gia>0))
        WHERE d.id IS NULL OR x.so_luong<=0
    ) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Dich vu khong hop le, khong thuoc phong hoac da ngung kinh doanh'; END IF;

    INSERT INTO booking (phong_id,khach_id,ngay_nhan,ngay_tra,trang_thai)
    VALUES (p_phong_id,p_khach_id,p_ngay_nhan,p_ngay_tra,'CHO_XAC_NHAN');
    SET v_booking_id=LAST_INSERT_ID();
    DELETE FROM dichvu WHERE booking_id=v_booking_id;
    INSERT INTO dichvu
        (ten,don_gia,so_luong,phong_id,booking_id,loai_dichvu,nhom_dich_vu,don_vi_tinh,dang_hoat_dong)
    SELECT d.ten,d.don_gia,
           CASE WHEN d.don_vi_tinh='giường/đêm' THEN x.so_luong*DATEDIFF(p_ngay_tra,p_ngay_nhan) ELSE x.so_luong END,
           p_phong_id,v_booking_id,d.loai_dichvu,d.nhom_dich_vu,d.don_vi_tinh,1
    FROM JSON_TABLE(p_dich_vu, '$[*]' COLUMNS(
        dichvu_id INT PATH '$.dichvu_id' ERROR ON EMPTY ERROR ON ERROR,
        so_luong INT PATH '$.so_luong' ERROR ON EMPTY ERROR ON ERROR
    )) AS x
    JOIN dichvu d ON d.id=x.dichvu_id AND d.booking_id IS NULL AND d.dang_hoat_dong=1
      AND ((d.loai_dichvu='MAC_DINH' AND d.phong_id=p_phong_id)
        OR (d.loai_dichvu='TUY_CHON' AND d.phong_id IS NULL));
    COMMIT;
    SELECT v_booking_id AS booking_id,p_phong_id AS phong_id,p_khach_id AS khach_id,
           p_ngay_nhan AS ngay_nhan,p_ngay_tra AS ngay_tra,
           'CHO_XAC_NHAN' AS trang_thai,v_selected_count AS so_dich_vu_da_chon;
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
    IN p_booking_id INT, IN p_ten VARCHAR(100),
    IN p_don_gia DECIMAL(12,2), IN p_so_luong INT
)
BEGIN
    DECLARE v_phong_id INT DEFAULT NULL;
    DECLARE v_status VARCHAR(30) DEFAULT NULL;
    DECLARE v_not_found BOOLEAN DEFAULT FALSE;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET v_not_found=TRUE;
    DECLARE EXIT HANDLER FOR SQLEXCEPTION BEGIN ROLLBACK; RESIGNAL; END;
    START TRANSACTION;
    SELECT phong_id,trang_thai INTO v_phong_id,v_status FROM booking WHERE id=p_booking_id FOR UPDATE;
    IF v_not_found THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Booking khong ton tai'; END IF;
    IF v_status NOT IN ('CHO_XAC_NHAN','DA_XAC_NHAN','DANG_O') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='Khong the them dich vu cho booking da huy hoac hoan thanh';
    END IF;
    INSERT INTO dichvu
        (ten,don_gia,so_luong,phong_id,booking_id,loai_dichvu,nhom_dich_vu,don_vi_tinh,dang_hoat_dong)
    VALUES (p_ten,p_don_gia,p_so_luong,v_phong_id,p_booking_id,'TUY_CHON','KHAC','lần',1);
    COMMIT;
    SELECT LAST_INSERT_ID() AS dichvu_id,p_booking_id AS booking_id,
           p_ten AS ten_dich_vu,p_don_gia AS don_gia,p_so_luong AS so_luong,
           p_don_gia*p_so_luong AS thanh_tien;
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
           d.loai_dichvu,
           d.nhom_dich_vu,
           d.don_vi_tinh,
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

-- ============================================================================

-- Backfill the immutable seasonal price snapshot for the seed Booking/Pay rows.
-- This helper is called once during fresh setup and is dropped immediately afterwards.
DELIMITER $$
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
            SELECT MAX(m.id), COALESCE(MAX(pm.he_so_phu_thu),0.00)
            INTO v_season_id, v_factor
            FROM muacaodiem m
            JOIN phong_muacaodiem pm ON pm.muacaodiem_id=m.id
            WHERE pm.phong_id=v_room_id AND v_day BETWEEN m.tu_ngay AND m.den_ngay;
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


