# app/utils.py
from datetime import datetime, time, timedelta, date
from .models import Appointment
from django.utils import timezone
from typing import List, Optional
import pytz

# Working hours configuration
WORK_START = time(hour=9, minute=0)  # 9:00 AM
WORK_END = time(hour=18, minute=0)   # 6:00 PM
LUNCH_START = time(hour=13, minute=0)  # 1:00 PM
LUNCH_END = time(hour=14, minute=0)    # 2:00 PM
SLOT_DURATION_MINUTES = 30

# Holiday dates (can be configured)
HOLIDAYS = [
    # Add holiday dates here as date objects
    # date(2025, 1, 1),  # New Year
    # date(2025, 12, 25), # Christmas
]

class SlotError(Exception):
    """Custom exception for invalid slot operations."""
    pass

def is_working_day(check_date: date) -> bool:
    """
    Check if the given date is a working day (not weekend or holiday)
    
    Args:
        check_date: Date to check
        
    Returns:
        bool: True if working day, False otherwise
    """
    # Check if weekend (Saturday = 5, Sunday = 6)
    if check_date.weekday() >= 5:
        return False
    
    # Check if holiday
    if check_date in HOLIDAYS:
        return False
    
    return True

def generate_daily_slots(check_date: Optional[date] = None) -> List[str]:
    """
    Generate working slots for a given date, excluding lunch break
    
    Args:
        check_date: Date to generate slots for (defaults to today)
        
    Returns:
        List[str]: List of time slots in "HH:MM" format
    """
    if check_date is None:
        check_date = date.today()
    
    # Check if it's a working day
    if not is_working_day(check_date):
        return []
    
    slots = []
    current = datetime.combine(check_date, WORK_START)
    end = datetime.combine(check_date, WORK_END)
    
    while current < end:
        slot_time = current.time()
        
        # Skip lunch break
        if not (LUNCH_START <= slot_time < LUNCH_END):
            slots.append(slot_time.strftime("%H:%M"))
        
        current += timedelta(minutes=SLOT_DURATION_MINUTES)
    
    return slots

def get_booked_slots(doctor, check_date: date) -> List[str]:
    """
    Get all booked slots for a doctor on a specific date
    
    Args:
        doctor: Doctor instance
        check_date: Date to check
        
    Returns:
        List[str]: List of booked time slots in "HH:MM" format
    """
    # Only consider appointments that are NOT cancelled
    appointments = Appointment.objects.filter(
        doctor=doctor,
        date=check_date
    ).exclude(status='cancelled')
    
    booked_slots = []
    for appointment in appointments:
        if hasattr(appointment.slot, 'strftime'):
            booked_slots.append(appointment.slot.strftime("%H:%M"))
        else:
            booked_slots.append(str(appointment.slot))
    
    return booked_slots

def get_available_slots(doctor, check_date: date) -> List[str]:
    """
    Get available time slots for a doctor on a specific date
    
    Args:
        doctor: Doctor instance
        check_date: Date to check
        
    Returns:
        List[str]: List of available time slots in "HH:MM" format
    """
    # Generate all possible slots for the date
    all_slots = generate_daily_slots(check_date)
    
    # Get booked slots
    booked_slots = get_booked_slots(doctor, check_date)
    
    # Return slots that are not booked
    available = [slot for slot in all_slots if slot not in booked_slots]
    
    # If checking today, also filter out past slots
    if check_date == date.today():
        current_time = timezone.now().time()
        available = [slot for slot in available if datetime.strptime(slot, "%H:%M").time() > current_time]
    
    return available

def validate_slot(slot_str: str, check_date: date) -> time:
    """
    Validate if a slot is valid for the given date
    
    Args:
        slot_str: Time slot in "HH:MM" format
        check_date: Date to validate against
        
    Returns:
        time: Validated time object
        
    Raises:
        SlotError: If slot is invalid
    """
    try:
        slot_time = datetime.strptime(slot_str, "%H:%M").time()
    except ValueError:
        raise SlotError("Invalid time format. Use HH:MM format.")
    
    # Check if it's a working day
    if not is_working_day(check_date):
        raise SlotError("Selected date is not a working day.")
    
    # Get all valid slots for the date
    valid_slots = generate_daily_slots(check_date)
    
    if slot_str not in valid_slots:
        raise SlotError("Slot is not within working hours or is during lunch break.")
    
    # If it's today, check if the slot is not in the past
    if check_date == date.today():
        current_time = timezone.now().time()
        if slot_time <= current_time:
            raise SlotError("Cannot book appointments in the past.")
    
    return slot_time

def get_slot_duration() -> int:
    """
    Get the duration of each appointment slot in minutes
    
    Returns:
        int: Slot duration in minutes
    """
    return SLOT_DURATION_MINUTES

def get_working_hours() -> dict:
    """
    Get working hours configuration
    
    Returns:
        dict: Working hours information
    """
    return {
        'start': WORK_START.strftime("%H:%M"),
        'end': WORK_END.strftime("%H:%M"),
        'lunch_start': LUNCH_START.strftime("%H:%M"),
        'lunch_end': LUNCH_END.strftime("%H:%M"),
        'slot_duration': SLOT_DURATION_MINUTES
    }

def is_slot_available(doctor, check_date: date, slot_str: str) -> bool:
    """
    Check if a specific slot is available for a doctor
    
    Args:
        doctor: Doctor instance
        check_date: Date to check
        slot_str: Time slot in "HH:MM" format
        
    Returns:
        bool: True if slot is available, False otherwise
    """
    try:
        validate_slot(slot_str, check_date)
        available_slots = get_available_slots(doctor, check_date)
        return slot_str in available_slots
    except SlotError:
        return False

def get_next_available_slot(doctor, start_date: Optional[date] = None, days_ahead: int = 30) -> Optional[dict]:
    """
    Find the next available slot for a doctor starting from a given date
    
    Args:
        doctor: Doctor instance
        start_date: Date to start searching from (defaults to today)
        days_ahead: How many days ahead to search
        
    Returns:
        dict: Next available slot info or None if no slots found
    """
    if start_date is None:
        start_date = date.today()
    
    for i in range(days_ahead):
        check_date = start_date + timedelta(days=i)
        available_slots = get_available_slots(doctor, check_date)
        
        if available_slots:
            return {
                'date': check_date.strftime("%Y-%m-%d"),
                'slot': available_slots[0],
                'datetime': f"{check_date.strftime('%Y-%m-%d')} {available_slots}"
            }
    
    return None

def format_appointment_datetime(appointment_date: date, slot_time: str) -> str:
    """
    Format appointment date and time for display
    
    Args:
        appointment_date: Appointment date
        slot_time: Time slot in "HH:MM" format
        
    Returns:
        str: Formatted datetime string
    """
    try:
        date_str = appointment_date.strftime("%B %d, %Y")  # e.g., "January 15, 2025"
        time_obj = datetime.strptime(slot_time, "%H:%M").time()
        time_str = time_obj.strftime("%I:%M %p")  # e.g., "02:30 PM"
        return f"{date_str} at {time_str}"
    except (ValueError, AttributeError):
        return f"{appointment_date} at {slot_time}"
