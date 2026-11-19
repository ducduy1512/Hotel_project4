-- HOTEL MANAGEMENT: QR PAYMENT / SEPAY ADDITIVE MIGRATION
-- Run this once on the existing hotel_management_erd database.
-- This migration does not DROP or modify existing booking/payment data.

USE `hotel_management_erd`;

CREATE TABLE IF NOT EXISTS `payment_qr` (
  `pay_id` INT NOT NULL,
  `payment_code` VARCHAR(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `sepay_transaction_id` VARCHAR(80) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sepay_reference_code` VARCHAR(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `received_amount` DECIMAL(12,2) DEFAULT NULL,
  `received_account_number` VARCHAR(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `received_at` DATETIME DEFAULT NULL,
  PRIMARY KEY (`pay_id`),
  UNIQUE KEY `uq_payment_qr_code` (`payment_code`),
  UNIQUE KEY `uq_payment_qr_sepay_transaction` (`sepay_transaction_id`),
  CONSTRAINT `fk_payment_qr_pay` FOREIGN KEY (`pay_id`) REFERENCES `pay` (`id`)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `chk_payment_qr_amount` CHECK (`received_amount` IS NULL OR `received_amount` >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `sepay_webhook_events` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `transaction_id` VARCHAR(80) COLLATE utf8mb4_unicode_ci NOT NULL,
  `gateway` VARCHAR(60) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `account_number` VARCHAR(64) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `payment_code` VARCHAR(32) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `transfer_type` VARCHAR(16) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `transfer_amount` DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  `reference_code` VARCHAR(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `transaction_date` VARCHAR(40) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `pay_id` INT DEFAULT NULL,
  `processing_result` VARCHAR(40) COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'RECEIVED',
  `raw_payload` JSON NOT NULL,
  `received_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `processed_at` DATETIME DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_sepay_transaction_id` (`transaction_id`),
  KEY `idx_sepay_payment_code` (`payment_code`),
  KEY `idx_sepay_pay_id` (`pay_id`),
  KEY `idx_sepay_result` (`processing_result`),
  CONSTRAINT `fk_sepay_event_pay` FOREIGN KEY (`pay_id`) REFERENCES `pay` (`id`)
    ON DELETE SET NULL ON UPDATE CASCADE,
  CONSTRAINT `chk_sepay_transfer_amount` CHECK (`transfer_amount` >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SELECT 'QR payment migration completed' AS result;
SHOW TABLES LIKE 'payment_qr';
SHOW TABLES LIKE 'sepay_webhook_events';
