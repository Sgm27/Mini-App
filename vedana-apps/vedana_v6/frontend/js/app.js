'use strict';

// ============================================================
// APP STATE
// ============================================================
const state = {
    roomId:          null,
    photos:          [],     // [{ dataUrl, fileUrl, uploading, error }]
    voiceText:       '',
    voiceUrl:        null,
    isRecording:     false,
    cameraReady:     false,
    qrScanning:      false,
    qrFrame:         null,
    cameraStream:    null,
    mediaRecorder:   null,
    audioChunks:     [],
    recognition:     null,
    countdownTimer:  null,
};

const MAX_PHOTOS = 3;

// ============================================================
// SCREEN NAVIGATION
// ============================================================
let currentScreen = 'qr';

function showScreen(id, direction) {
    if (currentScreen === id) return;

    const cur  = document.getElementById('screen-' + currentScreen);
    const next = document.getElementById('screen-' + id);
    if (!cur || !next) return;

    cur.classList.remove('screen--active');
    if (direction !== 'back') {
        cur.classList.add('screen--exit');
    }

    // For back navigation: slide next in from left
    if (direction === 'back') {
        next.style.transform = 'translateX(-30%)';
        // Force reflow
        next.getBoundingClientRect();
        next.style.transform = '';
    }

    next.classList.add('screen--active');

    setTimeout(function () {
        cur.classList.remove('screen--exit');
        cur.style.transform = '';
    }, 320);

    currentScreen = id;
}

// ============================================================
// SCREEN 1 — QR SCANNER
// ============================================================
async function initQRScanner() {
    const btn = document.getElementById('btn-start-scan');
    if (btn) {
        btn.textContent = 'Đang khởi động...';
        btn.disabled = true;
    }

    // Verify jsQR loaded
    if (typeof jsQR === 'undefined') {
        showToast('Thư viện quét chưa tải, nhập thủ công', 'error');
        revealManualEntry();
        if (btn) { btn.textContent = 'Bắt đầu quét'; btn.disabled = false; }
        return;
    }

    try {
        await openQRCameraStream();
        if (btn) btn.style.display = 'none';
        document.getElementById('scanner-box').classList.add('scanner-box--active');
        state.qrScanning = true;
        tickQRScan();
    } catch (err) {
        console.error('QR camera error:', err);
        if (btn) { btn.textContent = 'Bắt đầu quét'; btn.disabled = false; }
        revealManualEntry();
        showToast('Không thể mở camera – hãy nhập thủ công', 'error');
    }
}

async function openQRCameraStream() {
    stopActiveStream();
    const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
    });
    state.cameraStream = stream;
    const vid = document.getElementById('qr-video');
    vid.srcObject = stream;
    await new Promise(function (res) { vid.onloadedmetadata = res; });
    await vid.play();
}

function tickQRScan() {
    if (!state.qrScanning) return;

    const vid    = document.getElementById('qr-video');
    const canvas = document.getElementById('qr-canvas');

    if (vid.readyState >= HTMLMediaElement.HAVE_ENOUGH_DATA && vid.videoWidth > 0) {
        canvas.width  = vid.videoWidth;
        canvas.height = vid.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(vid, 0, 0, canvas.width, canvas.height);
        const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const code = jsQR(imgData.data, imgData.width, imgData.height, { inversionAttempts: 'dontInvert' });
        if (code && code.data) {
            onQRFound(code.data);
            return;
        }
    }

    state.qrFrame = requestAnimationFrame(tickQRScan);
}

function onQRFound(raw) {
    state.qrScanning = false;
    cancelAnimationFrame(state.qrFrame);

    const roomId = extractRoomId(raw);
    if (!roomId) {
        showToast('Không quét được mã phòng', 'error');
        state.qrScanning = true;
        tickQRScan();
        return;
    }

    state.roomId = roomId;
    stopActiveStream();
    goToCameraScreen();
}

function extractRoomId(raw) {
    if (!raw) return null;
    raw = raw.trim();
    var patterns = [
        /\/rooms?\/([A-Za-z0-9]+)/i,
        /room[_-]?([A-Za-z0-9]+)/i,
        /phong[_-]?([A-Za-z0-9]+)/i,
        /^([A-Za-z0-9]{1,10})$/,
    ];
    for (var i = 0; i < patterns.length; i++) {
        var m = raw.match(patterns[i]);
        if (m) return m[1].toUpperCase();
    }
    // Fallback: first 10 non-whitespace chars
    return raw.replace(/\s+/g, '').substring(0, 10).toUpperCase() || null;
}

function revealManualEntry() {
    var el = document.getElementById('manual-entry');
    if (el) el.style.display = 'block';
}

function enterManualRoom() {
    var val = (document.getElementById('manual-room-id').value || '').trim();
    if (!val) { showToast('Nhập mã phòng trước', 'error'); return; }
    state.roomId = val.toUpperCase();
    stopActiveStream();
    goToCameraScreen();
}

// ============================================================
// SCREEN 2 — CAMERA CAPTURE
// ============================================================
function goToCameraScreen() {
    state.photos = [];
    showScreen('camera');
    setTimeout(openCaptureCamera, 150);
    syncCameraUI();
}

async function openCaptureCamera() {
    try {
        stopActiveStream();
        var stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: { ideal: 'environment' }, width: { ideal: 1920 }, height: { ideal: 1080 } },
            audio: false,
        });
        state.cameraStream = stream;
        state.cameraReady  = true;

        var vid = document.getElementById('camera-video');
        vid.srcObject = stream;
        await vid.play();

        var titleEl = document.getElementById('camera-room-title');
        if (titleEl) titleEl.textContent = 'PHÒNG ' + state.roomId;
    } catch (err) {
        console.error('Capture camera error:', err);
        state.cameraReady = false;
        showToast('Không thể mở camera', 'error');
    }
}

async function capturePhoto() {
    if (!state.cameraReady) { showToast('Camera chưa sẵn sàng', 'error'); return; }
    if (state.photos.length >= MAX_PHOTOS) { showToast('Đã đủ ' + MAX_PHOTOS + ' ảnh', 'error'); return; }

    var vid    = document.getElementById('camera-video');
    var canvas = document.getElementById('capture-canvas');
    canvas.width  = vid.videoWidth;
    canvas.height = vid.videoHeight;
    canvas.getContext('2d').drawImage(vid, 0, 0, canvas.width, canvas.height);
    var dataUrl = canvas.toDataURL('image/jpeg', 0.85);

    var idx = state.photos.length;
    state.photos.push({ dataUrl: dataUrl, fileUrl: null, uploading: true, error: false });
    renderThumbs();
    syncCameraUI();

    // Upload immediately
    try {
        var blob = dataUrlToBlob(dataUrl);
        var fd   = new FormData();
        fd.append('file', blob, 'photo_' + Date.now() + '.jpg');
        var result = await api.uploadForm('/api/upload', fd);
        state.photos[idx].fileUrl   = result.file_url;
        state.photos[idx].uploading = false;
        renderThumbs();
    } catch (e) {
        console.error('Photo upload error:', e);
        state.photos[idx].uploading = false;
        state.photos[idx].error     = true;
        renderThumbs();
        showToast('Lỗi tải ảnh, thử chụp lại', 'error');
    }

    if (state.photos.length >= MAX_PHOTOS) {
        setTimeout(proceedToReport, 500);
    }
}

function deletePhoto(idx) {
    state.photos.splice(idx, 1);
    renderThumbs();
    syncCameraUI();
}

function renderThumbs() {
    var strip = document.getElementById('thumb-strip');
    if (!strip) return;
    strip.innerHTML = state.photos.map(function (p, i) {
        return '<div class="thumb-item">' +
            '<img src="' + p.dataUrl + '" alt="Ảnh ' + (i + 1) + '">' +
            '<button class="thumb-del" onclick="deletePhoto(' + i + ')" aria-label="Xóa">×</button>' +
            (p.uploading ? '<div class="thumb-loading-overlay"><div class="mini-spin"></div></div>' : '') +
        '</div>';
    }).join('');
}

function syncCameraUI() {
    var counter = document.getElementById('photo-counter');
    if (counter) counter.textContent = state.photos.length + ' / ' + MAX_PHOTOS;

    var skipBtn = document.getElementById('btn-skip-cam');
    if (skipBtn) {
        skipBtn.style.visibility = (state.photos.length > 0 && state.photos.length < MAX_PHOTOS)
            ? 'visible' : 'hidden';
    }
}

function proceedToReport() {
    if (state.photos.length === 0) { showToast('Chụp ít nhất 1 ảnh', 'error'); return; }
    stopActiveStream();
    goToReportScreen();
}

// ============================================================
// SCREEN 3 — ROOM REPORT
// ============================================================
function goToReportScreen() {
    showScreen('report');

    var titleEl = document.getElementById('report-room-title');
    if (titleEl) titleEl.textContent = 'PHÒNG ' + state.roomId;

    renderReportPhotos();
    resetVoiceUI();
    setupSpeechRecognition();
}

function renderReportPhotos() {
    var strip = document.getElementById('report-photo-strip');
    if (!strip) return;
    strip.innerHTML = state.photos.map(function (p, i) {
        return '<div class="photo-strip-item"><img src="' + p.dataUrl + '" alt="Ảnh ' + (i + 1) + '"></div>';
    }).join('');
}

function resetVoiceUI() {
    var ta  = document.getElementById('voice-text');
    var ni  = document.getElementById('note-input');
    var btn = document.getElementById('btn-mic');
    var st  = document.getElementById('mic-status');
    if (ta)  ta.value  = '';
    if (ni)  ni.value  = '';
    if (btn) btn.classList.remove('mic-btn--recording');
    if (st)  { st.textContent = 'Nhấn để ghi âm'; st.classList.remove('mic-status--active'); }
    state.voiceText = '';
    state.voiceUrl  = null;
    state.isRecording = false;
}

function goBackToCamera() {
    stopRecording();
    showScreen('camera', 'back');
    // Restart camera if needed
    if (!state.cameraReady || !state.cameraStream) {
        setTimeout(openCaptureCamera, 150);
    }
}

// ============================================================
// VOICE RECORDING
// ============================================================
function setupSpeechRecognition() {
    var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { state.recognition = null; return; }

    var rec = new SR();
    rec.lang = 'vi-VN';
    rec.continuous = true;
    rec.interimResults = true;

    var finalText = '';

    rec.onresult = function (e) {
        var interim = '';
        for (var i = e.resultIndex; i < e.results.length; i++) {
            if (e.results[i].isFinal) {
                finalText += e.results[i][0].transcript + ' ';
            } else {
                interim += e.results[i][0].transcript;
            }
        }
        var ta = document.getElementById('voice-text');
        if (ta) ta.value = finalText + interim;
    };

    rec.onerror = function (e) {
        if (e.error === 'no-speech') return;
        console.error('SR error:', e.error);
        stopRecording();
        showToast('Lỗi nhận giọng nói', 'error');
    };

    rec.onend = function () {
        if (state.isRecording) {
            try { rec.start(); } catch (_) {}
        }
    };

    state.recognition = rec;
}

function toggleRecording() {
    if (state.isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
}

async function startRecording() {
    state.isRecording = true;

    var btn = document.getElementById('btn-mic');
    var st  = document.getElementById('mic-status');
    if (btn) btn.classList.add('mic-btn--recording');
    if (st)  { st.textContent = 'Đang ghi âm...'; st.classList.add('mic-status--active'); }

    // Speech-to-text
    if (state.recognition) {
        try { state.recognition.start(); } catch (e) { console.warn('SR start:', e); }
    }

    // Audio capture for upload
    try {
        var audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        state.audioChunks = [];
        state.mediaRecorder = new MediaRecorder(audioStream);

        state.mediaRecorder.ondataavailable = function (e) {
            if (e.data.size > 0) state.audioChunks.push(e.data);
        };

        state.mediaRecorder.onstop = async function () {
            audioStream.getTracks().forEach(function (t) { t.stop(); });
            var blob = new Blob(state.audioChunks, { type: 'audio/webm' });
            try {
                var fd = new FormData();
                fd.append('file', blob, 'voice_' + Date.now() + '.webm');
                var res = await api.uploadForm('/api/upload', fd);
                state.voiceUrl = res.file_url;
            } catch (e) {
                console.error('Audio upload error:', e);
            }
        };

        state.mediaRecorder.start();
    } catch (e) {
        console.warn('MediaRecorder not available:', e);
        // Speech-to-text may still work without audio recording
    }
}

function stopRecording() {
    if (!state.isRecording) return;
    state.isRecording = false;

    var btn = document.getElementById('btn-mic');
    var st  = document.getElementById('mic-status');
    if (btn) btn.classList.remove('mic-btn--recording');
    if (st)  { st.textContent = 'Ghi âm hoàn tất ✓'; st.classList.remove('mic-status--active'); }

    if (state.recognition) {
        try { state.recognition.stop(); } catch (_) {}
    }

    if (state.mediaRecorder && state.mediaRecorder.state !== 'inactive') {
        state.mediaRecorder.stop();
    }

    var ta = document.getElementById('voice-text');
    if (ta) state.voiceText = ta.value.trim();
}

// ============================================================
// SUBMIT REPORT
// ============================================================
async function submitReport() {
    if (state.photos.length === 0) { showToast('Cần ít nhất 1 ảnh', 'error'); return; }
    if (!state.roomId)              { showToast('Thiếu mã phòng', 'error');    return; }

    var uploading = state.photos.filter(function (p) { return p.uploading; });
    if (uploading.length > 0)       { showToast('Đang tải ảnh lên, vui lòng đợi...', 'error'); return; }

    var failed = state.photos.filter(function (p) { return p.error; });
    if (failed.length > 0)          { showToast('Có ảnh bị lỗi, xóa và chụp lại', 'error'); return; }

    stopRecording();

    var voiceText = (document.getElementById('voice-text')  || {}).value || '';
    var noteText  = (document.getElementById('note-input')  || {}).value || '';
    var combined  = [voiceText.trim(), noteText.trim()].filter(Boolean).join('\n') || null;

    var submitBtn = document.getElementById('btn-submit');
    if (submitBtn) { submitBtn.textContent = 'Đang gửi...'; submitBtn.disabled = true; }

    try {
        await api.post('/api/reports', {
            room_id:    state.roomId,
            note_text:  combined,
            voice_url:  state.voiceUrl,
            image_urls: state.photos.map(function (p) { return p.fileUrl; }).filter(Boolean),
        });
        goToSuccessScreen();
    } catch (err) {
        console.error('Submit error:', err);
        showToast('Lỗi gửi: ' + (err.message || 'Thử lại'), 'error');
    } finally {
        if (submitBtn) { submitBtn.textContent = 'GỬI BÁO CÁO'; submitBtn.disabled = false; }
    }
}

// ============================================================
// SCREEN 4 — SUCCESS
// ============================================================
function goToSuccessScreen() {
    showScreen('success');

    // Trigger pop animation after slide-in completes
    setTimeout(function () {
        var circle = document.getElementById('success-circle');
        if (circle) circle.classList.add('success-circle--pop');
    }, 320);

    var sub = document.getElementById('success-sub');
    if (sub) sub.textContent = 'Phòng ' + state.roomId + ' đã được ghi nhận';

    // Countdown auto-redirect
    var ticking = 3;
    var el = document.getElementById('countdown');
    if (el) el.textContent = ticking;

    clearInterval(state.countdownTimer);
    state.countdownTimer = setInterval(function () {
        ticking--;
        if (el) el.textContent = ticking;
        if (ticking <= 0) {
            clearInterval(state.countdownTimer);
            startNewRoom();
        }
    }, 1000);
}

function startNewRoom() {
    clearInterval(state.countdownTimer);
    state.countdownTimer = null;

    // Reset state
    state.roomId = null;
    state.photos = [];
    state.voiceText = '';
    state.voiceUrl = null;
    state.isRecording = false;
    state.cameraReady = false;
    state.audioChunks = [];

    // Reset success circle animation class for next time
    var circle = document.getElementById('success-circle');
    if (circle) circle.classList.remove('success-circle--pop');

    // Reset all screens to off-screen position
    document.querySelectorAll('.screen').forEach(function (s) {
        s.classList.remove('screen--active', 'screen--exit');
        s.style.transform = '';
    });
    currentScreen = 'qr';
    document.getElementById('screen-qr').classList.add('screen--active');

    // Reset QR screen UI
    var scanBtn = document.getElementById('btn-start-scan');
    if (scanBtn) { scanBtn.textContent = 'Bắt đầu quét'; scanBtn.disabled = false; scanBtn.style.display = ''; }
    var manualEntry = document.getElementById('manual-entry');
    if (manualEntry) manualEntry.style.display = 'none';
    var manualInput = document.getElementById('manual-room-id');
    if (manualInput) manualInput.value = '';
    document.getElementById('scanner-box').classList.remove('scanner-box--active');

    // Auto-start QR scanner
    setTimeout(initQRScanner, 400);
}

// ============================================================
// UTILITIES
// ============================================================
function stopActiveStream() {
    state.qrScanning = false;
    if (state.qrFrame) { cancelAnimationFrame(state.qrFrame); state.qrFrame = null; }
    if (state.cameraStream) {
        state.cameraStream.getTracks().forEach(function (t) { t.stop(); });
        state.cameraStream = null;
    }
    state.cameraReady = false;
}

function dataUrlToBlob(dataUrl) {
    var parts = dataUrl.split(',');
    var mime  = parts[0].match(/:(.*?);/)[1];
    var bstr  = atob(parts[1]);
    var n     = bstr.length;
    var u8    = new Uint8Array(n);
    while (n--) u8[n] = bstr.charCodeAt(n);
    return new Blob([u8], { type: mime });
}

var _toastTimer = null;
function showToast(msg, type) {
    var toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = msg;
    toast.className = 'toast toast--show' + (type ? ' toast--' + type : '');
    clearTimeout(_toastTimer);
    _toastTimer = setTimeout(function () { toast.className = 'toast'; }, 3200);
}

// ============================================================
// INIT
// ============================================================
document.addEventListener('DOMContentLoaded', function () {
    setTimeout(initQRScanner, 600);
});
