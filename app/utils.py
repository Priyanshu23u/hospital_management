from datetime import datetime, time, timedelta
from .models import Appointment

WORK_START = time(hour=10, minute=0)
WORK_END = time(hour=18, minute=0)
LUNCH_START = time(hour=13, minute=0)
LUNCH_END = time(hour=14, minute=0)
SLOT_MINUTES = 30

class SlotError(Exception):
    """Custom exception for invalid slot operations."""
    pass

def generate_daily_slots(date):
    """Generate working slots excluding lunch break."""
    slots = []
    cur = datetime.combine(date, WORK_START)
    end = datetime.combine(date, WORK_END)
    while cur < end:
        t = cur.time()
        if not (LUNCH_START <= t < LUNCH_END):
            slots.append(t.strftime("%H:%M"))
        cur += timedelta(minutes=SLOT_MINUTES)
    return slots

def get_booked_slots(doctor, date):
    # ✅ FIXED: Only consider appointments that are NOT cancelled
    appointments = Appointment.objects.filter(
        doctor=doctor, 
        date=date
    ).exclude(status='cancelled')  # ✅ This is the key fix
    
    return [a.slot.strftime("%H:%M") if hasattr(a.slot, 'strftime') else str(a.slot) for a in appointments]


def get_available_slots(doctor, date):
    all_slots = generate_daily_slots()
    booked = get_booked_slots(doctor, date)
    return [s for s in all_slots if s not in booked]

def validate_slot(slot_str, date):
    """Ensure slot is valid for the given date."""
    all_slots = generate_daily_slots(date)
    if slot_str not in all_slots:
        raise SlotError("Slot not valid or outside working hours.")
    return datetime.strptime(slot_str, "%H:%M").time()
