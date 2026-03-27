/**
 * Nhà Hàng Việt — Restaurant Staff Ordering App
 * Mobile-first, one-hand operation optimized
 */

// ── App State ────────────────────────────────────────────────
const state = {
    cart: new Map(),          // dish_id (int) → quantity (int)
    dishes: [],               // all dishes from server
    categories: [],           // all categories
    currentCategory: 0,       // 0 = all
    availabilityMap: new Map(),// dish_id → { can_serve, missing_ingredients }
    checkTimer: null,
    checking: false,
    selectedTable: null,
    currentTab: 'menu',
};

// ── Init ─────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initBottomNav();
    loadMenuTab();
});

// ── Bottom Navigation ────────────────────────────────────────
function initBottomNav() {
    document.querySelectorAll('.bottom-nav__item').forEach(item => {
        item.addEventListener('click', () => {
            document.querySelectorAll('.bottom-nav__item')
                .forEach(i => i.classList.remove('bottom-nav__item--active'));
            item.classList.add('bottom-nav__item--active');
            state.currentTab = item.dataset.tab;
            onTabChange(item.dataset.tab);
        });
    });
}

function onTabChange(tab) {
    switch (tab) {
        case 'menu':      loadMenuTab(); break;
        case 'order':     loadOrderTab(); break;
        case 'inventory': loadInventoryTab(); break;
    }
}

// ── Helpers ──────────────────────────────────────────────────
function getContent() { return document.getElementById('content-area'); }

function showLoading(container) {
    container.innerHTML = `
        <div class="loading-screen">
            <div class="spinner spinner--lg"></div>
            <p class="loading-text">Đang tải...</p>
        </div>`;
}

function showErrorState(container, msg, retryFn) {
    container.innerHTML = `
        <div class="error-state">
            <p class="error-state__msg">${escapeHtml(msg)}</p>
            ${retryFn ? `<button class="btn-retry" id="retry-btn">Thử lại</button>` : ''}
        </div>`;
    if (retryFn) container.querySelector('#retry-btn').addEventListener('click', retryFn);
}

function escapeHtml(text) {
    const d = document.createElement('div');
    d.textContent = String(text ?? '');
    return d.innerHTML;
}

function formatPrice(n) {
    return n.toLocaleString('vi-VN') + 'đ';
}

function formatNum(n) {
    if (n === Math.floor(n)) return n.toString();
    return parseFloat(n.toFixed(3)).toString();
}

function cartTotal() {
    let total = 0;
    for (const [id, qty] of state.cart.entries()) {
        const d = state.dishes.find(x => x.id === id);
        if (d) total += d.price * qty;
    }
    return total;
}

function cartCount() {
    let n = 0;
    for (const q of state.cart.values()) n += q;
    return n;
}

function updateCartBadge() {
    const badge = document.getElementById('cart-badge');
    const n = cartCount();
    if (n > 0) {
        badge.textContent = n;
        badge.style.display = 'flex';
    } else {
        badge.style.display = 'none';
    }
}

function avatarClass(catId) {
    const map = { 1: 'cat1', 2: 'cat2', 3: 'cat3', 4: 'cat4' };
    return `dish-avatar--${map[catId] || 'cat2'}`;
}

function catEmoji(catId) {
    const map = { 1: '🥗', 2: '🍲', 3: '🍮', 4: '🥤' };
    return map[catId] || '🍽️';
}

function ingredientEmoji(name) {
    const n = name.toLowerCase();
    if (n.includes('tôm')) return '🦐';
    if (n.includes('thịt bò') || n.includes('bò')) return '🥩';
    if (n.includes('thịt heo') || n.includes('heo')) return '🥓';
    if (n.includes('gà')) return '🐔';
    if (n.includes('cá')) return '🐟';
    if (n.includes('hải sản')) return '🦞';
    if (n.includes('rau')) return '🥬';
    if (n.includes('xoài')) return '🥭';
    if (n.includes('cam')) return '🍊';
    if (n.includes('trứng')) return '🥚';
    if (n.includes('gạo')) return '🌾';
    if (n.includes('cà phê')) return '☕';
    if (n.includes('sữa')) return '🥛';
    if (n.includes('mật ong')) return '🍯';
    if (n.includes('bắp')) return '🌽';
    if (n.includes('bánh')) return '🫓';
    if (n.includes('bún') || n.includes('phở')) return '🍜';
    return '🧂';
}

// ── Bottom Sheet ─────────────────────────────────────────────
function openBottomSheet(htmlContent) {
    const overlay = document.createElement('div');
    overlay.className = 'sheet-overlay';
    overlay.innerHTML = `
        <div class="bottom-sheet">
            <div class="sheet-handle"></div>
            ${htmlContent}
        </div>`;
    document.querySelector('.app-shell').appendChild(overlay);
    overlay.addEventListener('click', e => {
        if (e.target === overlay) closeBottomSheet(overlay);
    });
    return overlay;
}

function closeBottomSheet(overlay) {
    overlay.style.opacity = '0';
    overlay.querySelector('.bottom-sheet').style.transform = 'translateY(100%)';
    overlay.querySelector('.bottom-sheet').style.transition = 'transform 0.25s ease';
    setTimeout(() => overlay.remove(), 260);
}

// ══════════════════════════════════════════════════════════════
// ── MENU TAB ─────────────────────────────────────────────────
// ══════════════════════════════════════════════════════════════
async function loadMenuTab() {
    const c = getContent();
    showLoading(c);
    try {
        const [cats, dishes] = await Promise.all([
            api.get('/api/menu/categories'),
            api.get('/api/menu/dishes'),
        ]);
        state.categories = cats;
        state.dishes = dishes;

        // Populate availability from initial server response
        state.availabilityMap.clear();
        dishes.forEach(d => {
            state.availabilityMap.set(d.id, {
                can_serve: d.can_serve,
                missing_ingredients: d.missing_ingredients,
            });
        });

        attachMenuDelegation(c);
        renderMenuTab(c);
    } catch (err) {
        showErrorState(c, 'Không thể tải thực đơn: ' + err.message, loadMenuTab);
    }
}

function renderMenuTab(c) {
    if (!c) c = getContent();
    const filtered = state.currentCategory === 0
        ? state.dishes
        : state.dishes.filter(d => d.category_id === state.currentCategory);

    const cartHasItems = state.cart.size > 0;

    c.innerHTML = `
        <div class="scroll-content">
            ${renderCategoryBar()}
            ${renderCheckingBar()}
            <div class="dish-list">
                ${renderDishGroups(filtered)}
            </div>
            ${cartHasItems ? renderCartBar() : ''}
        </div>`;

    attachMenuEvents(c);
    updateCartBadge();
}

function renderCategoryBar() {
    const allActive = state.currentCategory === 0 ? 'category-pill--active' : '';
    const pills = state.categories.map(cat => {
        const active = state.currentCategory === cat.id ? 'category-pill--active' : '';
        return `<button class="category-pill ${active}" data-cat="${cat.id}">
                    <span class="category-pill__icon">${cat.icon || ''}</span>
                    ${escapeHtml(cat.name)}
                </button>`;
    }).join('');

    return `<div class="category-bar">
                <button class="category-pill ${allActive}" data-cat="0">Tất cả</button>
                ${pills}
            </div>`;
}

function renderCheckingBar() {
    if (!state.checking) return '';
    return `<div class="checking-bar">
                <div class="spinner"></div>
                <span>Đang kiểm tra kho bếp...</span>
            </div>`;
}

function renderDishGroups(dishes) {
    if (dishes.length === 0) {
        return `<div class="empty-state">
                    <div class="empty-state__icon">🍽️</div>
                    <p class="empty-state__title">Không có món nào</p>
                </div>`;
    }

    if (state.currentCategory !== 0) {
        return dishes.map(d => renderDishCard(d)).join('');
    }

    // Group by category
    const grouped = {};
    dishes.forEach(d => {
        if (!grouped[d.category_id]) grouped[d.category_id] = { cat: d, items: [] };
        grouped[d.category_id].items.push(d);
    });

    return Object.values(grouped).map(g => `
        <div class="dish-section__title">
            ${g.cat.category_icon || ''} ${escapeHtml(g.cat.category_name || '')}
        </div>
        ${g.items.map(d => renderDishCard(d)).join('')}
    `).join('');
}

function renderDishCard(dish) {
    const qty = state.cart.get(dish.id) || 0;
    const avail = state.availabilityMap.get(dish.id) || { can_serve: true, missing_ingredients: [] };
    const inCart = qty > 0;
    const unavailable = !avail.can_serve;

    const cardCls = [
        'dish-card',
        inCart ? 'dish-card--in-cart' : '',
        unavailable ? 'dish-card--unavailable' : '',
    ].filter(Boolean).join(' ');

    const statusHtml = unavailable
        ? `<span class="dish-status dish-status--out">
               <span class="dish-status__dot"></span>Hết nguyên liệu
           </span>`
        : `<span class="dish-status dish-status--ok">
               <span class="dish-status__dot"></span>Có thể phục vụ
           </span>`;

    const imgHtml = dish.image
        ? `<img src="${API_URL}${escapeHtml(dish.image)}" alt="${escapeHtml(dish.name)}" loading="lazy" />`
        : catEmoji(dish.category_id);

    return `
        <div class="${cardCls}" data-dish="${dish.id}">
            <div class="dish-avatar ${avatarClass(dish.category_id)}">${imgHtml}</div>
            <div class="dish-info">
                <div class="dish-name">${escapeHtml(dish.name)}</div>
                <div class="dish-price">${formatPrice(dish.price)}</div>
                ${statusHtml}
            </div>
            <div class="qty-controls">
                ${qty > 0 ? `
                    <button class="qty-btn qty-btn--remove" data-action="remove" data-dish="${dish.id}">−</button>
                    <span class="qty-value">${qty}</span>
                ` : ''}
                <button class="qty-btn qty-btn--add" data-action="add" data-dish="${dish.id}">+</button>
            </div>
        </div>`;
}

function renderCartBar() {
    const count = cartCount();
    const total = cartTotal();
    return `
        <div class="cart-bar">
            <button class="cart-bar__btn" id="view-cart-btn">
                <div class="cart-bar__info">
                    <span class="cart-bar__count">${count}</span>
                    <span>Xem đơn hàng</span>
                </div>
                <span>${formatPrice(total)}</span>
            </button>
        </div>`;
}

function attachMenuDelegation(c) {
    // Qty buttons + view-cart (event delegation, attach ONCE)
    if (c._menuDelegationAttached) return;
    c._menuDelegationAttached = true;
    c.addEventListener('click', e => {
        // Qty buttons
        const actionBtn = e.target.closest('[data-action]');
        if (actionBtn) {
            const dishId = parseInt(actionBtn.dataset.dish);
            if (actionBtn.dataset.action === 'add') {
                addToCart(dishId);
            } else if (actionBtn.dataset.action === 'remove') {
                removeFromCart(dishId);
            }
            return;
        }
        // View cart button
        if (e.target.closest('#view-cart-btn')) {
            document.querySelectorAll('.bottom-nav__item')
                .forEach(i => i.classList.remove('bottom-nav__item--active'));
            document.querySelector('[data-tab="order"]').classList.add('bottom-nav__item--active');
            state.currentTab = 'order';
            loadOrderTab();
            return;
        }
    });
}

function attachMenuEvents(c) {
    // Category pills (re-binds after each render since innerHTML replaces them)
    c.querySelectorAll('.category-pill').forEach(btn => {
        btn.addEventListener('click', () => {
            state.currentCategory = parseInt(btn.dataset.cat);
            renderMenuTab(c);
        });
    });
}

function addToCart(dishId) {
    const current = state.cart.get(dishId) || 0;
    state.cart.set(dishId, current + 1);
    scheduleAvailabilityCheck();
    renderMenuTab();
}

function removeFromCart(dishId) {
    const current = state.cart.get(dishId) || 0;
    if (current <= 1) {
        state.cart.delete(dishId);
    } else {
        state.cart.set(dishId, current - 1);
    }
    scheduleAvailabilityCheck();
    renderMenuTab();
}

// ── Availability check (debounced) ───────────────────────────
function scheduleAvailabilityCheck() {
    if (state.checkTimer) clearTimeout(state.checkTimer);
    state.checking = state.cart.size > 0;
    state.checkTimer = setTimeout(runAvailabilityCheck, 500);
}

async function runAvailabilityCheck() {
    if (state.cart.size === 0) {
        state.checking = false;
        // Reset to server-provided per-dish availability
        state.dishes.forEach(d => {
            state.availabilityMap.set(d.id, {
                can_serve: d.can_serve,
                missing_ingredients: d.missing_ingredients,
            });
        });
        if (state.currentTab === 'menu') renderMenuTab();
        return;
    }

    const items = Array.from(state.cart.entries()).map(([id, qty]) => ({
        dish_id: id, quantity: qty,
    }));

    try {
        const result = await api.post('/api/menu/check-availability', { items });
        // Update map for cart items from server response
        result.dishes.forEach(r => {
            state.availabilityMap.set(r.dish_id, {
                can_serve: r.can_serve,
                missing_ingredients: r.missing_ingredients,
            });
        });
    } catch (_) { /* silent fail */ }

    state.checking = false;
    if (state.currentTab === 'menu') renderMenuTab();
    if (state.currentTab === 'order') loadOrderTab();
}

// ══════════════════════════════════════════════════════════════
// ── ORDER TAB ─────────────────────────────────────────────────
// ══════════════════════════════════════════════════════════════
async function loadOrderTab() {
    const c = getContent();

    if (state.cart.size === 0) {
        c.innerHTML = `
            <div class="empty-state" style="margin-top:48px">
                <div class="empty-state__icon">🛒</div>
                <p class="empty-state__title">Chưa có món nào</p>
                <p class="empty-state__desc">Quay lại thực đơn và chọn món<br>để bắt đầu đặt hàng</p>
            </div>`;
        return;
    }

    // Build order items list
    const orderItems = Array.from(state.cart.entries()).map(([id, qty]) => {
        const dish = state.dishes.find(d => d.id === id);
        const avail = state.availabilityMap.get(id) || { can_serve: true };
        return { dish, qty, avail };
    }).filter(x => x.dish);

    const allAvailable = orderItems.every(x => x.avail.can_serve);
    const total = cartTotal();
    const itemCount = cartCount();

    // Check cart availability fresh
    let cartCheck = null;
    try {
        const items = Array.from(state.cart.entries()).map(([id, qty]) => ({ dish_id: id, quantity: qty }));
        cartCheck = await api.post('/api/menu/check-availability', { items });
        // update map
        cartCheck.dishes.forEach(r => {
            state.availabilityMap.set(r.dish_id, {
                can_serve: r.can_serve,
                missing_ingredients: r.missing_ingredients,
            });
        });
    } catch (_) { /* silent */ }

    const canConfirm = cartCheck ? cartCheck.can_serve_all : allAvailable;

    c.innerHTML = `
        <div class="order-page">
            <div class="order-page__header">
                <div class="order-page__title">Đơn hàng của bạn</div>
                <div class="order-page__subtitle">${itemCount} món • ${formatPrice(total)}</div>
            </div>

            ${renderAvailabilityCard(cartCheck)}

            <div class="order-items">
                ${orderItems.map(({ dish, qty, avail }) => renderOrderItem(dish, qty, avail)).join('')}
            </div>

            ${renderOrderTotal(orderItems, total)}

            <div class="confirm-area">
                <button class="btn-confirm" id="confirm-btn" ${canConfirm ? '' : 'disabled'}>
                    ${canConfirm ? '✓ Xác nhận đơn hàng' : '⚠ Thiếu nguyên liệu'}
                </button>
            </div>
        </div>`;

    c.querySelector('#confirm-btn')?.addEventListener('click', showConfirmSheet);
}

function renderAvailabilityCard(check) {
    if (!check) return '';
    if (check.can_serve_all) {
        return `<div class="availability-card availability-card--ok" style="margin:12px 16px 0">
                    <div class="availability-card__title">✓ Có thể phục vụ tất cả các món</div>
                    Kho bếp đủ nguyên liệu cho đơn hàng này.
                </div>`;
    }
    const missing = check.missing_ingredients.map(t =>
        `${escapeHtml(t.name)}: thiếu ${formatNum(t.needed)} ${escapeHtml(t.unit)}`
    ).join(', ');
    return `<div class="availability-card availability-card--error" style="margin:12px 16px 0">
                <div class="availability-card__title">✗ Không đủ nguyên liệu</div>
                ${escapeHtml(missing)}
            </div>`;
}

function renderOrderItem(dish, qty, avail) {
    const unavail = !avail.can_serve;
    return `
        <div class="order-item ${unavail ? 'order-item--unavailable' : ''}">
            <div class="order-item__avatar ${avatarClass(dish.category_id)}">${catEmoji(dish.category_id)}</div>
            <div class="order-item__info">
                <div class="order-item__name">${escapeHtml(dish.name)}</div>
                <div class="order-item__meta">${qty} × ${formatPrice(dish.price)}
                    ${unavail ? '<span style="color:var(--clr-error);margin-left:4px">• Hết NL</span>' : ''}
                </div>
            </div>
            <div class="order-item__price">${formatPrice(dish.price * qty)}</div>
        </div>`;
}

function renderOrderTotal(items, total) {
    const rows = items.map(({ dish, qty }) =>
        `<div class="order-total__row">
            <span class="order-total__label">${escapeHtml(dish.name)} ×${qty}</span>
            <span class="order-total__value">${formatPrice(dish.price * qty)}</span>
        </div>`
    ).join('');
    return `
        <div class="order-total" style="margin-top:12px">
            ${rows}
            <div class="order-total__row order-total__row--grand">
                <span class="order-total__label">Tổng cộng</span>
                <span class="order-total__value">${formatPrice(total)}</span>
            </div>
        </div>`;
}

function showConfirmSheet() {
    const tables = ['1', '2', '3', '4', '5', '6', '7', '8'];
    const tablePills = tables.map(t =>
        `<button class="table-pill ${state.selectedTable === t ? 'table-pill--active' : ''}" data-table="${t}">Bàn ${t}</button>`
    ).join('');

    const overlay = openBottomSheet(`
        <h2 class="sheet-title">Xác nhận đơn hàng</h2>

        <div class="form-group">
            <label class="form-label">Số bàn</label>
            <div class="table-selector" id="table-selector">${tablePills}</div>
        </div>

        <div class="form-group">
            <label class="form-label">Ghi chú</label>
            <input class="form-input" type="text" id="order-note" placeholder="Yêu cầu đặc biệt...">
            <p class="form-hint">Không bắt buộc</p>
        </div>

        <div class="order-total" style="margin-bottom:16px">
            <div class="order-total__row order-total__row--grand">
                <span class="order-total__label">Tổng tiền</span>
                <span class="order-total__value">${formatPrice(cartTotal())}</span>
            </div>
        </div>

        <div class="btn-row">
            <button class="btn btn--secondary" id="cancel-confirm-btn" style="flex:1">Hủy</button>
            <button class="btn btn--primary" id="do-confirm-btn" style="flex:2">Xác nhận đặt món</button>
        </div>
    `);

    // Table selection
    overlay.querySelectorAll('.table-pill').forEach(p => {
        p.addEventListener('click', () => {
            overlay.querySelectorAll('.table-pill').forEach(x => x.classList.remove('table-pill--active'));
            p.classList.add('table-pill--active');
            state.selectedTable = p.dataset.table;
        });
    });

    overlay.querySelector('#cancel-confirm-btn').addEventListener('click', () => closeBottomSheet(overlay));

    overlay.querySelector('#do-confirm-btn').addEventListener('click', async () => {
        const note = overlay.querySelector('#order-note').value.trim();
        const btn = overlay.querySelector('#do-confirm-btn');
        btn.disabled = true;
        btn.textContent = 'Đang xử lý...';

        try {
            const items = Array.from(state.cart.entries()).map(([id, qty]) => ({
                dish_id: id, quantity: qty,
            }));
            const result = await api.post('/api/orders', {
                table_number: state.selectedTable,
                items,
                notes: note || null,
            });
            closeBottomSheet(overlay);
            state.cart.clear();
            state.availabilityMap.clear();
            // Reload dishes to refresh availability
            api.get('/api/menu/dishes').then(dishes => {
                state.dishes = dishes;
                dishes.forEach(d => state.availabilityMap.set(d.id, {
                    can_serve: d.can_serve,
                    missing_ingredients: d.missing_ingredients,
                }));
            });
            updateCartBadge();
            showOrderSuccess(result);
        } catch (err) {
            btn.disabled = false;
            btn.textContent = 'Xác nhận đặt món';
            // Show error inside sheet
            const errEl = overlay.querySelector('.btn-row');
            const old = overlay.querySelector('.sheet-error');
            if (old) old.remove();
            const errDiv = document.createElement('div');
            errDiv.className = 'availability-card availability-card--error sheet-error';
            errDiv.style.marginBottom = '12px';
            errDiv.textContent = err.message || 'Lỗi xác nhận đơn hàng';
            errEl.parentNode.insertBefore(errDiv, errEl);
        }
    });
}

function showOrderSuccess(order) {
    const c = getContent();
    const tableStr = order.table_number ? `Bàn ${order.table_number}` : 'Chưa chọn bàn';
    c.innerHTML = `
        <div class="success-screen">
            <div class="success-icon">✓</div>
            <div class="success-title">Đặt món thành công!</div>
            <div class="success-subtitle">Đơn hàng đã được xác nhận<br>và kho bếp đã được cập nhật.</div>
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

// ══════════════════════════════════════════════════════════════
// ── INVENTORY TAB ─────────────────────────────────────────────
// ══════════════════════════════════════════════════════════════
async function loadInventoryTab() {
    const c = getContent();
    showLoading(c);
    try {
        const ingredients = await api.get('/api/inventory/ingredients');
        renderInventoryTab(c, ingredients);
    } catch (err) {
        showErrorState(c, 'Không thể tải kho bếp: ' + err.message, loadInventoryTab);
    }
}

function renderInventoryTab(c, ingredients) {
    const lowItems = ingredients.filter(i => i.low_stock_warning).length;

    c.innerHTML = `
        <div class="inventory-page">
            <div class="inventory-header">
                <div>
                    <div class="inventory-title">Kho bếp</div>
                    ${lowItems > 0 ? `<div style="font-size:12px;color:var(--clr-warning);font-weight:600;margin-top:2px">⚠ ${lowItems} nguyên liệu sắp hết</div>` : ''}
                </div>
                <button class="btn-add-ingredient" id="add-ingredient-btn" title="Thêm nguyên liệu">+</button>
            </div>
            <div class="inventory-list">
                ${ingredients.map(i => renderIngredientCard(i)).join('')}
            </div>
        </div>`;

    // Edit buttons
    c.querySelectorAll('.ingredient-edit-btn').forEach(btn => {
        btn.addEventListener('click', e => {
            e.stopPropagation();
            const id = parseInt(btn.dataset.id);
            const ing = ingredients.find(x => x.id === id);
            if (ing) openEditIngredient(ing);
        });
    });

    // Card tap also opens edit
    c.querySelectorAll('.ingredient-card').forEach(card => {
        card.addEventListener('click', () => {
            const id = parseInt(card.dataset.id);
            const ing = ingredients.find(x => x.id === id);
            if (ing) openEditIngredient(ing);
        });
    });

    c.querySelector('#add-ingredient-btn').addEventListener('click', openAddIngredient);
}

function renderIngredientCard(ing) {
    const ratio = ing.warning_threshold > 0 ? ing.stock_quantity / ing.warning_threshold : 999;
    let cardCls = 'ingredient-card';
    let warnHtml = '';

    if (ing.stock_quantity === 0) {
        cardCls += ' ingredient-card--critical';
        warnHtml = `<span class="ingredient-warning ingredient-warning--critical">Hết</span>`;
    } else if (ing.low_stock_warning) {
        cardCls += ' ingredient-card--low';
        warnHtml = `<span class="ingredient-warning ingredient-warning--low">Sắp hết</span>`;
    }

    const stockColor = ing.stock_quantity === 0
        ? 'var(--clr-error)'
        : ing.low_stock_warning
        ? 'var(--clr-warning)'
        : 'var(--clr-success)';

    return `
        <div class="${cardCls}" data-id="${ing.id}">
            <div class="ingredient-icon">${ingredientEmoji(ing.name)}</div>
            <div class="ingredient-info">
                <div class="ingredient-name">${escapeHtml(ing.name)}</div>
                <div class="ingredient-stock">
                    <span style="color:${stockColor}">${formatNum(ing.stock_quantity)}</span>
                    ${escapeHtml(ing.unit)}
                    ${ing.warning_threshold > 0 ? `<span style="color:var(--clr-text-3)"> / ngưỡng: ${formatNum(ing.warning_threshold)}</span>` : ''}
                </div>
            </div>
            ${warnHtml}
            <button class="ingredient-edit-btn" data-id="${ing.id}" title="Chỉnh sửa">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4Z"/>
                </svg>
            </button>
        </div>`;
}

function openEditIngredient(ing) {
    const overlay = openBottomSheet(`
        <h2 class="sheet-title">Cập nhật nguyên liệu</h2>

        <div style="display:flex;align-items:center;gap:12px;margin-bottom:16px;background:var(--clr-primary-bg);padding:12px;border-radius:var(--r-md)">
            <span style="font-size:28px">${ingredientEmoji(ing.name)}</span>
            <div>
                <div style="font-size:16px;font-weight:700">${escapeHtml(ing.name)}</div>
                <div style="font-size:13px;color:var(--clr-text-3)">Đơn vị: ${escapeHtml(ing.unit)}</div>
            </div>
        </div>

        <div class="form-group">
            <label class="form-label">Số lượng tồn kho (${escapeHtml(ing.unit)})</label>
            <input class="form-input" type="number" id="stock-input" value="${ing.stock_quantity}" min="0" step="0.1">
        </div>

        <div class="form-group">
            <label class="form-label">Ngưỡng cảnh báo thấp (${escapeHtml(ing.unit)})</label>
            <input class="form-input" type="number" id="threshold-input" value="${ing.warning_threshold}" min="0" step="0.1">
            <p class="form-hint">Sẽ cảnh báo khi tồn kho ≤ ngưỡng này</p>
        </div>

        <div class="btn-row">
            <button class="btn btn--secondary" id="cancel-edit-btn" style="flex:1">Hủy</button>
            <button class="btn btn--primary" id="save-edit-btn" style="flex:2">Lưu cập nhật</button>
        </div>
    `);

    overlay.querySelector('#cancel-edit-btn').addEventListener('click', () => closeBottomSheet(overlay));

    overlay.querySelector('#save-edit-btn').addEventListener('click', async () => {
        const qty = parseFloat(overlay.querySelector('#stock-input').value);
        const threshold = parseFloat(overlay.querySelector('#threshold-input').value);

        if (isNaN(qty) || qty < 0) {
            overlay.querySelector('#stock-input').focus();
            return;
        }

        const btn = overlay.querySelector('#save-edit-btn');
        btn.disabled = true;
        btn.textContent = 'Đang lưu...';

        try {
            await api.put(`/api/inventory/ingredients/${ing.id}`, {
                stock_quantity: qty,
                warning_threshold: isNaN(threshold) ? ing.warning_threshold : threshold,
            });
            closeBottomSheet(overlay);
            loadInventoryTab();
            // Refresh dish availability
            api.get('/api/menu/dishes').then(dishes => {
                state.dishes = dishes;
                dishes.forEach(d => state.availabilityMap.set(d.id, {
                    can_serve: d.can_serve,
                    missing_ingredients: d.missing_ingredients,
                }));
            });
        } catch (err) {
            btn.disabled = false;
            btn.textContent = 'Lưu cập nhật';
            const errDiv = document.createElement('div');
            errDiv.className = 'availability-card availability-card--error';
            errDiv.style.marginBottom = '12px';
            errDiv.textContent = err.message;
            overlay.querySelector('.btn-row').parentNode.insertBefore(errDiv, overlay.querySelector('.btn-row'));
        }
    });
}

function openAddIngredient() {
    const overlay = openBottomSheet(`
        <h2 class="sheet-title">Thêm nguyên liệu mới</h2>

        <div class="form-group">
            <label class="form-label">Tên nguyên liệu</label>
            <input class="form-input" type="text" id="new-name" placeholder="VD: Thịt bò, Tôm tươi...">
        </div>

        <div class="form-group">
            <label class="form-label">Đơn vị</label>
            <input class="form-input" type="text" id="new-unit" placeholder="VD: kg, lít, cái, gói...">
        </div>

        <div class="form-group">
            <label class="form-label">Số lượng hiện có</label>
            <input class="form-input" type="number" id="new-stock" value="0" min="0" step="0.1">
        </div>

        <div class="form-group">
            <label class="form-label">Ngưỡng cảnh báo thấp</label>
            <input class="form-input" type="number" id="new-threshold" value="0" min="0" step="0.1">
        </div>

        <div class="btn-row">
            <button class="btn btn--secondary" id="cancel-add-btn" style="flex:1">Hủy</button>
            <button class="btn btn--primary" id="save-add-btn" style="flex:2">Thêm nguyên liệu</button>
        </div>
    `);

    overlay.querySelector('#cancel-add-btn').addEventListener('click', () => closeBottomSheet(overlay));

    overlay.querySelector('#save-add-btn').addEventListener('click', async () => {
        const name = overlay.querySelector('#new-name').value.trim();
        const unit = overlay.querySelector('#new-unit').value.trim();
        const stock = parseFloat(overlay.querySelector('#new-stock').value);
        const threshold = parseFloat(overlay.querySelector('#new-threshold').value) || 0;

        if (!name) { overlay.querySelector('#new-name').focus(); return; }
        if (!unit) { overlay.querySelector('#new-unit').focus(); return; }
        if (isNaN(stock) || stock < 0) { overlay.querySelector('#new-stock').focus(); return; }

        const btn = overlay.querySelector('#save-add-btn');
        btn.disabled = true;
        btn.textContent = 'Đang lưu...';

        try {
            await api.post('/api/inventory/ingredients', {
                name: name,
                unit: unit,
                stock_quantity: stock,
                warning_threshold: threshold,
            });
            closeBottomSheet(overlay);
            loadInventoryTab();
        } catch (err) {
            btn.disabled = false;
            btn.textContent = 'Thêm nguyên liệu';
            const errDiv = document.createElement('div');
            errDiv.className = 'availability-card availability-card--error';
            errDiv.style.marginBottom = '12px';
            errDiv.textContent = err.message;
            overlay.querySelector('.btn-row').parentNode.insertBefore(errDiv, overlay.querySelector('.btn-row'));
        }
    });
}
