-- ============================================================================
-- HOTEL MANAGEMENT: PEAK SURCHARGE BY PHYSICAL ROOM'S ROOM TYPE
-- Run AFTER Hotel_Peak_Season_NN_Migration.sql created phong_muacaodiem.
-- Adds 35% to the allowed rates, then applies the rate to EVERY physical room
-- based on phong.loai_phong_id -> loaiphong.ten.
-- This script is safe-update compatible and does not modify Booking snapshots.
-- ============================================================================
USE hotel_management_erd;
SET NAMES utf8mb4;
SET @OLD_SQL_SAFE_UPDATES = @@SQL_SAFE_UPDATES;
SET SQL_SAFE_UPDATES = 0;

-- Remove rate validators temporarily; run the updated Hotel_Trigger.sql
-- immediately after this patch to recreate them with 35% included.
DROP TRIGGER IF EXISTS trg_phong_muacaodiem_before_insert;
DROP TRIGGER IF EXISTS trg_phong_muacaodiem_before_update;

-- Remove rate validators temporarily; run the updated Hotel_Trigger.sql
-- immediately after this patch to recreate them with 35% included.
DROP TRIGGER IF EXISTS trg_phong_muacaodiem_before_insert;
DROP TRIGGER IF EXISTS trg_phong_muacaodiem_before_update;

-- Family uses 35%, so allow 0.35 in the junction-table constraint.
ALTER TABLE phong_muacaodiem
    DROP CHECK chk_pmd_he_so,
    ADD CONSTRAINT chk_pmd_he_so
      CHECK (he_so_phu_thu IN (0.10, 0.20, 0.25, 0.30, 0.35, 0.40, 0.50, 0.60));

START TRANSACTION;

-- Correct every existing link for the current 20/12/2026-31/12/2026 season
-- based on the room type assigned to each physical room.
UPDATE phong_muacaodiem pm
JOIN phong p ON p.id = pm.phong_id
JOIN loaiphong lp ON lp.id = p.loai_phong_id
JOIN muacaodiem m ON m.id = pm.muacaodiem_id
SET pm.he_so_phu_thu = CASE LOWER(TRIM(lp.ten))
    WHEN 'standard' THEN 0.20
    WHEN 'deluxe'   THEN 0.25
    WHEN 'vip'      THEN 0.30
    WHEN 'family'   THEN 0.35
    ELSE pm.he_so_phu_thu
END
WHERE m.tu_ngay = '2026-12-20'
  AND m.den_ngay = '2026-12-31'
  AND LOWER(TRIM(lp.ten)) IN ('standard', 'deluxe', 'vip', 'family');

-- Ensure ALL physical rooms are linked to this season. This adds missing
-- room links 501, 502, 601 as well as any other unlinked rooms.
INSERT INTO phong_muacaodiem (phong_id, muacaodiem_id, he_so_phu_thu)
SELECT p.id, m.id,
       CASE LOWER(TRIM(lp.ten))
           WHEN 'standard' THEN 0.20
           WHEN 'deluxe'   THEN 0.25
           WHEN 'vip'      THEN 0.30
           WHEN 'family'   THEN 0.35
       END
FROM muacaodiem m
CROSS JOIN phong p
JOIN loaiphong lp ON lp.id = p.loai_phong_id
LEFT JOIN phong_muacaodiem existing
       ON existing.phong_id = p.id AND existing.muacaodiem_id = m.id
WHERE m.tu_ngay = '2026-12-20'
  AND m.den_ngay = '2026-12-31'
  AND LOWER(TRIM(lp.ten)) IN ('standard', 'deluxe', 'vip', 'family')
  AND existing.phong_id IS NULL;

COMMIT;

SET SQL_SAFE_UPDATES = @OLD_SQL_SAFE_UPDATES;

-- Verify mapping by physical room and its assigned room type.
SELECT p.id AS phong_id, p.so_phong, lp.ten AS loai_phong,
       m.tu_ngay, m.den_ngay,
       CONCAT(ROUND(pm.he_so_phu_thu * 100), '%') AS phu_thu
FROM phong p
JOIN loaiphong lp ON lp.id = p.loai_phong_id
LEFT JOIN muacaodiem m
  ON m.tu_ngay = '2026-12-20' AND m.den_ngay = '2026-12-31'
LEFT JOIN phong_muacaodiem pm
  ON pm.phong_id = p.id AND pm.muacaodiem_id = m.id
ORDER BY p.id;
