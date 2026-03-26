-- =============================================
-- 002_kitchen.sql - Kitchen Warehouse Schema
-- =============================================

-- Nguyên vật liệu (ingredient catalog)
CREATE TABLE IF NOT EXISTS materials (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    unit VARCHAR(50) NOT NULL COMMENT 'kg, g, lít, ml, cái, hộp, bao, bó, quả',
    min_stock FLOAT DEFAULT 0 COMMENT 'Ngưỡng cảnh báo hết hàng',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tồn kho hiện tại
CREATE TABLE IF NOT EXISTS inventory (
    id INT AUTO_INCREMENT PRIMARY KEY,
    material_id INT NOT NULL,
    quantity FLOAT DEFAULT 0,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE CASCADE,
    UNIQUE KEY uq_material (material_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Phiếu nhập kho
CREATE TABLE IF NOT EXISTS import_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    supplier_name VARCHAR(200) DEFAULT NULL COMMENT 'Tên người/bộ phận bàn giao',
    notes TEXT DEFAULT NULL,
    image_url VARCHAR(500) DEFAULT NULL COMMENT 'Ảnh hoá đơn',
    created_by VARCHAR(100) DEFAULT 'Nhân viên kho',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Chi tiết phiếu nhập
CREATE TABLE IF NOT EXISTS import_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    import_record_id INT NOT NULL,
    material_id INT NOT NULL,
    quantity FLOAT NOT NULL,
    unit VARCHAR(50) NOT NULL,
    FOREIGN KEY (import_record_id) REFERENCES import_records(id) ON DELETE CASCADE,
    FOREIGN KEY (material_id) REFERENCES materials(id),
    INDEX idx_import_record (import_record_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Món ăn
CREATE TABLE IF NOT EXISTS dishes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(100) DEFAULT NULL,
    is_available TINYINT(1) DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Công thức món ăn
CREATE TABLE IF NOT EXISTS recipe_ingredients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    dish_id INT NOT NULL,
    material_id INT NOT NULL,
    quantity_required FLOAT NOT NULL COMMENT 'Lượng cần cho 1 phần',
    unit VARCHAR(50) NOT NULL,
    FOREIGN KEY (dish_id) REFERENCES dishes(id) ON DELETE CASCADE,
    FOREIGN KEY (material_id) REFERENCES materials(id),
    UNIQUE KEY uq_dish_material (dish_id, material_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================
-- Seed Data: Nguyên vật liệu phổ biến
-- =============================================
INSERT INTO materials (name, unit, min_stock) VALUES
('Thịt bò', 'kg', 2.0),
('Thịt heo', 'kg', 3.0),
('Thịt gà', 'kg', 2.0),
('Tôm', 'kg', 1.0),
('Cá', 'kg', 1.5),
('Mực', 'kg', 1.0),
('Trứng gà', 'quả', 20),
('Gạo', 'kg', 10.0),
('Bún', 'kg', 3.0),
('Bánh phở', 'kg', 3.0),
('Hành lá', 'bó', 5),
('Hành tây', 'kg', 1.0),
('Tỏi', 'kg', 0.5),
('Gừng', 'kg', 0.3),
('Ớt', 'kg', 0.2),
('Cà chua', 'kg', 1.0),
('Rau cải', 'bó', 10),
('Giá đỗ', 'kg', 1.0),
('Dầu ăn', 'lít', 2.0),
('Nước mắm', 'lít', 1.0),
('Muối', 'kg', 1.0),
('Đường', 'kg', 1.0),
('Tiêu', 'kg', 0.2),
('Mì chính', 'kg', 0.3)
ON DUPLICATE KEY UPDATE name=name;

-- Tồn kho ban đầu
INSERT INTO inventory (material_id, quantity)
SELECT id, CASE
    WHEN name = 'Thịt bò' THEN 5.0
    WHEN name = 'Thịt heo' THEN 8.0
    WHEN name = 'Thịt gà' THEN 4.0
    WHEN name = 'Tôm' THEN 2.0
    WHEN name = 'Cá' THEN 3.0
    WHEN name = 'Mực' THEN 1.5
    WHEN name = 'Trứng gà' THEN 30
    WHEN name = 'Gạo' THEN 20.0
    WHEN name = 'Bún' THEN 5.0
    WHEN name = 'Bánh phở' THEN 6.0
    WHEN name = 'Hành lá' THEN 8
    WHEN name = 'Hành tây' THEN 2.0
    WHEN name = 'Tỏi' THEN 1.0
    WHEN name = 'Gừng' THEN 0.5
    WHEN name = 'Ớt' THEN 0.3
    WHEN name = 'Cà chua' THEN 2.0
    WHEN name = 'Rau cải' THEN 12
    WHEN name = 'Giá đỗ' THEN 2.0
    WHEN name = 'Dầu ăn' THEN 3.0
    WHEN name = 'Nước mắm' THEN 2.0
    WHEN name = 'Muối' THEN 2.0
    WHEN name = 'Đường' THEN 2.0
    WHEN name = 'Tiêu' THEN 0.5
    WHEN name = 'Mì chính' THEN 0.5
    ELSE 0
END
FROM materials
ON DUPLICATE KEY UPDATE quantity=quantity;

-- =============================================
-- Seed Data: Món ăn và công thức
-- =============================================
INSERT INTO dishes (name, category) VALUES
('Phở bò', 'Phở'),
('Phở gà', 'Phở'),
('Bún bò Huế', 'Bún'),
('Bún riêu', 'Bún'),
('Cơm sườn', 'Cơm'),
('Cơm gà', 'Cơm'),
('Cơm tấm', 'Cơm'),
('Cơm rang dưa bò', 'Cơm'),
('Lẩu hải sản', 'Lẩu'),
('Lẩu gà', 'Lẩu')
ON DUPLICATE KEY UPDATE name=name;

-- Công thức (lượng cho 1 phần)
-- Phở bò
INSERT INTO recipe_ingredients (dish_id, material_id, quantity_required, unit)
SELECT d.id, m.id,
    CASE m.name
        WHEN 'Bánh phở' THEN 0.2
        WHEN 'Thịt bò' THEN 0.15
        WHEN 'Hành lá' THEN 0.1
        WHEN 'Hành tây' THEN 0.05
        WHEN 'Gừng' THEN 0.02
    END,
    m.unit
FROM dishes d, materials m
WHERE d.name = 'Phở bò'
  AND m.name IN ('Bánh phở', 'Thịt bò', 'Hành lá', 'Hành tây', 'Gừng')
ON DUPLICATE KEY UPDATE quantity_required=VALUES(quantity_required);

-- Phở gà
INSERT INTO recipe_ingredients (dish_id, material_id, quantity_required, unit)
SELECT d.id, m.id,
    CASE m.name
        WHEN 'Bánh phở' THEN 0.2
        WHEN 'Thịt gà' THEN 0.15
        WHEN 'Hành lá' THEN 0.1
        WHEN 'Gừng' THEN 0.02
    END,
    m.unit
FROM dishes d, materials m
WHERE d.name = 'Phở gà'
  AND m.name IN ('Bánh phở', 'Thịt gà', 'Hành lá', 'Gừng')
ON DUPLICATE KEY UPDATE quantity_required=VALUES(quantity_required);

-- Bún bò Huế
INSERT INTO recipe_ingredients (dish_id, material_id, quantity_required, unit)
SELECT d.id, m.id,
    CASE m.name
        WHEN 'Bún' THEN 0.2
        WHEN 'Thịt bò' THEN 0.15
        WHEN 'Hành tây' THEN 0.05
        WHEN 'Ớt' THEN 0.02
    END,
    m.unit
FROM dishes d, materials m
WHERE d.name = 'Bún bò Huế'
  AND m.name IN ('Bún', 'Thịt bò', 'Hành tây', 'Ớt')
ON DUPLICATE KEY UPDATE quantity_required=VALUES(quantity_required);

-- Bún riêu
INSERT INTO recipe_ingredients (dish_id, material_id, quantity_required, unit)
SELECT d.id, m.id,
    CASE m.name
        WHEN 'Bún' THEN 0.2
        WHEN 'Cà chua' THEN 0.1
        WHEN 'Trứng gà' THEN 1
    END,
    m.unit
FROM dishes d, materials m
WHERE d.name = 'Bún riêu'
  AND m.name IN ('Bún', 'Cà chua', 'Trứng gà')
ON DUPLICATE KEY UPDATE quantity_required=VALUES(quantity_required);

-- Cơm sườn
INSERT INTO recipe_ingredients (dish_id, material_id, quantity_required, unit)
SELECT d.id, m.id,
    CASE m.name
        WHEN 'Gạo' THEN 0.2
        WHEN 'Thịt heo' THEN 0.15
    END,
    m.unit
FROM dishes d, materials m
WHERE d.name = 'Cơm sườn'
  AND m.name IN ('Gạo', 'Thịt heo')
ON DUPLICATE KEY UPDATE quantity_required=VALUES(quantity_required);

-- Cơm gà
INSERT INTO recipe_ingredients (dish_id, material_id, quantity_required, unit)
SELECT d.id, m.id,
    CASE m.name
        WHEN 'Gạo' THEN 0.2
        WHEN 'Thịt gà' THEN 0.15
    END,
    m.unit
FROM dishes d, materials m
WHERE d.name = 'Cơm gà'
  AND m.name IN ('Gạo', 'Thịt gà')
ON DUPLICATE KEY UPDATE quantity_required=VALUES(quantity_required);

-- Cơm tấm
INSERT INTO recipe_ingredients (dish_id, material_id, quantity_required, unit)
SELECT d.id, m.id,
    CASE m.name
        WHEN 'Gạo' THEN 0.2
        WHEN 'Thịt heo' THEN 0.12
        WHEN 'Trứng gà' THEN 1
    END,
    m.unit
FROM dishes d, materials m
WHERE d.name = 'Cơm tấm'
  AND m.name IN ('Gạo', 'Thịt heo', 'Trứng gà')
ON DUPLICATE KEY UPDATE quantity_required=VALUES(quantity_required);

-- Cơm rang dưa bò
INSERT INTO recipe_ingredients (dish_id, material_id, quantity_required, unit)
SELECT d.id, m.id,
    CASE m.name
        WHEN 'Gạo' THEN 0.2
        WHEN 'Thịt bò' THEN 0.1
        WHEN 'Trứng gà' THEN 1
        WHEN 'Dầu ăn' THEN 0.05
    END,
    m.unit
FROM dishes d, materials m
WHERE d.name = 'Cơm rang dưa bò'
  AND m.name IN ('Gạo', 'Thịt bò', 'Trứng gà', 'Dầu ăn')
ON DUPLICATE KEY UPDATE quantity_required=VALUES(quantity_required);

-- Lẩu hải sản
INSERT INTO recipe_ingredients (dish_id, material_id, quantity_required, unit)
SELECT d.id, m.id,
    CASE m.name
        WHEN 'Tôm' THEN 0.2
        WHEN 'Mực' THEN 0.15
        WHEN 'Cá' THEN 0.15
        WHEN 'Rau cải' THEN 0.2
        WHEN 'Giá đỗ' THEN 0.1
    END,
    m.unit
FROM dishes d, materials m
WHERE d.name = 'Lẩu hải sản'
  AND m.name IN ('Tôm', 'Mực', 'Cá', 'Rau cải', 'Giá đỗ')
ON DUPLICATE KEY UPDATE quantity_required=VALUES(quantity_required);

-- Lẩu gà
INSERT INTO recipe_ingredients (dish_id, material_id, quantity_required, unit)
SELECT d.id, m.id,
    CASE m.name
        WHEN 'Thịt gà' THEN 0.3
        WHEN 'Rau cải' THEN 0.2
        WHEN 'Giá đỗ' THEN 0.1
        WHEN 'Gừng' THEN 0.03
    END,
    m.unit
FROM dishes d, materials m
WHERE d.name = 'Lẩu gà'
  AND m.name IN ('Thịt gà', 'Rau cải', 'Giá đỗ', 'Gừng')
ON DUPLICATE KEY UPDATE quantity_required=VALUES(quantity_required);

-- Track migration
INSERT INTO schema_migrations (version) VALUES ('002_kitchen') ON DUPLICATE KEY UPDATE version=version;
