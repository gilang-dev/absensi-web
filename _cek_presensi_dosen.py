import traceback

try:
    from datetime import datetime
    from app.schedule import get_schedules, get_schedule_status, WIB
    from app.db import get_db_connection

    now = datetime.now(WIB).replace(tzinfo=None)
    print('NOW', now, 'weekday', now.weekday())

    for s in get_schedules():
        print(s['id'], s['course'], s['lecturer'], 'day', s['day'], s['start'], s['end'], get_schedule_status(s, now))

    with get_db_connection() as c:
        with c.cursor() as cur:
            cur.execute('SELECT code, nip, name FROM lecturers')
            print('LECTURERS', cur.fetchall())
            cur.execute('SELECT * FROM lecturer_attendance')
            print('LECTURER_ATT', cur.fetchall())
except Exception:
    traceback.print_exc()
    print('ERROR', traceback.format_exc())
