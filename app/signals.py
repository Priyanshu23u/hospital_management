# app/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Profile, Doctor, Patient, Appointment, VisitNote
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create a Profile when a User is created
    """
    if created:
        # Only create profile if it doesn't exist
        if not hasattr(instance, 'profile'):
            Profile.objects.create(user=instance, role='patient')  # Default role
            logger.info(f"Profile created for user: {instance.username}")

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Save the profile when user is saved
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()

@receiver(post_save, sender=Appointment)
def appointment_status_changed(sender, instance, created, **kwargs):
    """
    Handle appointment status changes
    """
    if not created:  # Only for updates
        if instance.status == 'completed':
            # Create a visit note if it doesn't exist
            if not VisitNote.objects.filter(appointment=instance).exists():
                VisitNote.objects.create(
                    appointment=instance,
                    patient=instance.patient,
                    doctor=instance.doctor,
                    notes=f"Appointment completed on {instance.date}"
                )
                logger.info(f"Visit note created for completed appointment: {instance.id}")

@receiver(post_delete, sender=Appointment)
def cleanup_orphaned_visit_notes(sender, instance, **kwargs):
    """
    Clean up visit notes when appointment is deleted
    """
    try:
        # Optionally keep visit notes even after appointment deletion
        # or delete them - depends on your business logic
        pass
    except Exception as e:
        logger.error(f"Error cleaning up visit notes for appointment {instance.id}: {e}")
