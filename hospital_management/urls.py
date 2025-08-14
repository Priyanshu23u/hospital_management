from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, generics, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework.authtoken.models import Token   # ✅ Added for token auth
from django.contrib.auth import authenticate        # ✅ Added for login
from .models import User, Appointment, Document
from .serializers import AppointmentSerializer, DoctorSerializer, DocumentSerializer, UserSerializer
from datetime import datetime, time, timedelta
from groq import Groq
from .prompts import PATIENT_SYSTEM, DOCTOR_SYSTEM, HISTORY_SUMMARY_INSTRUCTION

# -----------------------------
# Permissions
# -----------------------------
class IsDoctor(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "doctor"

class IsPatient(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "patient"

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
        role = request.data.get("role", "").lower()
        if role not in ("patient", "doctor"):
            return Response({"error": "Role must be 'patient' or 'doctor'"}, status=400)

        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            return Response(
                {"message": "Signup successful", "token": token.key}, status=201
            )
        return Response(serializer.errors, status=400)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)
        if user:
            token, _ = Token.objects.get_or_create(user=user)
            return Response({"token": token.key, "role": user.role})
        return Response({"error": "Invalid credentials"}, status=400)


# ---------------------------
# DASHBOARDS
# ---------------------------
class DoctorDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role != "doctor":
            return Response({"error": "Only doctors can access this"}, status=403)
        appointments = Appointment.objects.filter(
            doctor=request.user
        ).order_by("-date", "-slot")
        serializer = AppointmentSerializer(appointments, many=True)
        return Response(serializer.data)


class PatientDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role != "patient":
            return Response({"error": "Only patients can access this"}, status=403)
        appointments = Appointment.objects.filter(
            patient=request.user
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
            queryset = User.objects.filter(role=role)
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
        queryset = User.objects.filter(role="doctor")
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
        if request.user.role != "patient":
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
        doctor = get_object_or_404(User, id=doctor_id, role="doctor")
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
        if request.user.role != "patient":
            return Response({"error": "Only patients can book"}, status=403)
        doctor_id = request.data.get("doctor")
        date_str = request.data.get("date")
        slot_str = request.data.get("slot")
        doctor = get_object_or_404(User, id=doctor_id, role="doctor")
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


# ---------------------------
# AI (GROQ)
# ---------------------------
_client = Groq(api_key=settings.GROQ_API_KEY)


def chat_with_groq(messages, model=None, temperature=0.2):
    model = model or settings.GROQ_MODEL
    resp = _client.chat.completions.create(
        model=model, messages=messages, temperature=temperature
    )
    return resp.choices[0].message.content


class ChatbotView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        role = request.data.get("role", "").lower()
        message = request.data.get("message")
        history = request.data.get("history", [])
        if role not in ("patient", "doctor") or not message:
            return Response({"error": "role and message required"}, status=400)
        system_prompt = PATIENT_SYSTEM if role == "patient" else DOCTOR_SYSTEM
        messages = [{"role": "system", "content": system_prompt}] + history + [
            {"role": "user", "content": message}
        ]
        try:
            answer = chat_with_groq(messages)
            return Response({"answer": answer})
        except Exception as e:
            return Response({"error": str(e)}, status=502)


class HistorySummarizerView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role != "doctor":
            return Response({"error": "Only doctors can summarize"}, status=403)
        raw = request.data.get("raw_history", "")
        if not raw.strip():
            return Response({"error": "raw_history required"}, status=400)
        messages = [
            {"role": "system", "content": DOCTOR_SYSTEM},
            {"role": "user", "content": f"{HISTORY_SUMMARY_INSTRUCTION}\n\n{raw}"},
        ]
        try:
            summary = chat_with_groq(messages, temperature=0.1)
            return Response({"summary": summary})
        except Exception as e:
            return Response({"error": str(e)}, status=502)
