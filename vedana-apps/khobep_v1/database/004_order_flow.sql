-- 004_order_flow.sql
-- Extend orders table for kitchen workflow

-- Update status enum: add 'completed' and 'rejected', remove 'cancelled'
ALTER TABLE orders
  MODIFY COLUMN status ENUM('pending', 'confirmed', 'completed', 'rejected') DEFAULT 'pending';

-- Add workflow columns
ALTER TABLE orders
  ADD COLUMN reject_reason TEXT NULL AFTER notes,
  ADD COLUMN confirmed_at DATETIME NULL AFTER reject_reason,
  ADD COLUMN completed_at DATETIME NULL AFTER confirmed_at;

-- Migrate any existing 'cancelled' orders to 'rejected'
UPDATE orders SET status = 'rejected' WHERE status = 'cancelled';

-- Track migration
INSERT INTO schema_migrations (version, applied_at)
VALUES ('004_order_flow', NOW());
