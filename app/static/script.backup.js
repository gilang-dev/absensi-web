function togglePassword() {

    const password =
        document.getElementById("password");

    if (password.type === "password") {

        password.type = "text";

    } else {

        password.type = "password";

    }
}


// =========================================
// POPUP ABSENSI BERHASIL (CEKLIS)
// =========================================

function showAttendanceSuccess(message, title) {

    if (!document.getElementById("attendanceSuccessStyle")) {

        const style = document.createElement("style");

        style.id = "attendanceSuccessStyle";

        style.textContent = `
.success-popup-overlay{position:fixed;inset:0;background:rgba(15,23,42,.55);display:flex;align-items:center;justify-content:center;z-index:99999;opacity:0;transition:opacity .25s ease}
.success-popup-overlay.show{opacity:1}
.success-popup{background:#fff;border-radius:20px;padding:36px 32px 28px;width:90%;max-width:340px;text-align:center;box-shadow:0 20px 60px rgba(0,0,0,.25);transform:scale(.85);transition:transform .3s cubic-bezier(.34,1.56,.64,1)}
.success-popup-overlay.show .success-popup{transform:scale(1)}
.success-circle{width:84px;height:84px;margin:0 auto 18px;border-radius:50%;background:#22c55e;display:flex;align-items:center;justify-content:center;box-shadow:0 0 0 10px rgba(34,197,94,.15)}
.success-circle svg{width:48px;height:48px}
.success-circle path{stroke:#fff;stroke-width:6;fill:none;stroke-linecap:round;stroke-linejoin:round;stroke-dasharray:50;stroke-dashoffset:50;animation:successDraw .45s .25s ease forwards}
@keyframes successDraw{to{stroke-dashoffset:0}}
.success-popup h3{margin:0 0 8px;font-size:22px;color:#0f172a}
.success-popup p{white-space:pre-line;margin:0 0 22px;font-size:15px;color:#475569;line-height:1.5}
.success-popup button{background:#22c55e;color:#fff;border:none;border-radius:10px;padding:10px 32px;font-size:15px;font-weight:600;cursor:pointer}
.success-popup button:hover{background:#16a34a}
`;

        document.head.appendChild(style);
    }

    const old = document.getElementById("attendanceSuccessPopup");

    if (old) {
        old.remove();
    }

    const overlay = document.createElement("div");

    overlay.id = "attendanceSuccessPopup";

    overlay.className = "success-popup-overlay";

    overlay.innerHTML = `
        <div class="success-popup">
            <div class="success-circle">
                <svg viewBox="0 0 52 52"><path d="M14 27 L23 36 L39 18"/></svg>
            </div>
            <h3>${title || "Absensi Berhasil!"}</h3>
            <p></p>
            <button type="button">OK</button>
        </div>
    `;

    overlay.querySelector("p").textContent =
        message || "Kehadiran Anda telah tercatat.";

    document.body.appendChild(overlay);

    requestAnimationFrame(function () {
        overlay.classList.add("show");
    });

    function closePopup() {

        overlay.classList.remove("show");

        setTimeout(function () {
            overlay.remove();
        }, 250);
    }

    overlay.querySelector("button").addEventListener("click", closePopup);

    overlay.addEventListener("click", function (event) {
        if (event.target === overlay) {
            closePopup();
        }
    });

    setTimeout(closePopup, 3000);
}


function logout() {

    window.location.href = "/";

}

async function startAttendanceCamera() {

    const video =
        document.getElementById(
            "attendanceCamera"
        );

    const status =
        document.getElementById(
            "cameraStatus"
        );

    const verifyButton =
        document.getElementById(
            "verifyButton"
        );

    try {

        attendanceStream =
            await navigator.mediaDevices.getUserMedia({
                video: {
                    width: {
                        ideal: 640
                    },

                    height: {
                        ideal: 480
                    },

                    facingMode: "user"
                },

                audio: false
            });

        video.srcObject =
            attendanceStream;

        status.textContent =
            "Kamera aktif. Posisikan wajah di dalam kotak.";

        verifyButton.disabled = false;

    } catch (error) {

        console.error(error);

        status.textContent =
            "Gagal mengakses kamera. Pastikan izin kamera diberikan.";

    }
}


const startAttendanceButton =
    document.getElementById(
        "startAttendanceCamera"
    );

if (startAttendanceButton) {

    startAttendanceButton.addEventListener(
        "click",
        startAttendanceCamera
    );

}

// =========================================
// FACE LOGIN CAMERA
// =========================================

let faceLoginStream = null;


// BUKA MODAL
async function openFaceLogin() {

    const modal = document.getElementById("faceLoginModal");
    const video = document.getElementById("faceLoginCamera");
    const status = document.getElementById("faceLoginStatus");

    modal.classList.add("active");

    status.textContent = "Meminta akses kamera...";

    try {

        faceLoginStream = await navigator.mediaDevices.getUserMedia({
            video: {
                width: {
                    ideal: 640
                },
                height: {
                    ideal: 480
                },
                facingMode: "user"
            },
            audio: false
        });

        video.srcObject = faceLoginStream;

        status.textContent =
            "Kamera aktif. Posisikan wajah di dalam kotak.";

    } catch (error) {

        console.error("Camera error:", error);

        status.textContent =
            "Kamera tidak dapat digunakan.";

        alert(
            "Kamera tidak dapat diakses.\n\n" +
            "Pastikan browser sudah diberikan izin kamera."
        );
    }
}


// TUTUP MODAL
function closeFaceLogin() {

    const modal = document.getElementById("faceLoginModal");

    modal.classList.remove("active");

    stopFaceLoginCamera();
}


// MATIKAN KAMERA
function stopFaceLoginCamera() {

    if (faceLoginStream) {

        faceLoginStream
            .getTracks()
            .forEach(track => track.stop());

        faceLoginStream = null;
    }

    const video =
        document.getElementById("faceLoginCamera");

    if (video) {
        video.srcObject = null;
    }
}

// CEGAH REQUEST LOGIN GANDA
let isFaceLoginProcessing = false;

async function captureFaceLogin() {

    // Jika proses masih berjalan, hentikan pemanggilan kedua
    if (isFaceLoginProcessing) {
        console.log("FACE LOGIN MASIH DIPROSES");
        return;
    }

    isFaceLoginProcessing = true;

    const video =
        document.getElementById("faceLoginCamera");

    const canvas =
        document.getElementById("faceCanvas");

    const status =
        document.getElementById("faceLoginStatus");

    const button =
        document.getElementById("verifyFaceButton");

    console.log("=== CAPTURE FACE LOGIN ===");


    // =========================================
    // CEK VIDEO
    // =========================================

    if (!video) {
        console.error("Video tidak ditemukan");
        return;
    }

    if (!canvas) {
        console.error("Canvas tidak ditemukan");
        return;
    }

    if (
        video.videoWidth === 0 ||
        video.videoHeight === 0
    ) {

        alert(
            "Kamera belum siap. Tunggu sebentar."
        );

        return;
    }


    // =========================================
    // 1. AMBIL FRAME DARI VIDEO
    // =========================================

    canvas.width =
        video.videoWidth;

    canvas.height =
        video.videoHeight;

    const ctx =
        canvas.getContext("2d");


    // Mirror seperti kamera depan
    ctx.save();

    ctx.translate(
        canvas.width,
        0
    );

    ctx.scale(
        -1,
        1
    );

    ctx.drawImage(
        video,
        0,
        0,
        canvas.width,
        canvas.height
    );

    ctx.restore();


    // =========================================
    // 2. TAMPILKAN FOTO DI ATAS VIDEO
    // =========================================

    canvas.style.display = "block";


    // ❗ JANGAN:
    // video.pause()
    //
    // ❗ JANGAN:
    // video.srcObject = null
    //
    // ❗ JANGAN:
    // stop stream
    //
    // Video tetap hidup di belakang canvas.


    // =========================================
    // 3. UBAH STATUS
    // =========================================

    if (status) {

        status.textContent =
            "Memverifikasi wajah...";
    }


    if (button) {

        button.disabled = true;

        button.textContent =
            "MEMVERIFIKASI...";
    }


    // =========================================
    // 4. BUAT FILE FOTO
    // =========================================

    canvas.toBlob(
        async function(blob) {

            if (!blob) {

                console.error(
                    "Gagal membuat blob"
                );

                resetFaceLogin();

                return;
            }


            // =================================
            // 5. KIRIM KE FASTAPI
            // =================================

            const formData =
                new FormData();

            formData.append(
                "file",
                blob,
                "face_capture.jpg"
            );


            try {

                const response =
                    await fetch(
                        "/api/face-login",
                        {
                            method: "POST",
                            body: formData
                        }
                    );


                const data =
                    await response.json();


                console.log("HASIL FACE LOGIN:", data);
                console.log("FACENET SCORE:", data.facenet_score);

            // =================================
            // 6. HASIL
            // =================================

            if (data.success) {

                console.log("LOGIN BERHASIL");
                console.log("Nama:", data.name);
                console.log("Attendance:", data.attendance);

                const faceNetScore = data.facenet_score;

                console.log("FaceNet Score:", faceNetScore);

                if (status) {
                    status.textContent =
                        "✓ Login berhasil sebagai " +
                        data.name +

                        " | FaceNet Score: " +
                        (
                            faceNetScore !== null &&
                            faceNetScore !== undefined
                                ? Number(faceNetScore).toFixed(4)
                                : "Tidak tersedia"
                        );
                }

                if (button) {
                    button.disabled = true;
                    button.textContent = "BERHASIL";

                    showAttendanceSuccess(
                        "Selamat datang, " + data.name +
                        "\nFaceNet Score: " +
                        (
                            faceNetScore !== null &&
                            faceNetScore !== undefined
                                ? Number(faceNetScore).toFixed(4)
                                : "Tidak tersedia"
                        ),
                        "Login Berhasil!"
                    );
                }
                // =====================================
                // LANGSUNG KE DASHBOARD
                // =====================================

                setTimeout(() => {
                console.log("REDIRECT → /dashboard");

                setTimeout(() => window.location.replace("/dashboard"), 1800);

                }, 1000);


            } else {

                // =====================================
                // VERIFIKASI GAGAL
                // =====================================

                console.log(
                    "VERIFIKASI GAGAL:",
                    data.message
                );

                if (status) {
                    status.textContent =
                        data.message ||
                        "Wajah tidak dikenali.";
                }

                if (button) {
                    button.textContent = "GAGAL";
                    button.disabled = true;
                }

                // =====================================
                // KEMBALIKAN KE KAMERA REALTIME
                // =====================================

                setTimeout(() => {

                    resetFaceLogin();

                }, 1000);
            }

                // =================================
                // 7. TUNGGU SEBENTAR
                // =================================

            } catch (error) {

                console.error(
                    "ERROR FACE LOGIN:",
                    error
                );


                if (status) {

                    status.textContent =
                        "Terjadi kesalahan.";
                }


                setTimeout(
                    function() {

                        resetFaceLogin();

                    },
                    1000
                );
            }

        },
        "image/jpeg",
        0.95
    );
}
function resetFaceLogin() {
    isFaceLoginProcessing = false;
    console.log(
        "Kembali ke kamera realtime..."
    );

    const canvas =
        document.getElementById("faceCanvas");

    const status =
        document.getElementById("faceLoginStatus");

    const button =
        document.getElementById("verifyFaceButton");


    // =========================================
    // HILANGKAN FOTO CAPTURE
    // =========================================

    if (canvas) {
        canvas.style.display = "none";
    }


    // =========================================
    // KAMERA REALTIME
    // =========================================

    if (status) {
        status.textContent =
            "Kamera aktif. Posisikan wajah di dalam kotak.";
    }


    // =========================================
    // AKTIFKAN TOMBOL LAGI
    // =========================================

    if (button) {

        button.disabled = false;

        button.textContent =
            "VERIFIKASI WAJAH";
    }
}

// =========================================
// TOMBOL VERIFIKASI WAJAH
// =========================================

document.addEventListener("DOMContentLoaded", function () {

    const button =
        document.getElementById("verifyFaceButton");

    if (button) {

        button.addEventListener(
            "click",
            captureFaceLogin
        );

    }

});
// =========================================================
// LOAD DASHBOARD
// =========================================================

async function loadDashboard() {
    const dashboardPage = document.getElementById("page-dashboard");
    if (!dashboardPage) return;

    try {
        const response = await fetch("/api/dashboard");
        const data = await response.json();

        if (!data.success) {
            if (window.location.pathname !== "/" && window.location.pathname !== "") {
                window.location.href = "/";
            }
            return;
        }

        // Student Profile Header
        const studentName = data.student_name;
        const profileName = document.getElementById("profileName");
        const welcomeName = document.getElementById("welcomeName");
        const profileAvatar = document.getElementById("profileAvatar");

        if (profileName) profileName.textContent = studentName;
        if (welcomeName) welcomeName.textContent = studentName;

        if (profileAvatar) {
            const words = studentName.trim().split(/\s+/);
            let initials = words.length >= 2 ? words[0][0] + words[words.length - 1][0] : words[0].substring(0, 2);
            profileAvatar.textContent = initials.toUpperCase();
        }

        const schedules = data.schedules || [];

        // Statistics
        const totalCourses = document.getElementById("totalCourses");
        const totalAttendance = document.getElementById("totalAttendance");
        const attendancePercentage = document.getElementById("attendancePercentage");
        const todaySchedules = document.getElementById("todaySchedules");

        // Disesuaikan dengan status "ATTENDED" dari backend
        const attendedCount = schedules.filter(s => s.status === "ATTENDED").length;

        if (totalCourses) totalCourses.textContent = schedules.length;
        if (totalAttendance) totalAttendance.textContent = attendedCount;

        if (attendancePercentage) {
            const percentage = schedules.length > 0 ? Math.round((attendedCount / schedules.length) * 100) : 0;
            attendancePercentage.textContent = percentage + "%";
        }

        if (todaySchedules) {
            const jsDay = new Date().getDay();
            const todayDay = (jsDay + 6) % 7;
            const todayCount = schedules.filter(s => s.day === todayDay).length;
            todaySchedules.textContent = todayCount;
        }

        // Render Schedule Container
        const container = document.getElementById("scheduleContainer");
        if (!container) return;

        container.innerHTML = "";

        if (schedules.length === 0) {
            container.innerHTML = `<p style="color:#94a3b8; padding:20px 0;">Belum ada jadwal.</p>`;
            return;
        }

      schedules.forEach(schedule => {
         let attendanceHTML = "";

        // 1. SUDAH ABSEN (Baik HADIR maupun TERLAMBAT di DB)
        if (schedule.status === "SUDAH ABSEN") {
            const isLate = schedule.attendance_status === "TERLAMBAT";
            const badgeText = isLate ? "✓ SUDAH ABSEN" : "✓ SUDAH ABSEN";
            const badgeClass = isLate ? "attendance-success attendance-late" : "attendance-success";

            attendanceHTML = `
                <div class="${badgeClass}">
                    ${badgeText}
                    ${schedule.attendance_time ? `<small>${schedule.attendance_time}</small>` : ""}
                </div>
            `;
        } 
        // 2. BELUM ABSEN & WAKTU KELAS PAS (TEPAT WAKTU)
        else if (schedule.status === "ABSEN") {
            attendanceHTML = `
                <button class="attendance-button" onclick="openAttendance(${schedule.id})">
                    ABSEN
                </button>
            `;
        } 
        // 3. BELUM ABSEN & WAKTU KELAS SUDAH MASUK TOLERANSI TERLAMBAT
        else if (schedule.status === "TERLAMBAT") {
            attendanceHTML = `
                <button class="attendance-button attendance-late" onclick="openAttendance(${schedule.id})">
                    ABSEN TERLAMBAT
                </button>
            `;
        } 
        // 4. BELUM DIBUKA / DITUTUP
        else {
            attendanceHTML = `
                <div class="attendance-disabled">
                    ${schedule.status}
                </div>
            `;
        }

    container.innerHTML += `
        <div class="course-card">
            <div class="course-header">
                <h3>${schedule.course}</h3>
                <span>Kode: ${schedule.code}</span>
            </div>
            <div class="course-body">
                <p><strong>Dosen:</strong> ${schedule.lecturer}</p>
                <p><strong>Hari:</strong> ${schedule.day_name}</p>
                <p><strong>Waktu:</strong> ${schedule.start} - ${schedule.end}</p>
                <p><strong>Ruangan:</strong> ${schedule.room}</p>
                <p><strong>SKS:</strong> ${schedule.sks}</p>
                ${attendanceHTML}
            </div>
        </div>
    `;
});

    } catch (error) {
        console.error("ERROR LOAD DASHBOARD:", error);
        const container = document.getElementById("scheduleContainer");
        if (container) {
            container.innerHTML = `<p style="color:#ef4444;">Gagal memuat jadwal.</p>`;
        }
    }
}

// ============================================================
// ABSENSI DASHBOARD
// ============================================================

let attendanceStream = null;

let selectedScheduleId = null;


// ============================================================
// BUKA KAMERA ABSENSI
// ============================================================

async function openAttendance(scheduleId) {

    const modal =
        document.getElementById(
            "attendanceModal"
        );

    const video =
        document.getElementById(
            "attendanceCamera"
        );

    const status =
        document.getElementById(
            "attendanceStatus"
        );

    const button =
        document.getElementById(
            "verifyAttendanceButton"
        );


    selectedScheduleId = scheduleId;


    if (!modal || !video) {
        return;
    }


    modal.classList.add("active");


    if (status) {
        status.textContent =
            "Meminta akses kamera...";
    }


    if (button) {
        button.disabled = false;

        button.textContent =
            "VERIFIKASI ABSENSI";
    }


    try {

        attendanceStream =
            await navigator.mediaDevices.getUserMedia({

                video: {
                    width: {
                        ideal: 640
                    },

                    height: {
                        ideal: 480
                    },

                    facingMode: "user"
                },

                audio: false

            });


        video.srcObject =
            attendanceStream;


        if (status) {

            status.textContent =
                "Kamera aktif. Posisikan wajah di dalam kotak.";
        }


    } catch (error) {

        console.error(
            "ERROR KAMERA ABSENSI:",
            error
        );


        if (status) {

            status.textContent =
                "Kamera tidak dapat digunakan.";
        }
    }
}


// ============================================================
// TUTUP KAMERA ABSENSI
// ============================================================

function closeAttendance() {

    const modal =
        document.getElementById(
            "attendanceModal"
        );


    if (modal) {
        modal.classList.remove("active");
    }


    stopAttendanceCamera();
}


// ============================================================
// STOP CAMERA
// ============================================================

function stopAttendanceCamera() {

    if (attendanceStream) {

        attendanceStream
            .getTracks()
            .forEach(
                track => track.stop()
            );

        attendanceStream = null;
    }


    const video =
        document.getElementById(
            "attendanceCamera"
        );


    if (video) {

        video.srcObject = null;
    }
}


// ============================================================
// CAPTURE ABSENSI
// ============================================================

async function captureAttendance() {

    const video =
        document.getElementById(
            "attendanceCamera"
        );

    const canvas =
        document.getElementById(
            "attendanceCanvas"
        );

    const status =
        document.getElementById(
            "attendanceStatus"
        );

    const button =
        document.getElementById(
            "verifyAttendanceButton"
        );


    if (!video || !canvas) {
        return;
    }


    if (
        video.videoWidth === 0 ||
        video.videoHeight === 0
    ) {

        alert(
            "Kamera belum siap. Tunggu sebentar."
        );

        return;
    }


    // ========================================================
    // CAPTURE FRAME
    // ========================================================

    canvas.width =
        video.videoWidth;

    canvas.height =
        video.videoHeight;


    const ctx =
        canvas.getContext("2d");


    ctx.save();

    ctx.translate(
        canvas.width,
        0
    );

    ctx.scale(
        -1,
        1
    );

    ctx.drawImage(
        video,
        0,
        0,
        canvas.width,
        canvas.height
    );

    ctx.restore();


    canvas.style.display =
        "block";


    if (status) {

        status.textContent =
            "Memverifikasi absensi...";
    }


    if (button) {

        button.disabled = true;

        button.textContent =
            "MEMVERIFIKASI...";
    }


    // ========================================================
    // KIRIM KE BACKEND
    // ========================================================

    canvas.toBlob(
        async function(blob) {

            if (!blob) {

                resetAttendance();

                return;
            }


            const formData =
                new FormData();


            formData.append(
                "file",
                blob,
                "attendance_capture.jpg"
            );
            
            if (selectedScheduleId) {
                formData.append("schedule_id", selectedScheduleId); // <-- Sertakan ID jadwal
            }


            try {

                const startTime = performance.now();

                const response = await fetch(
                    "/api/attendance",
                    {
                        method: "POST",
                        body: formData
                    }
                );

                const endTime = performance.now();
                const latency = endTime - startTime;

                console.log(`Latency absensi: ${latency.toFixed(2)} ms`);


                const data =
                    await response.json();


                console.log(
                    "HASIL ABSENSI:",
                    data
                );


                // =================================================
                // BERHASIL
                // =================================================

                if (data.success) {

                    if (status) {

                        status.textContent =
                            "✓ " +
                            data.message;
                    }


                    if (button) {

                        button.textContent =
                            "ABSENSI BERHASIL";

                    showAttendanceSuccess(data.message);
                    }


                    setTimeout(
                        function() {

                            closeAttendance();

                            loadDashboard();

                        },
                        500
                    );


                }

                // =================================================
                // GAGAL
                // =================================================

                else {

                    if (status) {

                        status.textContent =
                            data.message ||
                            "Absensi gagal.";
                    }


                    if (button) {

                        button.textContent =
                            "GAGAL";
                    }


                    setTimeout(
                        function() {

                            resetAttendance();

                        },
                        1200
                    );
                }


            } catch (error) {

                console.error(
                    "ERROR ABSENSI:",
                    error
                );


                if (status) {

                    status.textContent =
                        "Terjadi kesalahan saat memproses absensi.";
                }


                setTimeout(
                    function() {

                        resetAttendance();

                    },
                    1200
                );
            }

        },
        "image/jpeg",
        0.95
    );
}


// ============================================================
// RESET ABSENSI
// ============================================================

function resetAttendance() {

    const canvas =
        document.getElementById(
            "attendanceCanvas"
        );

    const status =
        document.getElementById(
            "attendanceStatus"
        );

    const button =
        document.getElementById(
            "verifyAttendanceButton"
        );


    if (canvas) {

        canvas.style.display =
            "none";
    }


    if (status) {

        status.textContent =
            "Kamera aktif. Posisikan wajah di dalam kotak.";
    }


    if (button) {

        button.disabled = false;

        button.textContent =
            "VERIFIKASI ABSENSI";
    }
}

// =========================================================
// DASHBOARD PAGE NAVIGATION
// =========================================================

function showPage(page, clickedItem = null) {

    const pages = [
        "dashboard",
        "mahasiswa",
        "profil",
        "ujian",
        "jadwal-page",
        "pengaturan"
    ];

    pages.forEach(item => {

        const element =
            document.getElementById("page-" + item);

        if (element) {
            element.style.display = "none";
        }
    });

    const selectedPage =
        document.getElementById("page-" + page);

    if (selectedPage) {
        selectedPage.style.display = "block";
    }

    document
        .querySelectorAll(".menu-item")
        .forEach(item => {
            item.classList.remove("active");
        });

    if (clickedItem) {
        clickedItem.classList.add("active");
    }

    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });


    /* =========================================
       LOAD DATA HALAMAN JADWAL
    ========================================= */

    if (page === "jadwal-page") {
        loadSchedulePage();
    }
}

// =========================================================
// DEFAULT PAGE
// =========================================================

document.addEventListener("DOMContentLoaded", function () {

    // Sembunyikan semua halaman internal
    document.querySelectorAll(".page-section").forEach(function (page) {
        page.style.display = "none";
    });

    // Dashboard selalu tampil pertama jika berada di halaman dashboard
    const dashboardPage =
        document.getElementById("page-dashboard");

    if (dashboardPage) {
        dashboardPage.style.display = "block";

        // Load jadwal dashboard
        loadDashboard();
    }
});

async function loadSchedulePage() {
    try {
        const response = await fetch("/api/dashboard");
        const data = await response.json();

        if (!data.success) return;

        const container = document.getElementById("schedulePageContainer");
        if (!container) return;

        const schedules = data.schedules || [];
        container.innerHTML = "";

        if (schedules.length === 0) {
            container.innerHTML = `<p style="color:#94a3b8;">Belum ada jadwal.</p>`;
            return;
        }

        schedules.forEach(schedule => {
            let attendanceHTML = "";

            if (schedule.status === "ATTENDED") {
                attendanceHTML = `
                    <div class="attendance-success">
                        ✓ SUDAH ABSEN
                        ${schedule.attendance_time ? `<small>${schedule.attendance_time}</small>` : ""}
                    </div>
                `;
            } else if (schedule.status === "PRESENT") {
                attendanceHTML = `
                    <button class="attendance-button" onclick="openAttendance(${schedule.id})">
                        ABSEN
                    </button>
                `;
            } else if (schedule.status === "LATE") {
                attendanceHTML = `
                    <button class="attendance-button attendance-late" onclick="openAttendance(${schedule.id})">
                        ABSEN TERLAMBAT
                    </button>
                `;
            } else {
                attendanceHTML = `
                    <div class="attendance-disabled">
                        ${schedule.status}
                    </div>
                `;
            }

            container.innerHTML += `
                <div class="course-card">
                    <div class="course-header">
                        <h3>${schedule.course}</h3>
                        <span>Kode: ${schedule.code}</span>
                    </div>
                    <div class="course-body">
                        <p><strong>Dosen:</strong> ${schedule.lecturer}</p>
                        <p><strong>Hari:</strong> ${schedule.day_name}</p>
                        <p><strong>Waktu:</strong> ${schedule.start} - ${schedule.end}</p>
                        <p><strong>Ruangan:</strong> ${schedule.room}</p>
                        <p><strong>SKS:</strong> ${schedule.sks}</p>
                        ${attendanceHTML}
                    </div>
                </div>
            `;
        });

    } catch (error) {
        console.error("ERROR LOAD SCHEDULE PAGE:", error);
    }
}

async function login(event) {
    event.preventDefault();
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;

    if (!username || !password) {
        alert("NIM/Email dan password wajib diisi.");
        return;
    }

    try {
        const formData = new FormData();
        formData.append("username", username);
        formData.append("password", password);

        const response = await fetch("/api/login", {
            method: "POST",
            body: formData
        });

        const result = await response.json();

        console.log("LOGIN RESPONSE:", result);

        if (!result.success) {
            alert(result.message || "Login gagal.");
            return;
        }

        window.location.href = "/dashboard";

    } catch (error) {
        console.error("LOGIN ERROR:", error);
        alert("Terjadi kesalahan saat menghubungi server.");
    }
}