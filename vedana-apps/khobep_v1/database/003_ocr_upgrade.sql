-- 003_ocr_upgrade.sql
-- Add Vedana receiving note fields to import tables

ALTER TABLE import_receipts
  ADD COLUMN receipt_date DATE NULL,
  ADD COLUMN description VARCHAR(500) NULL,
  ADD COLUMN vendor_name VARCHAR(300) NULL,
  ADD COLUMN period VARCHAR(20) NULL,
  ADD COLUMN voucher_no VARCHAR(50) NULL,
  ADD COLUMN invoice_serial VARCHAR(50) NULL,
  ADD COLUMN invoice_no VARCHAR(50) NULL;

ALTER TABLE import_receipt_items
  ADD COLUMN item_code VARCHAR(50) NULL,
  ADD COLUMN item_name VARCHAR(200) NULL,
  ADD COLUMN unit_price DECIMAL(12,2) NULL,
  ADD COLUMN amount DECIMAL(15,2) NULL,
  ADD COLUMN location VARCHAR(50) NULL,
  ADD COLUMN acc_no VARCHAR(50) NULL;

-- schema_migrations table only has (version, applied_at) columns
INSERT INTO schema_migrations (version) VALUES ('003');
