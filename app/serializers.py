# app/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile, Doctor, Patient, Appointment, VisitNote, Document

# -------------------------
# USER & PROFILE SERIALIZERS
# -------------------------

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'password', 'full_name', 'date_joined', 'is_active']
        extra_kwargs = {
            'password': {'write_only': True},
            'date_joined': {'read_only': True},
            'is_active': {'read_only': True}
        }

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance

class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = ['id', 'user', 'user_id', 'username', 'email', 'full_name', 'role', 'dob', 'gender', 'phone']
        read_only_fields = ['id']

    def get_full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = UserSerializer.create(UserSerializer(), validated_data=user_data)
        profile = Profile.objects.create(user=user, **validated_data)
        return profile

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)
        
        # Update profile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update user fields if provided
        if user_data:
            user_serializer = UserSerializer(instance.user, data=user_data, partial=True)
            if user_serializer.is_valid():
                user_serializer.save()

        return instance

# -------------------------
# DOCTOR & PATIENT SERIALIZERS
# -------------------------

class DoctorSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    username = serializers.CharField(source='profile.user.username', read_only=True)
    email = serializers.EmailField(source='profile.user.email', read_only=True)
    phone = serializers.CharField(source='profile.phone', read_only=True)
    role = serializers.CharField(source='profile.role', read_only=True)
    user_id = serializers.IntegerField(source='profile.user.id', read_only=True)
    
    # Statistics fields
    total_appointments = serializers.SerializerMethodField()
    today_appointments = serializers.SerializerMethodField()
    total_patients = serializers.SerializerMethodField()

    class Meta:
        model = Doctor
        fields = [
            'id', 'name', 'full_name', 'username', 'email', 'phone', 'role', 'user_id',
            'specialization', 'bio', 'available',
            'total_appointments', 'today_appointments', 'total_patients'
        ]
        read_only_fields = ['id']

    def get_name(self, obj):
        return obj.profile.user.get_full_name() or obj.profile.user.username

    def get_full_name(self, obj):
        return obj.profile.user.get_full_name() or obj.profile.user.username

    def get_total_appointments(self, obj):
        return obj.appointment_set.count()

    def get_today_appointments(self, obj):
        from datetime import date
        return obj.appointment_set.filter(date=date.today()).count()

    def get_total_patients(self, obj):
        return obj.appointment_set.values('patient').distinct().count()

class PatientSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    username = serializers.CharField(source='profile.user.username', read_only=True)
    email = serializers.EmailField(source='profile.user.email', read_only=True)
    phone = serializers.CharField(source='profile.phone', read_only=True)
    role = serializers.CharField(source='profile.role', read_only=True)
    user_id = serializers.IntegerField(source='profile.user.id', read_only=True)
    
    # Statistics fields
    total_appointments = serializers.SerializerMethodField()
    upcoming_appointments = serializers.SerializerMethodField()
    total_documents = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            'id', 'name', 'full_name', 'username', 'email', 'phone', 'role', 'user_id',
            'total_appointments', 'upcoming_appointments', 'total_documents'
        ]
        read_only_fields = ['id']

    def get_name(self, obj):
        return obj.profile.user.get_full_name() or obj.profile.user.username

    def get_full_name(self, obj):
        return obj.profile.user.get_full_name() or obj.profile.user.username

    def get_total_appointments(self, obj):
        return obj.appointment_set.count()

    def get_upcoming_appointments(self, obj):
        from datetime import date
        return obj.appointment_set.filter(date__gte=date.today()).count()

    def get_total_documents(self, obj):
        return obj.document_set.count()

# -------------------------
# APPOINTMENT SERIALIZER
# -------------------------

class AppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()
    doctor_username = serializers.CharField(source='doctor.profile.user.username', read_only=True)
    patient_name = serializers.SerializerMethodField()
    patient_username = serializers.CharField(source='patient.profile.user.username', read_only=True)
    specialization = serializers.CharField(source='doctor.specialization', read_only=True)
    
    # Enhanced prescription handling
    prescription = serializers.SerializerMethodField()
    prescription_file = serializers.SerializerMethodField()
    has_prescription = serializers.SerializerMethodField()
    
    # Date/time formatting
    formatted_date = serializers.SerializerMethodField()
    formatted_time = serializers.SerializerMethodField()
    formatted_datetime = serializers.SerializerMethodField()
    
    # Status information
    can_cancel = serializers.SerializerMethodField()
    can_update = serializers.SerializerMethodField()
    
    # Visit notes
    visit_notes = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'patient_name', 'patient_username',
            'doctor', 'doctor_name', 'doctor_username', 'specialization',
            'date', 'formatted_date', 'slot', 'formatted_time', 'formatted_datetime',
            'status', 'prescription', 'prescription_file', 'has_prescription',
            'created_at', 'can_cancel', 'can_update', 'visit_notes'
        ]
        read_only_fields = ['id', 'created_at']

    def get_doctor_name(self, obj):
        return obj.doctor.profile.user.get_full_name() or obj.doctor.profile.user.username

    def get_patient_name(self, obj):
        return obj.patient.profile.user.get_full_name() or obj.patient.profile.user.username

    def get_prescription(self, obj):
        """
        Return the prescription text from the related VisitNote or appointment field
        """
        try:
            # First, try to get from visit note
            latest_note = obj.visitnote_set.order_by('-visit_date').first()
            if latest_note and latest_note.notes:
                return latest_note.notes
            
            # Fallback to appointment prescription field
            return obj.prescription if obj.prescription else None
        except Exception:
            return obj.prescription if obj.prescription else None

    def get_prescription_file(self, obj):
        """
        Return the prescription file URL if available
        """
        try:
            latest_note = obj.visitnote_set.order_by('-visit_date').first()
            if latest_note and latest_note.prescription:
                request = self.context.get('request')
                if request and hasattr(latest_note.prescription, 'url'):
                    return request.build_absolute_uri(latest_note.prescription.url)
                return latest_note.prescription.url if hasattr(latest_note.prescription, 'url') else str(latest_note.prescription)
            return None
        except Exception:
            return None

    def get_has_prescription(self, obj):
        """
        Check if appointment has any prescription (text or file)
        """
        try:
            latest_note = obj.visitnote_set.order_by('-visit_date').first()
            if latest_note and (latest_note.notes or latest_note.prescription):
                return True
            return bool(obj.prescription)
        except Exception:
            return bool(obj.prescription)

    def get_formatted_date(self, obj):
        if obj.date:
            return obj.date.strftime("%B %d, %Y")  # e.g., "January 15, 2025"
        return None

    def get_formatted_time(self, obj):
        if obj.slot:
            if isinstance(obj.slot, str):
                return obj.slot
            return obj.slot.strftime("%I:%M %p")  # e.g., "02:30 PM"
        return None

    def get_formatted_datetime(self, obj):
        if obj.date and obj.slot:
            date_str = obj.date.strftime("%B %d, %Y")
            if isinstance(obj.slot, str):
                time_str = obj.slot
            else:
                time_str = obj.slot.strftime("%I:%M %p")
            return f"{date_str} at {time_str}"
        return None

    def get_can_cancel(self, obj):
        """
        Check if appointment can be cancelled
        """
        from datetime import date
        return obj.status == 'booked' and obj.date >= date.today()

    def get_can_update(self, obj):
        """
        Check if appointment can be updated
        """
        from datetime import date
        return obj.status == 'booked' and obj.date >= date.today()

    def get_visit_notes(self, obj):
        """
        Get all visit notes for this appointment
        """
        try:
            notes = obj.visitnote_set.all().order_by('-visit_date')
            return VisitNoteSerializer(notes, many=True, context=self.context).data
        except Exception:
            return []

    def validate(self, data):
        """
        Validate appointment data
        """
        from datetime import date
        from .utils import is_slot_available, validate_slot
        
        appointment_date = data.get('date')
        slot = data.get('slot')
        doctor = data.get('doctor')
        
        if appointment_date and appointment_date < date.today():
            raise serializers.ValidationError("Cannot book appointments in the past")
        
        # For updates, check if we're actually changing date/time
        if self.instance:
            if (appointment_date == self.instance.date and 
                slot == self.instance.slot and 
                doctor == self.instance.doctor):
                return data
        
        # Validate slot availability
        if appointment_date and slot and doctor:
            try:
                from .utils import validate_slot, is_slot_available
                validate_slot(str(slot), appointment_date)
                if not is_slot_available(doctor, appointment_date, str(slot)):
                    raise serializers.ValidationError("Selected time slot is not available")
            except Exception as e:
                raise serializers.ValidationError(f"Slot validation error: {str(e)}")
        
        return data

# -------------------------
# VISIT NOTE SERIALIZER
# -------------------------

class VisitNoteSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()
    patient_name = serializers.SerializerMethodField()
    appointment_details = serializers.SerializerMethodField()
    prescription_file_url = serializers.SerializerMethodField()
    formatted_visit_date = serializers.SerializerMethodField()

    class Meta:
        model = VisitNote
        fields = [
            'id', 'appointment', 'patient', 'patient_name', 
            'doctor', 'doctor_name', 'visit_date', 'formatted_visit_date',
            'notes', 'prescription', 'prescription_file_url', 'appointment_details'
        ]
        read_only_fields = ['id', 'visit_date']

    def get_doctor_name(self, obj):
        return obj.doctor.profile.user.get_full_name() or obj.doctor.profile.user.username

    def get_patient_name(self, obj):
        return obj.patient.profile.user.get_full_name() or obj.patient.profile.user.username

    def get_appointment_details(self, obj):
        if obj.appointment:
            return {
                'id': obj.appointment.id,
                'date': obj.appointment.date,
                'slot': obj.appointment.slot,
                'status': obj.appointment.status
            }
        return None

    def get_prescription_file_url(self, obj):
        if obj.prescription:
            request = self.context.get('request')
            if request and hasattr(obj.prescription, 'url'):
                return request.build_absolute_uri(obj.prescription.url)
            return obj.prescription.url if hasattr(obj.prescription, 'url') else str(obj.prescription)
        return None

    def get_formatted_visit_date(self, obj):
        if obj.visit_date:
            return obj.visit_date.strftime("%B %d, %Y at %I:%M %p")
        return None

# -------------------------
# DOCUMENT SERIALIZER
# -------------------------

class DocumentSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    patient_username = serializers.CharField(source='patient.profile.user.username', read_only=True)
    file_url = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()
    file_type = serializers.SerializerMethodField()
    
    # Related appointment info
    appointment_info = serializers.SerializerMethodField()
    doctor_name = serializers.SerializerMethodField()
    
    # Formatted fields
    formatted_upload_date = serializers.SerializerMethodField()
    doc_type_display = serializers.SerializerMethodField()
    
    # Permissions
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id', 'patient', 'patient_name', 'patient_username', 
            'appointment', 'appointment_info', 'doctor_name',
            'file', 'file_url', 'file_name', 'file_size', 'file_type',
            'doc_type', 'doc_type_display', 'description', 
            'uploaded_at', 'formatted_upload_date', 'can_delete'
        ]
        read_only_fields = ['id', 'uploaded_at']

    def get_patient_name(self, obj):
        return obj.patient.profile.user.get_full_name() or obj.patient.profile.user.username

    def get_file_url(self, obj):
        if obj.file:
            request = self.context.get('request')
            if request and hasattr(obj.file, 'url'):
                return request.build_absolute_uri(obj.file.url)
            return obj.file.url if hasattr(obj.file, 'url') else str(obj.file)
        return None

    def get_file_name(self, obj):
        if obj.file:
            return obj.file.name.split('/')[-1]
        return None

    def get_file_size(self, obj):
        if obj.file:
            try:
                return obj.file.size
            except (ValueError, OSError):
                return None
        return None

    def get_file_type(self, obj):
        if obj.file:
            try:
                file_name = obj.file.name
                return file_name.split('.')[-1].upper() if '.' in file_name else 'Unknown'
            except:
                return 'Unknown'
        return None

    def get_appointment_info(self, obj):
        if obj.appointment:
            return {
                'id': obj.appointment.id,
                'date': obj.appointment.date,
                'slot': obj.appointment.slot,
                'status': obj.appointment.status,
                'doctor_name': obj.appointment.doctor.profile.user.get_full_name() or obj.appointment.doctor.profile.user.username
            }
        return None

    def get_doctor_name(self, obj):
        if obj.appointment and obj.appointment.doctor:
            return obj.appointment.doctor.profile.user.get_full_name() or obj.appointment.doctor.profile.user.username
        return None

    def get_formatted_upload_date(self, obj):
        if obj.uploaded_at:
            return obj.uploaded_at.strftime("%B %d, %Y at %I:%M %p")
        return None

    def get_doc_type_display(self, obj):
        return obj.get_doc_type_display()

    def get_can_delete(self, obj):
        # Only the patient who uploaded can delete, or admin
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return (request.user == obj.patient.profile.user or 
                    request.user.is_staff or 
                    request.user.is_superuser)
        return False

    def validate_file(self, value):
        """
        Validate uploaded file
        """
        if not value:
            raise serializers.ValidationError("No file provided")
        
        # Check file size (limit to 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError("File size too large. Maximum size is 10MB.")
        
        # Check file extension
        allowed_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx', '.txt']
        file_extension = '.' + value.name.split('.')[-1].lower()
        if file_extension not in allowed_extensions:
            raise serializers.ValidationError(
                f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        return value

# -------------------------
# SPECIALIZED SERIALIZERS
# -------------------------

class DoctorStatsSerializer(serializers.ModelSerializer):
    """Serializer for doctor statistics"""
    name = serializers.SerializerMethodField()
    total_appointments = serializers.SerializerMethodField()
    today_appointments = serializers.SerializerMethodField()
    completed_appointments = serializers.SerializerMethodField()
    total_patients = serializers.SerializerMethodField()
    
    class Meta:
        model = Doctor
        fields = [
            'id', 'name', 'specialization', 
            'total_appointments', 'today_appointments', 
            'completed_appointments', 'total_patients'
        ]

    def get_name(self, obj):
        return obj.profile.user.get_full_name() or obj.profile.user.username

    def get_total_appointments(self, obj):
        return obj.appointment_set.count()

    def get_today_appointments(self, obj):
        from datetime import date
        return obj.appointment_set.filter(date=date.today()).count()

    def get_completed_appointments(self, obj):
        return obj.appointment_set.filter(status='completed').count()

    def get_total_patients(self, obj):
        return obj.appointment_set.values('patient').distinct().count()

class PatientStatsSerializer(serializers.ModelSerializer):
    """Serializer for patient statistics"""
    name = serializers.SerializerMethodField()
    total_appointments = serializers.SerializerMethodField()
    upcoming_appointments = serializers.SerializerMethodField()
    completed_appointments = serializers.SerializerMethodField()
    total_documents = serializers.SerializerMethodField()
    last_appointment = serializers.SerializerMethodField()
    
    class Meta:
        model = Patient
        fields = [
            'id', 'name', 'total_appointments', 'upcoming_appointments',
            'completed_appointments', 'total_documents', 'last_appointment'
        ]

    def get_name(self, obj):
        return obj.profile.user.get_full_name() or obj.profile.user.username

    def get_total_appointments(self, obj):
        return obj.appointment_set.count()

    def get_upcoming_appointments(self, obj):
        from datetime import date
        return obj.appointment_set.filter(date__gte=date.today()).count()

    def get_completed_appointments(self, obj):
        return obj.appointment_set.filter(status='completed').count()

    def get_total_documents(self, obj):
        return obj.document_set.count()

    def get_last_appointment(self, obj):
        from datetime import date
        last_appt = obj.appointment_set.filter(date__lt=date.today()).order_by('-date', '-slot').first()
        if last_appt:
            return {
                'date': last_appt.date,
                'doctor': last_appt.doctor.profile.user.get_full_name() or last_appt.doctor.profile.user.username,
                'status': last_appt.status
            }
        return None

# -------------------------
# SIMPLE SERIALIZERS (for dropdowns, etc.)
# -------------------------

class SimpleDoctorSerializer(serializers.ModelSerializer):
    """Simple serializer for doctor dropdowns"""
    name = serializers.SerializerMethodField()
    
    class Meta:
        model = Doctor
        fields = ['id', 'name', 'specialization']

    def get_name(self, obj):
        return obj.profile.user.get_full_name() or obj.profile.user.username

class SimplePatientSerializer(serializers.ModelSerializer):
    """Simple serializer for patient dropdowns"""
    name = serializers.SerializerMethodField()
    
    class Meta:
        model = Patient
        fields = ['id', 'name']

    def get_name(self, obj):
        return obj.profile.user.get_full_name() or obj.profile.user.username

class SimpleAppointmentSerializer(serializers.ModelSerializer):
    """Simple serializer for appointment dropdowns"""
    display_text = serializers.SerializerMethodField()
    
    class Meta:
        model = Appointment
        fields = ['id', 'date', 'slot', 'status', 'display_text']

    def get_display_text(self, obj):
        return f"{obj.date} {obj.slot} - {obj.status}"
