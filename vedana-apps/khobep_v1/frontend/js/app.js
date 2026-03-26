/**
 * Kho Bếp — Kitchen Warehouse App
 * Main application logic
 */

// ─── State ───────────────────────────────────────
const state = {
  currentTab: 'import',
  // Import screen
  importMethod: null,    // 'camera' | 'voice'
  reviewItems: [],       // [{name, quantity, unit, material_id}]
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
  const d = new Date(dt);
  const h = d.getHours().toString().padStart(2,'0');
  const m = d.getMinutes().toString().padStart(2,'0');
  const day = d.getDate().toString().padStart(2,'0');
  const mon = (d.getMonth()+1).toString().padStart(2,'0');
  return `${h}:${m} — ${day}/${mon}`;
}

function formatQty(qty, unit) {
  const v = parseFloat(qty);
  return `${v % 1 === 0 ? v.toFixed(0) : v.toFixed(1)} ${unit}`;
}

function showLoading(container) {
  container.innerHTML = `<div class="loading-screen"><div class="spinner"></div></div>`;
}

function showEmpty(container, title, text) {
  container.innerHTML = `<div class="empty-state"><div class="empty-state__icon">📦</div><div class="empty-state__title">${escapeHtml(title)}</div><p class="empty-state__text">${escapeHtml(text)}</p></div>`;
}

function showError(container, msg) {
  container.innerHTML = `<div class="empty-state"><div class="empty-state__icon">⚠️</div><div class="empty-state__title">Có lỗi xảy ra</div><p class="empty-state__text">${escapeHtml(msg)}</p><button class="btn btn--secondary mt-md" onclick="loadTab('${state.currentTab}')">Thử lại</button></div>`;
}

// =============================================
// TAB 1: NHẬP KHO
// =============================================
function renderImportTab() {
  const content = document.getElementById('content');
  // Reset state on tab load
  state.reviewItems = [];
  state.capturedImageB64 = null;
  state.importMethod = null;

  content.innerHTML = `
    <div style="padding: var(--space-xl) var(--space-lg);">

      <!-- Header Banner -->
      <div style="background: linear-gradient(135deg, var(--orange) 0%, var(--orange-dark) 100%);
                  border-radius: var(--radius-xl); padding: var(--space-lg) var(--space-xl);
                  color: white; margin-bottom: var(--space-xl);">
        <div style="font-size:var(--text-xs); font-weight:600; opacity:0.8; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;">
          Hôm nay — ${new Date().toLocaleDateString('vi-VN', {weekday:'long', day:'2-digit', month:'2-digit', year:'numeric'})}
        </div>
        <div style="font-size:var(--text-2xl); font-weight:800; letter-spacing:-0.5px;">Nhập Nguyên Vật Liệu</div>
        <div style="font-size:var(--text-sm); opacity:0.8; margin-top:4px;">Chọn phương thức nhập hàng</div>
      </div>

      <!-- Action Buttons -->
      <div style="display:flex; flex-direction:column; gap:var(--space-md);">

        <button class="action-btn action-btn--primary" id="btn-camera" onclick="startCameraInput()">
          <span class="action-btn__emoji">📷</span>
          <div class="action-btn__text">
            <div class="action-btn__title">Chụp Ảnh Hoá Đơn</div>
            <div class="action-btn__desc">AI tự động nhận diện nguyên vật liệu</div>
          </div>
        </button>

        <button class="action-btn" id="btn-voice" onclick="startVoiceInput()">
          <span class="action-btn__emoji">🎤</span>
          <div class="action-btn__text" style="color:var(--text)">
            <div class="action-btn__title">Nhập Bằng Giọng Nói</div>
            <div class="action-btn__desc" style="color:var(--text-muted)">Nói tên và số lượng nguyên liệu</div>
          </div>
        </button>

        <button class="action-btn" id="btn-manual" onclick="openManualAdd()">
          <span class="action-btn__emoji">✏️</span>
          <div class="action-btn__text" style="color:var(--text)">
            <div class="action-btn__title">Nhập Thủ Công</div>
            <div class="action-btn__desc" style="color:var(--text-muted)">Chọn nguyên vật liệu từ danh sách</div>
          </div>
        </button>

      </div>

      <!-- Review Section (shown after extraction) -->
      <div id="review-section" style="display:none; margin-top:var(--space-xl);">
        <div class="section-header" style="padding:0 0 var(--space-sm);">
          <span class="section-title">Danh sách nhận được</span>
          <button class="section-action" onclick="openAddItem()">+ Thêm</button>
        </div>
        <div style="background:var(--white); border-radius:var(--radius-lg); overflow:hidden; box-shadow:var(--shadow-sm);">
          <div id="review-list"></div>
        </div>
        <!-- Supplier -->
        <div class="form-group mt-lg">
          <label class="form-label" for="supplier-input">Người bàn giao (tuỳ chọn)</label>
          <input class="form-input" type="text" id="supplier-input" placeholder="Tên bộ phận thu mua / nhà cung cấp">
        </div>
        <button class="btn btn--primary btn--full btn--lg" id="btn-confirm" onclick="confirmImport()">
          ✓ Xác Nhận Nhập Kho
        </button>
      </div>

    </div>
  `;
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
  const reviewSection = document.getElementById('review-section');
  if (reviewSection) reviewSection.style.display = 'none';

  // Show processing state (inline in content)
  const processingDiv = document.createElement('div');
  processingDiv.id = 'ocr-processing';
  processingDiv.innerHTML = `
    <div class="ocr-processing" style="margin-top:var(--space-xl);">
      <div style="font-size:48px;">🔍</div>
      <div class="spinner" style="margin:0 auto;"></div>
      <p class="text-muted text-sm text-center">Đang phân tích ảnh hoá đơn...<br>Vui lòng đợi trong giây lát</p>
    </div>
  `;
  content.appendChild(processingDiv);

  // Show image preview
  const imgPreview = document.createElement('img');
  imgPreview.src = dataUrl;
  imgPreview.className = 'camera-preview';
  imgPreview.style.cssText = 'margin:0 var(--space-lg) var(--space-md); width:calc(100% - 32px);';
  processingDiv.prepend(imgPreview);

  try {
    const result = await api.post('/api/ocr/image', { image_base64: dataUrl });
    state.reviewItems = result.items || [];
    document.getElementById('ocr-processing')?.remove();
    if (state.reviewItems.length === 0) {
      showToast('Không nhận diện được nguyên vật liệu. Thử lại hoặc nhập thủ công.', 'error');
    } else {
      renderReviewList();
      showToast(`Nhận diện được ${state.reviewItems.length} mặt hàng`, 'success');
    }
  } catch (err) {
    document.getElementById('ocr-processing')?.remove();
    showToast('Lỗi nhận diện ảnh: ' + err.message, 'error');
    // Still show manual add option
    renderReviewList();
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
      <div class="voice-ring" id="voice-btn">🎤</div>
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
    voiceHint.textContent = '🔴 Đang nghe... Nói tên và số lượng nguyên liệu';
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
      voiceHint.textContent = '✅ Đã ghi âm xong. Nhấn Xác nhận để phân tích.';
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
    if (state.reviewItems.length === 0) {
      showToast('Không nhận diện được. Thêm thủ công.', 'error');
    } else {
      renderReviewList();
      showToast(`Nhận diện được ${state.reviewItems.length} mặt hàng`, 'success');
    }
  } catch (err) {
    showToast('Lỗi phân tích: ' + err.message, 'error');
    renderReviewList();
  }
}

// ─── Manual Add ───────────────────────────────────
function openManualAdd() {
  renderReviewList();
  setTimeout(() => openAddItem(), 100);
}

async function openAddItem() {
  // Load materials for selection
  let materials = [];
  try { materials = await api.get('/api/materials'); } catch (e) { /* ignore */ }

  const overlay = openBottomSheet(`
    <h2 style="font-size:var(--text-lg); font-weight:700; margin-bottom:var(--space-lg);">Thêm Nguyên Vật Liệu</h2>

    <div class="search-bar" style="margin:0 0 var(--space-md);">
      <svg class="search-bar__icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
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
  renderReviewList();
  showToast(`Đã thêm: ${name} (${qty} ${unit})`);
}

// ─── Review List ──────────────────────────────────
function renderReviewList() {
  const reviewSection = document.getElementById('review-section');
  if (!reviewSection) return;
  reviewSection.style.display = 'block';

  const listEl = document.getElementById('review-list');
  if (!listEl) return;

  if (state.reviewItems.length === 0) {
    listEl.innerHTML = `<div class="empty-state" style="padding:24px;"><div class="empty-state__icon">🛒</div><p class="empty-state__text">Chưa có nguyên vật liệu nào.<br>Thêm bằng nút "+ Thêm" phía trên.</p></div>`;
    return;
  }

  listEl.innerHTML = state.reviewItems.map((item, idx) => `
    <div class="review-item">
      <div class="review-item__num">${idx + 1}</div>
      <div style="flex:1; min-width:0;">
        <div class="review-item__name ${item.material_id ? '' : 'review-item__unmatched'}">
          ${escapeHtml(item.name)}${item.material_id ? '' : ' ⚠'}
        </div>
        <div class="text-xs text-muted">${item.material_id ? '' : 'Chưa khớp danh mục · '}</div>
      </div>
      <div class="stepper">
        <button class="stepper__btn" onclick="changeItemQty(${idx}, -0.5)">−</button>
        <span class="stepper__value" style="min-width:48px;">${parseFloat(item.quantity).toFixed(item.quantity % 1 === 0 ? 0 : 1)} ${item.unit}</span>
        <button class="stepper__btn" onclick="changeItemQty(${idx}, 0.5)">+</button>
      </div>
      <button class="review-item__delete" onclick="removeReviewItem(${idx})">✕</button>
    </div>
  `).join('');
}

function changeItemQty(idx, delta) {
  const item = state.reviewItems[idx];
  if (!item) return;
  item.quantity = Math.max(0.1, parseFloat(item.quantity) + delta);
  renderReviewList();
}

function removeReviewItem(idx) {
  state.reviewItems.splice(idx, 1);
  renderReviewList();
}

// ─── Confirm Import ───────────────────────────────
async function confirmImport() {
  if (state.reviewItems.length === 0) { showToast('Chưa có nguyên vật liệu', 'error'); return; }

  const unmatchedItems = state.reviewItems.filter(i => !i.material_id);
  if (unmatchedItems.length > 0) {
    const names = unmatchedItems.map(i => i.name).join(', ');
    showToast(`Một số mặt hàng chưa khớp danh mục: ${names}. Bỏ qua và tiếp tục?`, 'error');
    // Proceed anyway after 2s or user can edit
  }

  const validItems = state.reviewItems.filter(i => i.material_id);
  if (validItems.length === 0) {
    showToast('Không có mặt hàng nào khớp với danh mục', 'error');
    return;
  }

  const btn = document.getElementById('btn-confirm');
  if (btn) { btn.disabled = true; btn.innerHTML = `<div class="spinner spinner--sm spinner--white"></div> Đang lưu...`; }

  const supplier = document.getElementById('supplier-input')?.value || '';

  try {
    await api.post('/api/imports', {
      supplier_name: supplier || null,
      created_by: 'Nhân viên kho',
      items: validItems.map(i => ({ material_id: i.material_id, quantity: i.quantity, unit: i.unit })),
    });

    showToast(`✓ Nhập kho thành công ${validItems.length} mặt hàng!`, 'success');

    // Reset
    state.reviewItems = [];
    renderImportTab();
  } catch (err) {
    showToast('Lỗi: ' + err.message, 'error');
    if (btn) { btn.disabled = false; btn.innerHTML = '✓ Xác Nhận Nhập Kho'; }
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
      <button class="sub-tab ${state.invSubTab==='materials'?'sub-tab--active':''}" onclick="switchInvTab('materials')">📦 Nguyên Liệu</button>
      <button class="sub-tab ${state.invSubTab==='dishes'?'sub-tab--active':''}" onclick="switchInvTab('dishes')">🍽 Món Ăn</button>
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
      <svg class="search-bar__icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input class="search-bar__input" type="text" placeholder="Tìm nguyên vật liệu..." value="${escapeHtml(state.invSearch)}" id="inv-search-input" autocomplete="off">
    </div>

    ${outCount > 0 ? `<div class="alert alert--danger" style="margin-bottom:var(--space-sm);"><span class="alert__icon">🔴</span><span class="alert__text">${outCount} nguyên liệu đã HẾT</span></div>` : ''}
    ${lowCount > 0 ? `<div class="alert alert--warning" style="margin-bottom:var(--space-sm);"><span class="alert__icon">🟡</span><span class="alert__text">${lowCount} nguyên liệu SẮP HẾT</span></div>` : ''}

    <div style="background:var(--white); border-radius:var(--radius-lg); overflow:hidden; box-shadow:var(--shadow-sm); margin:0 var(--space-lg);">
      ${filtered.length === 0
        ? `<div class="empty-state"><div class="empty-state__icon">🔍</div><p class="empty-state__text">Không tìm thấy</p></div>`
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
          ${mat.stock_status==='ok'?'✓ Đủ hàng':mat.stock_status==='low'?'⚠ Sắp hết':'✕ Hết hàng'}
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
      <button class="chip ${state.dishFilter==='available'?'chip--active':''}" onclick="filterDishes('available')">✓ Phục vụ (${available})</button>
      <button class="chip ${state.dishFilter==='unavailable'?'chip--active':''}" onclick="filterDishes('unavailable')">✕ Hết NL (${unavailable})</button>
    </div>

    <div class="dish-grid">
      ${filtered.map(d => {
        const emoji = {'Phở':'🍜','Bún':'🍜','Cơm':'🍚','Lẩu':'🫕'}[d.category] || '🍽';
        return `
          <div class="dish-card ${d.is_available?'':'dish-card--unavailable'}" onclick="showDishDetail(${d.id})">
            <div class="dish-card__emoji">${emoji}</div>
            <div class="dish-card__name">${escapeHtml(d.name)}</div>
            <div class="dish-card__category">${escapeHtml(d.category || '')}</div>
            <span class="badge badge--${d.is_available?'available':'unavailable'}">
              ${d.is_available ? '✓ Phục vụ' : '✕ Hết NL'}
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
      <div style="font-size:40px; margin-bottom:8px;">${{'Phở':'🍜','Bún':'🍜','Cơm':'🍚','Lẩu':'🫕'}[dish.category]||'🍽'}</div>
      <h2 style="font-size:var(--text-xl); font-weight:800; margin-bottom:4px;">${escapeHtml(dish.name)}</h2>
      <span class="badge badge--${dish.is_available?'available':'unavailable'}">
        ${dish.is_available ? '✓ Có thể phục vụ' : '✕ Hết nguyên liệu'}
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

  const today = new Date().toLocaleDateString('vi-VN', { day:'2-digit', month:'2-digit' });

  content.innerHTML = `

    <!-- Stats Grid -->
    <div class="stats-grid">
      <div class="stat-card stat-card--orange">
        <div class="stat-card__icon">🍽</div>
        <div class="stat-card__value">${overview.total_available_dishes}</div>
        <div class="stat-card__label">Món có thể phục vụ</div>
      </div>
      <div class="stat-card ${overview.total_unavailable_dishes > 0 ? 'stat-card--danger' : ''}">
        <div class="stat-card__icon">❌</div>
        <div class="stat-card__value" style="${overview.total_unavailable_dishes > 0 ? 'color:white' : 'color:var(--danger)'}">${overview.total_unavailable_dishes}</div>
        <div class="stat-card__label" style="${overview.total_unavailable_dishes > 0 ? '' : 'color:var(--text-muted)'}">Món hết nguyên liệu</div>
      </div>
      <div class="stat-card">
        <div class="stat-card__icon">📦</div>
        <div class="stat-card__value">${overview.total_materials}</div>
        <div class="stat-card__label">Nguyên vật liệu</div>
      </div>
      <div class="stat-card ${overview.out_of_stock_count > 0 ? 'stat-card--danger' : ''}">
        <div class="stat-card__icon">⚠️</div>
        <div class="stat-card__value" style="${overview.out_of_stock_count > 0 ? 'color:white' : 'color:var(--warning)'}">${overview.low_stock_count + overview.out_of_stock_count}</div>
        <div class="stat-card__label">Nguyên liệu cần nhập</div>
      </div>
    </div>

    <!-- Today Import Summary -->
    <div class="section-header">
      <span class="section-title">📋 Nhập kho hôm nay (${today})</span>
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
        <span class="section-title">🔴 Cảnh báo tồn kho</span>
      </div>
      <div style="background:var(--white); border-radius:var(--radius-lg); overflow:hidden; box-shadow:var(--shadow-sm); margin:0 var(--space-lg);">
        ${lowStock.map(item => `
          <div class="mat-item">
            <div class="mat-item__dot mat-item__dot--${item.status}"></div>
            <div class="mat-item__info">
              <div class="mat-item__name">${escapeHtml(item.material_name)}</div>
              <div class="mat-item__detail">${item.status === 'out' ? '🔴 Hết hàng' : `🟡 Còn ${item.quantity} ${item.unit} / ngưỡng ${item.min_stock} ${item.unit}`}</div>
            </div>
            <span class="badge badge--${item.status}">${item.status === 'out' ? 'HẾT' : 'SẮP HẾT'}</span>
          </div>
        `).join('')}
      </div>
    ` : `
      <div class="section-header mt-md">
        <span class="section-title">✅ Tồn kho ổn định</span>
      </div>
      <div style="margin:0 var(--space-lg); background:var(--success-bg); border-radius:var(--radius-lg); padding:var(--space-lg); text-align:center; border:1px solid #86efac;">
        <div style="font-size:24px; margin-bottom:4px;">✅</div>
        <div style="font-size:var(--text-sm); color:var(--success); font-weight:600;">Tất cả nguyên liệu đủ hàng</div>
      </div>
    `}

    <!-- Import History -->
    <div class="section-header mt-md">
      <span class="section-title">📜 Lịch sử nhập kho</span>
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
      ${rec.supplier_name ? `<p class="text-sm mt-sm">👤 ${escapeHtml(rec.supplier_name)}</p>` : ''}
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
      histEl.innerHTML = `<div class="empty-state"><div class="empty-state__icon">📋</div><p class="empty-state__text">Chưa có lịch sử nhập kho</p></div>`;
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
