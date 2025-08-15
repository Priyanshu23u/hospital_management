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
class SignupView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        email = request.data.get("email")
        role = request.data.get("role")  # "doctor" or "patient"

        if role not in ["doctor", "patient"]:
            return Response({"error": "Role must be 'doctor' or 'patient'."}, status=400)

        # Create user
        user = User.objects.create_user(username=username, password=password, email=email)

        # Create profile
        profile = Profile.objects.create(user=user, role=role)

        # Create doctor or patient record
        if role == "doctor":
            Doctor.objects.create(profile=profile, specialization=request.data.get("specialization", "General"))
        else:
            Patient.objects.create(profile=profile)

        # Create token for authentication
        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            "message": "User registered successfully",
            "token": token.key,
            "role": role
        }, status=201)

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
class DoctorDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.profile.role != "doctor":
            return Response({"error": "Only doctors can access this"}, status=403)

        try:
            doctor_obj = Doctor.objects.get(profile__user=request.user)
        except Doctor.DoesNotExist:
            return Response({"error": "Doctor profile not found"}, status=404)

        appointments = Appointment.objects.filter(
            doctor=doctor_obj
        ).order_by("-date", "-slot")

        serializer = AppointmentSerializer(appointments, many=True)
        return Response(serializer.data)



class PatientDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.profile.role != "patient":
            return Response({"error": "Only patients can access this"}, status=403)

        try:
            patient_obj = Patient.objects.get(profile__user=request.user)
        except Patient.DoesNotExist:
            return Response({"error": "Patient profile not found"}, status=404)

        appointments = Appointment.objects.filter(
            patient=patient_obj
        ).order_by("-date", "-slot")

        serializer = AppointmentSerializer(appointments, many=True)
        return Response(serializer.data)



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
        queryset = Doctor.objects.filter(profile__role="doctor")

        if specialization:
            queryset = queryset.filter(specialization__icontains=specialization)
        if available:
            queryset = queryset.filter(available=available.lower() == "true")
        serializer = DoctorSerializer(queryset, many=True)
        return Response(serializer.data)


# ---------------------------
# DOCUMENT UPLOAD
# ---------------------------
class DocumentUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.profile.role != "patient":
            return Response({"error": "Only patients can upload"}, status=403)
        data = request.data.copy()
        data["patient"] = request.user.id
        serializer = DocumentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


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
    appointments = Appointment.objects.filter(doctor=doctor, date=date)
    return [a.slot.strftime("%H:%M") for a in appointments]


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
        doctor = get_object_or_404(User, id=doctor_id, profile__role="doctor")
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({"error": "Invalid date"}, status=400)
        available = get_available_slots(doctor, date)
        return Response({"available_slots": available})


class AppointmentListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        appointments = Appointment.objects.all()
        serializer = AppointmentSerializer(appointments, many=True)
        return Response(serializer.data)

    def post(self, request):
        if request.user.profile.role != "patient":
            return Response({"error": "Only patients can book"}, status=403)
        doctor_id = request.data.get("doctor")
        date_str = request.data.get("date")
        slot_str = request.data.get("slot")
        doctor = get_object_or_404(User, id=doctor_id, profile__role="doctor")
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        if slot_str not in get_available_slots(doctor, date):
            return Response({"error": "Slot not available"}, status=400)
        data = request.data.copy()
        data["patient"] = request.user.id
        serializer = AppointmentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


class AppointmentDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk)
        serializer = AppointmentSerializer(appointment)
        return Response(serializer.data)

    def put(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk)
        if request.user != appointment.doctor and request.user != appointment.patient:
            return Response({"error": "Not authorized"}, status=403)
        # Slot validation if changing date/slot
        new_slot = request.data.get("slot")
        new_date = request.data.get("date")
        if new_slot and new_date:
            doctor = appointment.doctor
            date = datetime.strptime(new_date, "%Y-%m-%d").date()
            if new_slot not in get_available_slots(doctor, date):
                return Response({"error": "Slot not available"}, status=400)
        serializer = AppointmentSerializer(appointment, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

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


User = get_user_model()

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def chat_with_ai(request):
    """
    Role-aware chatbot for both Doctor and Patient using Groq.
    Expects: { "messages": [ {role, content}, ... ] }
    Returns: { "reply": str }
    """
    try:
        messages = request.data.get("messages", [])
        if not isinstance(messages, list) or not messages:
            return Response({"detail": "Provide 'messages' as a non-empty list."}, status=400)

        # Detect role
        user = request.user
        if Doctor.objects.filter(profile__user=user).exists():
            system_prompt = DOCTOR_SYSTEM_PROMPT
        elif Patient.objects.filter(profile__user=user).exists():
            system_prompt = PATIENT_SYSTEM_PROMPT
        else:
            system_prompt = "You are a helpful assistant."
        # Prepend system prompt
        full_messages = [{"role": "system", "content": system_prompt}] + messages

        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=full_messages,
            temperature=0.6,
            max_tokens=600,
        )

        # ✅ FIX: Access .content instead of ["content"]
        reply = completion.choices[0].message.content
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

        # Securely detect role from Profile
        role = request.user.profile.role.lower()
        user_obj = None

        if role == "doctor":
            try:
                user_obj = Doctor.objects.get(profile__user=request.user)
            except Doctor.DoesNotExist:
                return Response({"error": "Doctor profile not found"}, status=404)
            system_prompt = DOCTOR_SYSTEM_PROMPT

        elif role == "patient":
            try:
                user_obj = Patient.objects.get(profile__user=request.user)
            except Patient.DoesNotExist:
                return Response({"error": "Patient profile not found"}, status=404)
            system_prompt = PATIENT_SYSTEM_PROMPT

        else:
            return Response({"error": "Invalid role"}, status=400)

        # Build AI message list
        messages = [{"role": "system", "content": system_prompt}] + history + [
            {"role": "user", "content": message}
        ]

        try:
            answer = chat_with_ai(messages)
            return Response({
                "role": role,
                "user": str(user_obj),
                "message": message,
                "answer": answer
            })
        except Exception as e:
            return Response({"error": str(e)}, status=502)

class HistorySummarizerView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # Ensure only doctors can access
        if request.user.profile.role != "doctor":
            return Response({"error": "Only doctors can summarize"}, status=403)

        # Fetch the doctor object safely
        try:
            doctor = Doctor.objects.get(profile__user=request.user)
        except Doctor.DoesNotExist:
            return Response({"error": "Doctor profile not found"}, status=404)

        # Get raw history text from request
        raw = request.data.get("raw_history", "")
        if not raw.strip():
            return Response({"error": "raw_history required"}, status=400)

        # Prepare messages for AI summarization
        messages = [
            {"role": "system", "content": DOCTOR_SYSTEM_PROMPT},  # Your base doctor system prompt
            {
                "role": "user",
                "content": f"{HISTORY_SUMMARY_INSTRUCTION}\n\n{raw}"
            },
        ]

        # Call Groq AI
        try:
            summary = chat_with_ai(messages, temperature=0.1)
            return Response({
                "doctor": str(doctor),  # Include doctor info for context if needed
                "summary": summary
            })
        except Exception as e:
            return Response({"error": str(e)}, status=502)
