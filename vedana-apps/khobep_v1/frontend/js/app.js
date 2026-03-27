/**
 * Kho Bếp — Kitchen Warehouse App
 * Main application logic
 */

// ─── Icon System ─────────────────────────────────
function icon(name, size = 20) {
  const p = {
    'chef-hat': '<path d="M6 13.87A4 4 0 0 1 7.41 6a5.11 5.11 0 0 1 1.05-1.54 5 5 0 0 1 7.08 0A5.11 5.11 0 0 1 16.59 6 4 4 0 0 1 18 13.87V21H6z"/><line x1="6" y1="17" x2="18" y2="17"/>',
    'camera': '<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/>',
    'mic': '<path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/>',
    'edit-3': '<path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/>',
    'package': '<line x1="16.5" y1="9.4" x2="7.5" y2="4.21"/><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/>',
    'utensils': '<path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2"/><path d="M7 2v20"/><path d="M21 15V2a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3zm0 0v7"/>',
    'shopping-cart': '<circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/>',
    'alert-triangle': '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    'alert-circle': '<circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>',
    'check-circle': '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
    'x-circle': '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>',
    'clipboard': '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/>',
    'search': '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    'clock': '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    'user': '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    'check': '<polyline points="20 6 9 17 4 12"/>',
    'x': '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
    'trash-2': '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/>',
    'plus': '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
    'scan': '<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><line x1="7" y1="12" x2="17" y2="12"/>',
    'inbox': '<polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
    'refresh': '<polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>',
    'bar-chart-2': '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
    'upload': '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
    'trending-down': '<polyline points="23 18 13.5 8.5 8.5 13.5 1 6"/><polyline points="17 18 23 18 23 12"/>',
    'chevron-left': '<polyline points="15 18 9 12 15 6"/>',
  };
  const sw = size <= 16 ? 2.5 : 2;
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round">${p[name] || ''}</svg>`;
}

function iconInline(name, size = 14, color = '') {
  const style = `display:inline-flex;vertical-align:middle;line-height:1;${color ? 'color:' + color + ';' : ''}`;
  return `<span style="${style}">${icon(name, size)}</span>`;
}

// ─── State ───────────────────────────────────────
const state = {
  currentTab: 'import',
  // Import screen
  importMethod: null,    // 'camera' | 'voice'
  reviewItems: [],       // [{name, quantity, unit, material_id, item_code, unit_price, amount, location, acc_no, is_new}]
  receiptHeader: null,   // {receipt_date, description, vendor_name, period, voucher_no, invoice_serial, invoice_no}
  receiptSummary: null,  // {sub_amount, discount, vat, total_amount}
  capturedImageB64: null,
  // Inventory screen
  invSubTab: 'materials',
  invSearch: '',
  inventoryData: [],
  dishesData: [],
  dishFilter: 'all',     // 'all'|'available'|'unavailable'
  // Reports
  reportData: null,
  historyData: [],
  lowStockData: [],
};

const UNITS = ['kg', 'g', 'lít', 'ml', 'cái', 'hộp', 'bao', 'bó', 'quả', 'túi', 'lon', 'chai', 'thùng'];

// ─── Init ────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initBottomNav();
  loadTab('import');
});

function initBottomNav() {
  document.querySelectorAll('.bottom-nav__item').forEach(item => {
    item.addEventListener('click', () => {
      document.querySelectorAll('.bottom-nav__item').forEach(i => i.classList.remove('bottom-nav__item--active'));
      item.classList.add('bottom-nav__item--active');
      loadTab(item.dataset.tab);
    });
  });
}

function loadTab(tab) {
  state.currentTab = tab;
  const titles = { import: 'Nhập Kho', inventory: 'Tồn Kho', reports: 'Báo Cáo' };
  document.getElementById('page-title').textContent = titles[tab] || tab;
  document.getElementById('page-subtitle').textContent = '';
  document.getElementById('top-bar-actions').innerHTML = '';

  switch (tab) {
    case 'import':    renderImportTab(); break;
    case 'inventory': renderInventoryTab(); break;
    case 'reports':   renderReportsTab(); break;
  }
}

// ─── Toast ───────────────────────────────────────
let toastTimer = null;
function showToast(msg, type = 'success') {
  let toast = document.getElementById('toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast';
    toast.className = 'toast';
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.className = `toast toast--${type} toast--visible`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('toast--visible'), 2500);
}

// ─── Bottom Sheet ────────────────────────────────
function openBottomSheet(html) {
  const overlay = document.getElementById('sheet-overlay');
  overlay.hidden = false;
  overlay.innerHTML = `<div class="bottom-sheet"><div class="sheet-handle"></div>${html}</div>`;
  overlay.addEventListener('click', e => { if (e.target === overlay) closeBottomSheet(); }, { once: true });
  return overlay;
}

function closeBottomSheet() {
  const overlay = document.getElementById('sheet-overlay');
  overlay.hidden = true;
  overlay.innerHTML = '';
}

// ─── Helpers ─────────────────────────────────────
function escapeHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function formatTime(dt) {
  // Server stores UTC — append 'Z' if no timezone info so JS parses as UTC
  const raw = String(dt);
  const d = new Date(/[Z+\-]\d|[Z]$/i.test(raw) ? raw : raw + 'Z');
  const fmt = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Ho_Chi_Minh',
    hour: '2-digit', minute: '2-digit',
    day: '2-digit', month: '2-digit',
    hour12: false,
  });
  const p = Object.fromEntries(fmt.formatToParts(d).map(x => [x.type, x.value]));
  return `${p.hour}:${p.minute} — ${p.day}/${p.month}`;
}

function formatQty(qty, unit) {
  const v = parseFloat(qty);
  return `${v % 1 === 0 ? v.toFixed(0) : v.toFixed(1)} ${unit}`;
}

function showLoading(container) {
  container.innerHTML = `<div class="loading-screen"><div class="spinner"></div></div>`;
}

function showEmpty(container, title, text) {
  container.innerHTML = `<div class="empty-state"><div class="empty-state__icon">${icon('package', 40)}</div><div class="empty-state__title">${escapeHtml(title)}</div><p class="empty-state__text">${escapeHtml(text)}</p></div>`;
}

function showError(container, msg) {
  container.innerHTML = `<div class="empty-state"><div class="empty-state__icon" style="color:var(--warning);">${icon('alert-triangle', 40)}</div><div class="empty-state__title">Có lỗi xảy ra</div><p class="empty-state__text">${escapeHtml(msg)}</p><button class="btn btn--secondary mt-md" onclick="loadTab('${state.currentTab}')">Thử lại</button></div>`;
}

// =============================================
// TAB 1: NHẬP KHO
// =============================================
function renderImportTab() {
  state.reviewItems = [];
  state.capturedImageB64 = null;
  state.importMethod = null;
  state.receiptHeader = null;
  state.receiptSummary = null;
  renderImportSelectPage();
}

function renderImportSelectPage() {
  document.getElementById('page-title').textContent = 'Nhập Kho';
  document.getElementById('page-subtitle').textContent = '';
  document.getElementById('top-bar-actions').innerHTML = '';

  const content = document.getElementById('content');
  content.innerHTML = `
    <div style="padding: var(--space-xl) var(--space-lg);">

      <!-- Header -->
      <div style="text-align:center; padding:var(--space-lg) 0 var(--space-2xl);">
        <div style="width:64px;height:64px;border-radius:var(--radius-xl);background:linear-gradient(135deg,var(--orange),var(--orange-dark));display:flex;align-items:center;justify-content:center;margin:0 auto var(--space-lg);color:white;box-shadow:var(--shadow-orange);">
          ${icon('upload', 28)}
        </div>
        <h2 style="font-size:var(--text-2xl); font-weight:800; color:var(--text); letter-spacing:-0.5px; margin-bottom:4px;">Nhập Nguyên Vật Liệu</h2>
        <p style="font-size:var(--text-sm); color:var(--text-muted);">
          ${new Date().toLocaleDateString('vi-VN', {weekday:'long', day:'2-digit', month:'2-digit', year:'numeric', timeZone:'Asia/Ho_Chi_Minh'})}
        </p>
      </div>

      <!-- Method Cards -->
      <div class="method-grid">
        <button class="method-card" onclick="startCameraInput()">
          <div class="method-card__icon" style="background:var(--orange);color:white;box-shadow:var(--shadow-orange);">
            ${icon('camera', 26)}
          </div>
          <div class="method-card__title">Chụp Ảnh Hoá Đơn</div>
          <div class="method-card__desc">AI tự động nhận diện nguyên vật liệu</div>
        </button>

        <button class="method-card" onclick="startVoiceInput()">
          <div class="method-card__icon" style="background:#EEF2FF;color:#6366F1;">
            ${icon('mic', 26)}
          </div>
          <div class="method-card__title">Nhập Bằng Giọng Nói</div>
          <div class="method-card__desc">Nói tên và số lượng nguyên liệu</div>
        </button>
      </div>

      <button class="method-card method-card--wide" onclick="openManualAdd()">
        <div class="method-card__icon method-card__icon--sm" style="background:var(--success-bg);color:var(--success);">
          ${icon('edit-3', 22)}
        </div>
        <div style="text-align:left;">
          <div class="method-card__title" style="margin-bottom:2px;">Nhập Thủ Công</div>
          <div class="method-card__desc">Chọn nguyên vật liệu từ danh sách có sẵn</div>
        </div>
      </button>

    </div>
  `;
}

function renderImportReviewPage() {
  document.getElementById('page-title').textContent = 'Xác nhận nhập';
  document.getElementById('page-subtitle').textContent = state.reviewItems.length > 0 ? `${state.reviewItems.length} mặt hàng` : '';
  document.getElementById('top-bar-actions').innerHTML = `
    <button class="top-bar__btn" onclick="openAddItem()" title="Thêm mặt hàng">
      ${icon('plus', 20)}
    </button>
  `;

  const h = state.receiptHeader;
  const s = state.receiptSummary;

  const headerHtml = h ? `
    <div class="receipt-header-card">
      <div class="receipt-header-card__title">${icon('clipboard', 16)} Thông tin phiếu nhập</div>
      <div class="receipt-header-grid">
        ${h.voucher_no ? `<div class="receipt-field"><span class="receipt-field__label">Số phiếu</span><span class="receipt-field__value">${escapeHtml(h.voucher_no)}</span></div>` : ''}
        ${h.receipt_date ? `<div class="receipt-field"><span class="receipt-field__label">Ngày nhập</span><span class="receipt-field__value">${escapeHtml(h.receipt_date)}</span></div>` : ''}
        ${h.vendor_name ? `<div class="receipt-field receipt-field--wide"><span class="receipt-field__label">Nhà cung cấp</span><span class="receipt-field__value">${escapeHtml(h.vendor_name)}</span></div>` : ''}
        ${h.description ? `<div class="receipt-field receipt-field--wide"><span class="receipt-field__label">Nội dung</span><span class="receipt-field__value">${escapeHtml(h.description)}</span></div>` : ''}
        ${h.invoice_no ? `<div class="receipt-field"><span class="receipt-field__label">Số HĐ</span><span class="receipt-field__value">${escapeHtml(h.invoice_no)}</span></div>` : ''}
        ${h.invoice_serial ? `<div class="receipt-field"><span class="receipt-field__label">Seri HĐ</span><span class="receipt-field__value">${escapeHtml(h.invoice_serial)}</span></div>` : ''}
        ${h.period ? `<div class="receipt-field"><span class="receipt-field__label">Kỳ KT</span><span class="receipt-field__value">${escapeHtml(h.period)}</span></div>` : ''}
      </div>
    </div>
  ` : '';

  const summaryHtml = s ? `
    <div class="receipt-summary-card">
      <div class="receipt-summary-row">
        <span>Thành tiền</span>
        <span>${s.sub_amount != null ? Number(s.sub_amount).toLocaleString('vi-VN') + ' đ' : '-'}</span>
      </div>
      ${s.discount ? `<div class="receipt-summary-row"><span>Giảm giá</span><span>${Number(s.discount).toLocaleString('vi-VN')} đ</span></div>` : ''}
      ${s.vat ? `<div class="receipt-summary-row"><span>Thuế GTGT</span><span>${Number(s.vat).toLocaleString('vi-VN')} đ</span></div>` : ''}
      <div class="receipt-summary-row receipt-summary-row--total">
        <span>Tổng cộng</span>
        <span>${s.total_amount != null ? Number(s.total_amount).toLocaleString('vi-VN') + ' đ' : '-'}</span>
      </div>
    </div>
  ` : '';

  const content = document.getElementById('content');
  content.innerHTML = `
    <div style="padding: var(--space-lg);">
      <button class="back-link" onclick="backToImportSelect()">
        ${icon('chevron-left', 16)} Chọn phương thức khác
      </button>

      ${headerHtml}

      <div style="background:var(--white); border-radius:var(--radius-lg); overflow:hidden; box-shadow:var(--shadow-sm); margin-top:var(--space-md);">
        <div id="review-list"></div>
      </div>

      ${summaryHtml}

      <div class="form-group mt-lg">
        <label class="form-label" for="supplier-input">Người bàn giao (tuỳ chọn)</label>
        <input class="form-input" type="text" id="supplier-input" placeholder="Tên bộ phận thu mua / nhà cung cấp" value="${h && h.vendor_name ? escapeHtml(h.vendor_name) : ''}">
      </div>
      <button class="btn btn--primary btn--full btn--lg" id="btn-confirm" onclick="confirmImport()">
        ${icon('check', 18)} Xác Nhận Nhập Kho
      </button>
    </div>
  `;

  updateReviewList();
}

function backToImportSelect() {
  state.reviewItems = [];
  renderImportSelectPage();
}

// ─── Camera Input ─────────────────────────────────
function startCameraInput() {
  const input = document.getElementById('camera-input');
  input.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (ev) => {
      state.capturedImageB64 = ev.target.result;
      await processOcrImage(ev.target.result);
    };
    reader.readAsDataURL(file);
  };
  input.click();
}

async function processOcrImage(dataUrl) {
  const content = document.getElementById('content');

  content.innerHTML = `
    <div style="padding: var(--space-xl) var(--space-lg);">
      <img src="${dataUrl}" class="camera-preview" style="width:100%; margin-bottom:var(--space-lg); border-radius:var(--radius-lg);">
      <div class="ocr-processing">
        <div style="color:var(--orange);">${icon('scan', 44)}</div>
        <div class="spinner" style="margin:0 auto;"></div>
        <p class="text-muted text-sm text-center">Đang phân tích phiếu nhập kho...<br>Vui lòng đợi trong giây lát</p>
      </div>
    </div>
  `;

  try {
    const result = await api.post('/api/ocr/image', { image_base64: dataUrl });

    // New response format: {header, items, summary}
    state.receiptHeader = result.header || null;
    state.receiptSummary = result.summary || null;
    state.reviewItems = (result.items || []).map(item => ({
      name: item.name,
      quantity: item.quantity,
      unit: item.unit,
      material_id: item.material_id,
      item_code: item.item_code || null,
      unit_price: item.unit_price || null,
      amount: item.amount || null,
      location: item.location || null,
      acc_no: item.acc_no || null,
      is_new: item.is_new || false,
    }));

    if (state.currentTab !== 'import') return;
    if (state.reviewItems.length === 0) {
      showToast('Không nhận diện được. Thử nhập thủ công.', 'error');
    } else {
      showToast(`Nhận diện được ${state.reviewItems.length} mặt hàng`, 'success');
    }
    renderImportReviewPage();
  } catch (err) {
    showToast('Lỗi nhận diện ảnh: ' + err.message, 'error');
    if (state.currentTab === 'import') renderImportReviewPage();
  }
}

// ─── Voice Input ──────────────────────────────────
function startVoiceInput() {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    showToast('Trình duyệt không hỗ trợ giọng nói. Dùng Chrome hoặc nhập thủ công.', 'error');
    return;
  }

  const overlay = openBottomSheet(`
    <div class="text-center" style="padding: var(--space-xl) 0;">
      <h2 style="font-size:var(--text-xl); font-weight:700; margin-bottom:var(--space-md);">Nhập Giọng Nói</h2>
      <div class="voice-ring" id="voice-btn">${icon('mic', 32)}</div>
      <p class="text-muted text-sm" id="voice-hint" style="margin-top:var(--space-lg); line-height:1.6;">
        Nhấn vào nút micro để bắt đầu<br>
        <span style="font-size:11px;">Ví dụ: "5 kg thịt bò, 3 lít nước mắm, 2 bó rau cải"</span>
      </p>
      <div class="voice-transcript mt-lg" id="voice-transcript" style="display:none;"></div>
      <button class="btn btn--primary btn--full mt-lg" id="voice-submit" style="display:none;" onclick="submitVoiceTranscript()">
        Xác nhận & Phân tích
      </button>
    </div>
  `);

  const recognition = new SpeechRecognition();
  recognition.lang = 'vi-VN';
  recognition.continuous = false;
  recognition.interimResults = true;

  let finalTranscript = '';
  let isListening = false;

  const voiceBtn = document.getElementById('voice-btn');
  const voiceHint = document.getElementById('voice-hint');
  const voiceTranscript = document.getElementById('voice-transcript');

  voiceBtn.addEventListener('click', () => {
    if (isListening) {
      recognition.stop();
      return;
    }
    isListening = true;
    finalTranscript = '';
    voiceBtn.classList.add('voice-ring--listening');
    voiceHint.innerHTML = '<span class="rec-dot"></span> Đang nghe... Nói tên và số lượng nguyên liệu';
    voiceTranscript.style.display = 'none';
    recognition.start();
  });

  recognition.onresult = e => {
    let interim = '';
    finalTranscript = '';
    for (let i = 0; i < e.results.length; i++) {
      if (e.results[i].isFinal) finalTranscript += e.results[i][0].transcript + ' ';
      else interim += e.results[i][0].transcript;
    }
    voiceTranscript.style.display = 'block';
    voiceTranscript.textContent = finalTranscript || interim || '...';
  };

  recognition.onend = () => {
    isListening = false;
    voiceBtn.classList.remove('voice-ring--listening');
    if (finalTranscript.trim()) {
      voiceHint.innerHTML = `${iconInline('check-circle', 15, 'var(--success)')} Đã ghi âm xong. Nhấn Xác nhận để phân tích.`;
      document.getElementById('voice-submit').style.display = 'flex';
      document.getElementById('voice-submit').dataset.transcript = finalTranscript.trim();
    } else {
      voiceHint.innerHTML = 'Không nghe thấy gì. Nhấn nút để thử lại.<br><span style="font-size:11px;">Ví dụ: "5 kg thịt bò, 3 lít nước mắm"</span>';
    }
  };

  recognition.onerror = () => {
    isListening = false;
    voiceBtn.classList.remove('voice-ring--listening');
    voiceHint.textContent = 'Lỗi micro. Thử lại hoặc dùng nhập thủ công.';
  };
}

async function submitVoiceTranscript() {
  const btn = document.getElementById('voice-submit');
  const transcript = btn.dataset.transcript;
  closeBottomSheet();

  // Show processing
  showToast('Đang phân tích giọng nói...', 'success');

  try {
    const result = await api.post('/api/ocr/voice', { transcript });
    state.reviewItems = result.items || [];
    if (state.currentTab !== 'import') return;
    if (state.reviewItems.length === 0) {
      showToast('Không nhận diện được. Thêm thủ công.', 'error');
    } else {
      showToast(`Nhận diện được ${state.reviewItems.length} mặt hàng`, 'success');
    }
    renderImportReviewPage();
  } catch (err) {
    showToast('Lỗi phân tích: ' + err.message, 'error');
    if (state.currentTab === 'import') renderImportReviewPage();
  }
}

// ─── Manual Add ───────────────────────────────────
function openManualAdd() {
  renderImportReviewPage();
  setTimeout(() => openAddItem(), 200);
}

async function openAddItem() {
  // Load materials for selection
  let materials = [];
  try { materials = await api.get('/api/materials'); } catch (e) { /* ignore */ }

  const overlay = openBottomSheet(`
    <h2 style="font-size:var(--text-lg); font-weight:700; margin-bottom:var(--space-lg);">Thêm Nguyên Vật Liệu</h2>

    <div class="search-bar" style="margin:0 0 var(--space-md);">
      <span class="search-bar__icon">${icon('search', 16)}</span>
      <input class="search-bar__input" type="text" id="mat-search" placeholder="Tìm nguyên vật liệu..." autocomplete="off">
    </div>

    <div class="mat-selector-list" id="mat-list">
      ${materials.map(m => `
        <div class="mat-selector-item" onclick="selectMaterial(${m.id}, '${escapeHtml(m.name)}', '${m.unit}')">
          <span class="mat-selector-item__name">${escapeHtml(m.name)}</span>
          <span class="mat-selector-item__unit">${m.unit}</span>
        </div>
      `).join('')}
    </div>

    <div class="divider mt-md mb-md"></div>
    <div style="font-size:var(--text-xs); color:var(--text-muted); text-align:center;">
      Hoặc nhập tên mới nếu không tìm thấy trong danh sách
    </div>
    <input class="form-input mt-md" type="text" id="custom-mat-name" placeholder="Tên nguyên vật liệu mới...">
    <div class="unit-pills mt-sm" id="custom-unit-pills">
      ${UNITS.map((u,i) => `<button class="unit-pill${i===0?' unit-pill--active':''}" onclick="selectCustomUnit('${u}',this)">${u}</button>`).join('')}
    </div>
    <button class="btn btn--ghost btn--full mt-md" onclick="addCustomItem()">+ Thêm mặt hàng mới</button>
  `);

  // Search filter
  document.getElementById('mat-search').addEventListener('input', e => {
    const q = e.target.value.toLowerCase();
    document.querySelectorAll('.mat-selector-item').forEach(item => {
      item.style.display = item.querySelector('.mat-selector-item__name').textContent.toLowerCase().includes(q) ? '' : 'none';
    });
  });
}

let selectedCustomUnit = 'kg';
function selectCustomUnit(unit, el) {
  selectedCustomUnit = unit;
  document.querySelectorAll('.unit-pill').forEach(p => p.classList.remove('unit-pill--active'));
  el.classList.add('unit-pill--active');
}

function selectMaterial(id, name, unit) {
  openAddQtySheet(id, name, unit);
}

function addCustomItem() {
  const nameEl = document.getElementById('custom-mat-name');
  const name = nameEl?.value.trim();
  if (!name) { showToast('Nhập tên nguyên vật liệu', 'error'); return; }
  openAddQtySheet(null, name, selectedCustomUnit);
}

function openAddQtySheet(materialId, name, unit) {
  closeBottomSheet();
  const overlay = openBottomSheet(`
    <h2 style="font-size:var(--text-lg); font-weight:700; margin-bottom:4px;">${escapeHtml(name)}</h2>
    <p class="text-muted text-sm mb-lg">Nhập số lượng nhận được</p>

    <div class="form-group">
      <label class="form-label">Số lượng</label>
      <div style="display:flex; gap:var(--space-md); align-items:center;">
        <div class="stepper" style="flex:1;">
          <button class="stepper__btn" onclick="stepQty(-1, '${unit}')">−</button>
          <input class="stepper__value" type="number" id="qty-input" value="1" min="0.1" step="0.5">
          <button class="stepper__btn" onclick="stepQty(1, '${unit}')">+</button>
        </div>
        <div style="min-width:60px;">
          <select class="form-select" id="unit-select" style="min-height:44px;">
            ${UNITS.map(u => `<option value="${u}" ${u===unit?'selected':''}>${u}</option>`).join('')}
          </select>
        </div>
      </div>
    </div>

    <!-- Quick qty buttons -->
    <div class="chips-row" style="padding:0; margin-bottom:var(--space-lg);">
      ${['0.5','1','2','3','5','10','20'].map(v => `<button class="chip" onclick="setQty(${v})">${v}</button>`).join('')}
    </div>

    <button class="btn btn--primary btn--full" onclick="addReviewItem(${materialId}, '${escapeHtml(name).replace(/'/g,"\\'")}')">
      + Thêm vào danh sách
    </button>
  `);

  document.getElementById('qty-input').focus();
  document.getElementById('qty-input').select();
}

function stepQty(delta, unit) {
  const input = document.getElementById('qty-input');
  let val = parseFloat(input.value) || 0;
  const step = ['g','ml'].includes(unit) ? 50 : 0.5;
  val = Math.max(0.1, val + delta * step);
  input.value = val % 1 === 0 ? val.toFixed(0) : parseFloat(val.toFixed(1));
}

function setQty(val) {
  const input = document.getElementById('qty-input');
  if (input) { input.value = val; input.focus(); }
}

function addReviewItem(materialId, name) {
  const qty = parseFloat(document.getElementById('qty-input')?.value) || 1;
  const unit = document.getElementById('unit-select')?.value || 'kg';
  closeBottomSheet();
  state.reviewItems.push({ name, quantity: qty, unit, material_id: materialId });
  updateReviewList();
  showToast(`Đã thêm: ${name} (${qty} ${unit})`);
}

// ─── Review List ──────────────────────────────────
function updateReviewList() {
  const listEl = document.getElementById('review-list');
  if (!listEl) return;

  const subtitle = document.getElementById('page-subtitle');
  if (subtitle && state.currentTab === 'import') {
    subtitle.textContent = state.reviewItems.length > 0 ? `${state.reviewItems.length} mặt hàng` : '';
  }

  if (state.reviewItems.length === 0) {
    listEl.innerHTML = `<div class="empty-state" style="padding:24px;"><div class="empty-state__icon">${icon('shopping-cart', 36)}</div><p class="empty-state__text">Chưa có nguyên vật liệu nào.<br>Nhấn nút + ở góc phải để thêm.</p></div>`;
    return;
  }

  listEl.innerHTML = state.reviewItems.map((item, idx) => {
    const badge = item.is_new
      ? `<span class="badge badge--new">Mới</span>`
      : (!item.material_id ? ` ${iconInline('alert-triangle', 13, 'var(--warning)')}` : '');
    const priceInfo = item.unit_price != null
      ? `<span class="text-xs text-muted">${Number(item.unit_price).toLocaleString('vi-VN')} đ/${item.unit}</span>`
      : '';
    const amountInfo = item.amount != null
      ? `<span class="text-xs" style="color:var(--orange);font-weight:600;">${Number(item.amount).toLocaleString('vi-VN')} đ</span>`
      : '';

    return `
      <div class="review-item">
        <div class="review-item__num">${idx + 1}</div>
        <div style="flex:1; min-width:0;">
          <div class="review-item__name">
            ${escapeHtml(item.name)} ${badge}
          </div>
          <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
            ${item.item_code ? `<span class="text-xs text-muted">Mã: ${escapeHtml(item.item_code)}</span>` : ''}
            ${priceInfo}
            ${amountInfo}
          </div>
        </div>
        <div class="stepper">
          <button class="stepper__btn" onclick="changeItemQty(${idx}, -0.5)">−</button>
          <span class="stepper__value">${parseFloat(item.quantity).toFixed(item.quantity % 1 === 0 ? 0 : 1)} ${item.unit}</span>
          <button class="stepper__btn" onclick="changeItemQty(${idx}, 0.5)">+</button>
        </div>
        <button class="review-item__delete" onclick="removeReviewItem(${idx})">${icon('x', 14)}</button>
      </div>
    `;
  }).join('');
}

function changeItemQty(idx, delta) {
  const item = state.reviewItems[idx];
  if (!item) return;
  item.quantity = Math.max(0.1, parseFloat(item.quantity) + delta);
  updateReviewList();
}

function removeReviewItem(idx) {
  state.reviewItems.splice(idx, 1);
  updateReviewList();
}

// ─── Confirm Import ───────────────────────────────
async function confirmImport() {
  if (state.reviewItems.length === 0) { showToast('Chưa có nguyên vật liệu', 'error'); return; }

  // All items should have material_id now (auto-created by backend)
  const validItems = state.reviewItems.filter(i => i.material_id);
  if (validItems.length === 0) {
    showToast('Không có mặt hàng nào hợp lệ', 'error');
    return;
  }

  const btn = document.getElementById('btn-confirm');
  if (btn) { btn.disabled = true; btn.innerHTML = `<div class="spinner spinner--sm spinner--white"></div> Đang lưu...`; }

  const supplier = document.getElementById('supplier-input')?.value || '';
  const h = state.receiptHeader;

  try {
    await api.post('/api/imports', {
      supplier_name: supplier || null,
      created_by: 'Nhân viên kho',
      // Header fields from OCR
      receipt_date: h?.receipt_date || null,
      description: h?.description || null,
      vendor_name: h?.vendor_name || null,
      period: h?.period || null,
      voucher_no: h?.voucher_no || null,
      invoice_serial: h?.invoice_serial || null,
      invoice_no: h?.invoice_no || null,
      // Items with full details
      items: validItems.map(i => ({
        material_id: i.material_id,
        quantity: i.quantity,
        unit: i.unit,
        item_code: i.item_code || null,
        item_name: i.name || null,
        unit_price: i.unit_price || null,
        amount: i.amount || null,
        location: i.location || null,
        acc_no: i.acc_no || null,
      })),
    });

    showToast(`Nhập kho thành công ${validItems.length} mặt hàng!`, 'success');

    // Reset
    state.reviewItems = [];
    state.receiptHeader = null;
    state.receiptSummary = null;
    renderImportTab();
  } catch (err) {
    showToast('Lỗi: ' + err.message, 'error');
    if (btn) { btn.disabled = false; btn.innerHTML = `${icon('check', 18)} Xác Nhận Nhập Kho`; }
  }
}

// =============================================
// TAB 2: TỒN KHO
// =============================================
function renderInventoryTab() {
  const content = document.getElementById('content');

  // Add recalculate button to top bar
  document.getElementById('top-bar-actions').innerHTML = `
    <button class="top-bar__btn" id="btn-recalc" title="Cập nhật trạng thái món ăn" onclick="recalculateDishes()">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
        <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
      </svg>
    </button>
  `;

  content.innerHTML = `
    <div class="sub-tabs" id="inv-sub-tabs">
      <button class="sub-tab ${state.invSubTab==='materials'?'sub-tab--active':''}" onclick="switchInvTab('materials')">${icon('package', 15)} Nguyên Liệu</button>
      <button class="sub-tab ${state.invSubTab==='dishes'?'sub-tab--active':''}" onclick="switchInvTab('dishes')">${icon('utensils', 15)} Món Ăn</button>
    </div>
    <div id="inv-content"></div>
  `;

  if (state.invSubTab === 'materials') loadMaterialsTab();
  else loadDishesTab();
}

function switchInvTab(tab) {
  state.invSubTab = tab;
  document.querySelectorAll('.sub-tab').forEach(t => {
    t.classList.toggle('sub-tab--active', t.textContent.includes(tab === 'materials' ? 'Nguyên' : 'Món'));
  });
  if (tab === 'materials') loadMaterialsTab();
  else loadDishesTab();
}

async function loadMaterialsTab() {
  const invContent = document.getElementById('inv-content');
  showLoading(invContent);

  try {
    const data = await api.get('/api/inventory');
    state.inventoryData = data;
    renderMaterialsList(data);
  } catch (err) {
    showError(invContent, err.message);
  }
}

function renderMaterialsList(data) {
  const invContent = document.getElementById('inv-content');
  const filtered = data.filter(m =>
    !state.invSearch || m.material_name.toLowerCase().includes(state.invSearch.toLowerCase())
  );

  const outCount = data.filter(m => m.stock_status === 'out').length;
  const lowCount = data.filter(m => m.stock_status === 'low').length;

  invContent.innerHTML = `
    <div class="search-bar">
      <span class="search-bar__icon">${icon('search', 16)}</span>
      <input class="search-bar__input" type="text" placeholder="Tìm nguyên vật liệu..." value="${escapeHtml(state.invSearch)}" id="inv-search-input" autocomplete="off">
    </div>

    ${outCount > 0 ? `<div class="alert alert--danger" style="margin-bottom:var(--space-sm);"><span class="alert__icon" style="color:var(--danger);">${icon('alert-circle', 18)}</span><span class="alert__text">${outCount} nguyên liệu đã HẾT</span></div>` : ''}
    ${lowCount > 0 ? `<div class="alert alert--warning" style="margin-bottom:var(--space-sm);"><span class="alert__icon" style="color:var(--warning);">${icon('alert-triangle', 18)}</span><span class="alert__text">${lowCount} nguyên liệu SẮP HẾT</span></div>` : ''}

    <div style="background:var(--white); border-radius:var(--radius-lg); overflow:hidden; box-shadow:var(--shadow-sm); margin:0 var(--space-lg);">
      ${filtered.length === 0
        ? `<div class="empty-state"><div class="empty-state__icon">${icon('search', 36)}</div><p class="empty-state__text">Không tìm thấy</p></div>`
        : filtered.map(m => `
          <div class="mat-item" onclick="showMaterialDetail(${m.material_id})">
            <div class="mat-item__dot mat-item__dot--${m.stock_status}"></div>
            <div class="mat-item__info">
              <div class="mat-item__name">${escapeHtml(m.material_name)}</div>
              ${m.min_stock > 0 ? `<div class="mat-item__detail">Ngưỡng: ${m.min_stock} ${m.unit}</div>` : ''}
            </div>
            <div class="mat-item__qty">
              <div class="mat-item__qty-val">${parseFloat(m.quantity).toFixed(m.quantity % 1 === 0 ? 0 : 1)}</div>
              <div class="mat-item__qty-unit">${m.unit}</div>
            </div>
          </div>
        `).join('')}
    </div>
    <div style="padding:var(--space-md) var(--space-lg); text-align:center;">
      <span style="font-size:var(--text-xs); color:var(--text-faint);">${filtered.length} nguyên vật liệu</span>
    </div>
  `;

  document.getElementById('inv-search-input')?.addEventListener('input', e => {
    state.invSearch = e.target.value;
    renderMaterialsList(state.inventoryData);
  });
}

function showMaterialDetail(materialId) {
  const mat = state.inventoryData.find(m => m.material_id === materialId);
  if (!mat) return;

  const fillPct = mat.min_stock > 0
    ? Math.min(100, (mat.quantity / (mat.min_stock * 2)) * 100)
    : mat.quantity > 0 ? 70 : 0;

  openBottomSheet(`
    <h2 style="font-size:var(--text-xl); font-weight:700; margin-bottom:4px;">${escapeHtml(mat.material_name)}</h2>
    <p class="text-muted text-sm mb-lg">Chi tiết tồn kho</p>

    <div style="text-align:center; padding:var(--space-xl) 0;">
      <div style="font-size:52px; font-weight:800; letter-spacing:-1px; color:${mat.stock_status==='out'?'var(--danger)':mat.stock_status==='low'?'var(--warning)':'var(--success)'};">
        ${parseFloat(mat.quantity).toFixed(mat.quantity % 1 === 0 ? 0 : 1)}
      </div>
      <div style="font-size:var(--text-lg); color:var(--text-muted); font-weight:600;">${mat.unit}</div>
    </div>

    <div style="background:var(--border); height:8px; border-radius:var(--radius-full); margin-bottom:var(--space-lg); overflow:hidden;">
      <div style="height:100%; width:${fillPct}%; background:${mat.stock_status==='out'?'var(--danger)':mat.stock_status==='low'?'var(--warning)':'var(--success)'}; border-radius:var(--radius-full); transition:width 0.5s;"></div>
    </div>

    <div style="background:var(--bg); border-radius:var(--radius-md); padding:var(--space-lg); display:flex; justify-content:space-between;">
      <div>
        <div class="text-xs text-muted" style="text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;">Trạng thái</div>
        <span class="badge badge--${mat.stock_status}">
          ${mat.stock_status==='ok'?`${icon('check', 12)} Đủ hàng`:mat.stock_status==='low'?`${icon('alert-triangle', 12)} Sắp hết`:`${icon('x', 12)} Hết hàng`}
        </span>
      </div>
      ${mat.min_stock > 0 ? `<div>
        <div class="text-xs text-muted" style="text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;">Ngưỡng tối thiểu</div>
        <div style="font-size:var(--text-base); font-weight:700;">${mat.min_stock} ${mat.unit}</div>
      </div>` : ''}
    </div>

    <button class="btn btn--primary btn--full mt-lg" onclick="closeBottomSheet(); document.querySelector('[data-tab=import]').click()">
      + Nhập thêm ${escapeHtml(mat.material_name)}
    </button>
  `);
}

async function loadDishesTab() {
  const invContent = document.getElementById('inv-content');
  showLoading(invContent);

  try {
    const data = await api.get('/api/dishes');
    state.dishesData = data;
    renderDishesList(data);
  } catch (err) {
    showError(invContent, err.message);
  }
}

function renderDishesList(data) {
  const invContent = document.getElementById('inv-content');
  const available = data.filter(d => d.is_available).length;
  const unavailable = data.filter(d => !d.is_available).length;

  const filtered = state.dishFilter === 'available' ? data.filter(d => d.is_available)
    : state.dishFilter === 'unavailable' ? data.filter(d => !d.is_available)
    : data;

  invContent.innerHTML = `
    <div class="chips-row" style="padding-top:var(--space-md); padding-bottom:var(--space-md);">
      <button class="chip ${state.dishFilter==='all'?'chip--active':''}" onclick="filterDishes('all')">Tất cả (${data.length})</button>
      <button class="chip ${state.dishFilter==='available'?'chip--active':''}" onclick="filterDishes('available')">${icon('check', 12)} Phục vụ (${available})</button>
      <button class="chip ${state.dishFilter==='unavailable'?'chip--active':''}" onclick="filterDishes('unavailable')">${icon('x', 12)} Hết NL (${unavailable})</button>
    </div>

    <div class="dish-grid">
      ${filtered.map(d => {
        const catColor = {'Phở':'background:#FEF3C7;color:#D97706;','Bún':'background:#FEE2E2;color:#DC2626;','Cơm':'background:#DCFCE7;color:#16A34A;','Lẩu':'background:#FCE7F3;color:#DB2777;'}[d.category] || '';
        return `
          <div class="dish-card ${d.is_available?'':'dish-card--unavailable'}" onclick="showDishDetail(${d.id})">
            <div class="dish-card__emoji" ${catColor ? `style="${catColor}"` : ''}>${icon('utensils', 20)}</div>
            <div class="dish-card__name">${escapeHtml(d.name)}</div>
            <div class="dish-card__category">${escapeHtml(d.category || '')}</div>
            <span class="badge badge--${d.is_available?'available':'unavailable'}">
              ${d.is_available ? `${icon('check', 11)} Phục vụ` : `${icon('x', 11)} Hết NL`}
            </span>
          </div>
        `;
      }).join('')}
    </div>
  `;
}

function filterDishes(filter) {
  state.dishFilter = filter;
  renderDishesList(state.dishesData);
}

function showDishDetail(dishId) {
  const dish = state.dishesData.find(d => d.id === dishId);
  if (!dish) return;
  const missingList = dish.missing_ingredients?.length > 0
    ? dish.missing_ingredients.map(n => `<li style="padding:4px 0; border-bottom:1px solid var(--border-light);">• ${escapeHtml(n)}</li>`).join('')
    : '';

  openBottomSheet(`
    <div style="text-align:center; margin-bottom:var(--space-xl);">
      <div class="dish-card__emoji" style="width:56px;height:56px;margin:0 auto 8px;border-radius:var(--radius-lg);">${icon('utensils', 28)}</div>
      <h2 style="font-size:var(--text-xl); font-weight:800; margin-bottom:4px;">${escapeHtml(dish.name)}</h2>
      <span class="badge badge--${dish.is_available?'available':'unavailable'}">
        ${dish.is_available ? `${icon('check', 11)} Có thể phục vụ` : `${icon('x', 11)} Hết nguyên liệu`}
      </span>
    </div>
    ${missingList ? `
      <div style="background:var(--danger-bg); border-radius:var(--radius-md); padding:var(--space-lg); margin-bottom:var(--space-lg);">
        <div style="font-size:var(--text-sm); font-weight:700; color:var(--danger); margin-bottom:var(--space-sm);">Thiếu nguyên liệu:</div>
        <ul style="font-size:var(--text-sm); color:var(--danger);">${missingList}</ul>
      </div>
    ` : ''}
    ${dish.is_available ? '' : `
      <button class="btn btn--primary btn--full" onclick="closeBottomSheet(); document.querySelector('[data-tab=import]').click()">
        Đi nhập kho ngay
      </button>
    `}
  `);
}

async function recalculateDishes() {
  const btn = document.getElementById('btn-recalc');
  if (btn) btn.style.opacity = '0.5';
  try {
    await api.post('/api/inventory/recalculate', {});
    showToast('Đã cập nhật trạng thái món ăn', 'success');
    if (state.invSubTab === 'dishes') loadDishesTab();
  } catch (err) {
    showToast('Lỗi: ' + err.message, 'error');
  } finally {
    if (btn) btn.style.opacity = '1';
  }
}

// =============================================
// TAB 3: BÁO CÁO
// =============================================
async function renderReportsTab() {
  const content = document.getElementById('content');
  showLoading(content);

  try {
    const [overview, history, lowStock] = await Promise.all([
      api.get('/api/reports/overview'),
      api.get('/api/reports/history', { limit: 10 }),
      api.get('/api/reports/low-stock'),
    ]);
    state.reportData = overview;
    state.historyData = history;
    state.lowStockData = lowStock;
    renderReports(overview, history, lowStock);
  } catch (err) {
    showError(content, err.message);
  }
}

function renderReports(overview, history, lowStock) {
  const content = document.getElementById('content');

  const today = new Date().toLocaleDateString('vi-VN', { day:'2-digit', month:'2-digit', timeZone:'Asia/Ho_Chi_Minh' });

  content.innerHTML = `

    <!-- Stats Grid -->
    <div class="stats-grid">
      <div class="stat-card stat-card--orange">
        <div class="stat-card__icon">${icon('utensils', 20)}</div>
        <div class="stat-card__value">${overview.total_available_dishes}</div>
        <div class="stat-card__label">Món có thể phục vụ</div>
      </div>
      <div class="stat-card ${overview.total_unavailable_dishes > 0 ? 'stat-card--danger' : ''}">
        <div class="stat-card__icon" style="${overview.total_unavailable_dishes > 0 ? '' : 'background:var(--danger-bg); color:var(--danger);'}">${icon('x-circle', 20)}</div>
        <div class="stat-card__value" style="${overview.total_unavailable_dishes > 0 ? 'color:white' : 'color:var(--danger)'}">${overview.total_unavailable_dishes}</div>
        <div class="stat-card__label" style="${overview.total_unavailable_dishes > 0 ? '' : 'color:var(--text-muted)'}">Món hết nguyên liệu</div>
      </div>
      <div class="stat-card">
        <div class="stat-card__icon" style="background:var(--orange-pale); color:var(--orange);">${icon('package', 20)}</div>
        <div class="stat-card__value">${overview.total_materials}</div>
        <div class="stat-card__label">Nguyên vật liệu</div>
      </div>
      <div class="stat-card ${overview.out_of_stock_count > 0 ? 'stat-card--danger' : ''}">
        <div class="stat-card__icon" style="${overview.out_of_stock_count > 0 ? '' : 'background:var(--warning-bg); color:var(--warning);'}">${icon('alert-triangle', 20)}</div>
        <div class="stat-card__value" style="${overview.out_of_stock_count > 0 ? 'color:white' : 'color:var(--warning)'}">${overview.low_stock_count + overview.out_of_stock_count}</div>
        <div class="stat-card__label">Nguyên liệu cần nhập</div>
      </div>
    </div>

    <!-- Today Import Summary -->
    <div class="section-header">
      <span class="section-title">${icon('clipboard', 16)} Nhập kho hôm nay (${today})</span>
    </div>
    ${overview.today_import_count === 0
      ? `<div style="padding:var(--space-lg); text-align:center; color:var(--text-muted); font-size:var(--text-sm);">Chưa có phiếu nhập nào hôm nay</div>`
      : `<div style="margin:0 var(--space-lg); background:var(--orange-pale); border-radius:var(--radius-lg); padding:var(--space-lg); border:1px solid var(--orange-tint);">
          <div style="font-size:var(--text-2xl); font-weight:800; color:var(--orange);">${overview.today_import_count} phiếu</div>
          <div style="font-size:var(--text-sm); color:var(--orange-dark); margin-top:4px;">${overview.today_import_items} mặt hàng đã nhập</div>
        </div>`
    }

    <!-- Low Stock Warnings -->
    ${lowStock.length > 0 ? `
      <div class="section-header mt-md">
        <span class="section-title" style="color:var(--danger);">${icon('alert-circle', 16)} Cảnh báo tồn kho</span>
      </div>
      <div style="background:var(--white); border-radius:var(--radius-lg); overflow:hidden; box-shadow:var(--shadow-sm); margin:0 var(--space-lg);">
        ${lowStock.map(item => `
          <div class="mat-item">
            <div class="mat-item__dot mat-item__dot--${item.status}"></div>
            <div class="mat-item__info">
              <div class="mat-item__name">${escapeHtml(item.material_name)}</div>
              <div class="mat-item__detail">${item.status === 'out' ? `${iconInline('alert-circle', 12, 'var(--danger)')} Hết hàng` : `${iconInline('alert-triangle', 12, 'var(--warning)')} Còn ${item.quantity} ${item.unit} / ngưỡng ${item.min_stock} ${item.unit}`}</div>
            </div>
            <span class="badge badge--${item.status}">${item.status === 'out' ? 'HẾT' : 'SẮP HẾT'}</span>
          </div>
        `).join('')}
      </div>
    ` : `
      <div class="section-header mt-md">
        <span class="section-title" style="color:var(--success);">${icon('check-circle', 16)} Tồn kho ổn định</span>
      </div>
      <div style="margin:0 var(--space-lg); background:var(--success-bg); border-radius:var(--radius-lg); padding:var(--space-lg); text-align:center; border:1px solid #86efac;">
        <div style="color:var(--success); margin-bottom:4px;">${icon('check-circle', 32)}</div>
        <div style="font-size:var(--text-sm); color:var(--success); font-weight:600;">Tất cả nguyên liệu đủ hàng</div>
      </div>
    `}

    <!-- Import History -->
    <div class="section-header mt-md">
      <span class="section-title">${icon('clock', 16)} Lịch sử nhập kho</span>
      <button class="section-action" onclick="loadFullHistory()">Xem thêm</button>
    </div>
    ${history.length === 0
      ? `<div style="padding:var(--space-lg); text-align:center; color:var(--text-muted); font-size:var(--text-sm);">Chưa có lịch sử nhập kho</div>`
      : history.map(rec => `
        <div class="import-card" onclick="showImportDetail(${rec.id})">
          <div class="import-card__header">
            <div>
              <div class="import-card__supplier">${escapeHtml(rec.supplier_name || 'Không rõ')}</div>
              <div style="font-size:var(--text-xs); color:var(--text-muted);">bởi ${escapeHtml(rec.created_by)}</div>
            </div>
            <div class="import-card__time">${formatTime(rec.created_at)}</div>
          </div>
          <div class="import-card__tags">
            ${rec.items.slice(0,5).map(it => `<span class="import-card__tag">${escapeHtml(it.material_name)} ${it.quantity}${it.unit}</span>`).join('')}
            ${rec.items.length > 5 ? `<span class="import-card__tag">+${rec.items.length - 5} mặt hàng</span>` : ''}
          </div>
        </div>
      `).join('')
    }

    <div style="height:var(--space-xl);"></div>
  `;
}

function showImportDetail(importId) {
  const rec = state.historyData.find(r => r.id === importId);
  if (!rec) return;

  openBottomSheet(`
    <div style="margin-bottom:var(--space-lg);">
      <h2 style="font-size:var(--text-lg); font-weight:700;">Phiếu nhập kho #${rec.id}</h2>
      <p class="text-muted text-sm">${formatTime(rec.created_at)} • ${escapeHtml(rec.created_by)}</p>
      ${rec.supplier_name ? `<p class="text-sm mt-sm" style="display:flex;align-items:center;gap:4px;">${iconInline('user', 14, 'var(--text-muted)')} ${escapeHtml(rec.supplier_name)}</p>` : ''}
    </div>
    <div style="background:var(--bg); border-radius:var(--radius-md); overflow:hidden;">
      ${rec.items.map((it, i) => `
        <div class="mat-item" style="${i===0?'border-top:none':''}">
          <div class="review-item__num">${i+1}</div>
          <div class="mat-item__info">
            <div class="mat-item__name">${escapeHtml(it.material_name)}</div>
          </div>
          <div class="mat-item__qty">
            <div class="mat-item__qty-val">${it.quantity}</div>
            <div class="mat-item__qty-unit">${it.unit}</div>
          </div>
        </div>
      `).join('')}
    </div>
    ${rec.notes ? `<p class="text-sm text-muted mt-lg">Ghi chú: ${escapeHtml(rec.notes)}</p>` : ''}
  `);
}

async function loadFullHistory() {
  const overlay = openBottomSheet(`
    <h2 style="font-size:var(--text-lg); font-weight:700; margin-bottom:var(--space-lg);">Lịch sử nhập kho</h2>
    <div id="history-content"><div class="loading-screen"><div class="spinner"></div></div></div>
  `);

  try {
    const data = await api.get('/api/reports/history', { limit: 50 });
    const histEl = document.getElementById('history-content');
    if (!histEl) return;
    if (data.length === 0) {
      histEl.innerHTML = `<div class="empty-state"><div class="empty-state__icon">${icon('clipboard', 36)}</div><p class="empty-state__text">Chưa có lịch sử nhập kho</p></div>`;
      return;
    }
    histEl.innerHTML = data.map(rec => `
      <div class="import-card" style="margin:0 0 var(--space-md);" onclick="showImportDetailInline(${JSON.stringify(rec).replace(/"/g,'&quot;')})">
        <div class="import-card__header">
          <div>
            <div class="import-card__supplier">${escapeHtml(rec.supplier_name || 'Không rõ')}</div>
            <div style="font-size:var(--text-xs); color:var(--text-muted);">${escapeHtml(rec.created_by)}</div>
          </div>
          <div class="import-card__time">${formatTime(rec.created_at)}</div>
        </div>
        <div class="import-card__tags">
          ${rec.items.slice(0,4).map(it => `<span class="import-card__tag">${escapeHtml(it.material_name)} ${it.quantity}${it.unit}</span>`).join('')}
          ${rec.items.length > 4 ? `<span class="import-card__tag">+${rec.items.length-4}</span>` : ''}
        </div>
      </div>
    `).join('');
  } catch (err) {
    const histEl = document.getElementById('history-content');
    if (histEl) histEl.innerHTML = `<p class="text-danger text-sm text-center">${escapeHtml(err.message)}</p>`;
  }
}
