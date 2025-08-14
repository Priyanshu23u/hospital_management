# app/utils.py
from datetime import datetime, time, timedelta
from .models import Appointment

# Constants
WORK_START = time(hour=10, minute=0)
WORK_END = time(hour=18, minute=0)
LUNCH_START = time(hour=13, minute=0)
LUNCH_END = time(hour=14, minute=0)
SLOT_MINUTES = 30

def generate_daily_slots(date):
    """
    Generate all valid slots for a date between 10:00 and 18:00,
    excluding lunch 13:00–14:00.
    """
    slots = []
    cur = datetime.combine(date, WORK_START)
    end = datetime.combine(date, WORK_END)
    while cur < end:
        t = cur.time()
        if not (LUNCH_START <= t < LUNCH_END):
            slots.append(t.strftime("%H:%M"))
        cur += timedelta(minutes=SLOT_MINUTES)
    return slots

def get_booked_slots(doctor_id, date):
    """
    Return booked slots for a given doctor/date as list of HH:MM strings.
    """
    qs = Appointment.objects.filter(
        doctor_id=doctor_id, date=date, status="booked"
    )
    return [appt.slot.strftime("%H:%M") for appt in qs]

def get_available_slots(doctor_id, date):
    """
    Return available slots by subtracting booked from generated slots.
    """
    all_slots = generate_daily_slots(date)
    booked = set(get_booked_slots(doctor_id, date))
    return [s for s in all_slots if s not in booked]
