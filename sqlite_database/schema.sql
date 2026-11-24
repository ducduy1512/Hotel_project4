PRAGMA foreign_keys = OFF;
CREATE TABLE IF NOT EXISTS `loaiphong` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `ten` TEXT NOT NULL,
  `gia_co_ban` NUMERIC NOT NULL,
  `suc_chua` INTEGER NOT NULL,
  UNIQUE (`ten`),
  CONSTRAINT `chk_gia_phong` CHECK (`gia_co_ban` >= 0),
  CONSTRAINT `chk_suc_chua` CHECK (`suc_chua` > 0)
);

CREATE TABLE IF NOT EXISTS `phong` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `so_phong` TEXT NOT NULL,
  `loai_phong_id` INTEGER NOT NULL,
  `trang_thai` TEXT NOT NULL DEFAULT 'SAN_SANG',
  UNIQUE (`so_phong`),
  CONSTRAINT `fk_phong_loaiphong` FOREIGN KEY (`loai_phong_id`) REFERENCES `loaiphong` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_trang_thai_phong` CHECK (`trang_thai` IN ('SAN_SANG', 'DANG_SU_DUNG', 'BAO_TRI'))
);

CREATE TABLE IF NOT EXISTS `khach` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `ho_ten` TEXT NOT NULL,
  `cccd` TEXT NOT NULL,
  `sdt` TEXT NOT NULL,
  UNIQUE (`cccd`),
  UNIQUE (`sdt`)
);

CREATE TABLE IF NOT EXISTS `booking` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `phong_id` INTEGER NOT NULL,
  `khach_id` INTEGER NOT NULL,
  `ngay_nhan` TEXT NOT NULL,
  `ngay_tra` TEXT NOT NULL,
  `trang_thai` TEXT NOT NULL DEFAULT 'CHO_XAC_NHAN',
  `tien_phong_du_kien` NUMERIC NOT NULL DEFAULT 0.00,
  `tien_phu_phi_mua_cao_diem` NUMERIC NOT NULL DEFAULT 0.00,
  `ap_dung_mua_cao_diem` INTEGER NOT NULL DEFAULT 0,
  `chi_tiet_mua_cao_diem` TEXT DEFAULT NULL,
  CONSTRAINT `fk_booking_khach` FOREIGN KEY (`khach_id`) REFERENCES `khach` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_booking_phong` FOREIGN KEY (`phong_id`) REFERENCES `phong` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_ngay_booking` CHECK (`ngay_tra` > `ngay_nhan`),
  CONSTRAINT `chk_trang_thai_booking` CHECK (`trang_thai` IN ('CHO_XAC_NHAN', 'DA_XAC_NHAN', 'DANG_O', 'DA_HUY', 'HOAN_THANH'))
);

CREATE TABLE IF NOT EXISTS `dichvu` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `ten` TEXT NOT NULL,
  `don_gia` NUMERIC NOT NULL DEFAULT 0.00,
  `so_luong` INTEGER NOT NULL DEFAULT 1,
  `loai_dichvu` TEXT NOT NULL DEFAULT 'MAC_DINH' CHECK (`loai_dichvu` IN ('MAC_DINH', 'TUY_CHON')),
  `nhom_dich_vu` TEXT NOT NULL DEFAULT 'KHAC',
  `don_vi_tinh` TEXT NOT NULL DEFAULT 'lần',
  `dang_hoat_dong` INTEGER NOT NULL DEFAULT 1,
  `phong_id` INTEGER DEFAULT NULL,
  `booking_id` INTEGER DEFAULT NULL,
  CONSTRAINT `fk_dichvu_phong` FOREIGN KEY (`phong_id`) REFERENCES `phong` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_dichvu_booking` FOREIGN KEY (`booking_id`) REFERENCES `booking` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_dichvu_gia` CHECK (`don_gia` >= 0),
  CONSTRAINT `chk_dichvu_soluong` CHECK (`so_luong` > 0)
);

CREATE TABLE IF NOT EXISTS `muacaodiem` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `tu_ngay` TEXT NOT NULL,
  `den_ngay` TEXT NOT NULL,
  CONSTRAINT `chk_ngay_caodiem` CHECK (`den_ngay` >= `tu_ngay`)
);

CREATE TABLE IF NOT EXISTS `phong_muacaodiem` (
  `phong_id` INTEGER NOT NULL,
  `muacaodiem_id` INTEGER NOT NULL,
  `he_so_phu_thu` NUMERIC NOT NULL,
  PRIMARY KEY (`phong_id`, `muacaodiem_id`),
  CONSTRAINT `fk_pmd_phong` FOREIGN KEY (`phong_id`) REFERENCES `phong` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_pmd_muacaodiem` FOREIGN KEY (`muacaodiem_id`) REFERENCES `muacaodiem` (`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `chk_pmd_he_so` CHECK (`he_so_phu_thu` IN (0.10, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.60))
);

CREATE TABLE IF NOT EXISTS `pay` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `booking_id` INTEGER NOT NULL,
  `khach_id` INTEGER NOT NULL,
  `ngay_thanh_toan` TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `so_tien` NUMERIC NOT NULL,
  `method` TEXT NOT NULL,
  `status` TEXT NOT NULL DEFAULT 'CHO_THANH_TOAN',
  `tien_phong_ap_dung` NUMERIC NOT NULL DEFAULT 0.00,
  `tien_phu_phi_mua_cao_diem` NUMERIC NOT NULL DEFAULT 0.00,
  `ap_dung_mua_cao_diem` INTEGER NOT NULL DEFAULT 0,
  `chi_tiet_mua_cao_diem` TEXT DEFAULT NULL,
  CONSTRAINT `fk_pay_booking` FOREIGN KEY (`booking_id`) REFERENCES `booking` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `fk_pay_khach` FOREIGN KEY (`khach_id`) REFERENCES `khach` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_pay_method` CHECK (`method` IN ('TIEN_MAT', 'CHUYEN_KHOAN', 'THE')),
  CONSTRAINT `chk_pay_sotien` CHECK (`so_tien` >= 0),
  CONSTRAINT `chk_pay_status` CHECK (`status` IN ('CHO_THANH_TOAN', 'THANH_CONG', 'THAT_BAI', 'HOAN_TIEN'))
);

CREATE TABLE IF NOT EXISTS `hoadon` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `pay_id` INTEGER NOT NULL,
  `tien_phong` NUMERIC NOT NULL,
  `tien_phu_phi_mua_cao_diem` NUMERIC NOT NULL DEFAULT 0.00,
  `tien_dich_vu` NUMERIC NOT NULL,
  `tong_tien` NUMERIC NOT NULL,
  `ngay_lap` TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (`pay_id`),
  CONSTRAINT `fk_hoadon_pay` FOREIGN KEY (`pay_id`) REFERENCES `pay` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT `chk_hoadon_tien` CHECK (
    `tien_phong` >= 0
    AND `tien_phu_phi_mua_cao_diem` >= 0
    AND `tien_dich_vu` >= 0
    AND `tong_tien` >= 0
    AND `tong_tien` = (`tien_phong` + `tien_phu_phi_mua_cao_diem` + `tien_dich_vu`)
  )
);

CREATE TABLE IF NOT EXISTS `payment_qr` (
  `pay_id` INTEGER NOT NULL,
  `payment_code` TEXT NOT NULL,
  `created_at` TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `sepay_transaction_id` TEXT DEFAULT NULL,
  `sepay_reference_code` TEXT DEFAULT NULL,
  `received_amount` NUMERIC DEFAULT NULL,
  `received_account_number` TEXT DEFAULT NULL,
  `received_at` TEXT DEFAULT NULL,
  PRIMARY KEY (`pay_id`),
  UNIQUE (`payment_code`),
  UNIQUE (`sepay_transaction_id`),
  CONSTRAINT `fk_payment_qr_pay` FOREIGN KEY (`pay_id`) REFERENCES `pay` (`id`)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `chk_payment_qr_amount` CHECK (`received_amount` IS NULL OR `received_amount` >= 0)
);

CREATE TABLE IF NOT EXISTS `sepay_webhook_events` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `transaction_id` TEXT NOT NULL,
  `gateway` TEXT DEFAULT NULL,
  `account_number` TEXT DEFAULT NULL,
  `payment_code` TEXT DEFAULT NULL,
  `transfer_type` TEXT DEFAULT NULL,
  `transfer_amount` NUMERIC NOT NULL DEFAULT 0.00,
  `reference_code` TEXT DEFAULT NULL,
  `transaction_date` TEXT DEFAULT NULL,
  `pay_id` INTEGER DEFAULT NULL,
  `processing_result` TEXT NOT NULL DEFAULT 'RECEIVED',
  `raw_payload` TEXT NOT NULL,
  `received_at` TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `processed_at` TEXT DEFAULT NULL,
  UNIQUE (`transaction_id`),
  CONSTRAINT `fk_sepay_event_pay` FOREIGN KEY (`pay_id`) REFERENCES `pay` (`id`)
    ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `chk_sepay_transfer_amount` CHECK (`transfer_amount` >= 0)
);

CREATE TABLE IF NOT EXISTS `users` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `username` TEXT NOT NULL,
  `full_name` TEXT NOT NULL,
  `password_hash` TEXT NOT NULL,
  `role` TEXT NOT NULL DEFAULT 'CUSTOMER' CHECK (`role` IN ('ADMIN', 'CUSTOMER')),
  `khach_id` INTEGER DEFAULT NULL,
  `is_active` INTEGER NOT NULL DEFAULT 1,
  `created_at` TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (`username`),
  UNIQUE (`khach_id`),
  CONSTRAINT `fk_users_khach` FOREIGN KEY (`khach_id`)
    REFERENCES `khach` (`id`) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE INDEX IF NOT EXISTS `fk_phong_loaiphong` ON `phong` (`loai_phong_id`);

CREATE INDEX IF NOT EXISTS `fk_booking_phong` ON `booking` (`phong_id`);

CREATE INDEX IF NOT EXISTS `fk_booking_khach` ON `booking` (`khach_id`);

CREATE INDEX IF NOT EXISTS `idx_booking_ngay` ON `booking` (`ngay_nhan`, `ngay_tra`);

CREATE INDEX IF NOT EXISTS `fk_dichvu_phong` ON `dichvu` (`phong_id`);

CREATE INDEX IF NOT EXISTS `fk_dichvu_booking` ON `dichvu` (`booking_id`);

CREATE INDEX IF NOT EXISTS `idx_phong_muacaodiem_season` ON `phong_muacaodiem` (`muacaodiem_id`);

CREATE INDEX IF NOT EXISTS `fk_pay_booking` ON `pay` (`booking_id`);

CREATE INDEX IF NOT EXISTS `fk_pay_khach` ON `pay` (`khach_id`);

CREATE INDEX IF NOT EXISTS `idx_sepay_payment_code` ON `sepay_webhook_events` (`payment_code`);

CREATE INDEX IF NOT EXISTS `idx_sepay_pay_id` ON `sepay_webhook_events` (`pay_id`);

CREATE INDEX IF NOT EXISTS `idx_sepay_result` ON `sepay_webhook_events` (`processing_result`);
PRAGMA foreign_keys = ON;
