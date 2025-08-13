# app/admin.py
from django.contrib import admin
from .models import Profile, Doctor, Patient, Appointment, VisitNote, Document

admin.site.register(Profile)
admin.site.register(Doctor)
admin.site.register(Patient)
admin.site.register(Appointment)
admin.site.register(VisitNote)
admin.site.register(Document)
