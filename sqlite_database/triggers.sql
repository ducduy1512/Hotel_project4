-- SQLite equivalents of the core MySQL business-rule triggers.
-- Snapshot pricing and multi-step procedures are implemented in database.py.
PRAGMA foreign_keys = ON;

CREATE TRIGGER IF NOT EXISTS trg_booking_bi_validate
BEFORE INSERT ON booking
BEGIN
  SELECT CASE WHEN NEW.ngay_nhan IS NULL OR NEW.ngay_tra IS NULL OR NEW.ngay_tra <= NEW.ngay_nhan
    THEN RAISE(ABORT, 'Ngay nhan va ngay tra khong hop le') END;
  SELECT CASE WHEN NEW.trang_thai NOT IN ('CHO_XAC_NHAN','DA_XAC_NHAN','DANG_O','DA_HUY','HOAN_THANH')
    THEN RAISE(ABORT, 'Trang thai Booking khong hop le') END;
  SELECT CASE WHEN NOT EXISTS (SELECT 1 FROM phong WHERE id=NEW.phong_id)
    THEN RAISE(ABORT, 'Phong khong ton tai') END;
  SELECT CASE WHEN NEW.trang_thai <> 'DA_HUY' AND (SELECT trang_thai FROM phong WHERE id=NEW.phong_id)='BAO_TRI'
    THEN RAISE(ABORT, 'Phong dang bao tri, khong the dat') END;
  SELECT CASE WHEN NEW.trang_thai <> 'DA_HUY' AND EXISTS (
    SELECT 1 FROM booking b WHERE b.phong_id=NEW.phong_id AND b.trang_thai<>'DA_HUY'
      AND NEW.ngay_nhan < b.ngay_tra AND NEW.ngay_tra > b.ngay_nhan)
    THEN RAISE(ABORT, 'Phong da co Booking trung khoang thoi gian') END;
  SELECT CASE WHEN NEW.trang_thai='DANG_O' AND (SELECT trang_thai FROM phong WHERE id=NEW.phong_id)='DANG_SU_DUNG'
    THEN RAISE(ABORT, 'Phong dang co khach su dung') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_booking_ai_default_services
AFTER INSERT ON booking
WHEN NEW.trang_thai <> 'DA_HUY'
BEGIN
  INSERT INTO dichvu (ten,don_gia,so_luong,phong_id,booking_id,loai_dichvu,nhom_dich_vu,don_vi_tinh,dang_hoat_dong)
  SELECT ten,don_gia,so_luong,NEW.phong_id,NEW.id,'MAC_DINH',nhom_dich_vu,don_vi_tinh,1
  FROM dichvu WHERE phong_id=NEW.phong_id AND booking_id IS NULL
    AND loai_dichvu='MAC_DINH' AND dang_hoat_dong=1 AND don_gia=0;
  UPDATE phong SET trang_thai='DANG_SU_DUNG' WHERE id=NEW.phong_id AND NEW.trang_thai='DANG_O';
END;

CREATE TRIGGER IF NOT EXISTS trg_booking_bu_validate
BEFORE UPDATE ON booking
BEGIN
  SELECT CASE WHEN NEW.ngay_nhan IS NULL OR NEW.ngay_tra IS NULL OR NEW.ngay_tra <= NEW.ngay_nhan
    THEN RAISE(ABORT, 'Ngay nhan va ngay tra khong hop le') END;
  SELECT CASE WHEN OLD.trang_thai IN ('DA_HUY','HOAN_THANH') AND (
    NEW.phong_id<>OLD.phong_id OR NEW.khach_id<>OLD.khach_id OR NEW.ngay_nhan<>OLD.ngay_nhan OR
    NEW.ngay_tra<>OLD.ngay_tra OR NEW.trang_thai<>OLD.trang_thai)
    THEN RAISE(ABORT, 'Booking da huy/hoan thanh khong duoc thay doi') END;
  SELECT CASE WHEN NEW.phong_id=OLD.phong_id AND NEW.ngay_nhan=OLD.ngay_nhan AND NEW.ngay_tra=OLD.ngay_tra AND (
    NEW.tien_phong_du_kien<>OLD.tien_phong_du_kien OR
    NEW.tien_phu_phi_mua_cao_diem<>OLD.tien_phu_phi_mua_cao_diem OR
    NEW.ap_dung_mua_cao_diem<>OLD.ap_dung_mua_cao_diem OR
    NEW.chi_tiet_mua_cao_diem IS NOT OLD.chi_tiet_mua_cao_diem)
    THEN RAISE(ABORT, 'Snapshot gia Booking khong duoc sua truc tiep') END;
  SELECT CASE WHEN OLD.trang_thai='CHO_XAC_NHAN' AND NEW.trang_thai NOT IN ('CHO_XAC_NHAN','DA_XAC_NHAN','DA_HUY')
    THEN RAISE(ABORT, 'Chuyen trang thai Booking khong hop le') END;
  SELECT CASE WHEN OLD.trang_thai='DA_XAC_NHAN' AND NEW.trang_thai NOT IN ('DA_XAC_NHAN','DANG_O','DA_HUY')
    THEN RAISE(ABORT, 'Chuyen trang thai Booking khong hop le') END;
  SELECT CASE WHEN OLD.trang_thai='DANG_O' AND NEW.trang_thai NOT IN ('DANG_O','HOAN_THANH')
    THEN RAISE(ABORT, 'Booking dang o chi duoc chuyen sang HOAN_THANH') END;
  SELECT CASE WHEN OLD.trang_thai IN ('DA_HUY','HOAN_THANH') AND NEW.trang_thai<>OLD.trang_thai
    THEN RAISE(ABORT, 'Booking da ket thuc, khong the mo lai') END;
  SELECT CASE WHEN (NEW.phong_id<>OLD.phong_id OR NEW.ngay_nhan<>OLD.ngay_nhan OR NEW.ngay_tra<>OLD.ngay_tra)
      AND EXISTS (SELECT 1 FROM pay WHERE booking_id=OLD.id)
    THEN RAISE(ABORT, 'Booking da co giao dich Pay, khong duoc doi phong hoac ngay') END;
  SELECT CASE WHEN NEW.khach_id<>OLD.khach_id AND EXISTS (SELECT 1 FROM pay WHERE booking_id=OLD.id)
    THEN RAISE(ABORT, 'Booking da co giao dich, khong duoc doi khach hang') END;
  SELECT CASE WHEN NEW.trang_thai='DA_HUY' AND OLD.trang_thai<>'DA_HUY' AND EXISTS (
    SELECT 1 FROM pay WHERE booking_id=OLD.id AND status IN ('CHO_THANH_TOAN','THANH_CONG'))
    THEN RAISE(ABORT, 'Can xu ly giao dich dang cho/thanh cong truoc khi huy Booking') END;
  SELECT CASE WHEN NEW.trang_thai<>'DA_HUY' AND EXISTS (
    SELECT 1 FROM booking b WHERE b.phong_id=NEW.phong_id AND b.id<>OLD.id AND b.trang_thai<>'DA_HUY'
      AND NEW.ngay_nhan < b.ngay_tra AND NEW.ngay_tra > b.ngay_nhan)
    THEN RAISE(ABORT, 'Cap nhat that bai: phong da co Booking trung lich') END;
  SELECT CASE WHEN (NEW.phong_id<>OLD.phong_id OR NEW.ngay_nhan<>OLD.ngay_nhan OR NEW.ngay_tra<>OLD.ngay_tra)
      AND (SELECT trang_thai FROM phong WHERE id=NEW.phong_id)='BAO_TRI'
    THEN RAISE(ABORT, 'Phong moi khong ton tai hoac dang bao tri') END;
  SELECT CASE WHEN NEW.trang_thai='DANG_O' AND
      (OLD.trang_thai<>'DANG_O' OR NEW.phong_id<>OLD.phong_id) AND
      (SELECT trang_thai FROM phong WHERE id=NEW.phong_id)='DANG_SU_DUNG'
    THEN RAISE(ABORT, 'Phong dang duoc su dung boi khach khac') END;
  SELECT CASE WHEN NEW.trang_thai='DANG_O' AND
      (OLD.trang_thai<>'DANG_O' OR NEW.phong_id<>OLD.phong_id) AND EXISTS(
        SELECT 1 FROM booking b WHERE b.phong_id=NEW.phong_id AND b.id<>OLD.id AND b.trang_thai='DANG_O')
    THEN RAISE(ABORT, 'Phong da co Booking khac dang luu tru') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_booking_au_room_status
AFTER UPDATE OF trang_thai,phong_id ON booking
BEGIN
  UPDATE phong SET trang_thai='SAN_SANG'
  WHERE id=OLD.phong_id AND OLD.trang_thai='DANG_O'
    AND (NEW.trang_thai<>'DANG_O' OR NEW.phong_id<>OLD.phong_id)
    AND trang_thai<>'BAO_TRI'
    AND NOT EXISTS (SELECT 1 FROM booking WHERE phong_id=OLD.phong_id AND id<>NEW.id AND trang_thai='DANG_O');
  UPDATE phong SET trang_thai='DANG_SU_DUNG' WHERE id=NEW.phong_id
    AND NEW.trang_thai='DANG_O' AND (OLD.trang_thai<>'DANG_O' OR NEW.phong_id<>OLD.phong_id);
  UPDATE dichvu SET phong_id=NEW.phong_id WHERE booking_id=NEW.id AND NEW.phong_id<>OLD.phong_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_muacaodiem_bi_validate
BEFORE INSERT ON muacaodiem
BEGIN
  SELECT CASE WHEN NEW.den_ngay < NEW.tu_ngay THEN RAISE(ABORT,'Khoang ngay mua cao diem khong hop le') END;
END;
CREATE TRIGGER IF NOT EXISTS trg_muacaodiem_bu_validate
BEFORE UPDATE ON muacaodiem
BEGIN
  SELECT CASE WHEN NEW.den_ngay < NEW.tu_ngay THEN RAISE(ABORT,'Khoang ngay mua cao diem khong hop le') END;
  SELECT CASE WHEN EXISTS (
    SELECT 1 FROM phong_muacaodiem a JOIN phong_muacaodiem b ON a.phong_id=b.phong_id
    WHERE a.muacaodiem_id=OLD.id AND b.muacaodiem_id<>OLD.id
      AND NEW.tu_ngay<= (SELECT den_ngay FROM muacaodiem WHERE id=b.muacaodiem_id)
      AND NEW.den_ngay>= (SELECT tu_ngay FROM muacaodiem WHERE id=b.muacaodiem_id))
    THEN RAISE(ABORT,'Mua cao diem bi trung khoang ngay cua phong') END;
END;
CREATE TRIGGER IF NOT EXISTS trg_phong_muacaodiem_bi_validate
BEFORE INSERT ON phong_muacaodiem
BEGIN
  SELECT CASE WHEN NEW.he_so_phu_thu NOT IN (0.10,0.20,0.25,0.30,0.35,0.40,0.50,0.60)
    THEN RAISE(ABORT,'He so phu thu mua cao diem khong hop le') END;
  SELECT CASE WHEN EXISTS (
    SELECT 1 FROM phong_muacaodiem pm JOIN muacaodiem a ON a.id=pm.muacaodiem_id
    JOIN muacaodiem b ON b.id=NEW.muacaodiem_id
    WHERE pm.phong_id=NEW.phong_id AND a.id<>NEW.muacaodiem_id
      AND b.tu_ngay<=a.den_ngay AND b.den_ngay>=a.tu_ngay)
    THEN RAISE(ABORT,'Phong da co mua cao diem trung ngay') END;
END;
CREATE TRIGGER IF NOT EXISTS trg_phong_muacaodiem_bu_validate
BEFORE UPDATE ON phong_muacaodiem
BEGIN
  SELECT CASE WHEN NEW.he_so_phu_thu NOT IN (0.10,0.20,0.25,0.30,0.35,0.40,0.50,0.60)
    THEN RAISE(ABORT,'He so phu thu mua cao diem khong hop le') END;
  SELECT CASE WHEN EXISTS (
    SELECT 1 FROM phong_muacaodiem pm JOIN muacaodiem a ON a.id=pm.muacaodiem_id
    JOIN muacaodiem b ON b.id=NEW.muacaodiem_id
    WHERE pm.phong_id=NEW.phong_id AND NOT(pm.phong_id=OLD.phong_id AND pm.muacaodiem_id=OLD.muacaodiem_id)
      AND b.tu_ngay<=a.den_ngay AND b.den_ngay>=a.tu_ngay)
    THEN RAISE(ABORT,'Phong da co mua cao diem trung ngay') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_dichvu_bi_validate
BEFORE INSERT ON dichvu
BEGIN
  SELECT CASE WHEN NEW.ten IS NULL OR trim(NEW.ten)='' OR NEW.don_gia IS NULL OR NEW.don_gia<0
       OR NEW.so_luong IS NULL OR NEW.so_luong<=0
       OR NEW.nhom_dich_vu IS NULL OR trim(NEW.nhom_dich_vu)=''
       OR NEW.don_vi_tinh IS NULL OR trim(NEW.don_vi_tinh)=''
    THEN RAISE(ABORT,'Thong tin dich vu khong hop le') END;
  SELECT CASE WHEN NEW.booking_id IS NULL AND NEW.phong_id IS NULL
       AND (NEW.loai_dichvu<>'TUY_CHON' OR NEW.don_gia<=0)
    THEN RAISE(ABORT,'Danh muc chung phai la dich vu TUY_CHON co gia lon hon 0') END;
  SELECT CASE WHEN NEW.booking_id IS NULL AND NEW.phong_id IS NOT NULL
       AND (NEW.loai_dichvu<>'MAC_DINH' OR NEW.don_gia<>0)
    THEN RAISE(ABORT,'Dich vu mac dinh cua phong phai co loai MAC_DINH va gia 0') END;
  SELECT CASE WHEN NEW.booking_id IS NOT NULL AND NOT EXISTS(
       SELECT 1 FROM booking b WHERE b.id=NEW.booking_id
         AND b.trang_thai NOT IN ('DA_HUY','HOAN_THANH'))
    THEN RAISE(ABORT,'Khong the them dich vu cho Booking khong ton tai/da ket thuc') END;
  SELECT CASE WHEN NEW.booking_id IS NOT NULL AND (
       (NEW.loai_dichvu='TUY_CHON' AND NEW.don_gia<=0) OR
       (NEW.loai_dichvu='MAC_DINH' AND NEW.don_gia<>0))
    THEN RAISE(ABORT,'Gia dich vu khong khop loai dich vu') END;
  SELECT CASE WHEN NEW.booking_id IS NOT NULL AND NEW.phong_id IS NOT
       (SELECT phong_id FROM booking WHERE id=NEW.booking_id)
    THEN RAISE(ABORT,'Phong cua dich vu khong khop voi phong cua Booking') END;
  SELECT CASE WHEN NEW.booking_id IS NOT NULL AND EXISTS(
       SELECT 1 FROM pay py JOIN hoadon hd ON hd.pay_id=py.id
       WHERE py.booking_id=NEW.booking_id)
    THEN RAISE(ABORT,'Booking da co hoa don, khong the them dich vu') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_dichvu_bu_validate
BEFORE UPDATE ON dichvu
BEGIN
  SELECT CASE WHEN NEW.ten IS NULL OR trim(NEW.ten)='' OR NEW.don_gia IS NULL OR NEW.don_gia<0
       OR NEW.so_luong IS NULL OR NEW.so_luong<=0
       OR NEW.nhom_dich_vu IS NULL OR trim(NEW.nhom_dich_vu)=''
       OR NEW.don_vi_tinh IS NULL OR trim(NEW.don_vi_tinh)=''
    THEN RAISE(ABORT,'Thong tin dich vu khong hop le') END;
  SELECT CASE WHEN OLD.booking_id IS NOT NULL AND NEW.booking_id IS NOT OLD.booking_id
    THEN RAISE(ABORT,'Khong duoc tach hoac chuyen dich vu da gan Booking') END;
  SELECT CASE WHEN NEW.booking_id IS NULL AND NEW.phong_id IS NULL
       AND (NEW.loai_dichvu<>'TUY_CHON' OR NEW.don_gia<=0)
    THEN RAISE(ABORT,'Danh muc chung phai la dich vu TUY_CHON co gia lon hon 0') END;
  SELECT CASE WHEN NEW.booking_id IS NULL AND NEW.phong_id IS NOT NULL
       AND (NEW.loai_dichvu<>'MAC_DINH' OR NEW.don_gia<>0)
    THEN RAISE(ABORT,'Dich vu mac dinh cua phong phai co loai MAC_DINH va gia 0') END;
  SELECT CASE WHEN NEW.booking_id IS NOT NULL AND NOT EXISTS(
       SELECT 1 FROM booking b WHERE b.id=NEW.booking_id
         AND b.trang_thai NOT IN ('DA_HUY','HOAN_THANH'))
    THEN RAISE(ABORT,'Khong duoc sua dich vu cua Booking khong ton tai/da ket thuc') END;
  SELECT CASE WHEN NEW.booking_id IS NOT NULL AND (
       (NEW.loai_dichvu='TUY_CHON' AND NEW.don_gia<=0) OR
       (NEW.loai_dichvu='MAC_DINH' AND NEW.don_gia<>0))
    THEN RAISE(ABORT,'Gia dich vu khong khop loai dich vu') END;
  SELECT CASE WHEN NEW.booking_id IS NOT NULL AND NEW.phong_id IS NOT
       (SELECT phong_id FROM booking WHERE id=NEW.booking_id)
    THEN RAISE(ABORT,'Phong cua dich vu phai khop voi phong cua Booking') END;
  SELECT CASE WHEN NEW.booking_id IS NOT NULL AND EXISTS(
       SELECT 1 FROM pay py JOIN hoadon hd ON hd.pay_id=py.id
       WHERE py.booking_id=NEW.booking_id)
    THEN RAISE(ABORT,'Booking da co hoa don, khong duoc sua dich vu') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_dichvu_bd_validate
BEFORE DELETE ON dichvu
BEGIN
  SELECT CASE WHEN OLD.booking_id IS NOT NULL AND NOT EXISTS(SELECT 1 FROM booking WHERE id=OLD.booking_id)
    THEN RAISE(ABORT,'Booking cua dich vu khong ton tai') END;
  SELECT CASE WHEN OLD.booking_id IS NOT NULL AND EXISTS(
       SELECT 1 FROM booking WHERE id=OLD.booking_id AND trang_thai IN ('DA_HUY','HOAN_THANH'))
    THEN RAISE(ABORT,'Khong duoc xoa dich vu cua Booking da huy/hoan thanh') END;
  SELECT CASE WHEN OLD.booking_id IS NOT NULL AND EXISTS(
       SELECT 1 FROM pay py JOIN hoadon hd ON hd.pay_id=py.id WHERE py.booking_id=OLD.booking_id)
    THEN RAISE(ABORT,'Booking da co hoa don, khong duoc xoa dich vu') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_pay_bi_validate
BEFORE INSERT ON pay
BEGIN
  SELECT CASE WHEN NEW.so_tien IS NULL OR NEW.so_tien<0
    THEN RAISE(ABORT,'So tien thanh toan khong duoc am') END;
  SELECT CASE WHEN NEW.status<>'CHO_THANH_TOAN'
    THEN RAISE(ABORT,'Giao dich moi phai bat dau o trang thai CHO_THANH_TOAN') END;
  SELECT CASE WHEN NOT EXISTS(
       SELECT 1 FROM booking b WHERE b.id=NEW.booking_id AND b.khach_id=NEW.khach_id
         AND b.trang_thai<>'DA_HUY')
    THEN RAISE(ABORT,'Booking/khach hang khong hop le cho thanh toan') END;
  SELECT CASE WHEN abs(NEW.so_tien - (
       COALESCE((SELECT tien_phong_du_kien FROM booking WHERE id=NEW.booking_id),0) +
       COALESCE((SELECT tien_phu_phi_mua_cao_diem FROM booking WHERE id=NEW.booking_id),0) +
       COALESCE((SELECT SUM(don_gia*so_luong) FROM dichvu WHERE booking_id=NEW.booking_id),0))) > 0.01
    THEN RAISE(ABORT,'So tien Pay phai bang tien phong + phu phi cao diem + dich vu Booking') END;
  SELECT CASE WHEN abs(NEW.tien_phong_ap_dung -
       COALESCE((SELECT tien_phong_du_kien FROM booking WHERE id=NEW.booking_id),0)) > 0.01
       OR abs(NEW.tien_phu_phi_mua_cao_diem -
       COALESCE((SELECT tien_phu_phi_mua_cao_diem FROM booking WHERE id=NEW.booking_id),0)) > 0.01
       OR NEW.ap_dung_mua_cao_diem <>
       COALESCE((SELECT ap_dung_mua_cao_diem FROM booking WHERE id=NEW.booking_id),0)
       OR NEW.chi_tiet_mua_cao_diem IS NOT
       (SELECT chi_tiet_mua_cao_diem FROM booking WHERE id=NEW.booking_id)
    THEN RAISE(ABORT,'Snapshot Pay khong khop snapshot gia Booking') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_pay_bu_validate
BEFORE UPDATE ON pay
BEGIN
  SELECT CASE WHEN NEW.booking_id<>OLD.booking_id OR NEW.khach_id<>OLD.khach_id OR
    NEW.ngay_thanh_toan<>OLD.ngay_thanh_toan OR NEW.so_tien<>OLD.so_tien OR NEW.method<>OLD.method
    OR NEW.tien_phong_ap_dung<>OLD.tien_phong_ap_dung OR NEW.tien_phu_phi_mua_cao_diem<>OLD.tien_phu_phi_mua_cao_diem
    OR NEW.chi_tiet_mua_cao_diem IS NOT OLD.chi_tiet_mua_cao_diem OR NEW.ap_dung_mua_cao_diem<>OLD.ap_dung_mua_cao_diem
    THEN RAISE(ABORT,'Thong tin co dinh cua giao dich khong duoc thay doi') END;
  SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM booking WHERE id=NEW.booking_id AND khach_id=NEW.khach_id)
    THEN RAISE(ABORT,'Khach hang cua Pay khong khop voi Booking') END;
  SELECT CASE WHEN NEW.status<>OLD.status AND NOT(
      (OLD.status='CHO_THANH_TOAN' AND NEW.status IN ('THANH_CONG','THAT_BAI')) OR
      (OLD.status='THAT_BAI' AND NEW.status='CHO_THANH_TOAN') OR
      (OLD.status='THANH_CONG' AND NEW.status='HOAN_TIEN'))
    THEN RAISE(ABORT,'Chuyen trang thai thanh toan khong hop le') END;
  SELECT CASE WHEN NEW.status='THANH_CONG' AND NOT EXISTS(SELECT 1 FROM hoadon WHERE pay_id=OLD.id)
    THEN RAISE(ABORT,'Can co hoa don truoc khi xac nhan thanh toan') END;
  SELECT CASE WHEN NEW.status='THANH_CONG' AND EXISTS(SELECT 1 FROM booking WHERE id=OLD.booking_id AND trang_thai='DA_HUY')
    THEN RAISE(ABORT,'Khong the thanh toan Booking da huy') END;
  SELECT CASE WHEN NEW.status='THANH_CONG' AND abs(NEW.so_tien-(SELECT tong_tien FROM hoadon WHERE pay_id=OLD.id))>0.01
    THEN RAISE(ABORT,'So tien Pay khong khop tong tien hoa don') END;
  SELECT CASE WHEN NEW.status='HOAN_TIEN' AND OLD.status<>'THANH_CONG'
    THEN RAISE(ABORT,'Chi duoc hoan tien cho giao dich da thanh cong') END;
END;
CREATE TRIGGER IF NOT EXISTS trg_pay_au_confirm_booking
AFTER UPDATE OF status ON pay
WHEN NEW.status='THANH_CONG' AND OLD.status<>'THANH_CONG'
BEGIN
  UPDATE booking SET trang_thai='DA_XAC_NHAN'
  WHERE id=NEW.booking_id AND trang_thai='CHO_XAC_NHAN';
END;

CREATE TRIGGER IF NOT EXISTS trg_hoadon_bi_validate
BEFORE INSERT ON hoadon
BEGIN
  SELECT CASE WHEN NEW.tien_phong IS NULL OR NEW.tien_phu_phi_mua_cao_diem IS NULL
       OR NEW.tien_dich_vu IS NULL OR NEW.tong_tien IS NULL
       OR NEW.tien_phong<0 OR NEW.tien_phu_phi_mua_cao_diem<0 OR NEW.tien_dich_vu<0
       OR abs(NEW.tong_tien-(NEW.tien_phong+NEW.tien_phu_phi_mua_cao_diem+NEW.tien_dich_vu))>0.01
    THEN RAISE(ABORT,'Thanh phan tien hoa don khong hop le') END;
  SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM pay WHERE id=NEW.pay_id AND status='CHO_THANH_TOAN')
    THEN RAISE(ABORT,'Hoa don chi duoc tao cho Pay dang cho thanh toan') END;
  SELECT CASE WHEN EXISTS(SELECT 1 FROM booking b JOIN pay py ON py.booking_id=b.id
       WHERE py.id=NEW.pay_id AND b.trang_thai='DA_HUY')
    THEN RAISE(ABORT,'Khong the lap hoa don cho Booking da huy') END;
  SELECT CASE WHEN abs(NEW.tien_phong -
       COALESCE((SELECT tien_phong_ap_dung FROM pay WHERE id=NEW.pay_id),0))>0.01
       OR abs(NEW.tien_phu_phi_mua_cao_diem -
       COALESCE((SELECT tien_phu_phi_mua_cao_diem FROM pay WHERE id=NEW.pay_id),0))>0.01
    THEN RAISE(ABORT,'Tien phong/phi cao diem hoa don khong khop snapshot Pay') END;
  SELECT CASE WHEN abs(NEW.tien_dich_vu - COALESCE((
       SELECT SUM(d.don_gia*d.so_luong) FROM dichvu d
       JOIN pay py ON py.booking_id=d.booking_id WHERE py.id=NEW.pay_id),0))>0.01
    THEN RAISE(ABORT,'Tien dich vu hoa don khong khop dich vu Booking') END;
  SELECT CASE WHEN abs(NEW.tong_tien - COALESCE((SELECT so_tien FROM pay WHERE id=NEW.pay_id),0))>0.01
    THEN RAISE(ABORT,'Tong tien hoa don khong khop so tien Pay') END;
END;

CREATE TRIGGER IF NOT EXISTS trg_hoadon_bu_immutable
BEFORE UPDATE ON hoadon
BEGIN
  SELECT RAISE(ABORT,'Hoa don da tao khong duoc sua truc tiep');
END;
CREATE TRIGGER IF NOT EXISTS trg_hoadon_bd_immutable
BEFORE DELETE ON hoadon
WHEN EXISTS(SELECT 1 FROM pay WHERE id=OLD.pay_id AND status IN ('THANH_CONG','HOAN_TIEN'))
BEGIN
  SELECT RAISE(ABORT,'Khong the xoa hoa don da thanh toan/hoan tien');
END;
