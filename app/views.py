from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, generics, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.authtoken.models import Token   # ✅ Added for token auth
from django.contrib.auth import authenticate        # ✅ Added for login
from .models import User, Appointment, Document, Doctor, Patient,VisitNote,Profile
from .serializers import AppointmentSerializer, DoctorSerializer, DocumentSerializer, UserSerializer
from datetime import datetime, time, timedelta
from groq import Groq
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils.timezone import now
from .models import Appointment, Doctor
from datetime import date
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Appointment, Document
from datetime import date
import os
from dotenv import load_dotenv
from rest_framework.decorators import api_view, permission_classes
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
# Hardcoded specializations
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
        username = request.data.get("username")
        password = request.data.get("password")
        email = request.data.get("email")
        role = request.data.get("role")  # doctor or patient

        if role not in ["doctor", "patient"]:
            return Response({"error": "Role must be 'doctor' or 'patient'."}, status=400)

        if role == "doctor":
            specializations = request.data.get("specialization", [])
            if not specializations:
                return Response({"error": "Specialization is required for doctors."}, status=400)

            # Ensure it’s a list
            if not isinstance(specializations, list):
                return Response({"error": "Specialization must be a list."}, status=400)

            # Validate against allowed list
            for sp in specializations:
                if sp not in SPECIALIZATION_CHOICES:
                    return Response({"error": f"Invalid specialization: {sp}"}, status=400)

            specializations_str = ", ".join(specializations)
        else:
            specializations_str = None  # Patients don’t need specialization

        # Create user
        user = User.objects.create_user(username=username, password=password, email=email)
        profile = Profile.objects.create(user=user, role=role)

        # Create related record
        if role == "doctor":
            Doctor.objects.create(profile=profile, specialization=specializations_str)
        else:
            Patient.objects.create(profile=profile)

        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            "message": "User registered successfully",
            "token": token.key,
            "role": role,
            "username": username
        }, status=201)


# Optional: API to fetch specializations
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
                "role": user.profile.role
            })
        return Response({"error": "Invalid credentials"}, status=400)


# ---------------------------
# DASHBOARDS
# ---------------------------
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from datetime import date
from .models import Appointment, Doctor

from datetime import date
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Appointment, Doctor

class DoctorDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Only doctors can access this view
        if request.user.profile.role != "doctor":
            return Response({"error": "Only doctors can access"}, status=403)

        today = date.today()
        
        try:
            # Get the logged-in doctor's profile
            doctor = Doctor.objects.get(profile=request.user.profile)
        except Doctor.DoesNotExist:
            return Response({"error": "Doctor profile not found"}, status=404)

        # Use 'slot' instead of 'time' for ordering
        appointments = Appointment.objects.filter(doctor=doctor).order_by("date", "slot")

        today_appts, upcoming, past = [], [], []

        for appt in appointments:
            # Safely get patient name
            patient_name = appt.patient.profile.user.username

            # Slot might already be a string like "09:30"
            slot_time = appt.slot if isinstance(appt.slot, str) else appt.slot.strftime("%H:%M")

            item = {
                "id": appt.id,
                "date": appt.date.strftime("%Y-%m-%d"),
                "time": slot_time, # keep frontend key 'time'
                "patient_name": patient_name,
                "status": appt.status,  # Add status field
                "reason": getattr(appt, "reason", ""), # in case 'reason' not required
                "prescription": getattr(appt, "prescription", "") or ""
            }

            if appt.date == today:
                today_appts.append(item)
            elif appt.date > today:
                upcoming.append(item)
            else:
                past.append(item)

        return Response({
            "doctor_name": request.user.username,
            "specialization": doctor.specialization,
            "today": today_appts,
            "upcoming": upcoming,
            "past": past
        })


from datetime import date
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Appointment, Patient


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
        
        # ✅ Start with Doctor queryset, not filtered by role
        queryset = Doctor.objects.select_related("profile__user").all()

        if specialization:
            # ✅ Handle both single specialization and comma-separated
            queryset = queryset.filter(specialization__icontains=specialization)
        
        if available:
            # ✅ Assuming you have an 'available' field in Doctor model
            # If not, remove this filter or add the field
            available_bool = available.lower() == "true"
            # queryset = queryset.filter(available=available_bool)

        # ✅ Return proper format expected by frontend
        doctors = []
        for doc in queryset:
            doctors.append({
                "id": doc.id,  # ✅ Use Doctor.id, not User.id
                "username": doc.profile.user.username,
                "specialization": doc.specialization
            })
        
        return Response(doctors)

# ---------------------------
# DOCUMENT UPLOAD
# ---------------------------
class DocumentUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.profile.role != "patient":
            return Response({"error": "Only patients can upload"}, status=403)
        
        # ✅ Get patient instance properly
        try:
            patient = Patient.objects.get(profile=request.user.profile)
        except Patient.DoesNotExist:
            return Response({"error": "Patient profile not found"}, status=404)
        
        # ✅ Handle file upload
        document_file = request.FILES.get("document")
        if not document_file:
            return Response({"error": "No document provided"}, status=400)
        
        # ✅ Create document record
        try:
            document = Document.objects.create(
                patient=patient,
                file=document_file,  # Changed from 'document' to 'file' to match the model
                doc_type=request.data.get('doc_type', 'other'),
                appointment_id=request.data.get('appointment_id') if request.data.get('appointment_id') else None
            )
            
            return Response({
                "id": document.id,
                "message": "Document uploaded successfully",
                "url": document.file.url if document.file else None,
                "doc_type": document.doc_type
            }, status=201)
        except Exception as e:
            return Response({"error": f"Upload failed: {str(e)}"}, status=500)


from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, generics, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.authtoken.models import Token   # ✅ Added for token auth
from django.contrib.auth import authenticate        # ✅ Added for login
from .models import User, Appointment, Document, Doctor, Patient,VisitNote,Profile
from .serializers import AppointmentSerializer, DoctorSerializer, DocumentSerializer, UserSerializer
from datetime import datetime, time, timedelta
from groq import Groq
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils.timezone import now
from .models import Appointment, Doctor
from datetime import date
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Appointment, Document
from datetime import date
import os
from dotenv import load_dotenv
from rest_framework.decorators import api_view, permission_classes
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
# Hardcoded specializations
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
        username = request.data.get("username")
        password = request.data.get("password")
        email = request.data.get("email")
        role = request.data.get("role")  # doctor or patient

        if role not in ["doctor", "patient"]:
            return Response({"error": "Role must be 'doctor' or 'patient'."}, status=400)

        if role == "doctor":
            specializations = request.data.get("specialization", [])
            if not specializations:
                return Response({"error": "Specialization is required for doctors."}, status=400)

            # Ensure it’s a list
            if not isinstance(specializations, list):
                return Response({"error": "Specialization must be a list."}, status=400)

            # Validate against allowed list
            for sp in specializations:
                if sp not in SPECIALIZATION_CHOICES:
                    return Response({"error": f"Invalid specialization: {sp}"}, status=400)

            specializations_str = ", ".join(specializations)
        else:
            specializations_str = None  # Patients don’t need specialization

        # Create user
        user = User.objects.create_user(username=username, password=password, email=email)
        profile = Profile.objects.create(user=user, role=role)

        # Create related record
        if role == "doctor":
            Doctor.objects.create(profile=profile, specialization=specializations_str)
        else:
            Patient.objects.create(profile=profile)

        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            "message": "User registered successfully",
            "token": token.key,
            "role": role,
            "username": username
        }, status=201)


# Optional: API to fetch specializations
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
                "role": user.profile.role
            })
        return Response({"error": "Invalid credentials"}, status=400)


# ---------------------------
# DASHBOARDS
# ---------------------------
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from datetime import date
from .models import Appointment, Doctor

from datetime import date
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Appointment, Doctor

class DoctorDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Only doctors can access this view
        if request.user.profile.role != "doctor":
            return Response({"error": "Only doctors can access"}, status=403)

        today = date.today()

        # Get the logged-in doctor's profile
        doctor = Doctor.objects.get(profile=request.user.profile)

        # Use 'slot' instead of 'time' for ordering
        appointments = Appointment.objects.filter(doctor=doctor).order_by("date", "slot")

        today_appts, upcoming, past = [], [], []

        for appt in appointments:
            # Safely get patient name
            patient_name = appt.patient.profile.user.username

            # Slot might already be a string like "09:30"
            slot_time = appt.slot if isinstance(appt.slot, str) else appt.slot.strftime("%H:%M")

            item = {
                "id": appt.id,
                "date": appt.date.strftime("%Y-%m-%d"),
                "time": slot_time,  # keep frontend key 'time'
                "patient_name": patient_name,
                "reason": getattr(appt, "reason", ""),  # in case 'reason' not required
                "prescription": getattr(appt, "prescription", "") or ""
            }

            if appt.date == today:
                today_appts.append(item)
            elif appt.date > today:
                upcoming.append(item)
            else:
                past.append(item)

        return Response({
            "doctor_name": request.user.username,
            "specialization": doctor.specialization,
            "today": today_appts,
            "upcoming": upcoming,
            "past": past
        })



from datetime import date
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Appointment, Patient


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
        
        # ✅ Start with Doctor queryset, not filtered by role
        queryset = Doctor.objects.select_related("profile__user").all()

        if specialization:
            # ✅ Handle both single specialization and comma-separated
            queryset = queryset.filter(specialization__icontains=specialization)
        
        if available:
            # ✅ Assuming you have an 'available' field in Doctor model
            # If not, remove this filter or add the field
            available_bool = available.lower() == "true"
            # queryset = queryset.filter(available=available_bool)

        # ✅ Return proper format expected by frontend
        doctors = []
        for doc in queryset:
            doctors.append({
                "id": doc.id,  # ✅ Use Doctor.id, not User.id
                "username": doc.profile.user.username,
                "specialization": doc.specialization
            })
        
        return Response(doctors)

# ---------------------------
# DOCUMENT UPLOAD
# ---------------------------
class DocumentUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.profile.role != "patient":
            return Response({"error": "Only patients can upload"}, status=403)
        
        # ✅ Get patient instance properly
        try:
            patient = Patient.objects.get(profile=request.user.profile)
        except Patient.DoesNotExist:
            return Response({"error": "Patient profile not found"}, status=404)
        
        # ✅ Handle file upload
        document_file = request.FILES.get("document")
        if not document_file:
            return Response({"error": "No document provided"}, status=400)
        
        # ✅ Create document record
        try:
            document = Document.objects.create(
                patient=patient,
                document=document_file,
                # Add other fields as needed based on your Document model
            )
            
            return Response({
                "id": document.id,
                "message": "Document uploaded successfully",
                "url": document.document.url if hasattr(document.document, 'url') else str(document.document)
            }, status=201)
        except Exception as e:
            return Response({"error": f"Upload failed: {str(e)}"}, status=500)


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



# ---------------------------
# APPOINTMENT CRUD (slot check)
# ---------------------------

class AvailableSlotsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        doctor_id = request.GET.get("doctor_id")
        date_str = request.GET.get("date")
        if not doctor_id or not date_str:
            return Response({"error": "doctor_id and date required"}, status=400)

        # ✅ Doctor, not User
        doctor = get_object_or_404(Doctor, id=doctor_id)

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Invalid date"}, status=400)

        # ✅ get_available_slots expects a Doctor instance
        available = get_available_slots(doctor, date)

        # ✅ return raw list for frontend
        return Response(available)



class AppointmentListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # List appointments based on user role
        if request.user.profile.role == "doctor":
            doctor = Doctor.objects.get(profile=request.user.profile)
            appts = Appointment.objects.filter(doctor=doctor).order_by("-date", "-slot")
        elif request.user.profile.role == "patient":
            patient = Patient.objects.get(profile=request.user.profile)
            appts = Appointment.objects.filter(patient=patient).order_by("-date", "-slot")
        else:
            # Admin can see all
            appts = Appointment.objects.all().order_by("-date", "-slot")
        
        serializer = AppointmentSerializer(appts, many=True)
        return Response(serializer.data)

    def post(self, request):
        # ✅ Only patients can book
        if request.user.profile.role != "patient":
            return Response({"error": "Only patients can book appointments"}, status=403)

        # ✅ Get patient instance
        try:
            patient_obj = Patient.objects.get(profile=request.user.profile)
        except Patient.DoesNotExist:
            return Response({"error": "Patient profile not found"}, status=404)

        # ✅ Extract data from request
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

        # ✅ Get Doctor instance
        try:
            doctor_obj = Doctor.objects.get(id=doctor_id)
        except Doctor.DoesNotExist:
            return Response({"error": f"Doctor with id {doctor_id} not found"}, status=404)

        # ✅ Validate date
        try:
            appointment_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=400)

        # ✅ Check if date is not in the past
        if appointment_date < date.today():
            return Response({"error": "Cannot book appointments in the past"}, status=400)

        # ✅ Check slot availability (now properly excludes cancelled appointments)
        available_slots = get_available_slots(doctor_obj, appointment_date)
        if slot_str not in available_slots:
            return Response({
                "error": "Slot not available",
                "available_slots": available_slots,
                "requested_slot": slot_str
            }, status=400)

        # ✅ Double-check: make sure no active booking exists for this slot
        existing_booking = Appointment.objects.filter(
            doctor=doctor_obj,
            date=appointment_date,
            slot=slot_str,
            status__in=['booked', 'confirmed']  # Only check active bookings
        ).exclude(status='cancelled').first()
        
        if existing_booking:
            return Response({
                "error": "Slot is already booked by another patient",
                "available_slots": available_slots
            }, status=400)

        # ✅ Create appointment
        try:
            appointment = Appointment.objects.create(
                doctor=doctor_obj,
                patient=patient_obj,
                date=appointment_date,
                slot=slot_str,
                status="booked"
            )
            
            serializer = AppointmentSerializer(appointment)
            return Response({
                "message": "Appointment booked successfully",
                "appointment": serializer.data
            }, status=201)
            
        except Exception as e:
            return Response({"error": f"Failed to create appointment: {str(e)}"}, status=500)
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Appointment

class AppointmentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            appointment = Appointment.objects.get(pk=pk)
        except Appointment.DoesNotExist:
            return Response({"error": "Appointment not found"}, status=404)

        # Only doctor who owns the appointment can update prescription
        if request.user.profile.role != "doctor" or appointment.doctor.profile != request.user.profile:
            return Response({"error": "Not authorized"}, status=403)

        prescription = request.data.get("prescription", "").strip()
        if not prescription:
            return Response({"error": "Prescription cannot be empty"}, status=400)

        appointment.prescription = prescription
        appointment.save()

        return Response({"message": "Prescription updated successfully"})


    def delete(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk)
        if request.user != appointment.doctor and request.user != appointment.patient:
            return Response({"error": "Not authorized"}, status=403)
        appointment.delete()
        return Response(status=204)

from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from .prompts import DOCTOR_SYSTEM_PROMPT, PATIENT_SYSTEM_PROMPT,HISTORY_SUMMARY_INSTRUCTION
# ---------------------------
# AI (GROQ)
# ---------------------------
_client = Groq(api_key=settings.GROQ_API_KEY)

# ---------------------------
# AI (GROQ) — helper
# ---------------------------
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

class HistorySummarizerView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.profile.role != "doctor":
            return Response({"error": "Only doctors can summarize"}, status=403)

        try:
            Doctor.objects.get(profile__user=request.user)
        except Doctor.DoesNotExist:
            return Response({"error": "Doctor profile not found"}, status=404)

        raw = request.data.get("raw_history", "")
        if not raw.strip():
            return Response({"error": "raw_history required"}, status=400)

        messages = [
            {"role": "system", "content": DOCTOR_SYSTEM_PROMPT},
            {"role": "user", "content": f"{HISTORY_SUMMARY_INSTRUCTION}\n\n{raw}"},
        ]
        try:
            summary = groq_chat(messages, temperature=0.1, max_tokens=500)
            return Response({"summary": summary})
        except Exception as e:
            return Response({"error": str(e)}, status=502)
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

        # Fetch appointments with related doctor and visit notes
        appointments = Appointment.objects.filter(patient=patient).select_related(
            "doctor", "doctor__profile__user"
        ).prefetch_related("visitnote_set").order_by("date", "slot")

        upcoming, past = [], []

        for appt in appointments:
            doctor_name = appt.doctor.profile.user.username
            slot_time = appt.slot if isinstance(appt.slot, str) else appt.slot.strftime("%H:%M")

            # ✅ FIXED: Get prescription from VisitNote properly
            prescription_value = ""
            try:
                # Get the latest visit note for this appointment
                visit_note = appt.visitnote_set.order_by('-visit_date').first()
                if visit_note:
                    # If prescription is a file field, get the URL
                    if visit_note.prescription:
                        if hasattr(visit_note.prescription, 'url'):
                            prescription_value = visit_note.prescription.url
                        else:
                            prescription_value = str(visit_note.prescription)
                    
                    # If no prescription file but has notes, use notes
                    if not prescription_value and visit_note.notes:
                        prescription_value = visit_note.notes
                        
            except Exception as e:
                print(f"Error getting prescription for appointment {appt.id}: {e}")

            # Fallback to appointment prescription field
            if not prescription_value:
                prescription_value = getattr(appt, "prescription", "") or ""

            item = {
                "id": appt.id,
                "date": appt.date.strftime("%Y-%m-%d"),
                "time": slot_time,
                "doctor_name": doctor_name,
                "status": getattr(appt, "status", "booked"),
                "prescription": prescription_value  # This should now show the prescription
            }

            if appt.date >= today:
                upcoming.append(item)
            else:
                past.append(item)

        patient_name = request.user.get_full_name() or request.user.username

        return Response({
            "patient_name": patient_name,
            "upcoming": upcoming,
            "past": past
        })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, patient__profile=request.user.profile)
    appointment.status = "cancelled"
    appointment.save()
    return Response({"success": True, "message": "Appointment cancelled"})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_appointment(request, appointment_id):
    """
    ✅ ENHANCED: Update appointment with proper slot availability checking
    """
    appointment = get_object_or_404(Appointment, id=appointment_id, patient__profile=request.user.profile)

    # Don't allow updating cancelled appointments
    if appointment.status == 'cancelled':
        return Response({"error": "Cannot update a cancelled appointment"}, status=400)

    doctor_id = request.data.get("doctor_id")
    date_str = request.data.get("date")
    slot_time = request.data.get("slot")
    document = request.FILES.get("document", None)

    if doctor_id:
        doctor = get_object_or_404(Doctor, id=doctor_id)
        appointment.doctor = doctor
    if date_str:
        appointment.date = datetime.strptime(date_str, "%Y-%m-%d").date()
    if slot_time:
        appointment.slot = slot_time
    if document:
        appointment.document = document

    # ✅ Prevent booking if slot is already taken by ACTIVE bookings
    if Appointment.objects.filter(
        doctor=appointment.doctor,
        date=appointment.date,
        slot=appointment.slot,
        status__in=['booked', 'confirmed']  # Only check active bookings
    ).exclude(id=appointment.id).exclude(status='cancelled').exists():
        return Response({"error": "Slot already booked"}, status=400)

    appointment.save()
    return Response({"success": True, "message": "Appointment updated"})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_doctors_by_specialization(request):
    specialization = request.query_params.get("specialization")
    if not specialization:
        return Response({"error": "Specialization required"}, status=400)
    doctors = Doctor.objects.filter(specialization=specialization).values("id", "profile__user__username")
    return Response(list(doctors))

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def view_prescription(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, patient__profile=request.user.profile)
    return Response({"prescription": appointment.prescription if appointment.prescription else ""})



# ---------------------------
# APPOINTMENT CRUD (slot check)
# ---------------------------


class AvailableSlotsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        doctor_id = request.GET.get("doctor_id")
        date_str = request.GET.get("date")
        if not doctor_id or not date_str:
            return Response({"error": "doctor_id and date required"}, status=400)

        # ✅ Doctor, not User
        doctor = get_object_or_404(Doctor, id=doctor_id)

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Invalid date"}, status=400)

        # ✅ get_available_slots now properly excludes cancelled appointments
        available = get_available_slots(doctor, date)

        # ✅ return raw list for frontend
        return Response(available)


class AppointmentListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        # List appointments based on user role
        if request.user.profile.role == "doctor":
            doctor = Doctor.objects.get(profile=request.user.profile)
            appts = Appointment.objects.filter(doctor=doctor).order_by("-date", "-slot")
        elif request.user.profile.role == "patient":
            patient = Patient.objects.get(profile=request.user.profile)
            appts = Appointment.objects.filter(patient=patient).order_by("-date", "-slot")
        else:
            # Admin can see all
            appts = Appointment.objects.all().order_by("-date", "-slot")
        
        serializer = AppointmentSerializer(appts, many=True)
        return Response(serializer.data)

    def post(self, request):
        # ✅ Only patients can book
        if request.user.profile.role != "patient":
            return Response({"error": "Only patients can book appointments"}, status=403)

        # ✅ Get patient instance
        try:
            patient_obj = Patient.objects.get(profile=request.user.profile)
        except Patient.DoesNotExist:
            return Response({"error": "Patient profile not found"}, status=404)

        # ✅ Extract data from request
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

        # ✅ Get Doctor instance
        try:
            doctor_obj = Doctor.objects.get(id=doctor_id)
        except Doctor.DoesNotExist:
            return Response({"error": f"Doctor with id {doctor_id} not found"}, status=404)

        # ✅ Validate date
        try:
            appointment_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=400)

        # ✅ Check if date is not in the past
        if appointment_date < date.today():
            return Response({"error": "Cannot book appointments in the past"}, status=400)

        # ✅ Check slot availability
        available_slots = get_available_slots(doctor_obj, appointment_date)
        if slot_str not in available_slots:
            return Response({
                "error": "Slot not available",
                "available_slots": available_slots
            }, status=400)

        # ✅ Create appointment
        try:
            appointment = Appointment.objects.create(
                doctor=doctor_obj,
                patient=patient_obj,
                date=appointment_date,
                slot=slot_str,
                status="booked"
            )
            
            serializer = AppointmentSerializer(appointment)
            return Response({
                "message": "Appointment booked successfully",
                "appointment": serializer.data
            }, status=201)
            
        except Exception as e:
            return Response({"error": f"Failed to create appointment: {str(e)}"}, status=500)

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Appointment

class AppointmentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            appointment = Appointment.objects.get(pk=pk)
        except Appointment.DoesNotExist:
            return Response({"error": "Appointment not found"}, status=404)

        # Only doctor who owns the appointment can update prescription
        if request.user.profile.role != "doctor" or appointment.doctor.profile != request.user.profile:
            return Response({"error": "Not authorized"}, status=403)

        prescription = request.data.get("prescription", "").strip()
        if not prescription:
            return Response({"error": "Prescription cannot be empty"}, status=400)

        appointment.prescription = prescription
        appointment.save()

        return Response({"message": "Prescription updated successfully"})


    def delete(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk)
        if request.user != appointment.doctor and request.user != appointment.patient:
            return Response({"error": "Not authorized"}, status=403)
        appointment.delete()
        return Response(status=204)

from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from .prompts import DOCTOR_SYSTEM_PROMPT, PATIENT_SYSTEM_PROMPT,HISTORY_SUMMARY_INSTRUCTION
# ---------------------------
# AI (GROQ)
# ---------------------------
_client = Groq(api_key=settings.GROQ_API_KEY)

# ---------------------------
# AI (GROQ) — helper
# ---------------------------
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

class HistorySummarizerView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.profile.role != "doctor":
            return Response({"error": "Only doctors can summarize"}, status=403)

        try:
            Doctor.objects.get(profile__user=request.user)
        except Doctor.DoesNotExist:
            return Response({"error": "Doctor profile not found"}, status=404)

        raw = request.data.get("raw_history", "")
        if not raw.strip():
            return Response({"error": "raw_history required"}, status=400)

        messages = [
            {"role": "system", "content": DOCTOR_SYSTEM_PROMPT},
            {"role": "user", "content": f"{HISTORY_SUMMARY_INSTRUCTION}\n\n{raw}"},
        ]
        try:
            summary = groq_chat(messages, temperature=0.1, max_tokens=500)
            return Response({"summary": summary})
        except Exception as e:
            return Response({"error": str(e)}, status=502)
class PatientDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.profile.role != "patient":
            return Response({"error": "Only patients can access"}, status=403)

        today = date.today()
        patient = Patient.objects.get(profile=request.user.profile)

        # Fetch appointments
        appointments = Appointment.objects.filter(patient=patient).select_related("doctor").order_by("date", "slot")

        upcoming, past = [], []
        for appt in appointments:
            doctor_name = appt.doctor.profile.user.username
            slot_time = appt.slot if isinstance(appt.slot, str) else appt.slot.strftime("%H:%M")
            
            # ✅ Handle prescription properly - could be URL or text
            prescription_value = getattr(appt, "prescription", "") or ""
            
            item = {
                "id": appt.id,
                "date": appt.date.strftime("%Y-%m-%d"),
                "time": slot_time,
                "doctor_name": doctor_name,
                "status": getattr(appt, "status", "booked"),  # Default status
                "prescription": prescription_value
            }
            
            if appt.date >= today:
                upcoming.append(item)
            else:
                past.append(item)

        return Response({
            "patient_name": request.user.username,
            "upcoming": upcoming,
            "past": past
        })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_appointment(request, appointment_id):
    """
    ✅ ENHANCED: Cancel appointment and make slot available
    """
    try:
        appointment = get_object_or_404(
            Appointment, 
            id=appointment_id, 
            patient__profile=request.user.profile
        )
        
        # Check if appointment is already cancelled
        if appointment.status == 'cancelled':
            return Response({
                "success": False, 
                "message": "Appointment is already cancelled"
            }, status=400)
        
        # Update status to cancelled instead of deleting
        appointment.status = "cancelled"
        appointment.save()
        
        return Response({
            "success": True, 
            "message": "Appointment cancelled successfully. The slot is now available for booking.",
            "appointment_id": appointment_id,
            "freed_slot": {
                "doctor_id": appointment.doctor.id,
                "date": appointment.date.strftime("%Y-%m-%d"),
                "time": appointment.slot if isinstance(appointment.slot, str) else appointment.slot.strftime("%H:%M")
            }
        })
        
    except Appointment.DoesNotExist:
        return Response({
            "success": False, 
            "message": "Appointment not found"
        }, status=404)
    except Exception as e:
        return Response({
            "success": False, 
            "message": f"Error cancelling appointment: {str(e)}"
        }, status=500)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_appointment(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, patient__profile=request.user.profile)

    doctor_id = request.data.get("doctor_id")
    date_str = request.data.get("date")
    slot_time = request.data.get("slot")
    document = request.FILES.get("document", None)

    if doctor_id:
        doctor = get_object_or_404(Doctor, id=doctor_id)
        appointment.doctor = doctor
    if date_str:
        appointment.date = datetime.strptime(date_str, "%Y-%m-%d").date()
    if slot_time:
        appointment.slot = slot_time
    if document:
        appointment.document = document

    # Prevent booking if slot is already taken
    if Appointment.objects.filter(
        doctor=appointment.doctor,
        date=appointment.date,
        slot=appointment.slot,
        status="booked"
    ).exclude(id=appointment.id).exists():
        return Response({"error": "Slot already booked"}, status=400)

    appointment.save()
    return Response({"success": True, "message": "Appointment updated"})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_doctors_by_specialization(request):
    specialization = request.query_params.get("specialization")
    if not specialization:
        return Response({"error": "Specialization required"}, status=400)
    doctors = Doctor.objects.filter(specialization=specialization).values("id", "profile__user__username")
    return Response(list(doctors))

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def view_prescription(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id, patient__profile=request.user.profile)
    return Response({"prescription": appointment.prescription if appointment.prescription else ""})

class DoctorPatientDetailView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, username):
        # Only doctors can access this view
        if request.user.profile.role != "doctor":
            return Response({"error": "Only doctors can access"}, status=403)
        
        try:
            # Get the doctor
            doctor = Doctor.objects.get(profile=request.user.profile)
            
            # Get patient by username
            patient_user = User.objects.get(username=username)
            patient = Patient.objects.get(profile__user=patient_user)
            
            # Get appointment history between this doctor and patient
            appointments = Appointment.objects.filter(
                doctor=doctor, 
                patient=patient
            ).order_by('-date', '-slot')
            
            appointment_history = []
            for appt in appointments:
                # Get visit notes for this appointment
                try:
                    visit_note = VisitNote.objects.get(appointment=appt)
                    prescription_file = visit_note.prescription.url if visit_note.prescription else None
                    notes = visit_note.notes
                except VisitNote.DoesNotExist:
                    prescription_file = None
                    notes = ""
                
                appointment_history.append({
                    "id": appt.id,
                    "date": appt.date.strftime("%Y-%m-%d"),
                    "time": appt.slot if isinstance(appt.slot, str) else appt.slot.strftime("%H:%M"),
                    "status": appt.status,
                    "notes": notes,
                    "prescription_file": prescription_file,
                    "prescription_text": getattr(appt, 'prescription', '') or ""
                })
            
            # Get all documents uploaded by this patient
            documents = Document.objects.filter(patient=patient).order_by('-uploaded_at')
            document_list = []
            for doc in documents:
                document_list.append({
                    "id": doc.id,
                    "file_url": doc.file.url,
                    "doc_type": doc.get_doc_type_display(),
                    "uploaded_at": doc.uploaded_at.strftime("%Y-%m-%d %H:%M"),
                    "appointment_id": doc.appointment.id if doc.appointment else None
                })
            
            # Get patient basic info
            patient_info = {
                "username": patient_user.username,
                "full_name": patient_user.get_full_name() or patient_user.username,
                "email": patient_user.email,
                "phone": patient.profile.phone,
                "dob": patient.profile.dob.strftime("%Y-%m-%d") if patient.profile.dob else None,
                "gender": patient.profile.gender
            }
            
            return Response({
                "patient_info": patient_info,
                "appointment_history": appointment_history,
                "documents": document_list,
                "doctor_name": doctor.profile.user.username
            })
            
        except User.DoesNotExist:
            return Response({"error": "Patient not found"}, status=404)
        except Patient.DoesNotExist:
            return Response({"error": "Patient profile not found"}, status=404)
        except Doctor.DoesNotExist:
            return Response({"error": "Doctor profile not found"}, status=404)

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
                    'notes': notes
                }
            )
            
            if not created:
                visit_note.notes = notes
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
            
            # Get patient
            patient_user = User.objects.get(username=patient_username)
            patient = Patient.objects.get(profile__user=patient_user)
            
            # Get all appointments and visit notes for this patient with this doctor
            appointments = Appointment.objects.filter(
                doctor=doctor, 
                patient=patient
            ).order_by('date', 'slot')
            
            # Compile medical history
            history_text = f"Medical History Summary for Patient: {patient_username}\n\n"
            
            for appt in appointments:
                history_text += f"Date: {appt.date}, Time: {appt.slot}\n"
                history_text += f"Status: {appt.status}\n"
                
                # Get visit notes
                try:
                    visit_note = VisitNote.objects.get(appointment=appt)
                    if visit_note.notes:
                        history_text += f"Notes: {visit_note.notes}\n"
                except VisitNote.DoesNotExist:
                    pass
                
                # Get prescription
                if hasattr(appt, 'prescription') and appt.prescription:
                    history_text += f"Prescription: {appt.prescription}\n"
                
                history_text += "\n" + "-"*50 + "\n\n"
            
            # Use AI to summarize
            messages = [
                {"role": "system", "content": DOCTOR_SYSTEM_PROMPT},
                {"role": "user", "content": f"Please provide a comprehensive medical summary of this patient's history:\n\n{history_text}"}
            ]
            
            summary = groq_chat(messages, temperature=0.1, max_tokens=800)
            
            return Response({
                "patient_username": patient_username,
                "summary": summary,
                "raw_history": history_text
            })
            
        except User.DoesNotExist:
            return Response({"error": "Patient not found"}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)

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
                    'notes': notes
                }
            )
            
            if not created:
                visit_note.notes = notes
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

# Add this view to your views.py
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_patient_documents(request, username):
    """Get all documents for a specific patient by username"""
    if request.user.profile.role != "doctor":
        return Response({"error": "Only doctors can access patient documents"}, status=403)
    
    try:
        # Get patient by username
        patient_user = User.objects.get(username=username)
        patient = Patient.objects.get(profile__user=patient_user)
        
        # Get all documents for this patient
        documents = Document.objects.filter(patient=patient).order_by('-uploaded_at')
        
        document_list = []
        for doc in documents:
            document_list.append({
                "id": doc.id,
                "file_url": doc.file.url if doc.file else None,
                "doc_type": doc.get_doc_type_display(),
                "uploaded_at": doc.uploaded_at.strftime("%Y-%m-%d %H:%M"),
                "appointment_id": doc.appointment.id if doc.appointment else None
            })
        
        return Response(document_list)
        
    except User.DoesNotExist:
        return Response({"error": "Patient not found"}, status=404)
    except Patient.DoesNotExist:
        return Response({"error": "Patient profile not found"}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=500)
