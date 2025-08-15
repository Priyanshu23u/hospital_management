from django.db import models
from django.contrib.auth.models import User

# Extend User with Profile for role & basic info
class Profile(models.Model):
    ROLE_CHOICES = [
        ('doctor', 'Doctor'),
        ('patient', 'Patient'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    dob = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, null=True, blank=True)
    phone = models.CharField(max_length=15, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

# Doctor details
class Doctor(models.Model):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE)
    specialization = models.CharField(max_length=120)
    bio = models.TextField(blank=True)
    available = models.BooleanField(default=True)

    def __str__(self):
        return f"Dr. {self.profile.user.first_name} - {self.specialization}"

# Patient details
class Patient(models.Model):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE)

    def __str__(self):
        return self.profile.user.get_full_name()

# Appointment model
class Appointment(models.Model):
    STATUS_CHOICES = [
        ('booked', 'Booked'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    date = models.DateField()
    slot = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='booked')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('doctor', 'date', 'slot')

    def __str__(self):
        return f"{self.date} {self.slot} - {self.patient} with {self.doctor}"

# Visit notes from doctor (with prescription)
class VisitNote(models.Model):
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name='visitnote_set')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    visit_date = models.DateTimeField(auto_now_add=True)
    notes = models.TextField()
    prescription = models.FileField(upload_to='prescriptions/', null=True, blank=True)  # File upload

    def __str__(self):
        return f"Note for {self.patient} by {self.doctor} on {self.visit_date}"

# Uploaded medical documents (linked to appointment)
class Document(models.Model):
    DOC_TYPE_CHOICES = [
        ('lab', 'Lab Report'),
        ('scan', 'Scan/X-ray'),
        ('prescription', 'Prescription'),
        ('other', 'Other'),
    ]
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, null=True, blank=True)  # link to booking
    file = models.FileField(upload_to='documents/')
    doc_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES, default='other')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.doc_type} for {self.patient}"
