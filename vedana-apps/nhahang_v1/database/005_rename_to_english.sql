-- Migration: Rename all Vietnamese table and column names to English
-- Date: 2026-03-26

SET FOREIGN_KEY_CHECKS = 0;

-- ============================================================
-- 1. Convert enum values in don_hang.trang_thai
-- ============================================================
ALTER TABLE don_hang MODIFY COLUMN trang_thai VARCHAR(50) DEFAULT 'pending';
UPDATE don_hang SET trang_thai = 'pending' WHERE trang_thai = 'cho_xac_nhan';
UPDATE don_hang SET trang_thai = 'confirmed' WHERE trang_thai = 'da_xac_nhan';
UPDATE don_hang SET trang_thai = 'cancelled' WHERE trang_thai = 'da_huy';
ALTER TABLE don_hang MODIFY COLUMN trang_thai ENUM('pending', 'confirmed', 'cancelled') DEFAULT 'pending';

-- ============================================================
-- 2. Rename columns in each table
-- ============================================================

-- danh_muc_mon
ALTER TABLE danh_muc_mon
    RENAME COLUMN ten_danh_muc TO name,
    RENAME COLUMN thu_tu TO sort_order;

-- mon_an
ALTER TABLE mon_an
    RENAME COLUMN ten_mon TO name,
    RENAME COLUMN gia TO price,
    RENAME COLUMN hinh_anh TO image,
    RENAME COLUMN mo_ta TO description,
    RENAME COLUMN danh_muc_id TO category_id;

-- nguyen_lieu
ALTER TABLE nguyen_lieu
    RENAME COLUMN ten_nguyen_lieu TO name,
    RENAME COLUMN don_vi TO unit,
    RENAME COLUMN so_luong_ton TO stock_quantity,
    RENAME COLUMN nguong_canh_bao TO warning_threshold;

-- cong_thuc_mon
ALTER TABLE cong_thuc_mon
    RENAME COLUMN mon_an_id TO dish_id,
    RENAME COLUMN nguyen_lieu_id TO ingredient_id,
    RENAME COLUMN so_luong_can TO required_quantity;

-- don_hang
ALTER TABLE don_hang
    RENAME COLUMN ma_ban TO table_number,
    RENAME COLUMN trang_thai TO status,
    RENAME COLUMN tong_tien TO total_amount,
    RENAME COLUMN ghi_chu TO notes;

-- chi_tiet_don_hang
ALTER TABLE chi_tiet_don_hang
    RENAME COLUMN don_hang_id TO order_id,
    RENAME COLUMN mon_an_id TO dish_id,
    RENAME COLUMN so_luong TO quantity,
    RENAME COLUMN don_gia TO unit_price;

-- phieu_nhap_kho
ALTER TABLE phieu_nhap_kho
    RENAME COLUMN nha_cung_cap TO supplier,
    RENAME COLUMN ghi_chu TO notes,
    RENAME COLUMN hinh_anh_url TO image_url,
    RENAME COLUMN nguoi_nhap TO received_by;

-- chi_tiet_nhap_kho
ALTER TABLE chi_tiet_nhap_kho
    RENAME COLUMN phieu_nhap_id TO import_receipt_id,
    RENAME COLUMN nguyen_lieu_id TO ingredient_id,
    RENAME COLUMN so_luong TO quantity,
    RENAME COLUMN don_vi TO unit;

-- ============================================================
-- 3. Drop old constraints before renaming tables
-- ============================================================

-- mon_an
ALTER TABLE mon_an DROP FOREIGN KEY mon_an_ibfk_1;

-- cong_thuc_mon
ALTER TABLE cong_thuc_mon DROP INDEX uq_mon_nguyen_lieu;
ALTER TABLE cong_thuc_mon DROP FOREIGN KEY cong_thuc_mon_ibfk_1;
ALTER TABLE cong_thuc_mon DROP FOREIGN KEY cong_thuc_mon_ibfk_2;

-- don_hang (no FKs)

-- chi_tiet_don_hang
ALTER TABLE chi_tiet_don_hang DROP FOREIGN KEY chi_tiet_don_hang_ibfk_1;
ALTER TABLE chi_tiet_don_hang DROP FOREIGN KEY chi_tiet_don_hang_ibfk_2;

-- chi_tiet_nhap_kho
ALTER TABLE chi_tiet_nhap_kho DROP FOREIGN KEY chi_tiet_nhap_kho_ibfk_1;
ALTER TABLE chi_tiet_nhap_kho DROP FOREIGN KEY chi_tiet_nhap_kho_ibfk_2;

-- ============================================================
-- 4. Rename tables
-- ============================================================
RENAME TABLE danh_muc_mon TO dish_categories;
RENAME TABLE mon_an TO dishes;
RENAME TABLE nguyen_lieu TO ingredients;
RENAME TABLE cong_thuc_mon TO recipes;
RENAME TABLE don_hang TO orders;
RENAME TABLE chi_tiet_don_hang TO order_items;
RENAME TABLE phieu_nhap_kho TO import_receipts;
RENAME TABLE chi_tiet_nhap_kho TO import_receipt_items;

-- ============================================================
-- 5. Re-create foreign keys with English names
-- ============================================================

-- dishes.category_id -> dish_categories.id
ALTER TABLE dishes
    ADD CONSTRAINT fk_dishes_category
    FOREIGN KEY (category_id) REFERENCES dish_categories(id) ON DELETE CASCADE;

-- recipes.dish_id -> dishes.id
-- recipes.ingredient_id -> ingredients.id
ALTER TABLE recipes
    ADD UNIQUE KEY uq_dish_ingredient (dish_id, ingredient_id),
    ADD CONSTRAINT fk_recipes_dish
    FOREIGN KEY (dish_id) REFERENCES dishes(id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_recipes_ingredient
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE;

-- order_items.order_id -> orders.id
-- order_items.dish_id -> dishes.id
ALTER TABLE order_items
    ADD CONSTRAINT fk_order_items_order
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_order_items_dish
    FOREIGN KEY (dish_id) REFERENCES dishes(id);

-- import_receipt_items.import_receipt_id -> import_receipts.id
-- import_receipt_items.ingredient_id -> ingredients.id
ALTER TABLE import_receipt_items
    ADD CONSTRAINT fk_import_receipt_items_receipt
    FOREIGN KEY (import_receipt_id) REFERENCES import_receipts(id) ON DELETE CASCADE,
    ADD CONSTRAINT fk_import_receipt_items_ingredient
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE RESTRICT;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================================
-- 6. Record migration
-- ============================================================
INSERT INTO schema_migrations (version) VALUES ('005_rename_to_english');
