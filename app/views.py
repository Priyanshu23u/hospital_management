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
