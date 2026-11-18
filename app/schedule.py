import os
from datetime import datetime, timedelta, time
from app.db import get_db_connection
from zoneinfo import ZoneInfo

WIB = ZoneInfo("Asia/Jakarta")

# Toleransi Absensi
OPEN_TOLERANCE_MINUTES = 15
LATE_AFTER_MINUTES = 15

DAY_NAMES = {
    0: "Senin",
    1: "Selasa",
    2: "Rabu",
    3: "Kamis",
    4: "Jumat",
    5: "Sabtu",
    6: "Minggu"
}


def format_time_field(time_val):
    """Mengubah tipe TIME PostgreSQL menjadi HH:MM."""

    if isinstance(time_val, time):
        return time_val.strftime("%H:%M")

    if isinstance(time_val, datetime):
        return time_val.strftime("%H:%M")

    if isinstance(time_val, timedelta):
        total_seconds = int(time_val.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"

    parts = str(time_val).split(":")
    return f"{int(parts[0]):02d}:{int(parts[1]):02d}"



def get_user_id_by_nim(student_nim):
    """Mencari ID user berdasarkan NIM."""

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id
                    FROM users
                    WHERE nim = %s
                    LIMIT 1
                    """,
                    (student_nim,)
                )

                row = cursor.fetchone()
                return row["id"] if row else None

    except Exception as e:
        print("ERROR GET USER ID:", repr(e))
        return None


def get_schedules():
    """Mengambil seluruh jadwal kuliah."""

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT *
                    FROM schedules
                    ORDER BY day ASC, start_time ASC
                    """
                )

                rows = cursor.fetchall()

                for row in rows:
                    row["start"] = format_time_field(
                        row["start_time"]
                    )

                    row["end"] = format_time_field(
                        row["end_time"]
                    )

                return rows

    except Exception as e:
        print("ERROR GET SCHEDULES:", repr(e))
        return []


def time_to_minutes(time_string):
    """Mengubah HH:MM menjadi total menit."""

    parts = time_string.split(":")
    return int(parts[0]) * 60 + int(parts[1])


def get_schedule_status(schedule, now=None):
    """Menentukan status jadwal absensi."""

    if now is None:
        now = datetime.now(WIB)

    if now.weekday() != int(schedule["day"]):
        return "BELUM DIBUKA"

    current_minutes = now.hour * 60 + now.minute

    start_minutes = time_to_minutes(schedule["start"])
    end_minutes = time_to_minutes(schedule["end"])

    open_minutes = start_minutes - OPEN_TOLERANCE_MINUTES
    late_minutes = start_minutes + LATE_AFTER_MINUTES

    if current_minutes < open_minutes:
        return "BELUM DIBUKA"

    if open_minutes <= current_minutes < late_minutes:
        return "ABSEN"

    if late_minutes <= current_minutes < end_minutes:
        return "TERLAMBAT"

    return "DITUTUP"


def get_student_attendance(user_id, schedule_id, date_string=None):
    """Mengecek absensi mahasiswa pada tanggal tertentu."""

    if date_string is None:
        date_string = datetime.now(WIB).date()

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        user_id,
                        schedule_id,
                        status,
                        attendance_time
                    FROM attendance_records
                    WHERE user_id = %s
                      AND schedule_id = %s
                      AND attendance_time::date = %s
                    LIMIT 1
                    """,
                    (user_id, schedule_id, date_string)
                )

                row = cursor.fetchone()

                if row:
                    attendance_time = row["attendance_time"]

                    if isinstance(attendance_time, datetime):
                        row["time"] = attendance_time.strftime(
                            "%H:%M:%S"
                        )
                    else:
                        row["time"] = str(attendance_time)

                return row

    except Exception as e:
        print("ERROR GET STUDENT ATTENDANCE:", repr(e))
        return None



def record_attendance(student_nim, schedule, window_status):
    """Menyimpan presensi ke Supabase berdasarkan NIM."""

    now = datetime.now(WIB).replace(tzinfo=None)
    today = now.date()
    time_display = now.strftime("%H:%M:%S")

    user_id = get_user_id_by_nim(student_nim)

    if user_id is None:
        return {
            "success": False,
            "message": f"NIM '{student_nim}' tidak ditemukan di database."
        }

    db_status = (
        "TERLAMBAT"
        if window_status == "TERLAMBAT"
        else "HADIR"
    )

    existing = get_student_attendance(
        user_id,
        schedule["id"],
        today
    )

    if existing:
        return {
            "success": True,
            "attended": True,
            "already_attended": True,
            "status": existing.get("status", "HADIR"),
            "attendance_time": existing.get("time", time_display),
            "message": "Anda sudah melakukan absensi."
        }

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO attendance_records
                    (
                        user_id,
                        schedule_id,
                        status,
                        attendance_time
                    )
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                    RETURNING id
                    """,
                    (
                        user_id,
                        schedule["id"],
                        db_status,
                        now
                    )
                )

                inserted = cursor.fetchone()

                if inserted is None:
                    return {
                        "success": True,
                        "attended": True,
                        "already_attended": True,
                        "status": db_status,
                        "message": "Anda sudah melakukan absensi."
                    }

        return {
            "success": True,
            "attended": True,
            "already_attended": False,
            "status": db_status,
            "attendance_time": time_display,
            "message": "Absensi berhasil disimpan."
        }

    except Exception as e:
        print("ERROR RECORD ATTENDANCE:", repr(e))

        return {
            "success": False,
            "message": "Gagal menyimpan absensi ke database."
        }

def process_face_attendance(student_nim, schedule_id=None):
    """Memproses presensi berdasarkan NIM dan hasil pengenalan wajah."""

    now = datetime.now(WIB).replace(tzinfo=None)
    schedules = get_schedules()

    active_schedule = None
    active_status = None

    if schedule_id is not None:
        for schedule in schedules:
            if str(schedule["id"]) == str(schedule_id):
                active_schedule = schedule
                active_status = get_schedule_status(schedule, now)
                break

        if active_schedule is None:
            return {
                "success": False,
                "attended": False,
                "message": "Jadwal kuliah tidak ditemukan."
            }

        if active_status not in ["ABSEN", "TERLAMBAT"]:
            return {
                "success": False,
                "attended": False,
                "message": "Presensi belum dibuka atau sudah ditutup."
            }

    else:
        for schedule in schedules:
            status = get_schedule_status(schedule, now)

            if status in ["ABSEN", "TERLAMBAT"]:
                active_schedule = schedule
                active_status = status
                break

    if active_schedule is None:
        return {
            "success": False,
            "attended": False,
            "message": "Tidak ada jadwal kuliah yang sedang membuka presensi."
        }

    return record_attendance(
        student_nim,
        active_schedule,
        active_status
    )



def get_dashboard_data(student_nim):
    """Mengambil jadwal dan riwayat presensi dashboard."""

    now = datetime.now(WIB).replace(tzinfo=None)
    today = now.date()

    dashboard_data = []

    try:
        conn = get_db_connection()

        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        s.*,
                        a.status AS attendance_status,
                        a.attendance_time AS recorded_attendance_time

                    FROM schedules s

                    LEFT JOIN attendance_records a
                        ON a.schedule_id = s.id
                        AND a.user_id = (
                            SELECT id
                            FROM users
                            WHERE nim = %s
                            LIMIT 1
                        )
                        AND a.attendance_time::date = %s

                    ORDER BY s.day ASC, s.start_time ASC
                    """,
                    (student_nim, today)
                )

                rows = cursor.fetchall()

        finally:
            conn.close()

        for schedule in rows:

            schedule["start"] = format_time_field(
                schedule["start_time"]
            )

            schedule["end"] = format_time_field(
                schedule["end_time"]
            )

            attendance = schedule["recorded_attendance_time"]

            if attendance is not None:

                dashboard_status = "SUDAH ABSEN"
                attendance_time = attendance.strftime("%H:%M:%S")

            else:

                dashboard_status = get_schedule_status(
                    schedule,
                    now
                )

                attendance_time = None

            dashboard_data.append({
                "id": schedule["id"],
                "course": schedule["course"],
                "code": schedule.get("code", "-"),
                "lecturer": schedule.get("lecturer", "-"),
                "sks": schedule.get("sks", 0),
                "room": schedule.get("room", "-"),
                "day": schedule["day"],

                "day_name": DAY_NAMES.get(
                    int(schedule["day"]),
                    "-"
                ),

                "start": schedule["start"],
                "end": schedule["end"],

                "status": dashboard_status,

                "attendance_status": schedule["attendance_status"],

                "attendance_time": attendance_time
            })

        return dashboard_data

    except Exception as e:
        print("ERROR GET DASHBOARD DATA:", repr(e))
        return []
