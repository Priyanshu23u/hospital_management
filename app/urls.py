# app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path("signup/", views.SignupView.as_view(), name="signup"),
    path("login/", views.LoginView.as_view(), name="login"),

    # Dashboards
    path("doctor/dashboard/", views.DoctorDashboardView.as_view(), name="doctor-dashboard"),
    path("patient/dashboard/", views.PatientDashboardView.as_view(), name="patient-dashboard"),

    # Users CRUD
    path("users/", views.UserListCreateView.as_view(), name="user-list-create"),
    path("users/<int:pk>/", views.UserDetailView.as_view(), name="user-detail"),

    # Doctor search
    path("doctors/", views.DoctorListView.as_view(), name="doctor-list"),

    # Document upload
    path("documents/upload/", views.DocumentUploadView.as_view(), name="document-upload"),

    # Slots and appointments
    path("slots/", views.AvailableSlotsView.as_view(), name="available-slots"),
    path("appointments/", views.AppointmentListCreateView.as_view(), name="appointment-list-create"),
    path("appointments/<int:pk>/", views.AppointmentDetailView.as_view(), name="appointment-detail"),

    # AI features
    path("chatbot/", views.ChatbotView.as_view(), name="chatbot"),
    path("summarize-history/", views.HistorySummarizerView.as_view(), name="history-summarizer"),
    path("chat/", views.chat_with_ai, name="chat_with_ai"),
]
