# Hospital Management System

## Project Description
The **Hospital Management System** is a web-based application designed to streamline interactions between doctors, patients, and administrative staff. It allows patients to sign up, book appointments, upload documents, and view prescriptions, while doctors can manage their dashboard, view appointments, and upload prescriptions. The system also includes features such as doctor search by specialization, a chatbot for patient queries, and secure authentication with role-based access. Built with Django and RESTful APIs, it provides a seamless and organized way to manage hospital operations digitally.

### Postman Collection
You can explore and test all API endpoints using this Postman documentation:  
[Hospital Management API - Postman](https://documenter.getpostman.com/view/37442600/2sB3BHkU9e)

## API Documentation
The system provides RESTful APIs for managing users, appointments, prescriptions, and chat interactions. APIs support role-based access for **patients** and **doctors**.

### Key Endpoints
- **User Management:**  
  - Signup: `POST /api/signup/`  
  - Login: `POST /api/login/`
- **Dashboards:**  
  - Doctor Dashboard: `GET /api/doctor/dashboard/`  
  - Patient Dashboard: `GET /api/patient/dashboard/`
- **Appointments & Prescriptions:**  
  - View Doctors: `GET /api/doctors/`  
  - Appointment Prescription: `GET /api/appointment/<id>/prescription/`  
  - My Prescriptions: `GET /api/my-prescriptions/`
- **Chatbot:**  
  - Send messages: `POST /api/chat/`

### Authentication
All endpoints require token-based authentication using the `Authorization` header:

