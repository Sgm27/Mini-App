# Design: Order Flow nhahang_v1 -> khobep_v1

## Overview

Khi nhahang_v1 tạo order, đơn hàng được lưu vào DB chung (`nha_hang_v1`) với status `pending`. Khobep_v1 hiển thị đơn mới trong tab "Đơn Bếp", nhân viên bếp xác nhận/từ chối. Khi bếp hoàn thành đơn, hệ thống trừ kho nguyên liệu tự động.

## Status Flow

```
pending → confirmed → completed (trừ kho)
              ↘ rejected (kèm lý do)
```

- `pending`: Nhahang vừa tạo, chờ bếp
- `confirmed`: Bếp đã nhận, đang nấu
- `completed`: Nấu xong, trừ kho tại thời điểm này
- `rejected`: Bếp từ chối (lý do: quá tải, thiết bị hỏng, nguyên liệu hư...)

## Database Changes

### Bảng `orders` — ALTER (không tạo bảng mới)

Hiện tại enum status là `('pending', 'confirmed', 'cancelled')`. Cần đổi thành:

```sql
ALTER TABLE orders
  MODIFY COLUMN status ENUM('pending', 'confirmed', 'completed', 'rejected') DEFAULT 'pending',
  ADD COLUMN reject_reason TEXT NULL AFTER notes,
  ADD COLUMN confirmed_at DATETIME NULL AFTER reject_reason,
  ADD COLUMN completed_at DATETIME NULL AFTER confirmed_at;
```

Lưu ý: Giá trị `cancelled` hiện tại không còn dùng. Nếu có dữ liệu cũ, cần migrate sang `rejected`.

### Không cần bảng mới

Cả 2 app đã map bảng `orders` và `order_items` qua SQLAlchemy. Khobep chỉ cần thêm model Order/OrderItem vào `models/kitchen.py`.

## nhahang_v1 Changes

### Backend

**models/nha_hang.py:**
- Cập nhật enum status: `('pending', 'confirmed', 'completed', 'rejected')` (bỏ `cancelled`)
- Thêm columns: `reject_reason`, `confirmed_at`, `completed_at`

**services/order_service.py — `create_order()`:**
- Giữ nguyên check availability (ngăn đặt món hết nguyên liệu)
- Tạo order với `status='pending'` (hiện tại đang set `'confirmed'`)
- **Bỏ phần deduct inventory** (step 4 hiện tại) — việc trừ kho sẽ do khobep thực hiện khi hoàn thành

**services/order_service.py — `get_orders()`:**
- Giữ nguyên, schema OrderOut đã có field `status` nên frontend sẽ tự hiển thị

**schemas/nha_hang.py — `OrderOut`:**
- Thêm `reject_reason: Optional[str] = None`
- Thêm `confirmed_at: Optional[str] = None`
- Thêm `completed_at: Optional[str] = None`

### Frontend

**js/app.js — Tab Order:**
- Hiển thị badge trạng thái cho mỗi đơn:
  - `pending` → badge vàng "Chờ bếp"
  - `confirmed` → badge xanh dương "Đang nấu"
  - `completed` → badge xanh lá "Hoàn thành"
  - `rejected` → badge đỏ "Từ chối" + hiển thị lý do
- Load lại danh sách mỗi lần mở tab Order

## khobep_v1 Changes

### Backend

**models/kitchen.py:**
- Thêm model `Order` và `OrderItem` (map bảng `orders` và `order_items` đã có)
- Order model cần: id, table_number, status, total_amount, notes, reject_reason, confirmed_at, completed_at, created_at, updated_at
- OrderItem model cần: id, order_id, dish_id, quantity, unit_price
- Relationships: Order → items, OrderItem → dish

**schemas/kitchen.py:**
- Thêm `OrderItemOut`: dish_id, dish_name, quantity, unit_price, subtotal
- Thêm `OrderOut`: id, table_number, status, total_amount, notes, reject_reason, items[], created_at, confirmed_at, completed_at
- Thêm `RejectOrderRequest`: reject_reason (required string)

**services/order_service.py (mới):**
- `get_orders(db, status_filter=None, limit=50)` — Lấy danh sách đơn, filter theo status
- `confirm_order(db, order_id)` — Set status=confirmed, confirmed_at=now
- `complete_order(db, order_id)` — Set status=completed, completed_at=now, **trừ kho nguyên liệu**, recalculate dish availability
- `reject_order(db, order_id, reason)` — Set status=rejected, reject_reason=reason

Logic trừ kho trong `complete_order`:
1. Lấy tất cả order_items của đơn
2. Với mỗi item, query recipes để biết nguyên liệu cần dùng
3. Tính tổng nguyên liệu = required_quantity * quantity
4. Trừ stock_quantity của ingredient (min 0)
5. Gọi `recalculate_all_dishes()` để cập nhật dish.active

**api/routes/orders.py (mới):**
- `GET /api/orders?status=pending&limit=50` — Danh sách đơn
- `PUT /api/orders/{id}/confirm` — Xác nhận đơn
- `PUT /api/orders/{id}/complete` — Hoàn thành + trừ kho
- `PUT /api/orders/{id}/reject` — Từ chối (body: {reject_reason})

**api/__init__.py:**
- Đăng ký router mới cho orders

### Frontend

**index.html:**
- Thêm tab thứ 4 "Đơn Bếp" vào bottom navigation (icon: clipboard/order)

**js/app.js:**
- Thêm state: `ordersData: []`, `orderFilter: 'pending'`
- Thêm function `renderOrdersTab()`:
  - Filter buttons: Chờ xử lý | Đang nấu | Hoàn thành | Từ chối
  - Danh sách đơn hàng dạng card:
    - Header: Đơn #id — Bàn X — Thời gian
    - Body: Danh sách món (tên, số lượng, đơn giá)
    - Footer: Tổng tiền + nút hành động
  - Đơn `pending`: Nút "Xác nhận" (xanh) + "Từ chối" (đỏ)
  - Đơn `confirmed`: Nút "Hoàn thành" (xanh lá)
  - Đơn `completed`/`rejected`: Chỉ hiển thị, không có nút
- Bottom sheet cho từ chối: input lý do + nút xác nhận
- Auto-reload danh sách khi chuyển tab

**css/style.css:**
- Style cho tab Đơn Bếp: cards, badges, action buttons
- Badge colors: pending=amber, confirmed=blue, completed=green, rejected=red

## Data Flow Summary

```
[nhahang frontend]
    │ POST /api/orders (table, items, notes)
    ↓
[nhahang backend]
    │ check availability → create order (status=pending, NO inventory deduction)
    ↓
[shared DB: orders table]
    ↓
[khobep backend]
    │ GET /api/orders?status=pending
    ↓
[khobep frontend - tab "Đơn Bếp"]
    │ Bếp bấm "Xác nhận" / "Từ chối"
    ↓
[khobep backend]
    │ PUT /api/orders/{id}/confirm  →  status=confirmed
    │ PUT /api/orders/{id}/reject   →  status=rejected + reason
    ↓
[khobep frontend]
    │ Bếp nấu xong, bấm "Hoàn thành"
    ↓
[khobep backend]
    │ PUT /api/orders/{id}/complete
    │   → status=completed
    │   → deduct ingredients from stock
    │   → recalculate dish availability
    ↓
[shared DB updated]
    ↓
[nhahang frontend - tab Order]
    │ GET /api/orders → thấy status mới (completed/rejected)
```

## Edge Cases

1. **Đơn bị reject nhưng nguyên liệu vẫn đủ**: Không ảnh hưởng kho, nhahang vẫn có thể đặt lại.
2. **Hai đơn pending cùng lúc dùng hết nguyên liệu**: Đơn đầu hoàn thành trừ kho, đơn sau khi bếp hoàn thành sẽ trừ tiếp (có thể về 0). Nhahang check availability sẽ tự disable món.
3. **Bếp xác nhận rồi muốn từ chối**: Không hỗ trợ trong phiên bản này. Chỉ đơn `pending` mới reject được.

## Files to Modify

### nhahang_v1
- `backend/app/models/nha_hang.py` — update Order model
- `backend/app/schemas/nha_hang.py` — update OrderOut schema
- `backend/app/services/order_service.py` — remove inventory deduction, set pending
- `frontend/js/app.js` — status badges in order tab

### khobep_v1
- `database/004_order_flow.sql` — ALTER orders table (new migration)
- `backend/app/models/kitchen.py` — add Order, OrderItem models
- `backend/app/schemas/kitchen.py` — add order schemas
- `backend/app/services/order_service.py` — new file, order business logic
- `backend/app/api/routes/orders.py` — new file, order endpoints
- `backend/app/api/__init__.py` — register orders router
- `frontend/index.html` — add 4th tab to bottom nav
- `frontend/js/app.js` — renderOrdersTab(), order actions
- `frontend/css/style.css` — order tab styling
