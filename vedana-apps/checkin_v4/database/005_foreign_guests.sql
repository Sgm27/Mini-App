ALTER TABLE guests
  ADD COLUMN guest_type VARCHAR(20) NOT NULL DEFAULT 'vietnamese',
  ADD COLUMN passport_number VARCHAR(50) DEFAULT NULL,
  ADD COLUMN nationality_code VARCHAR(10) DEFAULT NULL;

ALTER TABLE guests MODIFY identification_number VARCHAR(50) NULL;

ALTER TABLE guests DROP INDEX uq_guest_per_checkin;
ALTER TABLE guests
  ADD UNIQUE INDEX uq_vn_guest (checkin_id, identification_number),
  ADD UNIQUE INDEX uq_foreign_guest (checkin_id, passport_number);

INSERT IGNORE INTO schema_migrations (version) VALUES ('005_foreign_guests');
