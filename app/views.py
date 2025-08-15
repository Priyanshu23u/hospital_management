from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, generics, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .models import User, Appointment, Document, Doctor, Patient, VisitNote, Profile
from .serializers import (
    AppointmentSerializer, DoctorSerializer, DocumentSerializer, 
    UserSerializer, ProfileSerializer, PatientSerializer, VisitNoteSerializer
)
from django.contrib.auth import get_user_model
from datetime import datetime, time, timedelta, date
from groq import Groq
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.utils.timezone import now
import os
from dotenv import load_dotenv
from .prompts import DOCTOR_SYSTEM_PROMPT, PATIENT_SYSTEM_PROMPT, HISTORY_SUMMARY_INSTRUCTION
from .ai_groq import chat_with_groq
from django.db import IntegrityError

load_dotenv()

# -----------------------------
# Permissions
# -----------------------------

class IsDoctor(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.profile.role == "doctor"

class IsPatient(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.profile.role == "patient"

# -----------------------------
# Pagination
# -----------------------------

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100

# ---------------------------
# AUTHENTICATION
# ---------------------------

from django.db import transaction
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import permissions
from django.db import IntegrityError

SPECIALIZATION_CHOICES = [
    "General",
    "Cardiology", 
    "Dermatology",
    "Orthopedics",
    "Pediatrics",
    "Neurology",
    "Psychiatry",
    "Gynecology",
    "Urology",
    "Oncology",
    "Endocrinology",
    "Gastroenterology",
    "Pulmonology"
]

class SignupView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get("username", "").strip()
        password = request.data.get("password", "").strip()
        email = request.data.get("email", "").strip().lower()
        role = request.data.get("role", "").strip()

        # Basic validation
        if not username or not password or not email or not role:
            return Response({"error": "All fields are required."}, status=400)

        if role not in ["doctor", "patient"]:
            return Response({"error": "Role must be 'doctor' or 'patient'."}, status=400)

        # Check for existing users
        if User.objects.filter(username__iexact=username).exists():
            return Response({"error": "Username already exists."}, status=400)
        
        if User.objects.filter(email__iexact=email).exists():
            return Response({"error": "Email already exists."}, status=400)

        # Handle doctor specialization
        if role == "doctor":
            specializations = request.data.get("specialization", [])
            if not specializations:
                return Response({"error": "Specialization is required for doctors."}, status=400)

            if not isinstance(specializations, list):
                return Response({"error": "Specialization must be a list."}, status=400)

            for sp in specializations:
                if sp not in SPECIALIZATION_CHOICES:
                    return Response({"error": f"Invalid specialization: {sp}"}, status=400)

            specializations_str = ", ".join(specializations)
        else:
            specializations_str = None

        try:
            with transaction.atomic():
                # Create user
                user = User.objects.create_user(
                    username=username, 
                    password=password, 
                    email=email
                )
                
                # Create profile using get_or_create to avoid duplicates
                profile, created = Profile.objects.get_or_create(
                    user=user,
                    defaults={'role': role}
                )
                
                # If profile already existed, update the role
                if not created:
                    profile.role = role
                    profile.save()

                # Create role-specific models
                if role == "doctor":
                    Doctor.objects.get_or_create(
                        profile=profile,
                        defaults={'specialization': specializations_str}
                    )
                else:
                    Patient.objects.get_or_create(profile=profile)

                # Create authentication token
                token, _ = Token.objects.get_or_create(user=user)

                return Response({
                    "message": "User registered successfully",
                    "token": token.key,
                    "role": profile.role,
                    "username": user.username
                }, status=201)
            
        except IntegrityError as e:
            return Response({"error": "Username or email already exists."}, status=400)
        except Exception as e:
            return Response({"error": f"Registration failed: {str(e)}"}, status=500)

class SpecializationListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(SPECIALIZATION_CHOICES)

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                "token": token.key,
                "role": user.profile.role,
                "username": user.username
            })
        return Response({"error": "Invalid credentials"}, status=400)

# ---------------------------
# DASHBOARDS
# ---------------------------

class DoctorDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.profile.role != "doctor":
            return Response({"error": "Only doctors can access"}, status=403)

        today = date.today()

        try:
            doctor = Doctor.objects.get(profile=request.user.profile)
        except Doctor.DoesNotExist:
            return Response({"error": "Doctor profile not found"}, status=404)

        appointments = Appointment.objects.filter(doctor=doctor).order_by("date", "slot")

        today_appts, upcoming, past = [], [], []

        for appt in appointments:
            patient_name = appt.patient.profile.user.get_full_name() or appt.patient.profile.user.username
            slot_time = appt.slot if isinstance(appt.slot, str) else appt.slot.strftime("%H:%M")

            # Get prescription from visit note or appointment
            prescription = ""
            try:
                visit_note = VisitNote.objects.filter(appointment=appt).first()
                if visit_note and visit_note.notes:
                    prescription = visit_note.notes
                elif appt.prescription:
                    prescription = appt.prescription
            except:
                pass

            item = {
                "id": appt.id,
                "date": appt.date.strftime("%Y-%m-%d"),
                "time": slot_time,
                "patient_name": patient_name,
                "status": appt.status,
                "prescription": prescription
            }

            if appt.date == today:
                today_appts.append(item)
            elif appt.date > today:
                upcoming.append(item)
            else:
                past.append(item)

        return Response({
            "doctor_name": request.user.get_full_name() or request.user.username,
            "specialization": doctor.specialization,
            "today": today_appts,
            "upcoming": upcoming,
            "past": past
        })

class PatientDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.profile.role != "patient":
            return Response({"error": "Only patients can access"}, status=403)

        today = date.today()
        
        try:
            patient = Patient.objects.get(profile=request.user.profile)
        except Patient.DoesNotExist:
            return Response({"error": "Patient profile not found"}, status=404)

        appointments = Appointment.objects.filter(patient=patient).order_by("date", "slot")
        
        today_appts, upcoming, past = [], [], []

        for appt in appointments:
            doctor_name = appt.doctor.profile.user.get_full_name() or appt.doctor.profile.user.username
            slot_time = appt.slot if isinstance(appt.slot, str) else appt.slot.strftime("%H:%M")
            
            # Get prescription from visit note or appointment
            prescription = ""
            try:
                visit_note = VisitNote.objects.filter(appointment=appt).first()
                if visit_note and visit_note.notes:
                    prescription = visit_note.notes
                elif appt.prescription:
                    prescription = appt.prescription
            except:
                pass

            item = {
                "id": appt.id,
                "date": appt.date.strftime("%Y-%m-%d"),
                "time": slot_time,
                "doctor_name": doctor_name,
                "specialization": appt.doctor.specialization,
                "status": appt.status,
                "prescription": prescription
            }

            if appt.date == today:
                today_appts.append(item)
            elif appt.date > today:
                upcoming.append(item)
            else:
                past.append(item)

        # Get documents
        documents = Document.objects.filter(patient=patient).order_by('-uploaded_at')
        documents_data = DocumentSerializer(documents, many=True, context={'request': request}).data

        return Response({
            "patient_name": request.user.get_full_name() or request.user.username,
            "today": today_appts,
            "upcoming": upcoming,
            "past": past,
            "documents": documents_data
        })

# ---------------------------
# CRUD for DOCTORS / PATIENTS
# ---------------------------

class UserListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        role = request.query_params.get("role")
        if role:
            queryset = User.objects.filter(profile__role=role)
        else:
            queryset = User.objects.all()
        serializer = UserSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(UserSerializer(user).data, status=201)
        return Response(serializer.errors, status=400)

class UserDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        serializer = UserSerializer(user)
        return Response(serializer.data)

    def put(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        user.delete()
        return Response(status=204)

# ---------------------------
# DOCTOR SEARCH
# ---------------------------

class DoctorListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        specialization = request.query_params.get("specialization")
        available = request.query_params.get("available")

        queryset = Doctor.objects.select_related("profile__user").all()

        if specialization:
            queryset = queryset.filter(specialization__icontains=specialization)

        if available:
            available_bool = available.lower() == "true"
            queryset = queryset.filter(available=available_bool)

        doctors = []
        for doc in queryset:
            doctors.append({
                "id": doc.id,
                "username": doc.profile.user.username,
                "name": doc.profile.user.get_full_name() or doc.profile.user.username,
                "specialization": doc.specialization
            })

        return Response(doctors)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_doctors_by_specialization(request):
    specialization = request.GET.get('specialization')
    if specialization:
        doctors = Doctor.objects.filter(specialization__icontains=specialization)
        serializer = DoctorSerializer(doctors, many=True)
        return Response(serializer.data)
    return Response([])

# ---------------------------
# DOCUMENT MANAGEMENT
# ---------------------------

class DocumentUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.profile.role != "patient":
            return Response({"error": "Only patients can upload documents"}, status=403)

        try:
            patient = Patient.objects.get(profile=request.user.profile)
        except Patient.DoesNotExist:
            return Response({"error": "Patient profile not found"}, status=404)

        document_file = request.FILES.get("document")
        if not document_file:
            return Response({"error": "No document provided"}, status=400)

        doc_type = request.data.get('doc_type', 'other')
        description = request.data.get('description', '')
        appointment_id = request.data.get('appointment_id')

        appointment = None
        if appointment_id:
            try:
                appointment = Appointment.objects.get(id=appointment_id, patient=patient)
            except Appointment.DoesNotExist:
                return Response({"error": "Invalid appointment"}, status=400)

        try:
            document = Document.objects.create(
                patient=patient,
                file=document_file,
                doc_type=doc_type,
                description=description,
                appointment=appointment
            )

            serializer = DocumentSerializer(document, context={'request': request})
            return Response({
                "message": "Document uploaded successfully",
                "document": serializer.data
            }, status=201)

        except Exception as e:
            return Response({"error": f"Upload failed: {str(e)}"}, status=500)

    def get(self, request):
        """Get all documents for the current user"""
        if request.user.profile.role == "patient":
            try:
                patient = Patient.objects.get(profile=request.user.profile)
                documents = Document.objects.filter(patient=patient).order_by('-uploaded_at')
            except Patient.DoesNotExist:
                return Response({"error": "Patient profile not found"}, status=404)
        
        elif request.user.profile.role == "doctor":
            try:
                doctor = Doctor.objects.get(profile=request.user.profile)
                patient_ids = Appointment.objects.filter(doctor=doctor).values_list('patient_id', flat=True).distinct()
                documents = Document.objects.filter(patient_id__in=patient_ids).order_by('-uploaded_at')
            except Doctor.DoesNotExist:
                return Response({"error": "Doctor profile not found"}, status=404)
        else:
            return Response({"error": "Invalid user role"}, status=403)

        serializer = DocumentSerializer(documents, many=True, context={'request': request})
        return Response(serializer.data)

class PatientDocumentsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, patient_id=None):
        """Get documents for a specific patient"""
        
        if request.user.profile.role == "doctor":
            try:
                doctor = Doctor.objects.get(profile=request.user.profile)
                if patient_id:
                    patient = Patient.objects.get(id=patient_id)
                    appointments = Appointment.objects.filter(doctor=doctor, patient=patient)
                    if not appointments.exists():
                        return Response({"error": "You haven't treated this patient"}, status=403)
                    documents = Document.objects.filter(patient=patient).order_by('-uploaded_at')
                else:
                    patient_ids = Appointment.objects.filter(doctor=doctor).values_list('patient_id', flat=True).distinct()
                    documents = Document.objects.filter(patient_id__in=patient_ids).order_by('-uploaded_at')
            except (Doctor.DoesNotExist, Patient.DoesNotExist):
                return Response({"error": "Profile not found"}, status=404)
        
        elif request.user.profile.role == "patient":
            try:
                patient = Patient.objects.get(profile=request.user.profile)
                documents = Document.objects.filter(patient=patient).order_by('-uploaded_at')
            except Patient.DoesNotExist:
                return Response({"error": "Patient profile not found"}, status=404)
        else:
            return Response({"error": "Invalid user role"}, status=403)

        serializer = DocumentSerializer(documents, many=True, context={'request': request})
        return Response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_patient_documents(request, username):
    """Get all documents for a specific patient by username"""
    if request.user.profile.role != "doctor":
        return Response({"error": "Only doctors can access patient documents"}, status=403)

    try:
        patient_user = User.objects.get(username=username)
        patient = Patient.objects.get(profile__user=patient_user)
        
        doctor = Doctor.objects.get(profile=request.user.profile)
        appointments = Appointment.objects.filter(doctor=doctor, patient=patient)
        if not appointments.exists():
            return Response({"error": "You haven't treated this patient"}, status=403)

        documents = Document.objects.filter(patient=patient).order_by('-uploaded_at')
        
        document_list = []
        for doc in documents:
            document_list.append({
                "id": doc.id,
                "file_url": doc.file.url if doc.file else None,
                "file_name": doc.file.name.split('/')[-1] if doc.file else None,
                "doc_type": doc.get_doc_type_display(),
                "description": doc.description or "",
                "uploaded_at": doc.uploaded_at.strftime("%Y-%m-%d %H:%M"),
                "appointment_id": doc.appointment.id if doc.appointment else None,
                "doctor_name": doc.appointment.doctor.profile.user.get_full_name() if doc.appointment else None
            })

        return Response({
            "patient_name": patient.profile.user.get_full_name() or patient.profile.user.username,
            "documents": document_list
        })

    except User.DoesNotExist:
        return Response({"error": "Patient not found"}, status=404)
    except (Patient.DoesNotExist, Doctor.DoesNotExist):
        return Response({"error": "Profile not found"}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

# ---------------------------
# SLOT UTILS
# ---------------------------

def generate_daily_slots():
    slots = []
    start = time(10, 0)
    end = time(18, 0)
    current = datetime.combine(datetime.today(), start)
    end_dt = datetime.combine(datetime.today(), end)
    lunch_start = time(13, 0)
    lunch_end = time(14, 0)

    while current < end_dt:
        slot_time = current.time()
        if not (lunch_start <= slot_time < lunch_end):
            slots.append(slot_time.strftime("%H:%M"))
        current += timedelta(minutes=30)
    return slots

def get_booked_slots(doctor, date):
    appointments = Appointment.objects.filter(
        doctor=doctor,
        date=date
    ).exclude(status='cancelled')
    return [a.slot.strftime("%H:%M") if hasattr(a.slot, 'strftime') else str(a.slot) for a in appointments]

def get_available_slots(doctor, date):
    all_slots = generate_daily_slots()
    booked = get_booked_slots(doctor, date)
    return [s for s in all_slots if s not in booked]

# ---------------------------
# APPOINTMENT CRUD
# ---------------------------

class AvailableSlotsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        doctor_id = request.GET.get("doctor_id")
        date_str = request.GET.get("date")

        if not doctor_id or not date_str:
            return Response({"error": "doctor_id and date required"}, status=400)

        doctor = get_object_or_404(Doctor, id=doctor_id)

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Invalid date"}, status=400)

        available = get_available_slots(doctor, date)
        return Response(available)

class AppointmentListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.profile.role == "doctor":
            doctor = Doctor.objects.get(profile=request.user.profile)
            appts = Appointment.objects.filter(doctor=doctor).order_by("-date", "-slot")
        elif request.user.profile.role == "patient":
            patient = Patient.objects.get(profile=request.user.profile)
            appts = Appointment.objects.filter(patient=patient).order_by("-date", "-slot")
        else:
            appts = Appointment.objects.all().order_by("-date", "-slot")

        serializer = AppointmentSerializer(appts, many=True, context={'request': request})
        return Response(serializer.data)

    def post(self, request):
        if request.user.profile.role != "patient":
            return Response({"error": "Only patients can book appointments"}, status=403)

        try:
            patient_obj = Patient.objects.get(profile=request.user.profile)
        except Patient.DoesNotExist:
            return Response({"error": "Patient profile not found"}, status=404)

        doctor_id = request.data.get("doctor_id") or request.data.get("doctor")
        date_str = request.data.get("date")
        slot_str = request.data.get("slot") or request.data.get("time")

        if not all([doctor_id, date_str, slot_str]):
            return Response({
                "error": "doctor_id, date and time/slot are required",
                "received": {
                    "doctor_id": doctor_id,
                    "date": date_str,
                    "slot": slot_str
                }
            }, status=400)

        try:
            doctor_obj = Doctor.objects.get(id=doctor_id)
        except Doctor.DoesNotExist:
            return Response({"error": f"Doctor with id {doctor_id} not found"}, status=404)

        try:
            appointment_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=400)

        if appointment_date < date.today():
            return Response({"error": "Cannot book appointments in the past"}, status=400)

        available_slots = get_available_slots(doctor_obj, appointment_date)
        if slot_str not in available_slots:
            return Response({
                "error": "Slot not available",
                "available_slots": available_slots,
                "requested_slot": slot_str
            }, status=400)

        existing_booking = Appointment.objects.filter(
            doctor=doctor_obj,
            date=appointment_date,
            slot=slot_str,
            status__in=['booked', 'confirmed']
        ).exclude(status='cancelled').first()

        if existing_booking:
            return Response({
                "error": "Slot is already booked by another patient",
                "available_slots": available_slots
            }, status=400)

        try:
            appointment = Appointment.objects.create(
                doctor=doctor_obj,
                patient=patient_obj,
                date=appointment_date,
                slot=slot_str,
                status="booked"
            )

            serializer = AppointmentSerializer(appointment, context={'request': request})
            return Response({
                "message": "Appointment booked successfully",
                "appointment": serializer.data
            }, status=201)

        except Exception as e:
            return Response({"error": f"Failed to create appointment: {str(e)}"}, status=500)

class AppointmentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            appointment = Appointment.objects.get(pk=pk)
            
            # Check if user has permission to view this appointment
            if (request.user.profile.role == "patient" and appointment.patient.profile.user != request.user) or \
               (request.user.profile.role == "doctor" and appointment.doctor.profile.user != request.user):
                return Response({"error": "Not authorized"}, status=403)
            
            serializer = AppointmentSerializer(appointment, context={'request': request})
            return Response(serializer.data)
        except Appointment.DoesNotExist:
            return Response({"error": "Appointment not found"}, status=404)

    def patch(self, request, pk):
        try:
            appointment = Appointment.objects.get(pk=pk)
        except Appointment.DoesNotExist:
            return Response({"error": "Appointment not found"}, status=404)

        # Only allow updates by the patient who booked it or the assigned doctor
        if request.user.profile.role == "patient":
            if appointment.patient.profile.user != request.user:
                return Response({"error": "Not authorized"}, status=403)
        elif request.user.profile.role == "doctor":
            if appointment.doctor.profile.user != request.user:
                return Response({"error": "Not authorized"}, status=403)
        else:
            return Response({"error": "Not authorized"}, status=403)

        # Handle different update types
        if 'prescription' in request.data:
            prescription = request.data.get("prescription", "").strip()
            if not prescription:
                return Response({"error": "Prescription cannot be empty"}, status=400)
            appointment.prescription = prescription
            appointment.save()
            return Response({"message": "Prescription updated successfully"})

        # Handle status updates
        if 'status' in request.data:
            new_status = request.data.get('status')
            if new_status in ['completed', 'cancelled']:
                appointment.status = new_status
                appointment.save()
                return Response({"message": f"Appointment status updated to {new_status}"})

        # Handle appointment rescheduling
        if 'date' in request.data or 'slot' in request.data:
            new_date = request.data.get('date')
            new_slot = request.data.get('slot')
            new_doctor_id = request.data.get('doctor_id')

            if new_date:
                try:
                    appointment_date = datetime.strptime(new_date, "%Y-%m-%d").date()
                except ValueError:
                    return Response({"error": "Invalid date format"}, status=400)
                appointment.date = appointment_date

            if new_slot:
                appointment.slot = new_slot

            if new_doctor_id:
                try:
                    new_doctor = Doctor.objects.get(id=new_doctor_id)
                    appointment.doctor = new_doctor
                except Doctor.DoesNotExist:
                    return Response({"error": "Doctor not found"}, status=404)

            appointment.save()
            serializer = AppointmentSerializer(appointment, context={'request': request})
            return Response({
                "message": "Appointment updated successfully",
                "appointment": serializer.data
            })

        return Response({"error": "No valid update data provided"}, status=400)

    def delete(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk)
        
        # Check authorization
        if request.user.profile.role == "patient":
            if appointment.patient.profile.user != request.user:
                return Response({"error": "Not authorized"}, status=403)
        elif request.user.profile.role == "doctor":
            if appointment.doctor.profile.user != request.user:
                return Response({"error": "Not authorized"}, status=403)
        else:
            return Response({"error": "Not authorized"}, status=403)
        
        appointment.delete()
        return Response({"message": "Appointment deleted successfully"}, status=204)

# ---------------------------
# APPOINTMENT MANAGEMENT FUNCTIONS
# ---------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_appointment(request, pk):
    try:
        appointment = Appointment.objects.get(pk=pk)
        
        # Check if user can cancel this appointment
        if request.user.profile.role == "patient":
            if appointment.patient.profile.user != request.user:
                return Response({"error": "Not authorized"}, status=403)
        elif request.user.profile.role == "doctor":
            if appointment.doctor.profile.user != request.user:
                return Response({"error": "Not authorized"}, status=403)
        else:
            return Response({"error": "Not authorized"}, status=403)

        appointment.status = 'cancelled'
        appointment.save()
        
        return Response({"message": "Appointment cancelled successfully"})
    except Appointment.DoesNotExist:
        return Response({"error": "Appointment not found"}, status=404)

@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_appointment(request, pk):
    try:
        appointment = Appointment.objects.get(pk=pk)
        
        # Check authorization
        if request.user.profile.role == "patient":
            if appointment.patient.profile.user != request.user:
                return Response({"error": "Not authorized"}, status=403)
        else:
            return Response({"error": "Only patients can update appointments"}, status=403)

        # Update appointment fields
        new_date = request.data.get('date')
        new_slot = request.data.get('slot')
        new_doctor_id = request.data.get('doctor_id')

        if new_date:
            try:
                appointment_date = datetime.strptime(new_date, "%Y-%m-%d").date()
                if appointment_date < date.today():
                    return Response({"error": "Cannot schedule appointments in the past"}, status=400)
                appointment.date = appointment_date
            except ValueError:
                return Response({"error": "Invalid date format"}, status=400)

        if new_slot:
            appointment.slot = new_slot

        if new_doctor_id:
            try:
                new_doctor = Doctor.objects.get(id=new_doctor_id)
                appointment.doctor = new_doctor
            except Doctor.DoesNotExist:
                return Response({"error": "Doctor not found"}, status=404)

        appointment.save()
        serializer = AppointmentSerializer(appointment, context={'request': request})
        return Response({
            "message": "Appointment updated successfully",
            "appointment": serializer.data
        })

    except Appointment.DoesNotExist:
        return Response({"error": "Appointment not found"}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def view_prescription(request, pk):
    try:
        appointment = Appointment.objects.get(pk=pk)
        
        # Check authorization
        if request.user.profile.role == "patient":
            if appointment.patient.profile.user != request.user:
                return Response({"error": "Not authorized"}, status=403)
        elif request.user.profile.role == "doctor":
            if appointment.doctor.profile.user != request.user:
                return Response({"error": "Not authorized"}, status=403)
        else:
            return Response({"error": "Not authorized"}, status=403)

        # Get prescription from visit note or appointment
        prescription = ""
        try:
            visit_note = VisitNote.objects.filter(appointment=appointment).first()
            if visit_note and visit_note.notes:
                prescription = visit_note.notes
            elif appointment.prescription:
                prescription = appointment.prescription
        except:
            pass

        return Response({
            "appointment_id": appointment.id,
            "prescription": prescription,
            "date": appointment.date,
            "time": appointment.slot
        })

    except Appointment.DoesNotExist:
        return Response({"error": "Appointment not found"}, status=404)

# ---------------------------
# DOCTOR PATIENT DETAIL VIEW
# ---------------------------

class DoctorPatientDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, username):
        if request.user.profile.role != "doctor":
            return Response({"error": "Only doctors can access"}, status=403)

        try:
            doctor = Doctor.objects.get(profile=request.user.profile)
            patient_user = User.objects.get(username=username)
            patient = Patient.objects.get(profile__user=patient_user)

            # Get appointments between this doctor and patient
            appointments = Appointment.objects.filter(
                doctor=doctor,
                patient=patient
            ).order_by('-date', '-slot')

            if not appointments.exists():
                return Response({"error": "No appointments found with this patient"}, status=404)

            appointment_data = []
            for apt in appointments:
                # Get prescription
                prescription = ""
                try:
                    visit_note = VisitNote.objects.filter(appointment=apt).first()
                    if visit_note and visit_note.notes:
                        prescription = visit_note.notes
                    elif apt.prescription:
                        prescription = apt.prescription
                except:
                    pass

                appointment_data.append({
                    "id": apt.id,
                    "date": apt.date,
                    "time": apt.slot,
                    "status": apt.status,
                    "prescription": prescription
                })

            return Response({
                "patient_username": username,
                "patient_name": patient.profile.user.get_full_name() or username,
                "appointments": appointment_data
            })

        except User.DoesNotExist:
            return Response({"error": "Patient not found"}, status=404)
        except (Doctor.DoesNotExist, Patient.DoesNotExist):
            return Response({"error": "Profile not found"}, status=404)

# ---------------------------
# PRESCRIPTION MANAGEMENT
# ---------------------------

class SavePrescriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.profile.role != "doctor":
            return Response({"error": "Only doctors can save prescriptions"}, status=403)

        try:
            doctor = Doctor.objects.get(profile=request.user.profile)
            appointment_id = request.data.get("appointment_id")
            prescription_text = request.data.get("prescription", "").strip()
            notes = request.data.get("notes", "").strip()

            if not appointment_id:
                return Response({"error": "Appointment ID is required"}, status=400)

            appointment = Appointment.objects.get(id=appointment_id, doctor=doctor)

            # Update or create visit note
            visit_note, created = VisitNote.objects.get_or_create(
                appointment=appointment,
                defaults={
                    'patient': appointment.patient,
                    'doctor': doctor,
                    'notes': notes or prescription_text
                }
            )

            if not created:
                visit_note.notes = notes or prescription_text
                visit_note.save()

            # Also update appointment prescription field for backward compatibility
            if prescription_text:
                appointment.prescription = prescription_text
                appointment.save()

            return Response({
                "message": "Prescription saved successfully",
                "appointment_id": appointment_id
            })

        except Appointment.DoesNotExist:
            return Response({"error": "Appointment not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

# ---------------------------
# AI FEATURES
# ---------------------------

class PatientHistorySummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.profile.role != "doctor":
            return Response({"error": "Only doctors can access"}, status=403)

        try:
            doctor = Doctor.objects.get(profile=request.user.profile)
            patient_username = request.data.get("patient_username")

            if not patient_username:
                return Response({"error": "Patient username is required"}, status=400)

            patient_user = User.objects.get(username=patient_username)
            patient = Patient.objects.get(profile__user=patient_user)

            appointments = Appointment.objects.filter(
                doctor=doctor,
                patient=patient
            ).order_by('date', 'slot')

            history_text = f"Medical History Summary for Patient: {patient_username}\n\n"
            for appt in appointments:
                history_text += f"Date: {appt.date}, Time: {appt.slot}\n"
                history_text += f"Status: {appt.status}\n"

                try:
                    visit_note = VisitNote.objects.get(appointment=appt)
                    if visit_note.notes:
                        history_text += f"Notes: {visit_note.notes}\n"
                except VisitNote.DoesNotExist:
                    pass

                if hasattr(appt, 'prescription') and appt.prescription:
                    history_text += f"Prescription: {appt.prescription}\n"

                history_text += "\n" + "-"*50 + "\n\n"

            messages = [
                {"role": "system", "content": DOCTOR_SYSTEM_PROMPT},
                {"role": "user", "content": f"Please provide a comprehensive medical summary of this patient's history:\n\n{history_text}"}
            ]

            summary = chat_with_groq(messages, temperature=0.1)

            return Response({
                "patient_username": patient_username,
                "summary": summary,
                "raw_history": history_text
            })

        except User.DoesNotExist:
            return Response({"error": "Patient not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

class ChatbotView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_message = request.data.get("message", "").strip()
        if not user_message:
            return Response({"error": "Message is required"}, status=400)

        # Determine system prompt based on user role
        if request.user.profile.role == "doctor":
            system_prompt = DOCTOR_SYSTEM_PROMPT
        else:
            system_prompt = PATIENT_SYSTEM_PROMPT

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            response = chat_with_groq(messages, temperature=0.3)
            return Response({
                "response": response,
                "role": request.user.profile.role
            })
        except Exception as e:
            return Response({"error": f"AI service error: {str(e)}"}, status=500)

class HistorySummarizerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        history_text = request.data.get("history", "").strip()
        if not history_text:
            return Response({"error": "History text is required"}, status=400)

        messages = [
            {"role": "system", "content": DOCTOR_SYSTEM_PROMPT},
            {"role": "user", "content": f"{HISTORY_SUMMARY_INSTRUCTION}\n\n{history_text}"}
        ]

        try:
            summary = chat_with_groq(messages, temperature=0.1)
            return Response({"summary": summary})
        except Exception as e:
            return Response({"error": f"AI service error: {str(e)}"}, status=500)
def groq_chat(messages, temperature=0.6, max_tokens=600):
    """
    Low-level helper to call Groq with a list of {role, content} messages.
    Returns the assistant's reply (string).
    """
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    completion = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return completion.choices[0].message.content


User = get_user_model()

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def chat_with_ai(request):
    try:
        messages = request.data.get("messages", [])
        if not isinstance(messages, list) or not messages:
            return Response({"detail": "Provide 'messages' as a non-empty list."}, status=400)

        user = request.user
        if Doctor.objects.filter(profile__user=user).exists():
            system_prompt = DOCTOR_SYSTEM_PROMPT
        elif Patient.objects.filter(profile__user=user).exists():
            system_prompt = PATIENT_SYSTEM_PROMPT
        else:
            system_prompt = "You are a helpful assistant."

        full_messages = [{"role": "system", "content": system_prompt}] + messages
        reply = groq_chat(full_messages, temperature=0.6, max_tokens=600)
        return Response({"reply": reply})
    except Exception as e:
        return Response({"detail": str(e)}, status=500)

class ChatbotView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        message = request.data.get("message", "").strip()
        history = request.data.get("history", [])

        if not message:
            return Response({"error": "Message is required"}, status=400)

        role = request.user.profile.role.lower()

        if role == "doctor":
            try:
                Doctor.objects.get(profile__user=request.user)
            except Doctor.DoesNotExist:
                return Response({"error": "Doctor profile not found"}, status=404)
            system_prompt = DOCTOR_SYSTEM_PROMPT

        elif role == "patient":
            try:
                Patient.objects.get(profile__user=request.user)
            except Patient.DoesNotExist:
                return Response({"error": "Patient profile not found"}, status=404)
            system_prompt = PATIENT_SYSTEM_PROMPT
        else:
            return Response({"error": "Invalid role"}, status=400)

        messages = [{"role": "system", "content": system_prompt}] + history + [
            {"role": "user", "content": message}
        ]

        try:
            answer = groq_chat(messages, temperature=0.6, max_tokens=600)
            return Response({
                "role": role,
                "message": message,
                "answer": answer
            })
        except Exception as e:
            return Response({"error": str(e)}, status=502)

# Add this to your existing views.py

class PatientPrescriptionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get all prescriptions for the current patient"""
        if request.user.profile.role != "patient":
            return Response({"error": "Only patients can access"}, status=403)

        try:
            patient = Patient.objects.get(profile=request.user.profile)
            
            # Get all appointments with prescriptions
            appointments = Appointment.objects.filter(
                patient=patient
            ).exclude(prescription__isnull=True).exclude(prescription__exact='')
            
            # Get all visit notes with prescriptions
            visit_notes = VisitNote.objects.filter(patient=patient)
            
            prescriptions = []
            
            # Add appointment prescriptions
            for apt in appointments:
                if apt.prescription:
                    prescriptions.append({
                        'id': f'apt_{apt.id}',
                        'type': 'prescription',
                        'content': apt.prescription,
                        'date': apt.date,
                        'doctor_name': apt.doctor.profile.user.get_full_name() or apt.doctor.profile.user.username,
                        'appointment_id': apt.id,
                        'created_at': apt.created_at
                    })
            
            # Add visit note prescriptions
            for note in visit_notes:
                if note.notes:
                    prescriptions.append({
                        'id': f'note_{note.id}',
                        'type': 'visit_note',
                        'content': note.notes,
                        'date': note.appointment.date if note.appointment else None,
                        'doctor_name': note.doctor.profile.user.get_full_name() or note.doctor.profile.user.username,
                        'appointment_id': note.appointment.id if note.appointment else None,
                        'created_at': note.visit_date
                    })
                    
                if note.prescription:  # File prescription
                    prescriptions.append({
                        'id': f'file_{note.id}',
                        'type': 'prescription_file',
                        'file_url': note.prescription.url if note.prescription else None,
                        'date': note.appointment.date if note.appointment else None,
                        'doctor_name': note.doctor.profile.user.get_full_name() or note.doctor.profile.user.username,
                        'appointment_id': note.appointment.id if note.appointment else None,
                        'created_at': note.visit_date
                    })
            
            # Sort by date (newest first)
            prescriptions.sort(key=lambda x: x['created_at'], reverse=True)
            
            return Response({
                'prescriptions': prescriptions,
                'total_count': len(prescriptions)
            })
            
        except Patient.DoesNotExist:
            return Response({"error": "Patient profile not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

# Update the existing PatientDashboardView to include prescriptions
class PatientDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.profile.role != "patient":
            return Response({"error": "Only patients can access"}, status=403)

        today = date.today()
        
        try:
            patient = Patient.objects.get(profile=request.user.profile)
        except Patient.DoesNotExist:
            return Response({"error": "Patient profile not found"}, status=404)

        appointments = Appointment.objects.filter(patient=patient).order_by("date", "slot")
        
        today_appts, upcoming, past = [], [], []

        for appt in appointments:
            doctor_name = appt.doctor.profile.user.get_full_name() or appt.doctor.profile.user.username
            slot_time = appt.slot if isinstance(appt.slot, str) else appt.slot.strftime("%H:%M")
            
            # Get prescription from visit note or appointment
            prescription = ""
            try:
                visit_note = VisitNote.objects.filter(appointment=appt).first()
                if visit_note and visit_note.notes:
                    prescription = visit_note.notes
                elif appt.prescription:
                    prescription = appt.prescription
            except:
                pass

            item = {
                "id": appt.id,
                "date": appt.date.strftime("%Y-%m-%d"),
                "time": slot_time,
                "doctor_name": doctor_name,
                "specialization": appt.doctor.specialization,
                "status": appt.status,
                "prescription": prescription
            }

            if appt.date == today:
                today_appts.append(item)
            elif appt.date > today:
                upcoming.append(item)
            else:
                past.append(item)

        # Get documents
        documents = Document.objects.filter(patient=patient).order_by('-uploaded_at')
        documents_data = DocumentSerializer(documents, many=True, context={'request': request}).data

        # Get prescriptions separately
        prescriptions_view = PatientPrescriptionsView()
        prescriptions_response = prescriptions_view.get(request)
        prescriptions_data = prescriptions_response.data.get('prescriptions', []) if prescriptions_response.status_code == 200 else []

        return Response({
            "patient_name": request.user.get_full_name() or request.user.username,
            "today": today_appts,
            "upcoming": upcoming,
            "past": past,
            "documents": documents_data,
            "prescriptions": prescriptions_data  # Add prescriptions to response
        })
