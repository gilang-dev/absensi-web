'use strict';

// =========================================================
// HELPERS
// =========================================================

const $ = (id) => document.getElementById(id);

const CAMERA_CONSTRAINTS = {
    video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
    audio: false
};

const ESCAPE_MAP = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '\x22': '&quot;', '\x27': '&#39;' };

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>\x22\x27]/g, (c) => ESCAPE_MAP[c]);
}

function formatScore(score) {
    if (score === null || score === undefined) return 'Tidak tersedia';
    const n = Number(score);
    return Number.isNaN(n) ? 'Tidak tersedia' : n.toFixed(4);
}

function setStatus(el, text) {
    if (el) el.textContent = text;
}

function setButton(btn, text, disabled) {
    if (!btn) return;
    if (text !== undefined) btn.textContent = text;
    btn.disabled = disabled;
}

async function openCamera(video) {
    const stream = await navigator.mediaDevices.getUserMedia(CAMERA_CONSTRAINTS);
    video.srcObject = stream;
    return stream;
}

function stopStream(stream, video) {
    if (stream) stream.getTracks().forEach((track) => track.stop());
    if (video) video.srcObject = null;
}

// Ambil frame (mirror seperti kamera depan) dan tampilkan di atas video.
function captureFrame(video, canvas) {
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext('2d');
    ctx.save();
    ctx.translate(canvas.width, 0);
    ctx.scale(-1, 1);
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    ctx.restore();

    canvas.style.display = 'block';

    return new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.85));
}

async function postImage(url, blob, filename, extra = {}) {
    const formData = new FormData();
    formData.append('file', blob, filename);
    Object.entries(extra).forEach(([key, value]) => formData.append(key, value));

    const response = await fetch(url, { method: 'POST', body: formData });
    return response.json();
}


// =========================================================
// POPUP BERHASIL (CEKLIS) - login & absensi
// =========================================================

const POPUP_CSS = `
.sp-overlay{position:fixed;inset:0;z-index:99999;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.82);backdrop-filter:blur(8px);opacity:0;transition:opacity .2s ease}
.sp-overlay.show{opacity:1}
.sp-box{width:340px;max-width:92%;padding:32px 26px 24px;background:#11151c;border:1px solid rgba(255,255,255,.1);border-radius:18px;box-shadow:0 20px 60px rgba(0,0,0,.5);text-align:center;transform:scale(.9);transition:transform .25s cubic-bezier(.34,1.56,.64,1)}
.sp-overlay.show .sp-box{transform:scale(1)}
.sp-circle{width:80px;height:80px;margin:0 auto 18px;border-radius:50%;background:#22c55e;display:flex;align-items:center;justify-content:center;box-shadow:0 0 0 8px rgba(34,197,94,.15)}
.sp-circle svg{width:44px;height:44px}
.sp-circle path{fill:none;stroke:#fff;stroke-width:6;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:50;stroke-dashoffset:50;animation:spDraw .4s .2s ease forwards}
@keyframes spDraw{to{stroke-dashoffset:0}}
.sp-box h3{margin:0 0 6px;color:#fff;font-size:21px}
.sp-msg{margin:0 0 14px;color:#999;font-size:14px;line-height:1.5;white-space:pre-line}
.sp-score{display:flex;align-items:center;justify-content:space-between;margin:0 0 20px;padding:10px 14px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.08);border-radius:12px;color:#999;font-size:13px}
.sp-score strong{color:#fff;font-size:15px}
.sp-box button{width:100%;min-height:46px;border:none;border-radius:12px;background:linear-gradient(135deg,#2563eb,#7c3aed);color:#fff;font-size:15px;font-weight:700;cursor:pointer;transition:opacity .2s ease}
.sp-box button:hover{opacity:.9}
`;

const CHECK_SVG = '<svg viewBox="0 0 52 52"><path d="M14 27 L23 36 L39 18"/></svg>';

function showSuccessPopup({ title, message, score }) {
    if (!$('successPopupStyle')) {
        const style = document.createElement('style');
        style.id = 'successPopupStyle';
        style.textContent = POPUP_CSS;
        document.head.appendChild(style);
    }

    const old = $('successPopup');
    if (old) old.remove();

    const make = (tag, className, text) => {
        const el = document.createElement(tag);
        if (className) el.className = className;
        if (text !== undefined) el.textContent = text;
        return el;
    };

    const overlay = make('div', 'sp-overlay');
    overlay.id = 'successPopup';

    const box = make('div', 'sp-box');
    const circle = make('div', 'sp-circle');
    circle.innerHTML = CHECK_SVG;

    box.append(circle, make('h3', '', title), make('p', 'sp-msg', message));

    if (score !== undefined) {
        const row = make('div', 'sp-score');
        row.append(make('span', '', 'FaceNet Score'), make('strong', '', score));
        box.appendChild(row);
    }

    const okButton = make('button', '', 'OK');
    okButton.type = 'button';
    box.appendChild(okButton);
    overlay.appendChild(box);
    document.body.appendChild(overlay);

    requestAnimationFrame(() => overlay.classList.add('show'));

    let closed = false;
    const close = () => {
        if (closed) return;
        closed = true;
        overlay.classList.remove('show');
        setTimeout(() => overlay.remove(), 200);
    };

    okButton.addEventListener('click', close);
    overlay.addEventListener('click', (event) => {
        if (event.target === overlay) close();
    });
    setTimeout(close, 3000);
}


// =========================================================
// LOGIN & UTILITAS HALAMAN LOGIN
// =========================================================

function togglePassword() {
    const password = $('password');
    password.type = password.type === 'password' ? 'text' : 'password';
}

function logout() {
    window.location.href = '/';
}

async function login(event) {
    event.preventDefault();

    const username = $('username').value.trim();
    const password = $('password').value;

    if (!username || !password) {
        alert('NIM/Email dan password wajib diisi.');
        return;
    }

    try {
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch('/api/login', { method: 'POST', body: formData });
        const result = await response.json();

        if (!result.success) {
            alert(result.message || 'Login gagal.');
            return;
        }

        window.location.href = '/dashboard';

    } catch (error) {
        console.error('LOGIN ERROR:', error);
        alert('Terjadi kesalahan saat menghubungi server.');
    }
}


// =========================================================
// FACE LOGIN
// =========================================================

let faceLoginStream = null;
let isFaceLoginProcessing = false;

async function openFaceLogin() {
    const status = $('faceLoginStatus');

    $('faceLoginModal').classList.add('active');
    setStatus(status, 'Meminta akses kamera...');

    try {
        faceLoginStream = await openCamera($('faceLoginCamera'));
        setStatus(status, 'Kamera aktif. Posisikan wajah di dalam kotak.');

    } catch (error) {
        console.error('Camera error:', error);
        setStatus(status, 'Kamera tidak dapat digunakan.');
        alert('Kamera tidak dapat diakses.\n\nPastikan browser sudah diberikan izin kamera.');
    }
}

function stopFaceLoginCamera() {
    stopStream(faceLoginStream, $('faceLoginCamera'));
    faceLoginStream = null;
}

function closeFaceLogin() {
    $('faceLoginModal').classList.remove('active');
    stopFaceLoginCamera();
}

function resetFaceLogin() {
    isFaceLoginProcessing = false;

    const canvas = $('faceCanvas');
    if (canvas) canvas.style.display = 'none';

    setStatus($('faceLoginStatus'), 'Kamera aktif. Posisikan wajah di dalam kotak.');
    setButton($('verifyFaceButton'), 'VERIFIKASI WAJAH', false);
}

async function captureFaceLogin() {
    if (isFaceLoginProcessing) return;

    const video = $('faceLoginCamera');
    const canvas = $('faceCanvas');
    const status = $('faceLoginStatus');
    const button = $('verifyFaceButton');

    if (!video || !canvas) {
        console.error('Video atau canvas login wajah tidak ditemukan');
        return;
    }

    if (!video.videoWidth || !video.videoHeight) {
        alert('Kamera belum siap. Tunggu sebentar.');
        return;
    }

    isFaceLoginProcessing = true;
    setStatus(status, 'Memverifikasi wajah...');
    setButton(button, 'MEMVERIFIKASI...', true);

    try {
        const blob = await captureFrame(video, canvas);
        if (!blob) throw new Error('Gagal membuat gambar');

        const data = await postImage('/api/face-login', blob, 'face_capture.jpg');

        if (data.success) {
            const score = formatScore(data.facenet_score);

            setStatus(status, '\u2713 Login berhasil sebagai ' + data.name + ' | FaceNet Score: ' + score);
            setButton(button, 'BERHASIL', true);

            showSuccessPopup({
                title: 'Login Berhasil!',
                message: 'Selamat datang, ' + data.name,
                score
            });

            setTimeout(() => window.location.replace('/dashboard'), 1800);
            return;
        }

        setStatus(status, data.message || 'Wajah tidak dikenali.');
        setButton(button, 'GAGAL', true);
        setTimeout(resetFaceLogin, 1000);

    } catch (error) {
        console.error('ERROR FACE LOGIN:', error);
        setStatus(status, 'Terjadi kesalahan.');
        setTimeout(resetFaceLogin, 1000);
    }
}


// =========================================================
// DASHBOARD & JADWAL
// =========================================================

const STATUS_ATTENDED = ['SUDAH ABSEN', 'ATTENDED'];
const STATUS_OPEN = ['ABSEN', 'PRESENT'];
const STATUS_LATE = ['TERLAMBAT', 'LATE'];

let dashboardData = null;

function scheduleActionHtml(schedule) {
    const status = schedule.status;

    if (STATUS_ATTENDED.includes(status)) {
        const isLate = schedule.attendance_status === 'TERLAMBAT';
        const time = schedule.attendance_time
            ? '<small>' + escapeHtml(schedule.attendance_time) + '</small>'
            : '';
        return '<div class="attendance-success' + (isLate ? ' attendance-late' : '') + '">\u2713 SUDAH ABSEN ' + time + '</div>';
    }

    if (STATUS_OPEN.includes(status)) {
        return '<button class="attendance-button" onclick="openAttendance(' + Number(schedule.id) + ')">ABSEN</button>';
    }

    if (STATUS_LATE.includes(status)) {
        return '<button class="attendance-button attendance-late" onclick="openAttendance(' + Number(schedule.id) + ')">ABSEN TERLAMBAT</button>';
    }

    return '<div class="attendance-disabled">' + escapeHtml(status) + '</div>';
}

function scheduleCardHtml(schedule) {
    return `
        <div class="course-card">
            <div class="course-header">
                <h3>${escapeHtml(schedule.course)}</h3>
                <span>Kode: ${escapeHtml(schedule.code)}</span>
            </div>
            <div class="course-body">
                <p><strong>Dosen:</strong> ${escapeHtml(schedule.lecturer)}</p>
                <p><strong>Hari:</strong> ${escapeHtml(schedule.day_name)}</p>
                <p><strong>Waktu:</strong> ${escapeHtml(schedule.start)} - ${escapeHtml(schedule.end)}</p>
                <p><strong>Ruangan:</strong> ${escapeHtml(schedule.room)}</p>
                <p><strong>SKS:</strong> ${escapeHtml(schedule.sks)}</p>
                ${scheduleActionHtml(schedule)}
            </div>
        </div>`;
}

// Satu kali set innerHTML (bukan += di dalam loop) supaya render cepat.
function renderSchedules(containerId, schedules) {
    const container = $(containerId);
    if (!container) return;

    container.innerHTML = schedules.length === 0
        ? '<p style="color:#94a3b8; padding:20px 0;">Belum ada jadwal.</p>'
        : schedules.map(scheduleCardHtml).join('');
}

function getInitials(name) {
    const words = String(name || '').trim().split(/\s+/);
    const initials = words.length >= 2
        ? words[0][0] + words[words.length - 1][0]
        : words[0].substring(0, 2);
    return initials.toUpperCase();
}

async function loadDashboard() {
    if (!$('page-dashboard')) return;

    try {
        const response = await fetch('/api/dashboard');
        const data = await response.json();

        if (!data.success) {
            if (window.location.pathname !== '/' && window.location.pathname !== '') {
                window.location.href = '/';
            }
            return;
        }

        dashboardData = data;

        const schedules = data.schedules || [];
        const name = data.student_name;

        if ($('profileName')) $('profileName').textContent = name;
        if ($('welcomeName')) $('welcomeName').textContent = name;
        if ($('profileAvatar')) $('profileAvatar').textContent = getInitials(name);

        const attendedCount = schedules.filter((s) => STATUS_ATTENDED.includes(s.status)).length;
        const todayDay = (new Date().getDay() + 6) % 7;

        if ($('totalCourses')) $('totalCourses').textContent = schedules.length;
        if ($('totalAttendance')) $('totalAttendance').textContent = attendedCount;
        if ($('attendancePercentage')) {
            $('attendancePercentage').textContent =
                (schedules.length ? Math.round((attendedCount / schedules.length) * 100) : 0) + '%';
        }
        if ($('todaySchedules')) {
            $('todaySchedules').textContent = schedules.filter((s) => s.day === todayDay).length;
        }

        renderSchedules('scheduleContainer', schedules);
        renderSchedules('schedulePageContainer', schedules);

    } catch (error) {
        console.error('ERROR LOAD DASHBOARD:', error);
        const container = $('scheduleContainer');
        if (container) container.innerHTML = '<p style="color:#ef4444;">Gagal memuat jadwal.</p>';
    }
}

// Memakai data yang sudah dimuat; tidak fetch ulang kalau sudah ada.
function loadSchedulePage() {
    if (dashboardData) {
        renderSchedules('schedulePageContainer', dashboardData.schedules || []);
    } else {
        loadDashboard();
    }
}

function showPage(page, clickedItem = null) {
    const pages = ['dashboard', 'mahasiswa', 'profil', 'ujian', 'jadwal-page', 'pengaturan'];

    pages.forEach((item) => {
        const element = $('page-' + item);
        if (element) element.style.display = 'none';
    });

    const selectedPage = $('page-' + page);
    if (selectedPage) selectedPage.style.display = 'block';

    document.querySelectorAll('.menu-item').forEach((item) => item.classList.remove('active'));
    if (clickedItem) clickedItem.classList.add('active');

    window.scrollTo({ top: 0, behavior: 'smooth' });

    if (page === 'jadwal-page') loadSchedulePage();
}


// =========================================================
// ABSENSI (MODAL DASHBOARD)
// =========================================================

let attendanceStream = null;
let selectedScheduleId = null;
let isAttendanceProcessing = false;

async function openAttendance(scheduleId) {
    const modal = $('attendanceModal');
    const video = $('attendanceCamera');

    if (!modal || !video) return;

    selectedScheduleId = scheduleId;
    modal.classList.add('active');

    resetAttendance();
    setStatus($('attendanceStatus'), 'Meminta akses kamera...');

    try {
        attendanceStream = await openCamera(video);
        setStatus($('attendanceStatus'), 'Kamera aktif. Posisikan wajah di dalam kotak.');

    } catch (error) {
        console.error('ERROR KAMERA ABSENSI:', error);
        setStatus($('attendanceStatus'), 'Kamera tidak dapat digunakan.');
    }
}

function stopAttendanceCamera() {
    stopStream(attendanceStream, $('attendanceCamera'));
    attendanceStream = null;
}

function closeAttendance() {
    const modal = $('attendanceModal');
    if (modal) modal.classList.remove('active');
    stopAttendanceCamera();
}

function resetAttendance() {
    isAttendanceProcessing = false;

    const canvas = $('attendanceCanvas');
    if (canvas) canvas.style.display = 'none';

    setStatus($('attendanceStatus'), 'Kamera aktif. Posisikan wajah di dalam kotak.');
    setButton($('verifyAttendanceButton'), 'VERIFIKASI ABSENSI', false);
}

async function captureAttendance() {
    if (isAttendanceProcessing) return;

    const video = $('attendanceCamera');
    const canvas = $('attendanceCanvas');
    const status = $('attendanceStatus');
    const button = $('verifyAttendanceButton');

    if (!video || !canvas) return;

    if (!video.videoWidth || !video.videoHeight) {
        alert('Kamera belum siap. Tunggu sebentar.');
        return;
    }

    isAttendanceProcessing = true;
    setStatus(status, 'Memverifikasi absensi...');
    setButton(button, 'MEMVERIFIKASI...', true);

    try {
        const blob = await captureFrame(video, canvas);
        if (!blob) throw new Error('Gagal membuat gambar');

        const extra = selectedScheduleId ? { schedule_id: selectedScheduleId } : {};

        const startTime = performance.now();
        const data = await postImage('/api/attendance', blob, 'attendance_capture.jpg', extra);
        console.log('Latency absensi: ' + (performance.now() - startTime).toFixed(2) + ' ms');

        if (data.success) {
            closeAttendance();
            resetAttendance();

            showSuccessPopup({
                title: 'Absensi Berhasil!',
                message: data.message || 'Kehadiran Anda telah tercatat.',
                score: formatScore(data.facenet_score)
            });

            loadDashboard();
            return;
        }

        setStatus(status, data.message || 'Absensi gagal.');
        setButton(button, 'GAGAL', true);
        setTimeout(resetAttendance, 1200);

    } catch (error) {
        console.error('ERROR ABSENSI:', error);
        setStatus(status, 'Terjadi kesalahan saat memproses absensi.');
        setTimeout(resetAttendance, 1200);
    }
}


// =========================================================
// HALAMAN /attendance (attendance.html)
// =========================================================

async function startAttendanceCamera() {
    const status = $('cameraStatus');

    try {
        attendanceStream = await openCamera($('attendanceCamera'));
        setStatus(status, 'Kamera aktif. Posisikan wajah di dalam kotak.');
        $('verifyButton').disabled = false;

    } catch (error) {
        console.error(error);
        setStatus(status, 'Gagal mengakses kamera. Pastikan izin kamera diberikan.');
    }
}


// =========================================================
// INISIALISASI
// =========================================================

document.addEventListener('DOMContentLoaded', () => {
    const faceButton = $('verifyFaceButton');
    if (faceButton) faceButton.addEventListener('click', captureFaceLogin);

    const startButton = $('startAttendanceCamera');
    if (startButton) startButton.addEventListener('click', startAttendanceCamera);

    document.querySelectorAll('.page-section').forEach((page) => {
        page.style.display = 'none';
    });

    const dashboardPage = $('page-dashboard');
    if (dashboardPage) {
        dashboardPage.style.display = 'block';
        loadDashboard();
    }
});
