# 🏥 Hospital Management System (Django + HTMM/CSS/Js)

This project demonstrates a full-stack hospital management application with role-based dashboards, authentication, CRUD operations, pagination/filtering, and deployment on Render.  

It also includes **AI-assisted documentation** — showing prompts given to AI and the responses generated.

---

## Prompt 1: Project Requirements

**User Prompt:**  
"I want to build a 'Hospital Management Project', Please give what requirements should I have"

**AI Answer:**  
Outlined the requirements:  
- Authentication & Authorization (Admin, Doctor, Patient, Receptionist)  
- Patient Management (CRUD, search/filter, medical history)  
- Doctor Management (profiles, specialization, availability)  
- Appointment Management (booking, status, auto-calculated fee)  
- Prescription Management (doctor creates, patient views/downloads)  
- Billing & Reports (optional)  
- Dashboards (role-specific: Doctor vs Patient)  
- UI requirements (login, forms, pagination, filters)  
- Non-functional: Security, Scalability, Deployment, Documentation  

---

## Prompt 2: Django REST Framework CRUD Setup

**User Prompt:**  
"Provide Django REST Framework views and serializers for the Hospital Management project to support full CRUD operations."

**AI Answer:**  
- Created models: **User, Patient, Doctor, Appointment (with fee as calculated field), Prescription**  
- Provided serializers for each model  
- Implemented `ModelViewSet` classes for CRUD operations  
- Added DRF `DefaultRouter` for automatic RESTful API routing  
- Exposed endpoints:  
  - `/api/patients/`  
  - `/api/doctors/`  
  - `/api/appointments/`  
  - `/api/prescriptions/`

---

## Prompt 3: Pagination & Filtering

**User Prompt:**  
"Add pagination (5 items per page) and filter tasks by completed status in Django REST Framework, Not code"

**AI Answer:**  
- Explained **Pagination**: Use DRF’s pagination to show 5 items per page.  
  Example:  
  - `/api/appointments/?page=1` → first 5 items  
  - `/api/appointments/?page=2` → next 5 items  

- Explained **Filtering**: Allow filtering tasks/appointments by `completed` (boolean).  
  Example:  
  - `/api/tasks/?completed=true` → completed tasks  
  - `/api/tasks/?completed=false` → pending tasks  

- Explained **Combined usage**:  
  `/api/tasks/?completed=true&page=2` → shows page 2 of completed tasks.  

---

## Prompt 4: Frontend Content

**User Prompt:**  
"What Should be the content in frontend with a login page, Dashboard Page for both Doctor and Patient (with pagination), and CRUD functionality integrated with the Django API."

**AI Answer:**  
- **Login Page:** Username/password, login button, signup link, redirect by role  
- **Doctor Dashboard:**  
  - Appointments (paginated, filterable)  
  - Patient records (CRUD)  
  - Prescription management  
- **Patient Dashboard:**  
  - My Appointments (paginated, filterable)  
  - My Prescriptions (view/download)  
  - Profile management (CRUD)  
- **CRUD Integration:**  
  - Patients: Create, Read, Update, Delete  
  - Doctors: Create, Read, Update, Delete  
- Pagination integrated in both dashboards with “Next/Previous” navigation.  

---

## Prompt 5: Deployment on Render

**User Prompt:**  
"I want to deploy my application on render. Give steps to proceed"

**AI Answer:**  
- **Step 1:** Prepare repo (with `requirements.txt`, `package.json`, `render.yaml`)  
- **Step 2:** Setup PostgreSQL DB on Render → update `DATABASES` in Django  
- **Step 3:** Configure Django for production (Gunicorn, Whitenoise, static files)  
- **Step 4:** Deploy backend as Web Service  
  - Build: `pip install -r requirements.txt && python manage.py migrate && python manage.py collectstatic --noinput`  
  - Start: `gunicorn hospital.wsgi:application --log-file -`  
- **Step 5:** Deploy frontend as Static Site  
  - Build: `npm install && npm run build`  
  - Publish: `build/`  
- **Step 6:** Example `render.yaml` provided for one-click deploy  
- **Step 7:** Verify URLs:  
  - Backend → `https://hospital-backend.onrender.com/api/`  
  - Frontend → `https://hospital-frontend.onrender.com/`

---

## Prompt 6: Debugging — "Data can't be fetched" Error

**User Prompt:**  
"i am getting error in the code showing data cant be fetched, suggest what can I change"

**AI Answer:**  
Common causes and fixes:  

1. **API Base URL mismatch**  
   - Problem: It fetches `/api/...` but backend runs on `https://hospital-backend.onrender.com/api/`.  
   - Fix: Use full URL or environment variable for APIs.  

2. **CORS Issue**  
   - Problem: Backend blocks frontend requests from another domain.  
   - Fix: Install `django-cors-headers` and add frontend domain in `CORS_ALLOWED_ORIGINS`.  

3. **Pagination Response Handling**  
   - Problem: expects an array, but DRF returns `{count, next, previous, results}`.  
   - Fix: In frontend, use `data.results` instead of `data`.  

4. **Authentication / Permissions**  
   - Problem: DRF view requires login but request sent without token.  
   - Fix: Add `Authorization: Bearer <token>` header or set DRF permission to `AllowAny` for testing.  

5. **Debugging Steps**  
   - Check browser Network tab.  
   - If **CORS error** → enable `django-cors-headers`.  
   - If **404** → fix API URL.  
   - If **401 Unauthorized** → add proper auth headers.  

---

## ✅ Features Implemented
- Authentication system  
- CRUD operations (Patients, Doctors, Appointments, Prescriptions)  
- Pagination (5 items per page)  
- Filtering (by status)  
- Doctor & Patient dashboards  
- Deployment on Render  
- Troubleshooting guide for fetch errors  

---
