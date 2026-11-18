import cv2
import numpy as np
import json
import bcrypt
import time
import os


from pathlib import Path
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.face.detector import detect_face
from app.face.recognizer import recognize_face
from app.schedule import process_face_attendance, get_dashboard_data
from app.db import get_db_connection

from pathlib import Path
from fastapi import Form
from fastapi.responses import JSONResponse


app = FastAPI(
    title="Sistem Absensi Universitas ABCD"
)


# ============================================================
# SESSION
# ============================================================
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "123456789")
)

# ============================================================
# PATH CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent


# ============================================================
# TEMPLATE
# ============================================================

templates = Jinja2Templates(
    directory=str(BASE_DIR / "Templates")
)


# ============================================================
# STATIC
# ============================================================

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static"
)


# ============================================================
# LOGIN
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def login(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )

def get_user_by_username(username):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
        SELECT nim, email, name, face_name, password
        FROM users
        WHERE nim = %s OR LOWER(email) = LOWER(%s)
        LIMIT 1
            """,
            (username, username)
        )

        return cursor.fetchone()

    finally:
        cursor.close()
        connection.close()


def get_user_by_face_name(face_name):
    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT nim, email, name, face_name
            FROM users
            WHERE face_name = %s
            LIMIT 1
            """,
            (face_name,)
        )

        return cursor.fetchone()

    finally:
        cursor.close()
        connection.close()


@app.post("/api/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    try:
        user = get_user_by_username(username)

        if user is None:
            return {
                "success": False,
                "message": "NIM/Email atau password salah."
            }

        password_hash = user.get("password")

        if not password_hash:
            return {
                "success": False,
                "message": "NIM/Email atau password salah."
            }

        password_valid = bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8")
        )

        if not password_valid:
            return {
                "success": False,
                "message": "NIM/Email atau password salah."
            }

        # ==========================================
        # SIMPAN DATA AKUN KE SESSION
        # ==========================================

        request.session["student_name"] = user["name"]
        request.session["student_nim"] = user["nim"]
        request.session["face_name"] = user["face_name"]

        print()
        print("=" * 60)
        print("LOGIN BERHASIL")
        print("=" * 60)
        print("Nama      :", user["name"])
        print("NIM       :", user["nim"])
        print("Face Name :", user["face_name"])
        print("=" * 60)

        return {
            "success": True,
            "message": "Login berhasil.",
            "name": user["name"],
            "nim": user["nim"]
        }

    except Exception as e:

        print("LOGIN ERROR:", repr(e))

        return {
            "success": False,
            "message": f"Terjadi error: {str(e)}"
        }
    
# ============================================================
# DASHBOARD
# ============================================================
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):

    student_name = request.session.get("student_name")
    student_nim = request.session.get("student_nim")

    if not student_nim:
        return RedirectResponse(
            "/",
            status_code=303
        )

    return templates.TemplateResponse(
        request=request,
        name="Dashboard.html",
        context={
            "student_name": student_name
        }
    )



# ============================================================
# ATTENDANCE PAGE
# ============================================================

@app.get("/attendance", response_class=HTMLResponse)
async def attendance(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="attendance.html"
    )


# ============================================================
# FACE LOGIN
# ============================================================

@app.post("/api/face-login")
async def face_login(
    request: Request,
    file: UploadFile = File(...)
):

    image_bytes = await file.read()

    # ========================================================
    # 1. DETEKSI WAJAH
    # ========================================================

    # UKUR WAKTU MTCNN
    start_detect = time.perf_counter()

    detection = detect_face(image_bytes)

    detect_time = time.perf_counter() - start_detect

    print(f"WAKTU DETEKSI MTCNN: {detect_time:.3f} detik")

    if not detection.get("success", False):
        return {
            "success": False,
            "message": detection.get(
                "message",
                "Wajah tidak terdeteksi."
            )
        }

    # ========================================================
    # 2. BBOX
    # ========================================================

    bbox = detection.get("bbox")

    if bbox is None:
        return {
            "success": False,
            "message": "Bounding box wajah tidak ditemukan."
        }

    x1, y1, x2, y2 = map(int, bbox)

    # ========================================================
    # 3. DECODE IMAGE
    # ========================================================

    image_array = np.frombuffer(
        image_bytes,
        np.uint8
    )

    image = cv2.imdecode(
        image_array,
        cv2.IMREAD_COLOR
    )

    if image is None:
        return {
            "success": False,
            "message": "Gambar tidak valid."
        }

    # ========================================================
    # 4. CROP WAJAH
    # ========================================================

    h, w = image.shape[:2]

    x1 = max(0, min(x1, w - 1))
    y1 = max(0, min(y1, h - 1))
    x2 = max(0, min(x2, w))
    y2 = max(0, min(y2, h))

    if x2 <= x1 or y2 <= y1:
        return {
            "success": False,
            "message": "Bounding box wajah tidak valid."
        }

    face = image[
        y1:y2,
        x1:x2
    ]

    if face.size == 0:
        return {
            "success": False,
            "message": "Crop wajah gagal."
        }

    # ========================================================
    # 5. FACE RECOGNITION
    # ========================================================

    try:

# UKUR WAKTU FACENET
        start_recognition = time.perf_counter()

        result = recognize_face(face)

        recognition_time = time.perf_counter() - start_recognition

        print(f"WAKTU RECOGNITION: {recognition_time:.3f} detik")

        print()
        print("=" * 60)
        print("HASIL FACE RECOGNITION")
        print("=" * 60)
        print(result)
        print("=" * 60)

    except Exception as e:

        print(
            "ERROR RECOGNITION:",
            repr(e)
        )

        return {
            "success": False,
            "message": "Terjadi error saat mengenali wajah.",
            "error": str(e)
        }

    # ========================================================
    # 6. UNKNOWN
    # ========================================================

    recognized_name = result.get("name")

    if recognized_name == "UNKNOWN":
        return {
            "success": False,
            "message": "Wajah tidak dikenali.",
            "recognition": result
        }

    # ========================================================
    # 7. CARI AKUN BERDASARKAN FACE NAME
    # ========================================================

    try:
        user = get_user_by_face_name(recognized_name)

    except Exception as e:

        print(
            "ACCOUNT ERROR:",
            repr(e)
        )

        return {
            "success": False,
            "message": "Gagal membaca data akun.",
            "error": str(e)
        }

    # ========================================================
    # 8. FACE NAME TIDAK TERDAFTAR
    # ========================================================

    if user is None:

        return {
            "success": False,
            "message": (
                f"Wajah dikenali sebagai {recognized_name}, "
                "tetapi akun tidak ditemukan."
            ),
            "recognition": result
        }

    # ========================================================
    # 9. AMBIL DATA AKUN
    # ========================================================

    student_name = user["name"]
    student_nim = user["nim"]
    face_name = user["face_name"]

    # ========================================================
    # 10. SIMPAN SESSION
    # ========================================================

    request.session["student_name"] = student_name
    request.session["student_nim"] = student_nim
    request.session["face_name"] = face_name

    # ========================================================
    # 11. LOG LOGIN
    # ========================================================

    print()
    print("=" * 60)
    print("LOGIN DENGAN WAJAH BERHASIL")
    print("=" * 60)

    print("Nama       :", student_name)
    print("NIM        :", student_nim)
    print("Face Name  :", face_name)
    print("Recognized :", recognized_name)

    print("=" * 60)


    # ============================================================
    # 13. RETURN
    # ============================================================

    return {
        "success": True,

        "message":
            f"Login wajah berhasil. Selamat datang, {student_name}.",

        "name":
            student_name,

        "nim":
            student_nim,

        "face_name":
            face_name,

        "recognition":
            result,

        "facenet_score":
            result.get("facenet_score")
    }

# ============================================================
# DASHBOARD API
# ============================================================


@app.get("/api/dashboard")
async def api_dashboard(request: Request):

    student_name = request.session.get("student_name")
    student_nim = request.session.get("student_nim")

    if not student_nim:
        return {
            "success": False,
            "message": "NIM tidak ditemukan dalam session."
        }

    start = time.perf_counter()

    data = get_dashboard_data(student_nim)

    elapsed = time.perf_counter() - start

    print(f"LOAD DASHBOARD: {elapsed:.3f} detik")

    return {
        "success": True,
        "student_name": student_name,
        "student_nim": student_nim,
        "schedules": data
    }

# ============================================================
# ABSEN DARI DASHBOARD
# ============================================================

@app.post("/api/attendance")
async def attendance_api(
    request: Request,
    file: UploadFile = File(...),
    schedule_id: str = Form(None)  # <-- Tambahkan ini untuk menerima schedule_id dari frontend
):

    # ========================================================
    # 1. CEK SESSION
    # ========================================================

    student_name = request.session.get("student_name")
    student_nim = request.session.get("student_nim")
    face_name = request.session.get("face_name")

    if not student_name or not student_nim:
        return {
            "success": False,
            "message": "Session mahasiswa tidak lengkap. Silakan login kembali."
        }
    
    if not face_name:
        return {
            "success": False,
            "message": "Data face account tidak ditemukan."
        }

    # ========================================================
    # 2. BACA GAMBAR
    # ========================================================

    image_bytes = await file.read()

    if not image_bytes:
        return {
            "success": False,
            "message": "File gambar kosong."
        }

    # ========================================================
    # 3. DETEKSI WAJAH
    # ========================================================

    detection = detect_face(image_bytes)

    if not detection.get("success", False):
        return {
            "success": False,
            "message": detection.get(
                "message",
                "Wajah tidak terdeteksi."
            )
        }

    # ========================================================
    # 4. AMBIL BOUNDING BOX
    # ========================================================

    bbox = detection.get("bbox")

    if bbox is None:
        return {
            "success": False,
            "message": "Bounding box wajah tidak ditemukan."
        }

    x1, y1, x2, y2 = map(int, bbox)

    # ========================================================
    # 5. DECODE IMAGE
    # ========================================================

    image_array = np.frombuffer(
        image_bytes,
        np.uint8
    )

    image = cv2.imdecode(
        image_array,
        cv2.IMREAD_COLOR
    )

    if image is None:
        return {
            "success": False,
            "message": "Gambar tidak valid."
        }

    # ========================================================
    # 6. VALIDASI BBOX
    # ========================================================

    h, w = image.shape[:2]

    x1 = max(0, min(x1, w))
    y1 = max(0, min(y1, h))
    x2 = max(0, min(x2, w))
    y2 = max(0, min(y2, h))

    if x2 <= x1 or y2 <= y1:
        return {
            "success": False,
            "message": "Bounding box wajah tidak valid."
        }

    # ========================================================
    # 7. CROP WAJAH
    # ========================================================

    face = image[
        y1:y2,
        x1:x2
    ]

    if face.size == 0:
        return {
            "success": False,
            "message": "Crop wajah gagal."
        }

    # ========================================================
    # 8. FACE RECOGNITION
    # ========================================================

    try:

        result = recognize_face(face)

        print()
        print("=" * 60)
        print("VERIFIKASI ABSENSI")
        print("=" * 60)

        print("Akun       :", student_name)
        print("NIM        :", student_nim)
        print("Face akun  :", face_name)

        print()
        print("FaceNet    :", result.get("facenet_name"))
        print("Score      :", result.get("facenet_score"))

        print(
            "FINAL      :",
            result.get("name")
        )

        print("=" * 60)

    except Exception as e:

        print(
            "ERROR RECOGNITION:",
            repr(e)
        )

        return {
            "success": False,
            "message": "Terjadi error saat mengenali wajah.",
            "error": str(e)
        }

    # ========================================================
    # 9. WAJAH UNKNOWN
    # ========================================================

    recognized_name = result.get("name")

    if recognized_name == "UNKNOWN":
        return {
            "success": False,
            "message": "Wajah tidak dikenali.",
            "recognition": result
        }

    # ========================================================
    # 10. COCOKKAN WAJAH DENGAN AKUN
    # ========================================================

    if recognized_name != face_name:

        print()
        print("❌ WAJAH TIDAK SESUAI")
        print("Akun       :", student_name)
        print("Face akun  :", face_name)
        print("Terdeteksi :", recognized_name)

        return {
            "success": False,
            "message": (
                "Wajah tidak sesuai dengan "
                "akun yang sedang login."
            ),
            "account_name": student_name,
            "face_account": face_name,
            "recognized_name": recognized_name,
            "recognition": result
        }

    # ========================================================
    # 11. WAJAH SESUAI
    # ========================================================

    print()
    print("✅ WAJAH SESUAI")
    print("Mahasiswa :", student_name)

    # ========================================================
    # 12. PROSES ABSENSI (Menggunakan schedule_id)
    # ========================================================

    attendance_result = process_face_attendance(
        student_nim,
        schedule_id=schedule_id
    )

    # ========================================================
    # 13. LOG
    # ========================================================

    print()
    print("=" * 60)
    print("HASIL ABSENSI")
    print("=" * 60)

    print("Mahasiswa :", student_name)
    print("NIM       :", student_nim)
    print("Wajah     :", recognized_name)
    print("Attendance:", attendance_result)

    print("=" * 60)

    # ========================================================
    # 14. RETURN
    # ========================================================

    return {
        "success": attendance_result.get("success", True),
        "message": attendance_result.get(
            "message",
            "Proses absensi selesai."
        ),
        "name": student_name,
        "nim": student_nim,

        # HASIL FACENET
        "recognition": result,
        "facenet_score": result.get("facenet_score"),

        "attendance": attendance_result
    }