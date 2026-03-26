-- 004_nhap_kho.sql: Add warehouse import tables + expand ingredients for khobep integration

-- Import receipt header
CREATE TABLE IF NOT EXISTS phieu_nhap_kho (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nha_cung_cap VARCHAR(200) DEFAULT NULL COMMENT 'Tên nhà cung cấp/người giao',
  ghi_chu TEXT DEFAULT NULL,
  hinh_anh_url VARCHAR(500) DEFAULT NULL COMMENT 'Ảnh hoá đơn',
  nguoi_nhap VARCHAR(100) DEFAULT 'Nhan vien kho',
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Import receipt line items
CREATE TABLE IF NOT EXISTS chi_tiet_nhap_kho (
  id INT AUTO_INCREMENT PRIMARY KEY,
  phieu_nhap_id INT NOT NULL,
  nguyen_lieu_id INT NOT NULL,
  so_luong DECIMAL(10,3) NOT NULL,
  don_vi VARCHAR(50) NOT NULL,
  FOREIGN KEY (phieu_nhap_id) REFERENCES phieu_nhap_kho(id) ON DELETE CASCADE,
  FOREIGN KEY (nguyen_lieu_id) REFERENCES nguyen_lieu(id) ON DELETE RESTRICT,
  INDEX idx_phieu_nhap (phieu_nhap_id),
  INDEX idx_nguyen_lieu (nguyen_lieu_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Expand nguyen_lieu with common kitchen ingredients missing from nhahang seed data
-- (needed for khobep OCR matching)
INSERT IGNORE INTO nguyen_lieu (ten_nguyen_lieu, don_vi, so_luong_ton, nguong_canh_bao) VALUES
  ('Mực',         'kg',   1.500, 1.0),
  ('Giá đỗ',      'kg',   2.000, 1.0),
  ('Dầu ăn',      'lít',  3.000, 2.0),
  ('Nước mắm',    'lít',  2.000, 1.0),
  ('Muối',         'kg',   2.000, 1.0),
  ('Đường',        'kg',   2.000, 1.0),
  ('Tiêu',         'kg',   0.500, 0.2),
  ('Mì chính',    'kg',   0.500, 0.3),
  ('Hành lá',      'bó',   8.000, 5.0),
  ('Hành tây',     'kg',   2.000, 1.0),
  ('Tỏi',          'kg',   1.000, 0.5),
  ('Gừng',         'kg',   0.500, 0.3),
  ('Ớt',           'kg',   0.300, 0.2),
  ('Cà chua',      'kg',   2.000, 1.0),
  ('Rau cải',      'bó',  12.000, 5.0);

INSERT IGNORE INTO schema_migrations (version) VALUES ('004_nhap_kho');
