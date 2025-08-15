# app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # =======================
    # Authentication
    # =======================
    path("signup/", views.SignupView.as_view(), name="signup"),
    path("login/", views.LoginView.as_view(), name="login"),

    # =======================
    # Dashboards
    # =======================
    path("doctor/dashboard/", views.DoctorDashboardView.as_view(), name="doctor-dashboard"),
    path("patient/dashboard/", views.PatientDashboardView.as_view(), name="patient-dashboard"),

    # =======================
    # Appointment Management
    # =======================
    path('appointment/<int:pk>/cancel/', views.cancel_appointment, name='cancel_appointment'),
    path('appointment/<int:pk>/update/', views.update_appointment, name='update_appointment'),
    path('appointment/<int:pk>/prescription/', views.view_prescription, name='view_prescription'),

    # =======================
    # Doctor Search & Filter
    # =======================
    path('doctors/by-specialization/', views.get_doctors_by_specialization, name='get_doctors_by_specialization'),
    path("doctors/", views.DoctorListView.as_view(), name="doctor-list"),
    path("doctors/specializations/", views.SpecializationListView.as_view(), name="specializations-list"),

    # =======================
    # Doctor Patient Management
    # =======================
    path('doctor/patient/<str:username>/', views.DoctorPatientDetailView.as_view(), name='doctor-patient-detail'),
    path('save-prescription/', views.SavePrescriptionView.as_view(), name='save-prescription'),
    path('patient-history-summary/', views.PatientHistorySummaryView.as_view(), name='patient-history-summary'),

    # =======================
    # Document Management
    # =======================
    path("documents/upload/", views.DocumentUploadView.as_view(), name="document-upload"),
    path("documents/", views.DocumentUploadView.as_view(), name="document-list"),  # GET for listing
    path('patients/<str:username>/documents/', views.get_patient_documents, name='patient-documents'),
    path('patient/<int:patient_id>/documents/', views.PatientDocumentsView.as_view(), name='patient-documents-by-id'),
    path('my-documents/', views.PatientDocumentsView.as_view(), name='my-documents'),

    # =======================
    # Users CRUD
    # =======================
    path("users/", views.UserListCreateView.as_view(), name="user-list-create"),
    path("users/<int:pk>/", views.UserDetailView.as_view(), name="user-detail"),

    # =======================
    # Slots & Appointments API
    # =======================
    path("slots/", views.AvailableSlotsView.as_view(), name="available-slots"),
    path("appointments/", views.AppointmentListCreateView.as_view(), name="appointment-list-create"),
    path("appointments/<int:pk>/", views.AppointmentDetailView.as_view(), name="appointment-detail"),

    # =======================
    # AI Features
    # =======================
    path("chatbot/", views.ChatbotView.as_view(), name="chatbot"),
    path("summarize-history/", views.HistorySummarizerView.as_view(), name="history-summarizer"),
    path("chat/", views.chat_with_ai, name="chat_with_ai"),
    # Add this line to your existing urlpatterns in app/urls.py
    path('my-prescriptions/', views.PatientPrescriptionsView.as_view(), name='my-prescriptions'),

]
