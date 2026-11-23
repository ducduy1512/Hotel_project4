-- ============================================================================
-- HOTEL MANAGEMENT: MIGRATE PEAK SEASON FROM 1:N TO N:N
-- Target database: hotel_management_erd / MySQL 8.0.16+
-- IMPORTANT: BACK UP DATABASE FIRST. Stop Backend while running this migration.
-- This migration merges legacy rows with identical date ranges into one shared
-- MUACAODIEM row, preserving each room's rate in PHONG_MUACAODIEM.
-- It preserves Booking/Pay/Invoice JSON snapshots; historical totals are NOT
-- recalculated by this migration.
-- After this script, run Hotel_Procedures.sql, Hotel_Trigger.sql, Hotel_Report.sql.
-- ============================================================================
USE hotel_management_erd;
SET NAMES utf8mb4;

-- Preflight: stop if this is not the expected legacy schema.
SELECT COUNT(*) AS legacy_columns_found
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='muacaodiem'
  AND COLUMN_NAME IN ('id','phong_id','tu_ngay','den_ngay','he_so_gia');
-- Expected result: 5. If not 5, STOP and inspect the current schema.

-- Remove triggers and the reporting view that directly reference legacy columns before dropping them.
DROP VIEW IF EXISTS v_thong_ke_mua_cao_diem;
DROP TRIGGER IF EXISTS trg_booking_before_insert;
DROP TRIGGER IF EXISTS trg_booking_before_update;
DROP TRIGGER IF EXISTS trg_booking_peak_before_insert;
DROP TRIGGER IF EXISTS trg_booking_peak_before_update;
DROP TRIGGER IF EXISTS trg_muacaodiem_before_insert;
DROP TRIGGER IF EXISTS trg_muacaodiem_before_update;
DROP TRIGGER IF EXISTS trg_muacaodiem_after_insert;
DROP TRIGGER IF EXISTS trg_muacaodiem_after_update;
DROP TRIGGER IF EXISTS trg_muacaodiem_after_delete;
DROP TRIGGER IF EXISTS trg_phong_muacaodiem_before_insert;
DROP TRIGGER IF EXISTS trg_phong_muacaodiem_before_update;

-- Map each old room-specific season row to the lowest-ID shared season with
-- the same date range. This consolidates identical date windows into one row.
DROP TEMPORARY TABLE IF EXISTS tmp_peak_season_map;
CREATE TEMPORARY TABLE tmp_peak_season_map AS
SELECT old_row.id AS old_id,
       MIN(same_range.id) AS new_id,
       old_row.phong_id,
       old_row.he_so_gia,
       old_row.tu_ngay,
       old_row.den_ngay
FROM muacaodiem old_row
JOIN muacaodiem same_range
  ON same_range.tu_ngay=old_row.tu_ngay
 AND same_range.den_ngay=old_row.den_ngay
GROUP BY old_row.id, old_row.phong_id, old_row.he_so_gia,
         old_row.tu_ngay, old_row.den_ngay;

CREATE TABLE IF NOT EXISTS phong_muacaodiem (
  phong_id INT NOT NULL,
  muacaodiem_id INT NOT NULL,
  he_so_phu_thu DECIMAL(4,2) NOT NULL,
  PRIMARY KEY (phong_id, muacaodiem_id),
  KEY idx_phong_muacaodiem_season (muacaodiem_id),
  CONSTRAINT fk_pmd_phong FOREIGN KEY (phong_id)
    REFERENCES phong(id) ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT fk_pmd_muacaodiem FOREIGN KEY (muacaodiem_id)
    REFERENCES muacaodiem(id) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT chk_pmd_he_so CHECK (he_so_phu_thu IN (0.10,0.20,0.25,0.30,0.35,0.40,0.50,0.60))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Preserve legacy room/rate assignments. Duplicate exact pairs are ignored.
INSERT IGNORE INTO phong_muacaodiem (phong_id,muacaodiem_id,he_so_phu_thu)
SELECT phong_id,new_id,he_so_gia FROM tmp_peak_season_map;

-- Consolidate same-date duplicate season rows. Existing snapshots are JSON and
-- remain unchanged; new Bookings use the canonical shared season ID.
DELETE m FROM muacaodiem m
JOIN tmp_peak_season_map x ON x.old_id=m.id
WHERE x.old_id<>x.new_id;

-- Remove old 1:N FK/index/check/columns. The junction table is now authoritative.
ALTER TABLE muacaodiem
  DROP FOREIGN KEY fk_muacaodiem_phong,
  DROP CHECK chk_he_so_gia,
  DROP INDEX fk_muacaodiem_phong,
  DROP COLUMN phong_id,
  DROP COLUMN he_so_gia;

-- Rates are assigned to EACH PHYSICAL ROOM using its room type:
-- Standard=20%, Deluxe=25%, VIP=30%, Family=35%.
-- This updates existing links and creates missing links for every room.
SET @OLD_SQL_SAFE_UPDATES = @@SQL_SAFE_UPDATES;
SET SQL_SAFE_UPDATES = 0;
UPDATE phong_muacaodiem pm
JOIN phong p ON p.id=pm.phong_id
JOIN loaiphong lp ON lp.id=p.loai_phong_id
JOIN muacaodiem m ON m.id=pm.muacaodiem_id
SET pm.he_so_phu_thu = CASE LOWER(TRIM(lp.ten))
  WHEN 'standard' THEN 0.20
  WHEN 'deluxe' THEN 0.25
  WHEN 'vip' THEN 0.30
  WHEN 'family' THEN 0.35
  ELSE pm.he_so_phu_thu END
WHERE m.tu_ngay='2026-12-20' AND m.den_ngay='2026-12-31'
  AND LOWER(TRIM(lp.ten)) IN ('standard','deluxe','vip','family');

INSERT IGNORE INTO phong_muacaodiem (phong_id,muacaodiem_id,he_so_phu_thu)
SELECT p.id,m.id,
       CASE LOWER(TRIM(lp.ten))
         WHEN 'standard' THEN 0.20
         WHEN 'deluxe' THEN 0.25
         WHEN 'vip' THEN 0.30
         WHEN 'family' THEN 0.35
       END
FROM muacaodiem m
CROSS JOIN phong p
JOIN loaiphong lp ON lp.id=p.loai_phong_id
WHERE m.tu_ngay='2026-12-20' AND m.den_ngay='2026-12-31'
  AND LOWER(TRIM(lp.ten)) IN ('standard','deluxe','vip','family');
SET SQL_SAFE_UPDATES = @OLD_SQL_SAFE_UPDATES;

DROP TEMPORARY TABLE IF EXISTS tmp_peak_season_map;

-- Verification: should return 11 links for the confirmed season if the database has 11 rooms.
SELECT m.id AS mua_cao_diem_id,m.tu_ngay,m.den_ngay,
       p.id AS phong_id,p.so_phong,pm.he_so_phu_thu
FROM muacaodiem m
JOIN phong_muacaodiem pm ON pm.muacaodiem_id=m.id
JOIN phong p ON p.id=pm.phong_id
ORDER BY m.tu_ngay,p.so_phong;

-- Next, execute these scripts in MySQL Workbench, in this order:
-- 1. Hotel_Procedures.sql
-- 2. Hotel_Trigger.sql
-- 3. Hotel_Report.sql
