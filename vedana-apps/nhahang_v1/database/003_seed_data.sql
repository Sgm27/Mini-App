-- 003_seed_data.sql: Seed data for restaurant app

-- Categories
INSERT IGNORE INTO danh_muc_mon (id, ten_danh_muc, thu_tu, icon) VALUES
  (1, 'Khai vị', 1, '🥗'),
  (2, 'Món chính', 2, '🍲'),
  (3, 'Tráng miệng', 3, '🍮'),
  (4, 'Đồ uống', 4, '🥤');

-- Dishes
INSERT IGNORE INTO mon_an (id, ten_mon, gia, mo_ta, danh_muc_id, active) VALUES
  -- Khai vị
  (1,  'Gỏi cuốn tôm thịt',    35000, 'Gỏi cuốn tươi nhân tôm, thịt heo, bún, rau sống',     1, 1),
  (2,  'Chả giò hải sản',       40000, 'Chả giò giòn rụm nhân hải sản thơm ngon',               1, 1),
  (3,  'Súp cua bắp',           45000, 'Súp cua thơm ngọt với bắp non và trứng gà',             1, 1),
  (4,  'Gỏi xoài tôm',          38000, 'Gỏi xoài chua ngọt kết hợp tôm tươi giòn',              1, 1),

  -- Món chính
  (5,  'Phở bò tái',            65000, 'Phở bò tái thơm ngon với nước dùng hầm xương',           2, 1),
  (6,  'Bún bò Huế',            60000, 'Bún bò Huế đặc trưng cay thơm đúng vị xứ Huế',          2, 1),
  (7,  'Cơm chiên hải sản',     75000, 'Cơm chiên hải sản tươi ngon, ăn liền',                  2, 1),
  (8,  'Gà nướng mật ong',     120000, 'Gà nướng vàng óng, thấm mật ong thơm lừng',              2, 1),
  (9,  'Cá kho tộ',             95000, 'Cá basa kho tộ đậm đà, ăn với cơm trắng',                2, 1),
  (10, 'Bò lúc lắc',           150000, 'Bò lúc lắc sốt tiêu xanh, khoai tây chiên',              2, 1),

  -- Tráng miệng
  (11, 'Chè ba màu',            25000, 'Chè ba màu mát lạnh với đậu xanh, đậu đỏ, thạch',       3, 1),
  (12, 'Bánh flan',             20000, 'Bánh flan mềm mịn, thơm ngậy béo',                       3, 1),
  (13, 'Kem 3 vị',              25000, 'Kem vani, dâu, sô cô la mát lạnh',                        3, 1),

  -- Đồ uống
  (14, 'Trà đá',                10000, 'Trà đá mát lạnh miễn phí tiếp',                          4, 1),
  (15, 'Nước ngọt lon',         15000, 'Coca Cola, Pepsi, 7Up lạnh',                             4, 1),
  (16, 'Sinh tố xoài',          35000, 'Sinh tố xoài tươi xay mịn, thêm sữa',                   4, 1),
  (17, 'Cà phê sữa đá',         25000, 'Cà phê phin truyền thống, sữa đặc béo ngậy',             4, 1),
  (18, 'Nước ép cam',           30000, 'Cam vắt tươi nguyên chất, ngọt tự nhiên',                4, 1);

-- Ingredients (nguyen_lieu)
INSERT IGNORE INTO nguyen_lieu (id, ten_nguyen_lieu, don_vi, so_luong_ton, nguong_canh_bao) VALUES
  (1,  'Tôm tươi',           'kg',   5.000,  1.0),
  (2,  'Thịt heo',           'kg',   8.000,  2.0),
  (3,  'Bánh tráng',         'tờ',  60.000, 10.0),
  (4,  'Rau sống',           'kg',   3.000,  0.5),
  (5,  'Bún',                'kg',  10.000,  2.0),
  (6,  'Thịt bò',            'kg',   6.000,  1.5),
  (7,  'Bánh phở',           'kg',   8.000,  2.0),
  (8,  'Gạo tẻ',             'kg',  15.000,  3.0),
  (9,  'Hải sản hỗn hợp',   'kg',   4.000,  1.0),
  (10, 'Thịt gà',            'kg',  10.000,  2.0),
  (11, 'Mật ong',            'chai', 3.000,  0.5),
  (12, 'Cá basa',            'kg',   5.000,  1.0),
  (13, 'Bắp ngô',            'cái', 15.000,  3.0),
  (14, 'Xoài chín',          'kg',   4.000,  1.0),
  (15, 'Sữa đặc',            'hộp',  8.000,  2.0),
  (16, 'Cà phê',             'gói', 10.000,  2.0),
  (17, 'Trứng gà',           'quả', 20.000,  5.0),
  (18, 'Cam tươi',           'kg',   5.000,  1.0);

-- Recipes (cong_thuc_mon): amount per 1 serving
INSERT IGNORE INTO cong_thuc_mon (mon_an_id, nguyen_lieu_id, so_luong_can) VALUES
  -- 1. Gỏi cuốn tôm thịt
  (1, 1,  0.100),  -- Tôm 100g
  (1, 2,  0.050),  -- Thịt heo 50g
  (1, 3,  3.000),  -- Bánh tráng 3 tờ
  (1, 4,  0.050),  -- Rau sống 50g

  -- 2. Chả giò hải sản
  (2, 9,  0.100),  -- Hải sản 100g
  (2, 3,  2.000),  -- Bánh tráng 2 tờ
  (2, 4,  0.030),  -- Rau sống 30g

  -- 3. Súp cua bắp
  (3, 9,  0.100),  -- Hải sản 100g
  (3, 13, 1.000),  -- Bắp ngô 1 cái
  (3, 17, 1.000),  -- Trứng gà 1 quả
  (3, 4,  0.020),  -- Rau sống 20g

  -- 4. Gỏi xoài tôm
  (4, 1,  0.100),  -- Tôm 100g
  (4, 14, 0.150),  -- Xoài 150g
  (4, 4,  0.050),  -- Rau sống 50g

  -- 5. Phở bò tái
  (5, 6,  0.150),  -- Thịt bò 150g
  (5, 7,  0.200),  -- Bánh phở 200g
  (5, 4,  0.050),  -- Rau sống 50g

  -- 6. Bún bò Huế
  (6, 6,  0.120),  -- Thịt bò 120g
  (6, 5,  0.200),  -- Bún 200g
  (6, 4,  0.050),  -- Rau sống 50g

  -- 7. Cơm chiên hải sản
  (7, 9,  0.150),  -- Hải sản 150g
  (7, 8,  0.200),  -- Gạo 200g
  (7, 4,  0.030),  -- Rau sống 30g

  -- 8. Gà nướng mật ong
  (8, 10, 0.350),  -- Thịt gà 350g
  (8, 11, 0.050),  -- Mật ong 50ml

  -- 9. Cá kho tộ
  (9, 12, 0.250),  -- Cá basa 250g
  (9, 4,  0.020),  -- Rau sống 20g

  -- 10. Bò lúc lắc
  (10, 6, 0.200),  -- Thịt bò 200g
  (10, 8, 0.100),  -- Gạo (khoai tây) - dùng tạm

  -- 11. Chè ba màu
  (11, 15, 0.050), -- Sữa đặc 50g

  -- 12. Bánh flan
  (12, 17, 2.000), -- Trứng gà 2 quả
  (12, 15, 0.080), -- Sữa đặc 80g

  -- 13. Kem 3 vị
  (13, 15, 0.050), -- Sữa đặc 50g

  -- 16. Sinh tố xoài
  (16, 14, 0.150), -- Xoài 150g
  (16, 15, 0.030), -- Sữa đặc 30g

  -- 17. Cà phê sữa đá
  (17, 16, 0.015), -- Cà phê 15g
  (17, 15, 0.030), -- Sữa đặc 30g

  -- 18. Nước ép cam
  (18, 18, 0.200); -- Cam tươi 200g

-- Trà đá (14) và Nước ngọt lon (15) không cần nguyên liệu từ kho → luôn available

INSERT IGNORE INTO schema_migrations (version) VALUES ('003_seed_data');
