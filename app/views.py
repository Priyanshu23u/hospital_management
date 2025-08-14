# app/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from datetime import datetime
from django.db import IntegrityError, transaction

from .models import Doctor, Patient, Appointment
from .serializers import AppointmentSerializer
from .utils import generate_daily_slots, get_available_slots

class AvailableSlotsView(APIView):
    """
    GET /api/slots/?doctor_id=1&date=YYYY-MM-DD
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        doctor_id = request.query_params.get("doctor_id")
        date_str = request.query_params.get("date")

        if not doctor_id or not date_str:
            return Response(
                {"detail": "doctor_id and date are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        date = parse_date(date_str)
        if date is None:
            return Response(
                {"detail": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        doctor = get_object_or_404(Doctor, pk=doctor_id, available=True)
        slots = get_available_slots(doctor.id, date)
        return Response(
            {"date": date_str, "doctor_id": doctor.id, "available_slots": slots}
        )

class BookAppointmentView(APIView):
    """
    POST /api/book/
    {
        "doctor_id": 1,
        "date": "YYYY-MM-DD",
        "slot": "HH:MM"
    }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # Ensure user is patient
        try:
            patient = request.user.profile.patient
        except AttributeError:
            return Response(
                {"detail": "Only patients can book appointments."},
                status=status.HTTP_403_FORBIDDEN,
            )

        doctor_id = request.data.get("doctor_id")
        date_str = request.data.get("date")
        slot_str = request.data.get("slot")

        if not all([doctor_id, date_str, slot_str]):
            return Response(
                {"detail": "doctor_id, date, and slot are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        date = parse_date(date_str)
        if date is None:
            return Response(
                {"detail": "Invalid date format. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check doctor
        doctor = get_object_or_404(Doctor, pk=doctor_id, available=True)

        # Validate slot
        generated = generate_daily_slots(date)
        if slot_str not in generated:
            return Response(
                {"detail": "Slot not valid or outside working hours."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        slot_time = datetime.strptime(slot_str, "%H:%M").time()

        try:
            with transaction.atomic():
                appt = Appointment.objects.create(
                    patient=patient,
                    doctor=doctor,
                    date=date,
                    slot=slot_time,
                    status="booked",
                )
        except IntegrityError:
            return Response(
                {"detail": "Slot already booked."},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            {"status": "success", "appointment": AppointmentSerializer(appt).data},
            status=status.HTTP_201_CREATED,
        )
