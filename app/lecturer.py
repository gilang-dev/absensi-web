from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo

import bcrypt
from fastapi import APIRouter, Request, Form
import csv
import io
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from app.db import get_db_connection
from app.schedule import format_time_field, get_schedule_status, DAY_NAMES

WIB = ZoneInfo("Asia/Jakarta")
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "Templates"))

router = APIRouter()


def today_wib() -> date:
    return datetime.now(WIB).date()


def current_lecturer(request: Request):
    return request.session.get("lecturer_code")


def unauthorized():
    return {"success": False, "message": "Sesi dosen tidak valid. Silakan login ulang."}


def verify_password(plain, hashed):
    """Cek password bcrypt; hash tidak valid dianggap salah, bukan error."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), str(hashed or "").encode("utf-8"))
    except ValueError:
        print("LECTURER PASSWORD ERROR: hash di database bukan bcrypt yang valid")
        return False


def try_lecturer_login(request, nip, password):
    """Login dosen lewat NIP + password (tanpa FaceNet).

    Mengembalikan dict respons jika NIP milik dosen, atau None jika bukan dosen
    (atau tabel lecturers belum ada), sehingga alur mahasiswa tetap jalan.
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT code, name, password FROM lecturers WHERE nip = %s LIMIT 1",
                    (nip.strip(),),
                )
                row = cursor.fetchone()
    except Exception as e:
        print("LECTURER LOOKUP ERROR:", repr(e))
        return None

    if not row:
        return None

    if not verify_password(password, row["password"]):
        return {"success": False, "message": "NIP atau password salah."}

    request.session.clear()
    request.session["lecturer_code"] = row["code"]
    request.session["lecturer_name"] = row["name"]

    return {
        "success": True,
        "role": "lecturer",
        "redirect": "/lecturer",
        "name": row["name"],
        "message": "Login dosen berhasil.",
    }


def get_owned_schedule(cursor, schedule_id, code):
    cursor.execute(
        "SELECT * FROM schedules WHERE id = %s AND lecturer = %s LIMIT 1",
        (schedule_id, code),
    )
    return cursor.fetchone()


# ============================================================
# HALAMAN
# ============================================================

@router.get("/lecturer/login", response_class=HTMLResponse)
async def lecturer_login_page(request: Request):
    return templates.TemplateResponse(request=request, name="lecturer_login.html")


@router.get("/lecturer", response_class=HTMLResponse)
async def lecturer_page(request: Request):
    if not current_lecturer(request):
        return RedirectResponse("/lecturer/login", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="lecturer.html",
        context={"lecturer_name": request.session.get("lecturer_name", "")},
    )


# ============================================================
# AUTH
# ============================================================

@router.post("/api/lecturer/login")
async def lecturer_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT code, name, password
                    FROM lecturers
                    WHERE nip = %s
                    LIMIT 1
                    """,
                    (username.strip(),),
                )
                row = cursor.fetchone()

        if not row or not verify_password(password, row["password"]):
            return {"success": False, "message": "Kode/Email atau password salah."}

        request.session["lecturer_code"] = row["code"]
        request.session["lecturer_name"] = row["name"]

        return {"success": True, "name": row["name"]}

    except Exception as e:
        print("LECTURER LOGIN ERROR:", repr(e))
        return {"success": False, "message": "Terjadi kesalahan pada server."}


@router.post("/api/lecturer/logout")
async def lecturer_logout(request: Request):
    request.session.pop("lecturer_code", None)
    request.session.pop("lecturer_name", None)
    return {"success": True}


# ============================================================
# KELAS YANG DIAMPU
# ============================================================

@router.get("/api/lecturer/classes")
async def lecturer_classes(request: Request):
    code = current_lecturer(request)
    if not code:
        return unauthorized()

    today = today_wib()

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT s.*,
                           c.reason AS cancel_reason,
                           c.class_date AS cancel_date,
                           (SELECT COUNT(*) FROM attendance_records a
                             WHERE a.schedule_id = s.id
                               AND a.attendance_time::date = %s) AS present_today,
                           (SELECT la.status FROM lecturer_attendance la
                             WHERE la.schedule_id = s.id
                               AND la.class_date = %s) AS lecturer_status
                    FROM schedules s
                    LEFT JOIN class_cancellations c
                           ON c.schedule_id = s.id AND c.class_date = %s
                    WHERE s.lecturer = %s
                    ORDER BY s.day ASC, s.start_time ASC
                    """,
                    (today, today, today, code),
                )
                rows = cursor.fetchall()

                cursor.execute(
                    """
                    SELECT schedule_id, class_date, reason
                    FROM class_cancellations
                    WHERE created_by = %s AND class_date >= %s
                    ORDER BY class_date ASC
                    """,
                    (code, today),
                )
                upcoming = cursor.fetchall()

        classes = []
        for r in rows:
            classes.append({
                "id": r["id"],
                "course": r["course"],
                "code": r["code"],
                "room": r["room"],
                "sks": r["sks"],
                "day": r["day"],
                "day_name": DAY_NAMES.get(int(r["day"]), "-"),
                "start": format_time_field(r["start_time"]),
                "end": format_time_field(r["end_time"]),
                "is_today": int(r["day"]) == today.weekday(),
                "cancelled_today": r["cancel_date"] is not None,
                "cancel_reason": r["cancel_reason"],
                "present_today": int(r["present_today"]),
                "lecturer_status": r["lecturer_status"],
            })

        return {
            "success": True,
            "lecturer_name": request.session.get("lecturer_name"),
            "today": today.isoformat(),
            "classes": classes,
            "upcoming_cancellations": [
                {
                    "schedule_id": u["schedule_id"],
                    "date": u["class_date"].isoformat(),
                    "reason": u["reason"],
                }
                for u in upcoming
            ],
        }

    except Exception as e:
        print("LECTURER CLASSES ERROR:", repr(e))
        return {"success": False, "message": "Gagal memuat kelas."}


# ============================================================
# REKAP KEHADIRAN
# ============================================================

@router.get("/api/lecturer/recap")
async def lecturer_recap(request: Request, schedule_id: int):
    code = current_lecturer(request)
    if not code:
        return unauthorized()

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                schedule = get_owned_schedule(cursor, schedule_id, code)
                if not schedule:
                    return {"success": False, "message": "Kelas tidak ditemukan."}

                # Pertemuan = tanggal dengan minimal satu absensi (bukan yang dibatalkan)
                cursor.execute(
                    """
                    SELECT COUNT(DISTINCT attendance_time::date) AS meetings
                    FROM attendance_records
                    WHERE schedule_id = %s
                    """,
                    (schedule_id,),
                )
                meetings = int(cursor.fetchone()["meetings"])

                cursor.execute(
                    """
                    SELECT COUNT(*) AS cancelled
                    FROM class_cancellations WHERE schedule_id = %s
                    """,
                    (schedule_id,),
                )
                cancelled = int(cursor.fetchone()["cancelled"])

                cursor.execute(
                    """
                    SELECT u.id, u.name, u.nim,
                           COUNT(*) FILTER (WHERE a.status = 'HADIR')     AS hadir,
                           COUNT(*) FILTER (WHERE a.status = 'TERLAMBAT') AS terlambat
                    FROM users u
                    LEFT JOIN attendance_records a
                           ON a.user_id = u.id AND a.schedule_id = %s
                    GROUP BY u.id, u.name, u.nim
                    ORDER BY u.name ASC
                    """,
                    (schedule_id,),
                )
                students = cursor.fetchall()

        result = []
        for s in students:
            hadir = int(s["hadir"])
            terlambat = int(s["terlambat"])
            attended = hadir + terlambat
            alpha = max(meetings - attended, 0)
            percent = round(attended / meetings * 100) if meetings else 0
            result.append({
                "name": s["name"],
                "nim": s["nim"],
                "hadir": hadir,
                "terlambat": terlambat,
                "alpha": alpha,
                "percent": percent,
            })

        return {
            "success": True,
            "course": schedule["course"],
            "meetings": meetings,
            "cancelled": cancelled,
            "students": result,
        }

    except Exception as e:
        print("LECTURER RECAP ERROR:", repr(e))
        return {"success": False, "message": "Gagal memuat rekap."}


# ============================================================
# BATALKAN / PULIHKAN KELAS
# ============================================================

@router.post("/api/lecturer/cancel")
async def lecturer_cancel(
    request: Request,
    schedule_id: int = Form(...),
    class_date: str = Form(...),
    reason: str = Form(""),
):
    code = current_lecturer(request)
    if not code:
        return unauthorized()

    try:
        target = date.fromisoformat(class_date)
    except ValueError:
        return {"success": False, "message": "Format tanggal tidak valid."}

    if target < today_wib():
        return {"success": False, "message": "Tidak bisa membatalkan kelas yang sudah lewat."}

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                schedule = get_owned_schedule(cursor, schedule_id, code)
                if not schedule:
                    return {"success": False, "message": "Kelas tidak ditemukan."}

                if target.weekday() != int(schedule["day"]):
                    return {
                        "success": False,
                        "message": f"Tanggal tersebut bukan hari {DAY_NAMES[int(schedule['day'])]}.",
                    }

                cursor.execute(
                    """
                    INSERT INTO class_cancellations (schedule_id, class_date, reason, created_by)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (schedule_id, class_date)
                    DO UPDATE SET reason = EXCLUDED.reason
                    """,
                    (schedule_id, target, reason.strip()[:500], code),
                )

        return {"success": True, "message": "Kelas berhasil dibatalkan."}

    except Exception as e:
        print("LECTURER CANCEL ERROR:", repr(e))
        return {"success": False, "message": "Gagal membatalkan kelas."}


@router.post("/api/lecturer/uncancel")
async def lecturer_uncancel(
    request: Request,
    schedule_id: int = Form(...),
    class_date: str = Form(...),
):
    code = current_lecturer(request)
    if not code:
        return unauthorized()

    try:
        target = date.fromisoformat(class_date)
    except ValueError:
        return {"success": False, "message": "Format tanggal tidak valid."}

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                schedule = get_owned_schedule(cursor, schedule_id, code)
                if not schedule:
                    return {"success": False, "message": "Kelas tidak ditemukan."}

                cursor.execute(
                    "DELETE FROM class_cancellations WHERE schedule_id = %s AND class_date = %s",
                    (schedule_id, target),
                )

        return {"success": True, "message": "Pembatalan dicabut."}

    except Exception as e:
        print("LECTURER UNCANCEL ERROR:", repr(e))
        return {"success": False, "message": "Gagal mencabut pembatalan."}


# ============================================================
# KEHADIRAN PER PERTEMUAN + EXPORT CSV
# ============================================================

def compute_recap(cursor, schedule_id):
    cursor.execute(
        '''
        SELECT COUNT(DISTINCT attendance_time::date) AS meetings
        FROM attendance_records
        WHERE schedule_id = %s
        ''',
        (schedule_id,),
    )
    meetings = int(cursor.fetchone()['meetings'])

    cursor.execute(
        'SELECT COUNT(*) AS cancelled FROM class_cancellations WHERE schedule_id = %s',
        (schedule_id,),
    )
    cancelled = int(cursor.fetchone()['cancelled'])

    cursor.execute(
        '''
        SELECT u.id, u.name, u.nim,
               COUNT(*) FILTER (WHERE a.status = 'HADIR')     AS hadir,
               COUNT(*) FILTER (WHERE a.status = 'TERLAMBAT') AS terlambat
        FROM users u
        LEFT JOIN attendance_records a
               ON a.user_id = u.id AND a.schedule_id = %s
        GROUP BY u.id, u.name, u.nim
        ORDER BY u.name ASC
        ''',
        (schedule_id,),
    )
    students = cursor.fetchall()

    result = []
    for s in students:
        hadir = int(s['hadir'])
        terlambat = int(s['terlambat'])
        attended = hadir + terlambat
        result.append({
            'name': s['name'],
            'nim': s['nim'],
            'hadir': hadir,
            'terlambat': terlambat,
            'alpha': max(meetings - attended, 0),
            'percent': round(attended / meetings * 100) if meetings else 0,
        })

    return meetings, cancelled, result


@router.get('/api/lecturer/attendance')
async def lecturer_attendance(request: Request, schedule_id: int, class_date: str = ''):
    code = current_lecturer(request)
    if not code:
        return unauthorized()

    if class_date:
        try:
            target = date.fromisoformat(class_date)
        except ValueError:
            return {'success': False, 'message': 'Format tanggal tidak valid.'}
    else:
        target = today_wib()

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                schedule = get_owned_schedule(cursor, schedule_id, code)
                if not schedule:
                    return {'success': False, 'message': 'Kelas tidak ditemukan.'}

                cursor.execute(
                    '''
                    SELECT u.name, u.nim, a.status, a.attendance_time
                    FROM attendance_records a
                    JOIN users u ON u.id = a.user_id
                    WHERE a.schedule_id = %s
                      AND a.attendance_time::date = %s
                    ORDER BY a.attendance_time ASC
                    ''',
                    (schedule_id, target),
                )
                rows = cursor.fetchall()

                cursor.execute(
                    '''
                    SELECT DISTINCT attendance_time::date AS d
                    FROM attendance_records
                    WHERE schedule_id = %s
                    ORDER BY d DESC
                    ''',
                    (schedule_id,),
                )
                dates = [r['d'].isoformat() for r in cursor.fetchall()]

                cursor.execute(
                    'SELECT reason FROM class_cancellations WHERE schedule_id = %s AND class_date = %s',
                    (schedule_id, target),
                )
                cancel_row = cursor.fetchone()

                cursor.execute(
                    'SELECT status, check_in_time FROM lecturer_attendance WHERE schedule_id = %s AND class_date = %s',
                    (schedule_id, target),
                )
                lecturer_row = cursor.fetchone()

        records = [
            {
                'name': r['name'],
                'nim': r['nim'],
                'status': r['status'],
                'time': r['attendance_time'].strftime('%H:%M:%S'),
            }
            for r in rows
        ]

        return {
            'success': True,
            'course': schedule['course'],
            'date': target.isoformat(),
            'is_today': target == today_wib(),
            'lecturer': {'status': lecturer_row['status'], 'time': lecturer_row['check_in_time'].strftime('%H:%M:%S')} if lecturer_row else None,
            'cancelled': cancel_row is not None,
            'cancel_reason': cancel_row['reason'] if cancel_row else None,
            'hadir': sum(1 for r in records if r['status'] == 'HADIR'),
            'terlambat': sum(1 for r in records if r['status'] == 'TERLAMBAT'),
            'records': records,
            'meeting_dates': dates,
        }

    except Exception as e:
        print('LECTURER ATTENDANCE ERROR:', repr(e))
        return {'success': False, 'message': 'Gagal memuat kehadiran.'}


@router.get('/api/lecturer/recap/export')
async def lecturer_recap_export(request: Request, schedule_id: int):
    code = current_lecturer(request)
    if not code:
        return Response('Sesi dosen tidak valid.', status_code=401, media_type='text/plain')

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                schedule = get_owned_schedule(cursor, schedule_id, code)
                if not schedule:
                    return Response('Kelas tidak ditemukan.', status_code=404, media_type='text/plain')

                meetings, cancelled, students = compute_recap(cursor, schedule_id)

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(['Mata Kuliah', schedule['course']])
        writer.writerow(['Total Pertemuan', meetings])
        writer.writerow(['Kelas Dibatalkan', cancelled])
        writer.writerow([])
        writer.writerow(['Nama', 'NIM', 'Hadir', 'Terlambat', 'Alpha', 'Persen'])
        for s in students:
            writer.writerow([
                s['name'], s['nim'], s['hadir'], s['terlambat'], s['alpha'], str(s['percent']) + '%'
            ])

        filename = 'rekap_kelas_' + str(schedule_id) + '_' + today_wib().isoformat() + '.csv'

        return Response(
            '\ufeff' + buffer.getvalue(),
            media_type='text/csv; charset=utf-8',
            headers={'Content-Disposition': 'attachment; filename="' + filename + '"'},
        )

    except Exception as e:
        print('LECTURER EXPORT ERROR:', repr(e))
        return Response('Gagal membuat file rekap.', status_code=500, media_type='text/plain')


# ============================================================
# PRESENSI DOSEN (MULAI KELAS)
# ============================================================

@router.post('/api/lecturer/checkin')
async def lecturer_checkin(request: Request, schedule_id: int = Form(...)):
    code = current_lecturer(request)
    if not code:
        return unauthorized()

    now = datetime.now(WIB).replace(tzinfo=None)
    today = now.date()

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                schedule = get_owned_schedule(cursor, schedule_id, code)
                if not schedule:
                    return {'success': False, 'message': 'Kelas tidak ditemukan.'}

                cursor.execute(
                    'SELECT 1 FROM class_cancellations WHERE schedule_id = %s AND class_date = %s',
                    (schedule_id, today),
                )
                if cursor.fetchone():
                    return {'success': False, 'message': 'Kelas ini sudah ditandai tidak masuk hari ini.'}

                window = dict(schedule)
                window['start'] = format_time_field(schedule['start_time'])
                window['end'] = format_time_field(schedule['end_time'])
                window_status = get_schedule_status(window, now)

                if window_status not in ('ABSEN', 'TERLAMBAT'):
                    return {
                        'success': False,
                        'message': 'Mulai kelas hanya bisa pada hari dan jam kuliah (dibuka 15 menit sebelum mulai).',
                    }

                status = 'TERLAMBAT' if window_status == 'TERLAMBAT' else 'HADIR'

                cursor.execute(
                    '''
                    INSERT INTO lecturer_attendance
                        (schedule_id, class_date, lecturer_code, status, check_in_time)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (schedule_id, class_date) DO NOTHING
                    RETURNING id
                    ''',
                    (schedule_id, today, code, status, now),
                )
                inserted = cursor.fetchone()

        if inserted is None:
            return {'success': True, 'already': True, 'message': 'Kehadiran Anda hari ini sudah tercatat.'}

        return {
            'success': True,
            'already': False,
            'status': status,
            'time': now.strftime('%H:%M:%S'),
            'message': 'Kehadiran dosen tercatat (' + status + ').',
        }

    except Exception as e:
        print('LECTURER CHECKIN ERROR:', repr(e))
        return {'success': False, 'message': 'Gagal mencatat kehadiran dosen.'}
