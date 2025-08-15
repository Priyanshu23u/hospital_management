# app/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Profile, Doctor, Patient, Appointment, VisitNote, Document


# -------------------------
# USER & PROFILE SERIALIZERS
# -------------------------
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'password']
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = Profile
        fields = ['id', 'user', 'role', 'dob', 'gender', 'phone']

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user = UserSerializer.create(UserSerializer(), validated_data=user_data)
        profile = Profile.objects.create(user=user, **validated_data)
        return profile


# -------------------------
# DOCTOR & PATIENT SERIALIZERS
# -------------------------
class DoctorSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='profile.user.get_full_name', read_only=True)
    email = serializers.EmailField(source='profile.user.email', read_only=True)
    phone = serializers.CharField(source='profile.phone', read_only=True)
    role = serializers.CharField(source='profile.role', read_only=True)

    class Meta:
        model = Doctor
        fields = ['id', 'name', 'email', 'phone', 'role', 'specialization', 'bio', 'available']


class PatientSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='profile.user.get_full_name', read_only=True)
    email = serializers.EmailField(source='profile.user.email', read_only=True)
    phone = serializers.CharField(source='profile.phone', read_only=True)
    role = serializers.CharField(source='profile.role', read_only=True)

    class Meta:
        model = Patient
        fields = ['id', 'name', 'email', 'phone', 'role']


# -------------------------
# APPOINTMENT SERIALIZER
# -------------------------
# app/serializers.py
class AppointmentSerializer(serializers.ModelSerializer):
    doctor_name  = serializers.CharField(
        source='doctor.profile.user.get_full_name', read_only=True)
    patient_name = serializers.CharField(
        source='patient.profile.user.get_full_name', read_only=True)
    specialization = serializers.CharField(
        source='doctor.specialization', read_only=True)

    # NEW → surface the prescription
    prescription = serializers.SerializerMethodField()

    class Meta:
        model  = Appointment
        fields = [
            'id', 'patient', 'patient_name',
            'doctor', 'doctor_name', 'specialization',
            'date', 'slot', 'status', 'created_at',
            'prescription',                  # ← include it
        ]
        read_only_fields = ['id', 'status', 'created_at']

def get_prescription(self, obj):
    """
    Return the prescription text/URL from the related VisitNote.
    """
    try:
        # Get the latest visit note for this appointment
        latest_note = obj.visitnote_set.order_by('-visit_date').first()
        if latest_note:
            if latest_note.prescription:
                # If it's a file field, return URL
                if hasattr(latest_note.prescription, 'url'):
                    return latest_note.prescription.url
                else:
                    return str(latest_note.prescription)
            # Return notes if no prescription file
            return latest_note.notes if latest_note.notes else None
        return None
    except Exception:
        return None


# -------------------------
# VISIT NOTE SERIALIZER
# -------------------------
class VisitNoteSerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(source='doctor.profile.user.get_full_name', read_only=True)
    patient_name = serializers.CharField(source='patient.profile.user.get_full_name', read_only=True)

    class Meta:
        model = VisitNote
        fields = ['id', 'appointment', 'patient', 'patient_name', 'doctor', 'doctor_name', 'visit_date', 'notes', 'prescription']
        read_only_fields = ['id', 'visit_date']


# -------------------------
# DOCUMENT SERIALIZER
# -------------------------
class DocumentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(
        source='patient.profile.user.get_full_name', read_only=True)
    file_url = serializers.SerializerMethodField()          # NEW

    class Meta:
        model  = Document
        fields = ['id', 'patient', 'patient_name',
                  'file', 'file_url', 'doc_type', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and hasattr(obj.file, 'url'):
            return request.build_absolute_uri(obj.file.url) if request else obj.file.url
        return None

