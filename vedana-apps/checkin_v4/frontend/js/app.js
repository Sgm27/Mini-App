/**
 * Checkin Vedana — Check-in Wizard Application
 * 3-step wizard: Booking → ID Documents → Review & Confirm
 */

let currentTab = 'scan';
let currentMode = 'landing'; // 'landing' | 'checkin' | 'room-assignment' | 'export'

let wizardState = {
    currentStep: 1,
    booking: {
        booking_code: null,
        room_type: null,
        num_guests: null,
        arrival_date: null,
        departure_date: null,
    },
    contact: {
        name: null,
        phone: null,
    },
    guests: [],
};

document.addEventListener('DOMContentLoaded', () => {
    initBottomNav();
    showLanding();
    checkBackend();
});

async function checkBackend() {
    try {
        await api.get('/api/health');
        console.log('Backend connected');
    } catch (e) {
        console.warn('Backend not available:', e.message);
    }
}

/* ============================================
   BOTTOM NAV
   ============================================ */
function initBottomNav() {
    const navItems = document.querySelectorAll('.bottom-nav__item');
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            navItems.forEach(i => i.classList.remove('bottom-nav__item--active'));
            item.classList.add('bottom-nav__item--active');
            onTabChange(item.dataset.tab);
        });
    });
}

function onTabChange(tab) {
    currentTab = tab;
    switch (tab) {
        case 'scan': loadCheckinTab(); break;
        case 'history': loadHistoryTab(); break;
        case 'info': loadInfoTab(); break;
    }
}

/* ============================================
   LANDING SCREEN
   ============================================ */
function showLanding() {
    currentMode = 'landing';
    document.querySelector('.bottom-nav').style.display = 'none';
    document.getElementById('topBarLeft').innerHTML = '';
    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="landing fade-in">
            <div class="landing__header">
                <div class="landing__title">Xin chào!</div>
                <div class="landing__subtitle">Chọn thao tác bạn muốn thực hiện</div>
            </div>
            <div class="landing__cards">
                <button class="landing-card" id="btnLandingCheckin">
                    <div class="landing-card__icon landing-card__icon--orange">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
                            <polyline points="22 4 12 14.01 9 11.01"/>
                        </svg>
                    </div>
                    <div class="landing-card__text">
                        <div class="landing-card__title">Check-in</div>
                        <div class="landing-card__desc">Đăng ký khách mới</div>
                    </div>
                    <div class="landing-card__arrow">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
                    </div>
                </button>
                <button class="landing-card" id="btnLandingRoomAssign">
                    <div class="landing-card__icon landing-card__icon--blue">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
                            <polyline points="9 22 9 12 15 12 15 22"/>
                        </svg>
                    </div>
                    <div class="landing-card__text">
                        <div class="landing-card__title">Xếp phòng</div>
                        <div class="landing-card__desc">Gán phòng cho khách</div>
                    </div>
                    <div class="landing-card__arrow">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
                    </div>
                </button>
                <button class="landing-card" id="btnLandingExport">
                    <div class="landing-card__icon landing-card__icon--green">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                            <polyline points="14 2 14 8 20 8"/>
                            <line x1="16" y1="13" x2="8" y2="13"/>
                            <line x1="16" y1="17" x2="8" y2="17"/>
                            <polyline points="10 9 9 9 8 9"/>
                        </svg>
                    </div>
                    <div class="landing-card__text">
                        <div class="landing-card__title">Xuất Excel</div>
                        <div class="landing-card__desc">Xuất dữ liệu check-in theo thời gian</div>
                    </div>
                    <div class="landing-card__arrow">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
                    </div>
                </button>
            </div>
        </div>
    `;

    document.getElementById('btnLandingCheckin').addEventListener('click', enterCheckinMode);
    document.getElementById('btnLandingRoomAssign').addEventListener('click', enterRoomAssignMode);
    document.getElementById('btnLandingExport').addEventListener('click', enterExportMode);
}

function showBackButton(onBack) {
    document.getElementById('topBarLeft').innerHTML = `
        <button class="top-bar__action" id="btnTopBarBack">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
        </button>
    `;
    document.getElementById('btnTopBarBack').addEventListener('click', onBack);
}

function enterCheckinMode() {
    currentMode = 'checkin';
    document.querySelector('.bottom-nav').style.display = 'flex';
    showBackButton(showLanding);
    loadCheckinTab();
}

function enterRoomAssignMode() {
    currentMode = 'room-assignment';
    document.querySelector('.bottom-nav').style.display = 'none';
    showBackButton(showLanding);
    loadRoomAssignmentList();
}

/* ============================================
   EXPORT EXCEL MODE
   ============================================ */
function _formatDateInput(date) {
    const d = date.getDate().toString().padStart(2, '0');
    const m = (date.getMonth() + 1).toString().padStart(2, '0');
    const y = date.getFullYear();
    return `${d}/${m}/${y}`;
}

function _toInputDate(ddmmyyyy) {
    const [d, m, y] = ddmmyyyy.split('/');
    return `${y}-${m}-${d}`;
}

function _fromInputDate(isoDate) {
    const [y, m, d] = isoDate.split('-');
    return `${d}/${m}/${y}`;
}

function enterExportMode() {
    currentMode = 'export';
    document.querySelector('.bottom-nav').style.display = 'none';
    showBackButton(showLanding);

    const lastExport = localStorage.getItem('lastExportDate');
    const defaultFrom = lastExport || _formatDateInput(new Date(Date.now() - 7 * 86400000));
    const defaultTo = _formatDateInput(new Date());

    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="fade-in" style="padding:var(--space-lg);">
            <div class="section-header">
                <div>
                    <div class="section-header__title">Xuất Excel</div>
                    <div class="section-header__subtitle">Xuất dữ liệu check-in theo khoảng thời gian</div>
                </div>
            </div>

            <div class="export-form" style="margin-top:var(--space-xl);">
                <div class="form-field">
                    <label class="form-field__label">Từ ngày</label>
                    <input type="date" class="form-field__input" id="exportFromDate" value="${_toInputDate(defaultFrom)}">
                    <div style="font-size:11px;color:var(--color-text-muted);margin-top:4px;">
                        ${lastExport ? 'Lần xuất cuối: ' + lastExport : 'Mặc định: 7 ngày trước'}
                    </div>
                </div>
                <div class="form-field" style="margin-top:var(--space-lg);">
                    <label class="form-field__label">Đến ngày</label>
                    <input type="date" class="form-field__input" id="exportToDate" value="${_toInputDate(defaultTo)}">
                </div>

                <button class="btn btn--primary btn--full" id="btnDoExport" style="margin-top:var(--space-2xl);">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align:middle;margin-right:6px;">
                        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                        <polyline points="7 10 12 15 17 10"/>
                        <line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                    Xuất file Excel
                </button>
                <button class="btn btn--secondary btn--full" id="btnDoExportForeign" style="margin-top:var(--space-md);">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align:middle;margin-right:6px;">
                        <circle cx="12" cy="12" r="10"/>
                        <path d="M2 12h20"/>
                    </svg>
                    Xuất XML khách nước ngoài
                </button>
            </div>
        </div>
    `;

    document.getElementById('btnDoExport').addEventListener('click', handleExport);
    document.getElementById('btnDoExportForeign').addEventListener('click', handleExportForeign);
}

async function handleExport() {
    const fromInput = document.getElementById('exportFromDate').value;
    const toInput = document.getElementById('exportToDate').value;

    if (!fromInput || !toInput) {
        showToast('Vui lòng chọn đầy đủ ngày', 'error');
        return;
    }

    const fromDate = _fromInputDate(fromInput);
    const toDate = _fromInputDate(toInput);

    const btn = document.getElementById('btnDoExport');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner" style="width:18px;height:18px;border-width:2px;margin-right:6px;vertical-align:middle;"></span> Đang xuất...';

    try {
        await api.exportCheckinsByRange(fromDate, toDate);
        localStorage.setItem('lastExportDate', toDate);
        showToast('Đã tải file Excel thành công', 'success');
    } catch (e) {
        showToast(e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align:middle;margin-right:6px;">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            Xuất file Excel`;
    }
}

async function handleExportForeign() {
    const fromInput = document.getElementById('exportFromDate').value;
    const toInput = document.getElementById('exportToDate').value;

    if (!fromInput || !toInput) {
        showToast('Vui lòng chọn đầy đủ ngày', 'error');
        return;
    }

    const fromDate = _fromInputDate(fromInput);
    const toDate = _fromInputDate(toInput);

    const btn = document.getElementById('btnDoExportForeign');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner" style="width:18px;height:18px;border-width:2px;margin-right:6px;vertical-align:middle;"></span> Đang xuất...';

    try {
        await api.exportForeignCheckinsByRange(fromDate, toDate);
        showToast('Đã tải file XML thành công', 'success');
    } catch (e) {
        showToast(e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="vertical-align:middle;margin-right:6px;">
                <circle cx="12" cy="12" r="10"/>
                <path d="M2 12h20"/>
            </svg>
            Xuất XML khách nước ngoài`;
    }
}

/* ============================================
   WIZARD — Core
   ============================================ */
function resetWizard() {
    wizardState = {
        currentStep: 1,
        booking: { booking_code: null, room_type: null, num_guests: null, arrival_date: null, departure_date: null },
        contact: { name: null, phone: null },
        guests: [],
    };
}

function loadCheckinTab() {
    clearSuccessTimer();
    resetWizard();
    renderWizardStep();
}

function renderWizardStep() {
    const content = document.getElementById('content');
    const step = wizardState.currentStep;

    const stepsHtml = renderStepIndicator(step);

    let bodyHtml = '';
    switch (step) {
        case 1: bodyHtml = renderStep1(); break;
        case 2: bodyHtml = renderStep2(); break;
        case 3: bodyHtml = renderStep3(); break;
    }

    content.innerHTML = `<div class="fade-in">${stepsHtml}${bodyHtml}</div>`;

    switch (step) {
        case 1: bindStep1Events(); break;
        case 2: bindStep2Events(); break;
        case 3: bindStep3Events(); break;
    }
}

function renderStepIndicator(current) {
    const steps = [
        { num: 1, label: 'Đặt phòng' },
        { num: 2, label: 'Giấy tờ' },
        { num: 3, label: 'Xác nhận' },
    ];

    let html = '<div class="wizard-steps">';
    steps.forEach((s, i) => {
        const cls = s.num < current ? 'wizard-step--done' : s.num === current ? 'wizard-step--active' : '';
        const icon = s.num < current ? '&#10003;' : s.num;
        html += `<div class="wizard-step ${cls}">
            <div class="wizard-step__circle">${icon}</div>
            <span class="wizard-step__label">${s.label}</span>
        </div>`;
        if (i < steps.length - 1) {
            const lineCls = s.num < current ? 'wizard-step__line--done' : '';
            html += `<div class="wizard-step__line ${lineCls}"></div>`;
        }
    });
    html += '</div>';
    return html;
}

/* ============================================
   STEP 1 — Booking Upload
   ============================================ */
function renderStep1() {
    const b = wizardState.booking;
    const hasData = b.booking_code || b.room_type || b.num_guests || b.arrival_date || b.departure_date;

    let formHtml = '';
    if (hasData) {
        formHtml = `
            <div style="margin-top: var(--space-lg);">
                <div style="font-size:12px;font-weight:600;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.06em;margin-bottom:var(--space-md);">Thông tin đặt phòng</div>
                <div class="result-form">
                    <div class="result-field">
                        <div class="result-field__header"><span class="result-field__label">Mã đặt phòng *</span></div>
                        <input class="result-field__input" type="text" id="f_booking_code" value="${escapeHtml(b.booking_code || '')}" required>
                    </div>
                    <div class="result-field">
                        <div class="result-field__header"><span class="result-field__label">Loại phòng</span></div>
                        <input class="result-field__input" type="text" id="f_room_type" value="${escapeHtml(b.room_type || '')}">
                    </div>
                    <div class="result-field">
                        <div class="result-field__header"><span class="result-field__label">Số người *</span></div>
                        <input class="result-field__input" type="number" id="f_num_guests" value="${b.num_guests || ''}" min="1" required>
                    </div>
                    <div class="result-field">
                        <div class="result-field__header"><span class="result-field__label">Ngày nhận phòng *</span></div>
                        <input class="result-field__input" type="text" id="f_arrival_date" value="${escapeHtml(b.arrival_date || '')}" placeholder="DD/MM/YYYY" required>
                    </div>
                    <div class="result-field">
                        <div class="result-field__header"><span class="result-field__label">Ngày trả phòng *</span></div>
                        <input class="result-field__input" type="text" id="f_departure_date" value="${escapeHtml(b.departure_date || '')}" placeholder="DD/MM/YYYY" required>
                    </div>
                </div>
            </div>
            <div class="wizard-nav">
                <button class="btn btn--secondary flex-1" id="btnReuploadBooking">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 102.13-9.36L1 10"/></svg>
                    Upload lại
                </button>
                <button class="btn btn--primary flex-1 btn--lg" id="btnStep1Next">
                    Tiếp tục
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>
                </button>
            </div>
        `;
    }

    return `
        <div class="section-header">
            <div>
                <div class="section-header__title">Check-in</div>
                <div class="section-header__subtitle">Tải ảnh xác nhận đặt phòng</div>
            </div>
        </div>
        <div class="upload-zone" id="uploadZoneBooking" ${hasData ? 'style="display:none"' : ''}>
            <div class="upload-zone__icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <rect x="2" y="3" width="20" height="14" rx="2"/>
                    <path d="M8 21h8"/><path d="M12 17v4"/>
                    <path d="M7 8h.01"/><path d="M12 8l-3 3h6l-3-3z"/>
                </svg>
            </div>
            <div class="upload-zone__title">Tải ảnh xác nhận đặt phòng</div>
            <div class="upload-zone__subtitle">Ảnh chụp màn hình, email hoặc giấy xác nhận</div>
            <div class="upload-zone__actions">
                <button class="upload-zone__btn upload-zone__btn--primary" id="btnBookingCamera">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z"/><circle cx="12" cy="13" r="4"/></svg>
                    Chụp ảnh
                </button>
                <button class="upload-zone__btn upload-zone__btn--secondary" id="btnBookingGallery">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>
                    Thư viện
                </button>
            </div>
            <div class="upload-zone__hint">Hỗ trợ JPG, PNG, WEBP — Tối đa 10MB</div>
        </div>
        <input type="file" id="bookingFileCamera" accept="image/*" capture="environment" style="display:none">
        <input type="file" id="bookingFileGallery" accept="image/jpeg,image/png,image/webp" style="display:none">
        ${formHtml}
    `;
}

function bindStep1Events() {
    const hasData = wizardState.booking.booking_code || wizardState.booking.num_guests;

    const btnCamera = document.getElementById('btnBookingCamera');
    const btnGallery = document.getElementById('btnBookingGallery');
    const uploadZone = document.getElementById('uploadZoneBooking');

    if (btnCamera) btnCamera.addEventListener('click', (e) => { e.stopPropagation(); document.getElementById('bookingFileCamera').click(); });
    if (btnGallery) btnGallery.addEventListener('click', (e) => { e.stopPropagation(); document.getElementById('bookingFileGallery').click(); });
    if (uploadZone) uploadZone.addEventListener('click', () => document.getElementById('bookingFileGallery').click());

    document.getElementById('bookingFileCamera').addEventListener('change', handleBookingFile);
    document.getElementById('bookingFileGallery').addEventListener('change', handleBookingFile);

    if (hasData) {
        document.getElementById('btnReuploadBooking').addEventListener('click', () => {
            wizardState.booking = { booking_code: null, room_type: null, num_guests: null, arrival_date: null, departure_date: null };
            renderWizardStep();
        });
        document.getElementById('btnStep1Next').addEventListener('click', handleStep1Next);
    }
}

async function handleBookingFile(e) {
    const file = e.target.files[0];
    if (!file) return;

    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
        showToast('Chỉ chấp nhận ảnh JPG, PNG hoặc WEBP', 'error');
        return;
    }
    if (file.size > 10 * 1024 * 1024) {
        showToast('File quá lớn. Tối đa 10MB', 'error');
        return;
    }

    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="fade-in">${renderStepIndicator(1)}
        <div class="ocr-processing">
            <div class="ocr-processing__scanner"><div class="ocr-processing__scanner-inner">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M6 8h.01M6 12h.01M10 8h8M10 12h5"/></svg>
            </div></div>
            <div class="ocr-processing__title">Đang phân tích ảnh đặt phòng</div>
            <div class="ocr-processing__subtitle">Vui lòng đợi trong giây lát...</div>
        </div></div>
    `;

    try {
        const result = await api.ocrBooking(file);
        wizardState.booking = {
            booking_code: result.booking_code || '',
            room_type: result.room_type || '',
            num_guests: result.num_guests || 1,
            arrival_date: result.arrival_date || '',
            departure_date: result.departure_date || '',
        };
        renderWizardStep();
        showToast('Trích xuất thành công', 'success');
    } catch (error) {
        showToast(error.message || 'Không thể trích xuất thông tin đặt phòng', 'error');
        renderWizardStep();
    }
}

function handleStep1Next() {
    // Read form values
    const code = document.getElementById('f_booking_code').value.trim();
    const roomType = document.getElementById('f_room_type').value.trim();
    const numGuests = parseInt(document.getElementById('f_num_guests').value) || 0;
    const arrival = document.getElementById('f_arrival_date').value.trim();
    const departure = document.getElementById('f_departure_date').value.trim();

    if (!code) { showToast('Mã đặt phòng không được để trống', 'error'); return; }
    if (numGuests < 1) { showToast('Số người phải lớn hơn 0', 'error'); return; }
    if (!arrival) { showToast('Ngày nhận phòng không được để trống', 'error'); return; }
    if (!departure) { showToast('Ngày trả phòng không được để trống', 'error'); return; }

    wizardState.booking = { booking_code: code, room_type: roomType || null, num_guests: numGuests, arrival_date: arrival, departure_date: departure };
    wizardState.currentStep = 2;
    renderWizardStep();
}

/* ============================================
   STEP 2 — ID Document Upload
   ============================================ */
function renderStep2() {
    const guests = wizardState.guests;
    const numExpected = wizardState.booking.num_guests;

    let warningHtml = '';
    if (guests.length > 0 && guests.length !== numExpected) {
        warningHtml = `
            <div class="warning-banner">
                <div class="warning-banner__icon">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                </div>
                <span>Số lượng không khớp: Booking ghi ${numExpected} người, hiện có ${guests.length} hồ sơ.</span>
            </div>
        `;
    }

    let guestsHtml = '';
    if (guests.length > 0) {
        guestsHtml = `<div style="font-size:12px;font-weight:600;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.06em;margin-bottom:var(--space-md);">Hồ sơ đã quét (${guests.length})</div>`;
        guests.forEach((g, i) => {
            const isForeign = g.guest_type === 'foreign';
            const name = g.full_name || 'Không xác định';
            const idDisplay = isForeign
                ? (g.passport_number || 'Chưa có số hộ chiếu')
                : (g.identification_number || 'Chưa có số giấy tờ');
            const badgeClass = isForeign ? 'guest-badge--foreign' : 'guest-badge--vn';
            const badgeText = isForeign ? 'NN' : 'VN';
            const extraInfo = isForeign && g.nationality_code ? ` • ${g.nationality_code}` : '';
            const hasWarning = isForeign ? !g.passport_number : !g.identification_number;

            guestsHtml += `
                <div class="guest-card ${hasWarning ? 'guest-card__warn' : ''}">
                    <div class="guest-card__header">
                        <div style="display:flex;align-items:center;gap:8px;">
                            <span class="guest-badge ${badgeClass}">${badgeText}</span>
                            <span class="guest-card__name">${escapeHtml(name)}</span>
                        </div>
                        <button class="guest-card__remove" onclick="removeGuest(${i})">&#10005;</button>
                    </div>
                    <div class="guest-card__meta">
                        <span class="doc-type-badge doc-type-badge--${g.document_type || 'cccd'}" style="padding:1px 6px;font-size:10px;">${getDocTypeLabel(g.document_type)}</span>
                        <span>${escapeHtml(idDisplay)}${escapeHtml(extraInfo)}</span>
                    </div>
                </div>
            `;
        });
    }

    return `
        <div class="section-header">
            <div>
                <div class="section-header__title">Giấy tờ tùy thân</div>
                <div class="section-header__subtitle">Tải ảnh CCCD, Hộ chiếu, VNeID, Khai sinh</div>
            </div>
        </div>
        ${warningHtml}
        <div class="upload-zone" id="uploadZoneID">
            <div class="upload-zone__icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <rect x="2" y="4" width="20" height="16" rx="2"/>
                    <path d="M6 8h.01M6 12h.01M10 8h8M10 12h5"/>
                </svg>
            </div>
            <div class="upload-zone__title">Tải ảnh giấy tờ</div>
            <div class="upload-zone__subtitle">Hệ thống tự nhận diện CCCD, Hộ chiếu, VNeID...</div>
            <div class="upload-zone__actions">
                <button class="upload-zone__btn upload-zone__btn--primary" id="btnIDCamera">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z"/><circle cx="12" cy="13" r="4"/></svg>
                    Chụp ảnh
                </button>
                <button class="upload-zone__btn upload-zone__btn--secondary" id="btnIDGallery">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>
                    Thư viện
                </button>
            </div>
            <div class="upload-zone__hint">Hỗ trợ JPG, PNG, WEBP — Tối đa 10MB mỗi ảnh</div>
        </div>
        <input type="file" id="idFileCamera" accept="image/*" capture="environment" style="display:none">
        <input type="file" id="idFileGallery" accept="image/jpeg,image/png,image/webp" multiple style="display:none">
        ${guestsHtml}
        ${guests.length > 0 ? `
            <button class="add-more-btn" id="btnAddMore">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                Thêm ảnh
            </button>
        ` : ''}
        <div class="wizard-nav">
            <button class="btn btn--secondary flex-1" id="btnStep2Back">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
                Quay lại
            </button>
            <button class="btn btn--primary flex-1 btn--lg" id="btnStep2Next" ${guests.length === 0 ? 'disabled' : ''}>
                Tiếp tục
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
        </div>
    `;
}

function bindStep2Events() {
    const btnCamera = document.getElementById('btnIDCamera');
    const btnGallery = document.getElementById('btnIDGallery');
    const uploadZone = document.getElementById('uploadZoneID');
    const btnAddMore = document.getElementById('btnAddMore');

    if (btnCamera) btnCamera.addEventListener('click', (e) => { e.stopPropagation(); document.getElementById('idFileCamera').click(); });
    if (btnGallery) btnGallery.addEventListener('click', (e) => { e.stopPropagation(); document.getElementById('idFileGallery').click(); });
    if (uploadZone) uploadZone.addEventListener('click', () => document.getElementById('idFileGallery').click());
    if (btnAddMore) btnAddMore.addEventListener('click', () => document.getElementById('idFileGallery').click());

    document.getElementById('idFileCamera').addEventListener('change', handleIDFiles);
    document.getElementById('idFileGallery').addEventListener('change', handleIDFiles);

    document.getElementById('btnStep2Back').addEventListener('click', () => { wizardState.currentStep = 1; renderWizardStep(); });
    document.getElementById('btnStep2Next').addEventListener('click', () => { wizardState.currentStep = 3; renderWizardStep(); });
}

function removeGuest(index) {
    wizardState.guests.splice(index, 1);
    renderWizardStep();
}

async function handleIDFiles(e) {
    const files = Array.from(e.target.files);
    if (!files.length) return;

    const validFiles = files.filter(f => {
        if (!['image/jpeg', 'image/png', 'image/webp'].includes(f.type)) return false;
        if (f.size > 10 * 1024 * 1024) return false;
        return true;
    });

    if (!validFiles.length) {
        showToast('Không có file hợp lệ', 'error');
        return;
    }

    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="fade-in">${renderStepIndicator(2)}
        <div class="ocr-processing">
            <div class="ocr-processing__scanner"><div class="ocr-processing__scanner-inner">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M6 8h.01M6 12h.01M10 8h8M10 12h5"/></svg>
            </div></div>
            <div class="ocr-processing__title">Đang quét ${validFiles.length} ảnh giấy tờ</div>
            <div class="ocr-processing__subtitle">Tự động nhận diện loại giấy tờ...</div>
        </div></div>
    `;

    try {
        const result = await api.ocrBatchExtract(validFiles);
        const newGuests = result.guests || [];
        newGuests.forEach(newG => {
            const isForeign = newG.guest_type === 'foreign';
            if (isForeign) {
                // Merge foreign by passport_number
                if (!newG.passport_number) {
                    wizardState.guests.push(newG);
                    return;
                }
                const existing = wizardState.guests.find(g => g.guest_type === 'foreign' && g.passport_number === newG.passport_number);
                if (existing) {
                    for (const key of Object.keys(newG)) {
                        if (!existing[key] && newG[key]) existing[key] = newG[key];
                    }
                } else {
                    wizardState.guests.push(newG);
                }
            } else {
                // Merge VN by identification_number
                newG.guest_type = newG.guest_type || 'vietnamese';
                if (!newG.identification_number) {
                    wizardState.guests.push(newG);
                    return;
                }
                const existing = wizardState.guests.find(g => g.guest_type !== 'foreign' && g.identification_number === newG.identification_number);
                if (existing) {
                    for (const key of Object.keys(newG)) {
                        if ((!existing[key] || existing[key] === 'Không xác định') && newG[key] && newG[key] !== 'Không xác định') {
                            existing[key] = newG[key];
                        }
                    }
                } else {
                    wizardState.guests.push(newG);
                }
            }
        });
        renderWizardStep();

        const vnCount = newGuests.filter(g => g.guest_type !== 'foreign').length;
        const foreignCount = newGuests.filter(g => g.guest_type === 'foreign').length;
        let msg = `Đã quét ${result.total_profiles} hồ sơ`;
        if (vnCount > 0 && foreignCount > 0) msg += ` (${vnCount} VN, ${foreignCount} nước ngoài)`;
        showToast(msg, 'success');
    } catch (error) {
        showToast(error.message || 'Lỗi khi quét giấy tờ', 'error');
        renderWizardStep();
    }

    e.target.value = '';
}

/* ============================================
   STEP 3 — Review & Confirm
   ============================================ */
function renderStep3() {
    const b = wizardState.booking;
    const c = wizardState.contact;

    // Booking summary
    let bookingHtml = `
        <div class="review-section">
            <div class="review-section__title">Thông tin đặt phòng</div>
            <div class="review-summary">
                <div class="review-summary__row"><span class="review-summary__label">Mã đặt phòng</span><span class="review-summary__value">${escapeHtml(b.booking_code)}</span></div>
                <div class="review-summary__row"><span class="review-summary__label">Loại phòng</span><span class="review-summary__value">${escapeHtml(b.room_type || '—')}</span></div>
                <div class="review-summary__row"><span class="review-summary__label">Số người</span><span class="review-summary__value">${b.num_guests}</span></div>
                <div class="review-summary__row"><span class="review-summary__label">Nhận phòng</span><span class="review-summary__value">${escapeHtml(b.arrival_date)}</span></div>
                <div class="review-summary__row"><span class="review-summary__label">Trả phòng</span><span class="review-summary__value">${escapeHtml(b.departure_date)}</span></div>
            </div>
        </div>
    `;

    // Contact section
    let contactHtml = `
        <div class="review-section">
            <div class="review-section__title">Thông tin liên hệ</div>
            <div class="result-form">
                <div class="result-field">
                    <div class="result-field__header"><span class="result-field__label">Họ tên liên hệ *</span></div>
                    <input class="result-field__input" type="text" id="f_contact_name" value="${escapeHtml(c.name || '')}" placeholder="Nhập họ tên">
                </div>
                <div class="result-field">
                    <div class="result-field__header"><span class="result-field__label">Số điện thoại *</span></div>
                    <input class="result-field__input" type="tel" id="f_contact_phone" value="${escapeHtml(c.phone || '')}" placeholder="Nhập SĐT">
                </div>
            </div>
        </div>
    `;

    // Guest list — editable, different form per guest_type
    let guestsHtml = `<div class="review-section"><div class="review-section__title">Danh sách khách (${wizardState.guests.length})</div>`;
    wizardState.guests.forEach((g, i) => {
        const isForeign = g.guest_type === 'foreign';
        const badgeClass = isForeign ? 'guest-badge--foreign' : 'guest-badge--vn';
        const badgeText = isForeign ? 'Nước ngoài' : 'Việt Nam';

        guestsHtml += `
            <div class="guest-card" style="margin-bottom:var(--space-md);">
                <div style="display:flex;align-items:center;gap:8px;margin-bottom:var(--space-md);">
                    <span class="guest-badge ${badgeClass}">${badgeText}</span>
                    <span style="font-weight:700;font-size:14px;color:var(--color-primary);">Khách ${i + 1}</span>
                </div>
                <div class="result-form">
                    <div class="result-field">
                        <div class="result-field__header"><span class="result-field__label">Họ và tên *</span></div>
                        <input class="result-field__input" type="text" id="g_name_${i}" value="${escapeHtml(g.full_name || '')}">
                    </div>
                    <div class="result-field">
                        <div class="result-field__header"><span class="result-field__label">Giới tính</span></div>
                        <select class="result-field__select" id="g_gender_${i}">
                            <option value="">-- Chọn --</option>
                            ${isForeign ? `
                                <option value="M" ${g.gender === 'M' ? 'selected' : ''}>M (Male)</option>
                                <option value="F" ${g.gender === 'F' ? 'selected' : ''}>F (Female)</option>
                            ` : `
                                <option value="Nam" ${g.gender === 'Nam' ? 'selected' : ''}>Nam</option>
                                <option value="Nữ" ${g.gender === 'Nữ' ? 'selected' : ''}>Nữ</option>
                            `}
                        </select>
                    </div>
                    <div class="result-field">
                        <div class="result-field__header"><span class="result-field__label">Ngày sinh</span></div>
                        <input class="result-field__input" type="text" id="g_dob_${i}" value="${escapeHtml(g.date_of_birth || '')}" placeholder="DD/MM/YYYY">
                    </div>
                    ${isForeign ? `
                        <div class="result-field">
                            <div class="result-field__header"><span class="result-field__label">Số hộ chiếu *</span></div>
                            <input class="result-field__input" type="text" id="g_passport_${i}" value="${escapeHtml(g.passport_number || '')}">
                        </div>
                        <div class="result-field">
                            <div class="result-field__header"><span class="result-field__label">Mã quốc tịch (ISO alpha-3)</span></div>
                            <input class="result-field__input" type="text" id="g_natcode_${i}" value="${escapeHtml(g.nationality_code || '')}" placeholder="VD: GBR, CHN, DEU" maxlength="3" style="text-transform:uppercase;">
                        </div>
                    ` : `
                        <div class="result-field">
                            <div class="result-field__header"><span class="result-field__label">Số giấy tờ *</span></div>
                            <input class="result-field__input" type="text" id="g_id_${i}" value="${escapeHtml(g.identification_number || '')}">
                        </div>
                        <div class="result-field">
                            <div class="result-field__header"><span class="result-field__label">Địa chỉ</span></div>
                            <textarea class="result-field__input" id="g_addr_${i}" rows="2" style="resize:none;min-height:auto;">${escapeHtml(g.address || '')}</textarea>
                        </div>
                        <div class="result-field">
                            <div class="result-field__header"><span class="result-field__label">Loại giấy tờ</span></div>
                            <select class="result-field__select" id="g_doctype_${i}">
                                <option value="cccd" ${(g.document_type || 'cccd') === 'cccd' ? 'selected' : ''}>CCCD</option>
                                <option value="cmnd" ${g.document_type === 'cmnd' ? 'selected' : ''}>CMND</option>
                                <option value="passport" ${g.document_type === 'passport' ? 'selected' : ''}>Hộ chiếu</option>
                                <option value="birth_certificate" ${g.document_type === 'birth_certificate' ? 'selected' : ''}>Giấy khai sinh</option>
                                <option value="vneid" ${g.document_type === 'vneid' ? 'selected' : ''}>VNeID</option>
                            </select>
                        </div>
                        <div class="result-field">
                            <div class="result-field__header"><span class="result-field__label">Quốc tịch</span></div>
                            <input class="result-field__input" type="text" id="g_nationality_${i}" value="${escapeHtml(g.nationality || '')}" placeholder="VD: Việt Nam">
                        </div>
                    `}
                </div>
            </div>
        `;
    });
    guestsHtml += '</div>';

    return `
        <div class="section-header">
            <div>
                <div class="section-header__title">Xác nhận check-in</div>
                <div class="section-header__subtitle">Kiểm tra và xác nhận thông tin</div>
            </div>
        </div>
        ${bookingHtml}
        ${contactHtml}
        ${guestsHtml}
        <div class="wizard-nav">
            <button class="btn btn--secondary flex-1" id="btnStep3Back">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
                Quay lại
            </button>
            <button class="btn btn--primary flex-1 btn--lg" id="btnConfirmCheckin">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                Xác nhận
            </button>
        </div>
    `;
}

function bindStep3Events() {
    document.getElementById('btnStep3Back').addEventListener('click', () => {
        saveStep3ToState();
        wizardState.currentStep = 2;
        renderWizardStep();
    });
    document.getElementById('btnConfirmCheckin').addEventListener('click', handleConfirmCheckin);
}

function saveStep3ToState() {
    const contactName = document.getElementById('f_contact_name');
    const contactPhone = document.getElementById('f_contact_phone');
    if (contactName) wizardState.contact.name = contactName.value.trim() || null;
    if (contactPhone) wizardState.contact.phone = contactPhone.value.trim() || null;

    wizardState.guests.forEach((g, i) => {
        const name = document.getElementById(`g_name_${i}`);
        const gender = document.getElementById(`g_gender_${i}`);
        const dob = document.getElementById(`g_dob_${i}`);

        if (name) g.full_name = name.value.trim();
        if (gender) g.gender = gender.value || null;
        if (dob) g.date_of_birth = dob.value.trim() || null;

        if (g.guest_type === 'foreign') {
            const passport = document.getElementById(`g_passport_${i}`);
            const natCode = document.getElementById(`g_natcode_${i}`);
            if (passport) g.passport_number = passport.value.trim();
            if (natCode) g.nationality_code = natCode.value.trim().toUpperCase() || null;
        } else {
            const id = document.getElementById(`g_id_${i}`);
            const addr = document.getElementById(`g_addr_${i}`);
            const docType = document.getElementById(`g_doctype_${i}`);
            const nationality = document.getElementById(`g_nationality_${i}`);
            if (id) g.identification_number = id.value.trim();
            if (addr) g.address = addr.value.trim() || null;
            if (docType) g.document_type = docType.value || null;
            if (nationality) g.nationality = nationality.value.trim() || null;
        }
    });
}

async function handleConfirmCheckin() {
    saveStep3ToState();

    // Validate
    if (!wizardState.contact.name) { showToast('Vui lòng nhập họ tên liên hệ', 'error'); return; }
    if (!wizardState.contact.phone) { showToast('Vui lòng nhập số điện thoại', 'error'); return; }

    for (let i = 0; i < wizardState.guests.length; i++) {
        const g = wizardState.guests[i];
        if (!g.full_name) { showToast(`Khách ${i + 1}: Họ tên không được để trống`, 'error'); return; }
        if (g.guest_type === 'foreign') {
            if (!g.passport_number) { showToast(`Khách ${i + 1}: Số hộ chiếu không được để trống`, 'error'); return; }
        } else {
            if (!g.identification_number) { showToast(`Khách ${i + 1}: Số giấy tờ không được để trống`, 'error'); return; }
        }
    }

    const btn = document.getElementById('btnConfirmCheckin');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner" style="width:18px;height:18px;border-width:2px;"></div> Đang xử lý...';

    try {
        const payload = {
            booking: wizardState.booking,
            contact: wizardState.contact,
            guests: wizardState.guests.map(g => ({
                guest_type: g.guest_type || 'vietnamese',
                full_name: g.full_name,
                gender: g.gender || null,
                date_of_birth: g.date_of_birth || null,
                identification_number: g.identification_number || null,
                address: g.address || null,
                document_type: g.document_type || null,
                nationality: g.nationality || null,
                passport_number: g.passport_number || null,
                nationality_code: g.nationality_code || null,
            })),
        };

        await api.createCheckin(payload);
        showCheckinSuccess();
    } catch (error) {
        btn.disabled = false;
        btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> Xác nhận';
        showToast(error.message || 'Lỗi khi lưu check-in', 'error');
    }
}

let successTimer = null;

function showCheckinSuccess() {
    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="success-state fade-in">
            <div class="success-state__icon">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
            </div>
            <div class="success-state__title">Check-in thành công!</div>
            <div class="success-state__text">Thông tin đặt phòng và hồ sơ khách đã được lưu vào hệ thống.</div>
            <div class="success-state__countdown">Tự động chuyển sau <span id="countdown">5</span>s</div>
            <div class="flex flex-col gap-3" style="margin-top:var(--space-xl);">
                <button class="btn btn--primary btn--full btn--lg" id="btnNewCheckin">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                    Check-in mới
                </button>
                <button class="btn btn--secondary btn--full" id="btnGoHistory">
                    Xem lịch sử
                </button>
            </div>
        </div>
    `;

    document.getElementById('btnNewCheckin').addEventListener('click', () => {
        clearSuccessTimer();
        resetWizard();
        renderWizardStep();
    });
    document.getElementById('btnGoHistory').addEventListener('click', () => {
        clearSuccessTimer();
        onTabChange('history');
        document.querySelectorAll('.bottom-nav__item').forEach(i => i.classList.remove('bottom-nav__item--active'));
        document.querySelector('[data-tab=history]').classList.add('bottom-nav__item--active');
    });

    // Auto-redirect after 5s
    let seconds = 5;
    const countdownEl = document.getElementById('countdown');
    successTimer = setInterval(() => {
        seconds--;
        if (countdownEl) countdownEl.textContent = seconds;
        if (seconds <= 0) {
            clearSuccessTimer();
            resetWizard();
            renderWizardStep();
        }
    }, 1000);
}

function clearSuccessTimer() {
    if (successTimer) {
        clearInterval(successTimer);
        successTimer = null;
    }
}

/* ============================================
   HISTORY TAB
   ============================================ */
async function loadHistoryTab() {
    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="section-header">
            <div>
                <div class="section-header__title">Lịch sử</div>
                <div class="section-header__subtitle">Các lần check-in</div>
            </div>
        </div>
        <div class="loading"><div class="spinner"></div></div>
    `;

    try {
        const checkins = await api.getCheckins();
        if (!checkins || checkins.length === 0) {
            content.innerHTML = `
                <div class="section-header">
                    <div>
                        <div class="section-header__title">Lịch sử</div>
                        <div class="section-header__subtitle">Các lần check-in</div>
                    </div>
                </div>
                <div class="empty-state">
                    <div class="empty-state__icon">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                    </div>
                    <div class="empty-state__title">Chưa có check-in</div>
                    <div class="empty-state__text">Hãy thực hiện check-in để thấy dữ liệu ở đây.</div>
                </div>
            `;
            return;
        }

        const listHtml = checkins.map((ci, i) => `
            <div class="history-item fade-in stagger-${Math.min(i + 1, 5)}" onclick="showCheckinDetail(${ci.id})">
                <div class="history-item__avatar">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                </div>
                <div class="history-item__body">
                    <div class="history-item__name">${escapeHtml(ci.booking_code)}</div>
                    <div class="history-item__meta">
                        <span>${escapeHtml(ci.room_type || '—')}</span>
                        <span>•</span>
                        <span>${ci.num_guests} khách</span>
                        <span>•</span>
                        <span>${escapeHtml(ci.arrival_date)} → ${escapeHtml(ci.departure_date)}</span>
                    </div>
                </div>
                <div class="history-item__arrow">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
                </div>
            </div>
        `).join('');

        content.innerHTML = `
            <div class="section-header">
                <div>
                    <div class="section-header__title">Lịch sử</div>
                    <div class="section-header__subtitle">${checkins.length} lần check-in</div>
                </div>
            </div>
            <div class="flex flex-col gap-1">${listHtml}</div>
        `;
    } catch (error) {
        content.innerHTML = `
            <div class="section-header"><div><div class="section-header__title">Lịch sử</div></div></div>
            <div class="error-message">
                <span>${escapeHtml(error.message)}</span>
                <div class="error-message__actions"><button class="btn btn--secondary" onclick="loadHistoryTab()">Thử lại</button></div>
            </div>
        `;
    }
}

async function showCheckinDetail(checkinId) {
    try {
        const ci = await api.getCheckinDetail(checkinId);

        const guestsHtml = ci.guests.map(g => {
            const isForeign = (g.guest_type === 'foreign');
            const badgeClass = isForeign ? 'guest-badge--foreign' : 'guest-badge--vn';
            const badgeLabel = isForeign ? 'NN' : 'VN';
            const idDisplay = isForeign ? (g.passport_number || '') : (g.identification_number || '');
            const natInfo = isForeign && g.nationality_code ? ` • ${g.nationality_code}` : '';

            return `
                <div style="padding:var(--space-md) 0;border-bottom:1px solid var(--color-divider);">
                    <div style="display:flex;align-items:center;gap:6px;">
                        <span class="guest-badge ${badgeClass}">${badgeLabel}</span>
                        <span style="font-weight:600;font-size:14px;">${escapeHtml(g.full_name)}</span>
                    </div>
                    <div style="font-size:12px;color:var(--color-text-muted);margin-top:2px;">
                        <span class="doc-type-badge doc-type-badge--${g.document_type || 'cccd'}" style="padding:1px 6px;font-size:10px;">${getDocTypeLabel(g.document_type)}</span>
                        ${escapeHtml(idDisplay)}${escapeHtml(natInfo)} ${g.gender ? '• ' + escapeHtml(g.gender) : ''} ${g.date_of_birth ? '• ' + escapeHtml(g.date_of_birth) : ''}
                    </div>
                    ${!isForeign && g.address ? `<div style="font-size:12px;color:var(--color-text-muted);margin-top:2px;">${escapeHtml(g.address)}</div>` : ''}
                </div>
            `;
        }).join('');

        const overlay = openBottomSheet(`
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:var(--space-xl);">
                <h3 style="font-family:var(--font-display);font-size:17px;font-weight:700;">Chi tiết Check-in</h3>
                <span class="doc-type-badge doc-type-badge--cccd">${escapeHtml(ci.status)}</span>
            </div>
            <div class="review-summary" style="margin-bottom:var(--space-xl);">
                <div class="review-summary__row"><span class="review-summary__label">Mã đặt phòng</span><span class="review-summary__value">${escapeHtml(ci.booking_code)}</span></div>
                <div class="review-summary__row"><span class="review-summary__label">Loại phòng</span><span class="review-summary__value">${escapeHtml(ci.room_type || '—')}</span></div>
                <div class="review-summary__row"><span class="review-summary__label">Nhận phòng</span><span class="review-summary__value">${escapeHtml(ci.arrival_date)}</span></div>
                <div class="review-summary__row"><span class="review-summary__label">Trả phòng</span><span class="review-summary__value">${escapeHtml(ci.departure_date)}</span></div>
                <div class="review-summary__row"><span class="review-summary__label">Liên hệ</span><span class="review-summary__value">${escapeHtml(ci.contact_name || '—')} • ${escapeHtml(ci.contact_phone || '—')}</span></div>
                <div class="review-summary__row"><span class="review-summary__label">Ngày tạo</span><span class="review-summary__value">${formatDateVN(ci.created_at)}</span></div>
            </div>
            <div style="font-weight:700;font-size:14px;margin-bottom:var(--space-md);">Khách (${ci.guests.length})</div>
            ${guestsHtml}
            <div style="margin-top:var(--space-xl);">
                <button class="btn btn--secondary btn--full" id="btnCloseDetail">Đóng</button>
            </div>
        `);

        overlay.querySelector('#btnCloseDetail').addEventListener('click', () => closeBottomSheet(overlay));
    } catch (error) {
        showToast('Không thể tải chi tiết', 'error');
    }
}

/* ============================================
   INFO TAB (unchanged)
   ============================================ */
function loadInfoTab() {
    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="fade-in">
            <div class="section-header">
                <div>
                    <div class="section-header__title">Thông tin</div>
                    <div class="section-header__subtitle">Về ứng dụng Checkin Vedana</div>
                </div>
            </div>
            <div class="info-section">
                <div class="info-section__title">Tính năng</div>
                <div class="info-card">
                    <div class="info-card__row">
                        <div class="info-card__icon info-card__icon--orange">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                        </div>
                        <div class="info-card__text">
                            <div class="info-card__label">Check-in thông minh</div>
                            <div class="info-card__desc">Luồng 3 bước: Booking → Giấy tờ → Xác nhận</div>
                        </div>
                    </div>
                    <div class="info-card__row">
                        <div class="info-card__icon info-card__icon--orange">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 4v4a1 1 0 001 1h4M23 4v4a1 1 0 01-1 1h-4M1 20v-4a1 1 0 011-1h4M23 20v-4a1 1 0 00-1-1h-4"/></svg>
                        </div>
                        <div class="info-card__text">
                            <div class="info-card__label">Nhận diện OCR thông minh</div>
                            <div class="info-card__desc">Tự động trích xuất từ booking và giấy tờ</div>
                        </div>
                    </div>
                    <div class="info-card__row">
                        <div class="info-card__icon info-card__icon--blue">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                        </div>
                        <div class="info-card__text">
                            <div class="info-card__label">Bảo mật dữ liệu</div>
                            <div class="info-card__desc">Ảnh gốc được xóa ngay sau khi xử lý</div>
                        </div>
                    </div>
                    <div class="info-card__row">
                        <div class="info-card__icon info-card__icon--green">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                        </div>
                        <div class="info-card__text">
                            <div class="info-card__label">Xác minh & chỉnh sửa</div>
                            <div class="info-card__desc">Cho phép chỉnh sửa trước khi xác nhận</div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="info-section">
                <div class="info-section__title">Giấy tờ hỗ trợ</div>
                <div class="info-card">
                    <div class="info-card__row">
                        <div class="info-card__icon info-card__icon--orange"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="4" width="20" height="16" rx="2"/></svg></div>
                        <div class="info-card__text"><div class="info-card__label">CCCD / CMND</div></div>
                    </div>
                    <div class="info-card__row">
                        <div class="info-card__icon info-card__icon--blue"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/></svg></div>
                        <div class="info-card__text"><div class="info-card__label">Hộ chiếu</div></div>
                    </div>
                    <div class="info-card__row">
                        <div class="info-card__icon info-card__icon--green"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/></svg></div>
                        <div class="info-card__text"><div class="info-card__label">Giấy khai sinh</div></div>
                    </div>
                    <div class="info-card__row">
                        <div class="info-card__icon info-card__icon--blue"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="5" y="2" width="14" height="20" rx="2"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg></div>
                        <div class="info-card__text"><div class="info-card__label">VNeID (ảnh chụp màn hình)</div></div>
                    </div>
                </div>
            </div>
            <div class="info-section">
                <div class="info-section__title">Bảo mật</div>
                <div class="info-card" style="padding:var(--space-lg);font-size:13px;color:var(--color-text-secondary);line-height:1.7;">
                    Ảnh giấy tờ gốc <strong>không được lưu trữ</strong> trên hệ thống. Ảnh chỉ được xử lý tạm thời để trích xuất thông tin, sau đó bị xóa ngay lập tức.
                </div>
            </div>
        </div>
    `;
}

/* ============================================
   UTILITIES
   ============================================ */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDateVN(dateString) {
    if (!dateString) return '';
    const d = new Date(dateString);
    const day = String(d.getDate()).padStart(2, '0');
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const year = d.getFullYear();
    const hours = String(d.getHours()).padStart(2, '0');
    const mins = String(d.getMinutes()).padStart(2, '0');
    return `${day}/${month}/${year} ${hours}:${mins}`;
}

function getDocTypeLabel(type) {
    const map = { 'cccd': 'CCCD', 'cmnd': 'CMND', 'passport': 'Hộ chiếu', 'birth_certificate': 'Khai sinh', 'vneid': 'VNeID' };
    return map[type] || 'Giấy tờ';
}

function showToast(message, type = 'error') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    const icon = type === 'success'
        ? '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>'
        : '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>';
    toast.innerHTML = `${icon}<span>${escapeHtml(message)}</span>`;
    document.body.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('toast--visible'));
    setTimeout(() => { toast.classList.remove('toast--visible'); setTimeout(() => toast.remove(), 400); }, 3000);
}

function openBottomSheet(content) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `<div class="bottom-sheet"><div class="bottom-sheet__handle"></div>${content}</div>`;
    document.body.appendChild(overlay);
    requestAnimationFrame(() => overlay.classList.add('modal-overlay--active'));
    overlay.addEventListener('click', (e) => { if (e.target === overlay) closeBottomSheet(overlay); });
    return overlay;
}

function closeBottomSheet(overlay) {
    overlay.classList.remove('modal-overlay--active');
    overlay.addEventListener('transitionend', () => overlay.remove(), { once: true });
}

/* ============================================
   ROOM ASSIGNMENT — Danh sách checkin
   ============================================ */
async function loadRoomAssignmentList() {
    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="section-header">
            <div>
                <div class="section-header__title">Xếp phòng</div>
                <div class="section-header__subtitle">Chọn checkin để gán phòng</div>
            </div>
        </div>
        <div class="loading"><div class="spinner"></div></div>
    `;

    try {
        const data = await api.getGroupedCheckins();

        if (data.unassigned.length === 0 && data.assigned.length === 0) {
            content.innerHTML = `
                <div class="section-header"><div><div class="section-header__title">Xếp phòng</div></div></div>
                <div class="empty-state">
                    <div class="empty-state__icon">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
                    </div>
                    <div class="empty-state__title">Chưa có checkin</div>
                    <div class="empty-state__text">Hãy thực hiện check-in trước để xếp phòng.</div>
                </div>
            `;
            return;
        }

        let html = `
            <div class="section-header"><div>
                <div class="section-header__title">Xếp phòng</div>
                <div class="section-header__subtitle">Chọn checkin để gán phòng</div>
            </div></div>
        `;

        if (data.unassigned.length > 0) {
            html += `<div class="ra-section__title">Chưa xếp phòng <span class="ra-badge">${data.unassigned.length}</span></div>`;
            html += data.unassigned.map((ci, i) => renderCheckinItem(ci, i)).join('');
        }

        if (data.assigned.length > 0) {
            html += `<div class="ra-section__title" style="margin-top:var(--space-xl);">Đã xếp phòng</div>`;
            html += data.assigned.map((ci, i) => renderAssignedCheckinItem(ci, i)).join('');
        }

        content.innerHTML = `<div class="fade-in">${html}</div>`;

    } catch (error) {
        content.innerHTML = `
            <div class="section-header"><div><div class="section-header__title">Xếp phòng</div></div></div>
            <div class="error-message">
                <span>${escapeHtml(error.message)}</span>
                <div class="error-message__actions"><button class="btn btn--secondary" onclick="loadRoomAssignmentList()">Thử lại</button></div>
            </div>
        `;
    }
}

function renderCheckinItem(ci, index) {
    return `
        <div class="history-item fade-in stagger-${Math.min(index + 1, 5)}" onclick="startRoomSelection(${ci.id}, '${escapeHtml(ci.booking_code)}')">
            <div class="history-item__avatar">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            </div>
            <div class="history-item__body">
                <div class="history-item__name">${escapeHtml(ci.booking_code)}${ci.contact_name ? ' — ' + escapeHtml(ci.contact_name) : ''}</div>
                <div class="history-item__meta">
                    <span>${ci.num_guests} khách</span>
                    <span>•</span>
                    <span>${escapeHtml(ci.arrival_date)}</span>
                </div>
            </div>
            <div class="history-item__arrow">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
            </div>
        </div>
    `;
}

function renderAssignedCheckinItem(ci, index) {
    const roomTags = ci.rooms.map(r => `
        <span class="ra-room-tag">
            ${escapeHtml(r.room_number)}
            <button class="ra-room-tag__remove" onclick="event.stopPropagation(); handleReleaseRoom(${r.assignment_id}, '${escapeHtml(r.room_number)}')" title="Trả phòng">&#10005;</button>
        </span>
    `).join('');

    return `
        <div class="history-item fade-in stagger-${Math.min(index + 1, 5)}" onclick="startRoomSelection(${ci.id}, '${escapeHtml(ci.booking_code)}')">
            <div class="history-item__avatar" style="background:var(--color-success-bg);color:var(--color-success);">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
            </div>
            <div class="history-item__body">
                <div class="history-item__name">${escapeHtml(ci.booking_code)}${ci.contact_name ? ' — ' + escapeHtml(ci.contact_name) : ''}</div>
                <div class="history-item__meta">
                    <span>${ci.num_guests} khách</span>
                    <span>•</span>
                    <span>${escapeHtml(ci.arrival_date)}</span>
                </div>
                <div class="ra-room-tags">${roomTags}</div>
            </div>
            <div class="history-item__arrow">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
            </div>
        </div>
    `;
}

async function handleReleaseRoom(assignmentId, roomNumber) {
    if (!confirm(`Bạn có chắc muốn trả phòng ${roomNumber}?`)) return;
    try {
        await api.releaseRoom(assignmentId);
        showToast(`Đã trả phòng ${roomNumber}`, 'success');
        loadRoomAssignmentList();
    } catch (error) {
        showToast(error.message || 'Lỗi khi trả phòng', 'error');
    }
}

/* ============================================
   ROOM ASSIGNMENT — Chọn Building & Phòng
   ============================================ */
let selectedRooms = [];
let currentCheckinId = null;
let currentBookingCode = '';
let cachedRooms = [];

function startRoomSelection(checkinId, bookingCode) {
    currentCheckinId = checkinId;
    currentBookingCode = bookingCode;
    selectedRooms = [];
    showBackButton(() => {
        showBackButton(showLanding);
        loadRoomAssignmentList();
    });
    loadBuildingSelection();
}

async function loadBuildingSelection() {
    const content = document.getElementById('content');
    content.innerHTML = `
        <div class="section-header"><div>
            <div class="section-header__title">Chọn tòa nhà</div>
            <div class="section-header__subtitle">Booking: ${escapeHtml(currentBookingCode)}</div>
        </div></div>
        <div class="loading"><div class="spinner"></div></div>
    `;

    try {
        const buildings = await api.getBuildings();
        const gridHtml = buildings.map(b => `
            <button class="building-card" onclick="loadRoomGrid('${escapeHtml(b)}')">
                <div class="building-card__icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
                </div>
                <div class="building-card__name">${escapeHtml(b)}</div>
            </button>
        `).join('');

        content.innerHTML = `
            <div class="fade-in">
                <div class="section-header"><div>
                    <div class="section-header__title">Chọn tòa nhà</div>
                    <div class="section-header__subtitle">Booking: ${escapeHtml(currentBookingCode)}</div>
                </div></div>
                <div class="building-grid">${gridHtml}</div>
            </div>
        `;
    } catch (error) {
        content.innerHTML = `
            <div class="error-message">
                <span>${escapeHtml(error.message)}</span>
                <div class="error-message__actions"><button class="btn btn--secondary" onclick="loadBuildingSelection()">Thử lại</button></div>
            </div>
        `;
    }
}

async function loadRoomGrid(building) {
    selectedRooms = [];
    const content = document.getElementById('content');

    showBackButton(() => {
        showBackButton(() => {
            showBackButton(showLanding);
            loadRoomAssignmentList();
        });
        loadBuildingSelection();
    });

    content.innerHTML = `
        <div class="section-header"><div>
            <div class="section-header__title">Tòa ${escapeHtml(building)}</div>
            <div class="section-header__subtitle">Chọn phòng cho ${escapeHtml(currentBookingCode)}</div>
        </div></div>
        <div class="loading"><div class="spinner"></div></div>
    `;

    try {
        cachedRooms = await api.getRoomsByBuilding(building);
        renderRoomGrid(building, cachedRooms);
    } catch (error) {
        content.innerHTML = `
            <div class="error-message">
                <span>${escapeHtml(error.message)}</span>
                <div class="error-message__actions"><button class="btn btn--secondary" onclick="loadRoomGrid('${escapeHtml(building)}')">Thử lại</button></div>
            </div>
        `;
    }
}

function renderRoomGrid(building, rooms) {
    const content = document.getElementById('content');
    const gridHtml = rooms.map(r => {
        const isOccupied = r.status === 'occupied';
        const isSelected = selectedRooms.includes(r.id);
        let cls = 'room-cell';
        if (isOccupied) cls += ' room-cell--occupied';
        else if (isSelected) cls += ' room-cell--selected';

        return `
            <button class="${cls}" ${isOccupied ? 'disabled' : ''} onclick="toggleRoom(${r.id}, '${escapeHtml(building)}')">
                <div class="room-cell__number">${escapeHtml(r.room_number)}</div>
                <div class="room-cell__type">${escapeHtml(r.room_type)}</div>
            </button>
        `;
    }).join('');

    const selectedCount = selectedRooms.length;

    content.innerHTML = `
        <div class="fade-in">
            <div class="section-header"><div>
                <div class="section-header__title">Tòa ${escapeHtml(building)}</div>
                <div class="section-header__subtitle">Chọn phòng cho ${escapeHtml(currentBookingCode)}</div>
            </div></div>
            <div class="room-grid-legend">
                <span class="room-legend__item"><span class="room-legend__dot room-legend__dot--available"></span>Trống</span>
                <span class="room-legend__item"><span class="room-legend__dot room-legend__dot--occupied"></span>Đã gán</span>
                <span class="room-legend__item"><span class="room-legend__dot room-legend__dot--selected"></span>Đang chọn</span>
            </div>
            <div class="room-grid">${gridHtml}</div>
            <div class="wizard-nav" style="margin-top:var(--space-xl);">
                <button class="btn btn--secondary flex-1" onclick="loadBuildingSelection()">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
                    Đổi tòa
                </button>
                <button class="btn btn--primary flex-1 btn--lg" id="btnConfirmRooms" ${selectedCount === 0 ? 'disabled' : ''}>
                    Xác nhận (${selectedCount})
                </button>
            </div>
        </div>
    `;

    document.getElementById('btnConfirmRooms').addEventListener('click', () => confirmRoomAssignment(building));
}

function toggleRoom(roomId, building) {
    const idx = selectedRooms.indexOf(roomId);
    if (idx >= 0) {
        selectedRooms.splice(idx, 1);
    } else {
        selectedRooms.push(roomId);
    }
    renderRoomGrid(building, cachedRooms);
}

async function confirmRoomAssignment(building) {
    if (selectedRooms.length === 0) return;

    const btn = document.getElementById('btnConfirmRooms');
    btn.disabled = true;
    btn.innerHTML = '<div class="spinner" style="width:18px;height:18px;border-width:2px;"></div> Đang xử lý...';

    try {
        await api.assignRooms(currentCheckinId, selectedRooms);
        showToast('Xếp phòng thành công!', 'success');
        selectedRooms = [];
        showBackButton(showLanding);
        loadRoomAssignmentList();
    } catch (error) {
        showToast(error.message || 'Lỗi khi xếp phòng', 'error');
        loadRoomGrid(building);
    }
}
