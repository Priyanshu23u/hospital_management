# app/admin.py
from django.contrib import admin
from .models import Profile, Doctor, Patient, Appointment, VisitNote, Document

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone', 'dob', 'gender')
    list_filter = ('role', 'gender')
    search_fields = ('user__username', 'user__email', 'phone')
    ordering = ('user__username',)

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ('get_name', 'specialization', 'available', 'get_email')
    list_filter = ('specialization', 'available')
    search_fields = ('profile__user__username', 'profile__user__first_name', 'profile__user__last_name', 'specialization')
    ordering = ('profile__user__username',)

    def get_name(self, obj):
        return obj.profile.user.get_full_name() or obj.profile.user.username
    get_name.short_description = 'Name'

    def get_email(self, obj):
        return obj.profile.user.email
    get_email.short_description = 'Email'

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('get_name', 'get_email', 'get_phone')
    search_fields = ('profile__user__username', 'profile__user__first_name', 'profile__user__last_name', 'profile__user__email')
    ordering = ('profile__user__username',)

    def get_name(self, obj):
        return obj.profile.user.get_full_name() or obj.profile.user.username
    get_name.short_description = 'Name'

    def get_email(self, obj):
        return obj.profile.user.email
    get_email.short_description = 'Email'

    def get_phone(self, obj):
        return obj.profile.phone
    get_phone.short_description = 'Phone'

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('get_patient_name', 'get_doctor_name', 'date', 'slot', 'status', 'created_at')
    list_filter = ('status', 'date', 'doctor__specialization')
    search_fields = ('patient__profile__user__username', 'doctor__profile__user__username')
    ordering = ('-date', '-slot')
    date_hierarchy = 'date'

    def get_patient_name(self, obj):
        return obj.patient.profile.user.get_full_name() or obj.patient.profile.user.username
    get_patient_name.short_description = 'Patient'

    def get_doctor_name(self, obj):
        return obj.doctor.profile.user.get_full_name() or obj.doctor.profile.user.username
    get_doctor_name.short_description = 'Doctor'

@admin.register(VisitNote)
class VisitNoteAdmin(admin.ModelAdmin):
    list_display = ('get_patient_name', 'get_doctor_name', 'visit_date', 'get_appointment_date')
    list_filter = ('visit_date', 'doctor__specialization')
    search_fields = ('patient__profile__user__username', 'doctor__profile__user__username', 'notes')
    ordering = ('-visit_date',)
    date_hierarchy = 'visit_date'

    def get_patient_name(self, obj):
        return obj.patient.profile.user.get_full_name() or obj.patient.profile.user.username
    get_patient_name.short_description = 'Patient'

    def get_doctor_name(self, obj):
        return obj.doctor.profile.user.get_full_name() or obj.doctor.profile.user.username
    get_doctor_name.short_description = 'Doctor'

    def get_appointment_date(self, obj):
        if obj.appointment:
            return f"{obj.appointment.date} {obj.appointment.slot}"
        return "No appointment linked"
    get_appointment_date.short_description = 'Appointment'

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('get_patient_name', 'doc_type', 'description', 'uploaded_at', 'get_file_name')
    list_filter = ('doc_type', 'uploaded_at')
    search_fields = ('patient__profile__user__username', 'description', 'doc_type')
    ordering = ('-uploaded_at',)
    date_hierarchy = 'uploaded_at'

    def get_patient_name(self, obj):
        return obj.patient.profile.user.get_full_name() or obj.patient.profile.user.username
    get_patient_name.short_description = 'Patient'

    def get_file_name(self, obj):
        if obj.file:
            return obj.file.name.split('/')[-1]
        return "No file"
    get_file_name.short_description = 'File Name'
