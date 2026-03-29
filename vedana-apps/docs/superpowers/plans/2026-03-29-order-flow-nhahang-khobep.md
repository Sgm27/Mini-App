# Order Flow nhahang_v1 → khobep_v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable nhahang_v1 to create orders (pending), and khobep_v1 to confirm/reject/complete them with inventory deduction on completion.

**Architecture:** Shared MySQL database (`nha_hang_v1`). nhahang creates orders with status `pending` (no inventory deduction). khobep reads pending orders, manages lifecycle (confirm → complete with stock deduction, or reject with reason). Both frontends display order status.

**Tech Stack:** FastAPI + SQLAlchemy (Python), Vanilla JS frontend, MySQL (AWS RDS)

---

### Task 1: Database Migration — ALTER orders table

**Files:**
- Create: `khobep_v1/database/004_order_flow.sql`

- [ ] **Step 1: Write migration SQL**

```sql
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
INSERT INTO schema_migrations (version, name, applied_at)
VALUES (4, '004_order_flow', NOW());
```

- [ ] **Step 2: Run migration against RDS**

Run: `mysql -h mini-app-db.cx6g0gy84qmq.ap-southeast-1.rds.amazonaws.com -u admin -p nha_hang_v1 < khobep_v1/database/004_order_flow.sql`

Verify with: `DESCRIBE orders;` — should show status ENUM with 4 values, plus reject_reason, confirmed_at, completed_at columns.

- [ ] **Step 3: Commit**

```bash
git add khobep_v1/database/004_order_flow.sql
git commit -m "feat: add order flow migration — extend orders for kitchen workflow"
```

---

### Task 2: nhahang_v1 Backend — Update Order model & service

**Files:**
- Modify: `nhahang_v1/backend/app/models/nha_hang.py:77-89`
- Modify: `nhahang_v1/backend/app/schemas/nha_hang.py:109-118`
- Modify: `nhahang_v1/backend/app/services/order_service.py`

- [ ] **Step 1: Update Order model enum and add new columns**

In `nhahang_v1/backend/app/models/nha_hang.py`, update the `Order` class:

```python
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    table_number = Column(String(50), nullable=True)
    status = Column(
        Enum("pending", "confirmed", "completed", "rejected"), default="pending"
    )
    total_amount = Column(Numeric(10, 0), default=0)
    notes = Column(Text, nullable=True)
    reject_reason = Column(Text, nullable=True)
    confirmed_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("OrderItem", back_populates="order")
```

- [ ] **Step 2: Update OrderOut schema**

In `nhahang_v1/backend/app/schemas/nha_hang.py`, update `OrderOut`:

```python
class OrderOut(BaseModel):
    id: int
    table_number: Optional[str] = None
    status: str
    total_amount: float
    notes: Optional[str] = None
    reject_reason: Optional[str] = None
    confirmed_at: Optional[str] = None
    completed_at: Optional[str] = None
    items: List[OrderItemOut] = []
    created_at: str

    model_config = {"from_attributes": True}
```

- [ ] **Step 3: Update order_service.py — set pending, remove inventory deduction**

Replace the entire `create_order` function in `nhahang_v1/backend/app/services/order_service.py`:

```python
def create_order(db: Session, data: CreateOrderRequest) -> OrderOut:
    # 1. Availability check
    availability = check_cart_availability(db, data.items)
    if not availability.can_serve_all:
        missing = ", ".join(i.name for i in availability.missing_ingredients)
        raise HTTPException(
            status_code=400,
            detail=f"Không đủ nguyên liệu: {missing}",
        )

    # 2. Build order items + calculate total
    order_items = []
    total = 0.0
    for item in data.items:
        dish = db.query(Dish).filter(Dish.id == item.dish_id).first()
        if not dish:
            raise HTTPException(status_code=404, detail=f"Không tìm thấy món id={item.dish_id}")
        price = float(dish.price)
        subtotal = price * item.quantity
        total += subtotal
        order_items.append(
            {
                "dish_id": dish.id,
                "name": dish.name,
                "quantity": item.quantity,
                "unit_price": price,
                "subtotal": subtotal,
            }
        )

    # 3. Persist order with status=pending (kitchen will confirm)
    order = Order(
        table_number=data.table_number,
        status="pending",
        total_amount=total,
        notes=data.notes,
    )
    db.add(order)
    db.flush()

    for oi in order_items:
        db.add(
            OrderItem(
                order_id=order.id,
                dish_id=oi["dish_id"],
                quantity=oi["quantity"],
                unit_price=oi["unit_price"],
            )
        )

    # NOTE: No inventory deduction here — khobep deducts on completion

    db.commit()
    db.refresh(order)

    return OrderOut(
        id=order.id,
        table_number=order.table_number,
        status=order.status,
        total_amount=float(order.total_amount),
        notes=order.notes,
        reject_reason=order.reject_reason,
        confirmed_at=order.confirmed_at.isoformat() if order.confirmed_at else None,
        completed_at=order.completed_at.isoformat() if order.completed_at else None,
        items=[
            OrderItemOut(**{k: v for k, v in oi.items()}) for oi in order_items
        ],
        created_at=order.created_at.isoformat(),
    )
```

Also update `get_orders` to include new fields:

```python
def get_orders(db: Session, limit: int = 20) -> list[OrderOut]:
    orders = (
        db.query(Order)
        .order_by(Order.created_at.desc())
        .limit(limit)
        .all()
    )
    result = []
    for o in orders:
        items = []
        for oi in o.items:
            dish_name = oi.dish.name if oi.dish else f"Món #{oi.dish_id}"
            items.append(
                OrderItemOut(
                    dish_id=oi.dish_id,
                    name=dish_name,
                    quantity=oi.quantity,
                    unit_price=float(oi.unit_price),
                    subtotal=float(oi.unit_price) * oi.quantity,
                )
            )
        result.append(
            OrderOut(
                id=o.id,
                table_number=o.table_number,
                status=o.status,
                total_amount=float(o.total_amount),
                notes=o.notes,
                reject_reason=o.reject_reason,
                confirmed_at=o.confirmed_at.isoformat() if o.confirmed_at else None,
                completed_at=o.completed_at.isoformat() if o.completed_at else None,
                items=items,
                created_at=o.created_at.isoformat(),
            )
        )
    return result
```

- [ ] **Step 4: Remove unused imports**

In `nhahang_v1/backend/app/services/order_service.py`, remove `Recipe` and `Ingredient` from imports since we no longer deduct inventory:

```python
from app.models.nha_hang import OrderItem, Order, Dish
```

- [ ] **Step 5: Verify backend starts**

Run: `cd nhahang_v1/backend && python -c "from app.models.nha_hang import Order; print('OK:', [c.name for c in Order.__table__.columns])"`
Expected: prints column names including reject_reason, confirmed_at, completed_at

- [ ] **Step 6: Commit**

```bash
git add nhahang_v1/backend/app/models/nha_hang.py nhahang_v1/backend/app/schemas/nha_hang.py nhahang_v1/backend/app/services/order_service.py
git commit -m "feat(nhahang): create orders as pending, remove inventory deduction"
```

---

### Task 3: nhahang_v1 Frontend — Order status badges

**Files:**
- Modify: `nhahang_v1/frontend/js/app.js:624-657` (showOrderSuccess function)
- Modify: `nhahang_v1/frontend/js/app.js:460-530` (loadOrderTab area)

- [ ] **Step 1: Update showOrderSuccess message**

In `nhahang_v1/frontend/js/app.js`, find the `showOrderSuccess` function and change the success subtitle from "Đơn hàng đã được xác nhận\và kho bếp đã được cập nhật." to reflect pending status:

```javascript
function showOrderSuccess(order) {
    const c = getContent();
    const tableStr = order.table_number ? `Bàn ${order.table_number}` : 'Chưa chọn bàn';
    c.innerHTML = `
        <div class="success-screen">
            <div class="success-icon">✓</div>
            <div class="success-title">Đặt món thành công!</div>
            <div class="success-subtitle">Đơn hàng đã được gửi đến bếp<br>và đang chờ xác nhận.</div>
            <div class="success-order-id">Đơn #${order.id} · ${tableStr}</div>

            <div class="order-total" style="width:100%;max-width:340px;margin-top:8px">
                ${order.items.map(i => `
                    <div class="order-total__row">
                        <span class="order-total__label">${escapeHtml(i.name)} ×${i.quantity}</span>
                        <span class="order-total__value">${formatPrice(i.subtotal)}</span>
                    </div>
                `).join('')}
                <div class="order-total__row order-total__row--grand">
                    <span class="order-total__label">Tổng cộng</span>
                    <span class="order-total__value">${formatPrice(order.total_amount)}</span>
                </div>
            </div>

            <button class="btn-new-order" id="new-order-btn">+ Đặt đơn mới</button>
        </div>`;

    c.querySelector('#new-order-btn').addEventListener('click', () => {
        document.querySelectorAll('.bottom-nav__item')
            .forEach(i => i.classList.remove('bottom-nav__item--active'));
        document.querySelector('[data-tab="menu"]').classList.add('bottom-nav__item--active');
        state.currentTab = 'menu';
        loadMenuTab();
    });
}
```

- [ ] **Step 2: Add status badge helper function**

Add this function near the top of `nhahang_v1/frontend/js/app.js`, after the state declaration:

```javascript
function orderStatusBadge(status, rejectReason) {
    const map = {
        pending:   { label: 'Chờ bếp',    cls: 'badge--warning' },
        confirmed: { label: 'Đang nấu',   cls: 'badge--info' },
        completed: { label: 'Hoàn thành', cls: 'badge--success' },
        rejected:  { label: 'Từ chối',    cls: 'badge--error' },
    };
    const s = map[status] || { label: status, cls: '' };
    let html = `<span class="order-badge ${s.cls}">${s.label}</span>`;
    if (status === 'rejected' && rejectReason) {
        html += `<div class="reject-reason">${escapeHtml(rejectReason)}</div>`;
    }
    return html;
}
```

- [ ] **Step 3: Update order list rendering to show status badges**

Find the section in `loadOrderTab` where orders are rendered as a list and update each order card to include the status badge. Locate the order history rendering (the part that lists past orders) and ensure each order card shows:

```javascript
// Inside the order card rendering loop, add after the order header line:
${orderStatusBadge(order.status, order.reject_reason)}
```

The exact location depends on how orders are currently rendered. Find the `.order-history` or equivalent section and add the badge HTML after the order ID/table line.

- [ ] **Step 4: Add badge CSS to nhahang style.css**

Append to `nhahang_v1/frontend/css/style.css`:

```css
/* ── Order Status Badges ─────────────────────────── */
.order-badge {
    display: inline-block;
    font-size: 11px;
    font-weight: 600;
    padding: 2px 10px;
    border-radius: 999px;
    line-height: 1.6;
}
.badge--warning  { background: #FEF3C7; color: #92400E; }
.badge--info     { background: #DBEAFE; color: #1E40AF; }
.badge--success  { background: #DCFCE7; color: #166534; }
.badge--error    { background: #FEE2E2; color: #991B1B; }

.reject-reason {
    font-size: 12px;
    color: #991B1B;
    margin-top: 4px;
    font-style: italic;
}
```

- [ ] **Step 5: Commit**

```bash
git add nhahang_v1/frontend/js/app.js nhahang_v1/frontend/css/style.css
git commit -m "feat(nhahang): show order status badges (pending/confirmed/completed/rejected)"
```

---

### Task 4: khobep_v1 Backend — Order & OrderItem models

**Files:**
- Modify: `khobep_v1/backend/app/models/kitchen.py`

- [ ] **Step 1: Add Order and OrderItem models**

Append to `khobep_v1/backend/app/models/kitchen.py` (after `ImportReceiptItem` class):

```python
class Order(Base):
    """Orders — created by nhahang, managed by khobep."""
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    table_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 0), default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    items: Mapped[list["OrderItem"]] = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    """Order line items — created by nhahang."""
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"), nullable=False)
    dish_id: Mapped[int] = mapped_column(Integer, ForeignKey("dishes.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 0), nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="items")
    dish: Mapped["Dish"] = relationship("Dish")
```

- [ ] **Step 2: Verify model loads**

Run: `cd khobep_v1/backend && python -c "from app.models.kitchen import Order, OrderItem; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add khobep_v1/backend/app/models/kitchen.py
git commit -m "feat(khobep): add Order and OrderItem models"
```

---

### Task 5: khobep_v1 Backend — Order schemas

**Files:**
- Modify: `khobep_v1/backend/app/schemas/kitchen.py`

- [ ] **Step 1: Add order schemas**

Append before the `# ─── Reports` section in `khobep_v1/backend/app/schemas/kitchen.py`:

```python
# ─── Orders (kitchen workflow) ──────────────────────────────
class OrderItemOut(BaseModel):
    dish_id: int
    dish_name: str
    quantity: int
    unit_price: float
    subtotal: float

    model_config = {"from_attributes": True}


class OrderOut(BaseModel):
    id: int
    table_number: str | None = None
    status: str
    total_amount: float
    notes: str | None = None
    reject_reason: str | None = None
    items: list[OrderItemOut] = []
    created_at: datetime
    confirmed_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class RejectOrderRequest(BaseModel):
    reject_reason: str
```

- [ ] **Step 2: Verify schemas load**

Run: `cd khobep_v1/backend && python -c "from app.schemas.kitchen import OrderOut, OrderItemOut, RejectOrderRequest; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add khobep_v1/backend/app/schemas/kitchen.py
git commit -m "feat(khobep): add order schemas for kitchen workflow"
```

---

### Task 6: khobep_v1 Backend — Order service (business logic)

**Files:**
- Create: `khobep_v1/backend/app/services/order_service.py`

- [ ] **Step 1: Create order_service.py**

```python
"""Order business logic — kitchen confirms, completes (with stock deduction), or rejects."""

from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.kitchen import Order, OrderItem, Recipe, Ingredient, Dish
from app.schemas.kitchen import OrderOut, OrderItemOut
from app.services.inventory_service import recalculate_all_dishes


def _build_order_out(order: Order) -> OrderOut:
    items = []
    for oi in order.items:
        dish_name = oi.dish.name if oi.dish else f"Món #{oi.dish_id}"
        items.append(OrderItemOut(
            dish_id=oi.dish_id,
            dish_name=dish_name,
            quantity=oi.quantity,
            unit_price=float(oi.unit_price),
            subtotal=float(oi.unit_price) * oi.quantity,
        ))
    return OrderOut(
        id=order.id,
        table_number=order.table_number,
        status=order.status,
        total_amount=float(order.total_amount),
        notes=order.notes,
        reject_reason=order.reject_reason,
        items=items,
        created_at=order.created_at,
        confirmed_at=order.confirmed_at,
        completed_at=order.completed_at,
    )


def get_orders(db: Session, status_filter: str | None = None, limit: int = 50) -> list[OrderOut]:
    q = db.query(Order).order_by(Order.created_at.desc())
    if status_filter:
        q = q.filter(Order.status == status_filter)
    orders = q.limit(limit).all()
    return [_build_order_out(o) for o in orders]


def _get_order_or_404(db: Session, order_id: int) -> Order:
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy đơn #{order_id}")
    return order


def confirm_order(db: Session, order_id: int) -> OrderOut:
    order = _get_order_or_404(db, order_id)
    if order.status != "pending":
        raise HTTPException(status_code=400, detail=f"Chỉ đơn 'pending' mới xác nhận được (hiện tại: {order.status})")
    order.status = "confirmed"
    order.confirmed_at = datetime.utcnow()
    db.commit()
    db.refresh(order)
    return _build_order_out(order)


def complete_order(db: Session, order_id: int) -> OrderOut:
    order = _get_order_or_404(db, order_id)
    if order.status != "confirmed":
        raise HTTPException(status_code=400, detail=f"Chỉ đơn 'confirmed' mới hoàn thành được (hiện tại: {order.status})")

    # Deduct ingredients based on recipes
    ingredient_needs: dict[int, Decimal] = {}
    for oi in order.items:
        recipes = db.query(Recipe).filter(Recipe.dish_id == oi.dish_id).all()
        for r in recipes:
            ingredient_needs[r.ingredient_id] = (
                ingredient_needs.get(r.ingredient_id, Decimal("0"))
                + r.required_quantity * oi.quantity
            )

    for ing_id, needed in ingredient_needs.items():
        ing = db.query(Ingredient).filter(Ingredient.id == ing_id).first()
        if ing:
            new_qty = max(Decimal("0"), ing.stock_quantity - needed)
            ing.stock_quantity = new_qty

    order.status = "completed"
    order.completed_at = datetime.utcnow()
    db.commit()
    db.refresh(order)

    recalculate_all_dishes(db)

    return _build_order_out(order)


def reject_order(db: Session, order_id: int, reason: str) -> OrderOut:
    order = _get_order_or_404(db, order_id)
    if order.status != "pending":
        raise HTTPException(status_code=400, detail=f"Chỉ đơn 'pending' mới từ chối được (hiện tại: {order.status})")
    order.status = "rejected"
    order.reject_reason = reason
    db.commit()
    db.refresh(order)
    return _build_order_out(order)
```

- [ ] **Step 2: Verify service loads**

Run: `cd khobep_v1/backend && python -c "from app.services.order_service import get_orders, confirm_order, complete_order, reject_order; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add khobep_v1/backend/app/services/order_service.py
git commit -m "feat(khobep): add order service — confirm, complete (deduct stock), reject"
```

---

### Task 7: khobep_v1 Backend — Order API routes

**Files:**
- Create: `khobep_v1/backend/app/api/routes/orders.py`
- Modify: `khobep_v1/backend/app/api/routes/__init__.py`

- [ ] **Step 1: Create orders route file**

```python
"""Order endpoints for kitchen workflow."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.kitchen import OrderOut, RejectOrderRequest
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("", response_model=list[OrderOut])
def list_orders(
    status: str | None = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return order_service.get_orders(db, status_filter=status, limit=limit)


@router.put("/{order_id}/confirm", response_model=OrderOut)
def confirm_order(order_id: int, db: Session = Depends(get_db)):
    return order_service.confirm_order(db, order_id)


@router.put("/{order_id}/complete", response_model=OrderOut)
def complete_order(order_id: int, db: Session = Depends(get_db)):
    return order_service.complete_order(db, order_id)


@router.put("/{order_id}/reject", response_model=OrderOut)
def reject_order(
    order_id: int,
    payload: RejectOrderRequest,
    db: Session = Depends(get_db),
):
    return order_service.reject_order(db, order_id, payload.reject_reason)
```

- [ ] **Step 2: Register orders router**

In `khobep_v1/backend/app/api/routes/__init__.py`, add the import and registration:

```python
from fastapi import APIRouter, FastAPI

from app.api.routes import dishes, health, imports, inventory, materials, ocr, orders, reports, upload


def register_routes(app: FastAPI) -> None:
    api_router = APIRouter(prefix="/api")
    api_router.include_router(health.router, tags=["health"])
    api_router.include_router(upload.router, tags=["upload"])
    api_router.include_router(materials.router, tags=["materials"])
    api_router.include_router(inventory.router, tags=["inventory"])
    api_router.include_router(imports.router, tags=["imports"])
    api_router.include_router(dishes.router, tags=["dishes"])
    api_router.include_router(ocr.router, tags=["ocr"])
    api_router.include_router(reports.router, tags=["reports"])
    api_router.include_router(orders.router, tags=["orders"])
    app.include_router(api_router)
```

- [ ] **Step 3: Verify server starts and routes are registered**

Run: `cd khobep_v1/backend && python -c "from app.main import app; routes = [r.path for r in app.routes]; print([r for r in routes if 'order' in r])"`
Expected: prints routes containing `/api/orders`

- [ ] **Step 4: Commit**

```bash
git add khobep_v1/backend/app/api/routes/orders.py khobep_v1/backend/app/api/routes/__init__.py
git commit -m "feat(khobep): add order API routes — list, confirm, complete, reject"
```

---

### Task 8: khobep_v1 Frontend — Add "Đơn Bếp" tab to bottom nav

**Files:**
- Modify: `khobep_v1/frontend/index.html`

- [ ] **Step 1: Add 4th tab button to bottom navigation**

In `khobep_v1/frontend/index.html`, add the orders tab button before the closing `</nav>` tag (after the reports button):

```html
      <button class="bottom-nav__item" data-tab="orders">
        <span class="bottom-nav__icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>
            <rect x="8" y="2" width="8" height="4" rx="1" ry="1"/>
            <line x1="9" y1="12" x2="15" y2="12"/>
            <line x1="9" y1="16" x2="15" y2="16"/>
          </svg>
        </span>
        <span class="bottom-nav__label">Đơn Bếp</span>
      </button>
```

- [ ] **Step 2: Commit**

```bash
git add khobep_v1/frontend/index.html
git commit -m "feat(khobep): add 'Đơn Bếp' tab to bottom navigation"
```

---

### Task 9: khobep_v1 Frontend — Order tab JS logic

**Files:**
- Modify: `khobep_v1/frontend/js/app.js`

- [ ] **Step 1: Add orders state fields**

In `khobep_v1/frontend/js/app.js`, add to the `state` object (after `lowStockData: []`):

```javascript
  // Orders (kitchen workflow)
  ordersData: [],
  orderFilter: 'pending',   // 'pending'|'confirmed'|'completed'|'rejected'
```

- [ ] **Step 2: Add orders tab to loadTab function**

Update the `loadTab` function to handle the new tab. Add `orders: 'Đơn Bếp'` to the titles object, and add the case to the switch:

```javascript
function loadTab(tab) {
  state.currentTab = tab;
  const titles = { import: 'Nhập Kho', inventory: 'Tồn Kho', reports: 'Báo Cáo', orders: 'Đơn Bếp' };
  document.getElementById('page-title').textContent = titles[tab] || tab;
  document.getElementById('page-subtitle').textContent = '';
  document.getElementById('top-bar-actions').innerHTML = '';
  document.querySelector('.bottom-nav').style.display = '';
  document.querySelectorAll('.import-detail-back').forEach(b => b.remove());

  switch (tab) {
    case 'import':    renderImportTab(); break;
    case 'inventory': renderInventoryTab(); break;
    case 'reports':   renderReportsTab(); break;
    case 'orders':    renderOrdersTab(); break;
  }
}
```

- [ ] **Step 3: Add renderOrdersTab function**

Append the following function block to `khobep_v1/frontend/js/app.js`:

```javascript
// ─── Orders Tab (Đơn Bếp) ──────────────────────
async function renderOrdersTab() {
  const content = document.getElementById('content');
  content.innerHTML = `<div style="display:flex;justify-content:center;padding:40px 0"><div class="spinner"></div></div>`;

  try {
    const orders = await api.get('/api/orders', { status: state.orderFilter });
    state.ordersData = orders;
    renderOrdersList(orders);
  } catch (err) {
    content.innerHTML = `<div class="empty-state"><p>${err.message}</p><button class="btn btn--primary" onclick="renderOrdersTab()">Thử lại</button></div>`;
  }
}

function renderOrdersList(orders) {
  const content = document.getElementById('content');
  const filters = [
    { key: 'pending',   label: 'Chờ xử lý' },
    { key: 'confirmed', label: 'Đang nấu' },
    { key: 'completed', label: 'Hoàn thành' },
    { key: 'rejected',  label: 'Từ chối' },
  ];

  content.innerHTML = `
    <div class="orders-page">
      <div class="order-filters">
        ${filters.map(f => `
          <button class="order-filter-btn ${state.orderFilter === f.key ? 'order-filter-btn--active' : ''}"
                  data-filter="${f.key}">${f.label}</button>
        `).join('')}
      </div>
      <div class="orders-list">
        ${orders.length === 0
          ? `<div class="empty-state">
               <span style="font-size:40px">${icon('clipboard', 40)}</span>
               <p style="color:var(--text-muted);margin-top:12px">Không có đơn nào</p>
             </div>`
          : orders.map(o => renderOrderCard(o)).join('')
        }
      </div>
    </div>`;

  // Filter buttons
  content.querySelectorAll('.order-filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      state.orderFilter = btn.dataset.filter;
      renderOrdersTab();
    });
  });

  // Action buttons
  content.querySelectorAll('.order-confirm-btn').forEach(btn => {
    btn.addEventListener('click', () => confirmOrderAction(parseInt(btn.dataset.id)));
  });
  content.querySelectorAll('.order-complete-btn').forEach(btn => {
    btn.addEventListener('click', () => completeOrderAction(parseInt(btn.dataset.id)));
  });
  content.querySelectorAll('.order-reject-btn').forEach(btn => {
    btn.addEventListener('click', () => openRejectSheet(parseInt(btn.dataset.id)));
  });
}

function renderOrderCard(o) {
  const time = new Date(o.created_at).toLocaleString('vi-VN', { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' });
  const statusMap = {
    pending:   { label: 'Chờ xử lý', cls: 'order-status--pending' },
    confirmed: { label: 'Đang nấu',  cls: 'order-status--confirmed' },
    completed: { label: 'Hoàn thành', cls: 'order-status--completed' },
    rejected:  { label: 'Từ chối',   cls: 'order-status--rejected' },
  };
  const st = statusMap[o.status] || { label: o.status, cls: '' };

  let actions = '';
  if (o.status === 'pending') {
    actions = `
      <div class="order-actions">
        <button class="btn btn--danger-outline order-reject-btn" data-id="${o.id}">Từ chối</button>
        <button class="btn btn--primary order-confirm-btn" data-id="${o.id}">Xác nhận</button>
      </div>`;
  } else if (o.status === 'confirmed') {
    actions = `
      <div class="order-actions">
        <button class="btn btn--success order-complete-btn" data-id="${o.id}">Hoàn thành</button>
      </div>`;
  }

  return `
    <div class="order-card order-card--${o.status}">
      <div class="order-card__header">
        <div>
          <span class="order-card__id">Đơn #${o.id}</span>
          ${o.table_number ? `<span class="order-card__table">Bàn ${o.table_number}</span>` : ''}
        </div>
        <div style="text-align:right">
          <span class="order-status ${st.cls}">${st.label}</span>
          <div class="order-card__time">${time}</div>
        </div>
      </div>
      <div class="order-card__items">
        ${o.items.map(i => `
          <div class="order-card__item">
            <span>${i.dish_name} <span style="color:var(--text-muted)">×${i.quantity}</span></span>
            <span>${Number(i.subtotal).toLocaleString('vi-VN')}đ</span>
          </div>
        `).join('')}
      </div>
      <div class="order-card__footer">
        <span class="order-card__total">Tổng: ${Number(o.total_amount).toLocaleString('vi-VN')}đ</span>
        ${o.notes ? `<div class="order-card__notes">${iconInline('edit-3', 12)} ${o.notes}</div>` : ''}
        ${o.reject_reason ? `<div class="order-card__reject-reason">Lý do: ${o.reject_reason}</div>` : ''}
      </div>
      ${actions}
    </div>`;
}

async function confirmOrderAction(orderId) {
  try {
    await api.put(`/api/orders/${orderId}/confirm`);
    renderOrdersTab();
  } catch (err) {
    alert('Lỗi: ' + err.message);
  }
}

async function completeOrderAction(orderId) {
  try {
    await api.put(`/api/orders/${orderId}/complete`);
    renderOrdersTab();
  } catch (err) {
    alert('Lỗi: ' + err.message);
  }
}

function openRejectSheet(orderId) {
  const overlay = document.getElementById('sheet-overlay');
  overlay.hidden = false;
  overlay.innerHTML = `
    <div class="bottom-sheet">
      <div class="sheet-handle"></div>
      <h3 style="font-size:var(--text-lg);font-weight:700;margin-bottom:16px">Từ chối đơn #${orderId}</h3>
      <div class="form-group">
        <label class="form-label">Lý do từ chối</label>
        <textarea class="form-input" id="reject-reason" rows="3" placeholder="VD: Bếp quá tải, thiết bị hỏng..."></textarea>
      </div>
      <div class="btn-row">
        <button class="btn btn--secondary" id="reject-cancel" style="flex:1">Hủy</button>
        <button class="btn btn--danger" id="reject-submit" style="flex:2">Xác nhận từ chối</button>
      </div>
    </div>`;

  overlay.querySelector('#reject-cancel').addEventListener('click', () => {
    overlay.hidden = true;
    overlay.innerHTML = '';
  });

  overlay.querySelector('#reject-submit').addEventListener('click', async () => {
    const reason = overlay.querySelector('#reject-reason').value.trim();
    if (!reason) {
      overlay.querySelector('#reject-reason').focus();
      return;
    }
    const btn = overlay.querySelector('#reject-submit');
    btn.disabled = true;
    btn.textContent = 'Đang xử lý...';
    try {
      await api.put(`/api/orders/${orderId}/reject`, { reject_reason: reason });
      overlay.hidden = true;
      overlay.innerHTML = '';
      renderOrdersTab();
    } catch (err) {
      btn.disabled = false;
      btn.textContent = 'Xác nhận từ chối';
      alert('Lỗi: ' + err.message);
    }
  });
}
```

- [ ] **Step 4: Commit**

```bash
git add khobep_v1/frontend/js/app.js
git commit -m "feat(khobep): add orders tab — list, confirm, complete, reject UI"
```

---

### Task 10: khobep_v1 Frontend — Order tab CSS

**Files:**
- Modify: `khobep_v1/frontend/css/style.css`

- [ ] **Step 1: Add order tab styles**

Append to `khobep_v1/frontend/css/style.css`:

```css
/* =============================================
   Orders Tab (Đơn Bếp)
   ============================================= */
.orders-page {
  padding: var(--space-lg);
}

.order-filters {
  display: flex;
  gap: var(--space-sm);
  overflow-x: auto;
  padding-bottom: var(--space-md);
  -webkit-overflow-scrolling: touch;
}

.order-filter-btn {
  flex-shrink: 0;
  padding: 6px 16px;
  border-radius: var(--radius-full);
  border: 1.5px solid var(--border);
  background: var(--white);
  color: var(--text-muted);
  font-size: var(--text-sm);
  font-weight: 500;
  font-family: var(--font);
  cursor: pointer;
  transition: all 0.15s;
}

.order-filter-btn--active {
  background: var(--orange);
  color: var(--white);
  border-color: var(--orange);
}

.orders-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.order-card {
  background: var(--surface);
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
  overflow: hidden;
}

.order-card--pending  { border-left: 3px solid var(--warning); }
.order-card--confirmed { border-left: 3px solid #3B82F6; }
.order-card--completed { border-left: 3px solid var(--success); }
.order-card--rejected  { border-left: 3px solid var(--danger); }

.order-card__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: var(--space-md) var(--space-lg);
  border-bottom: 1px solid var(--border-light);
}

.order-card__id {
  font-weight: 700;
  font-size: var(--text-base);
}

.order-card__table {
  font-size: var(--text-sm);
  color: var(--text-muted);
  margin-left: var(--space-sm);
}

.order-card__time {
  font-size: var(--text-xs);
  color: var(--text-faint);
  margin-top: 2px;
}

.order-status {
  display: inline-block;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: var(--radius-full);
}

.order-status--pending   { background: var(--warning-bg); color: #92400E; }
.order-status--confirmed { background: #DBEAFE; color: #1E40AF; }
.order-status--completed { background: var(--success-bg); color: #166534; }
.order-status--rejected  { background: var(--danger-bg); color: #991B1B; }

.order-card__items {
  padding: var(--space-sm) var(--space-lg);
}

.order-card__item {
  display: flex;
  justify-content: space-between;
  padding: 4px 0;
  font-size: var(--text-sm);
}

.order-card__footer {
  padding: var(--space-sm) var(--space-lg) var(--space-md);
  border-top: 1px solid var(--border-light);
}

.order-card__total {
  font-weight: 700;
  font-size: var(--text-base);
  color: var(--orange);
}

.order-card__notes {
  font-size: var(--text-xs);
  color: var(--text-muted);
  margin-top: 4px;
}

.order-card__reject-reason {
  font-size: var(--text-xs);
  color: var(--danger);
  margin-top: 4px;
  font-style: italic;
}

.order-actions {
  display: flex;
  gap: var(--space-sm);
  padding: 0 var(--space-lg) var(--space-md);
}

.order-actions .btn {
  flex: 1;
}

.btn--success {
  background: var(--success);
  color: var(--white);
  border: none;
  padding: 10px 16px;
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: var(--text-sm);
  font-family: var(--font);
  cursor: pointer;
}

.btn--danger {
  background: var(--danger);
  color: var(--white);
  border: none;
  padding: 10px 16px;
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: var(--text-sm);
  font-family: var(--font);
  cursor: pointer;
}

.btn--danger-outline {
  background: var(--white);
  color: var(--danger);
  border: 1.5px solid var(--danger);
  padding: 10px 16px;
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: var(--text-sm);
  font-family: var(--font);
  cursor: pointer;
}
```

- [ ] **Step 2: Commit**

```bash
git add khobep_v1/frontend/css/style.css
git commit -m "feat(khobep): add CSS styles for orders tab"
```

---

### Task 11: End-to-end verification

**Files:** None (verification only)

- [ ] **Step 1: Start nhahang_v1 backend**

Run: `cd nhahang_v1/backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 2701`
Expected: Server starts on port 2701

- [ ] **Step 2: Start khobep_v1 backend (different port)**

Note: Both apps default to port 2701. For local testing, start khobep on a different port:
Run: `cd khobep_v1/backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 2702`
Expected: Server starts on port 2702

- [ ] **Step 3: Test order creation via nhahang API**

Run: `curl -X POST http://localhost:2701/api/orders -H "Content-Type: application/json" -d '{"table_number":"5","items":[{"dish_id":1,"quantity":2}]}'`
Expected: JSON response with `"status": "pending"` (NOT "confirmed")

- [ ] **Step 4: Test order listing via khobep API**

Run: `curl "http://localhost:2702/api/orders?status=pending"`
Expected: JSON array containing the order created in step 3

- [ ] **Step 5: Test confirm via khobep API**

Run: `curl -X PUT http://localhost:2702/api/orders/{ORDER_ID}/confirm`
Expected: JSON with `"status": "confirmed"` and `confirmed_at` timestamp

- [ ] **Step 6: Test complete via khobep API (should deduct stock)**

Run: `curl -X PUT http://localhost:2702/api/orders/{ORDER_ID}/complete`
Expected: JSON with `"status": "completed"` and `completed_at` timestamp. Verify stock was deducted by checking `curl http://localhost:2702/api/inventory`

- [ ] **Step 7: Test reject via khobep API (create another order first)**

Run: `curl -X PUT http://localhost:2702/api/orders/{NEW_ORDER_ID}/reject -H "Content-Type: application/json" -d '{"reject_reason":"Bếp quá tải"}'`
Expected: JSON with `"status": "rejected"` and `"reject_reason": "Bếp quá tải"`

- [ ] **Step 8: Commit all remaining changes (if any)**

```bash
git add -A
git commit -m "feat: complete order flow nhahang → khobep with kitchen workflow"
```
