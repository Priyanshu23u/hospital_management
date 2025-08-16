# 🏥 Hospital Management System

A comprehensive Django-based hospital management system with AI-powered features for managing appointments, patient records, and medical documentation.

## 🏗️ Architecture Overview


### System Architecture
The application follows a standard Django MVC (Model-View-Controller) architecture with REST API capabilities:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Django Backend │    │   Database      │
│   (HTML/JS)     │◄──►│   (REST API)     │◄──►│   (SQLITE3)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────┐
                       │  Groq AI API │
                       │  Integration │
                       └──────────────┘
```


### Project Structure
hospital_management/
├─ manage.py
├─ README.md
├─ requirements.txt                 # add (django, djangorestframework, drf-authtoken, python-decouple, groq, pytz, gunicorn, whitenoise)
├─ .gitignore
├─ .env.example                     # placeholders (NO real keys)
│
├─ app/
│  ├─ admin.py
│  ├─ ai_groq.py
│  ├─ models.py
│  ├─ prompts.py
│  ├─ serializers.py
│  ├─ urls.py
│  ├─ utils.py
│  ├─ views.py
│  └─ migrations/...
│
├─ hospital_management/
│  ├─ settings.py                   # add Whitenoise, CORS (if needed), paginate defaults
│  ├─ urls.py
│  ├─ asgi.py
│  └─ wsgi.py
│
├─ frontend/                        # keep, or move to templates/static if you prefer Django templating
│  ├─ login.html
│  ├─ signup.html
│  ├─ doctor_dashboard.html
│  ├─ patient_dashboard.html
│  └─ patient_detail.html
│
├─ media/                           # protect in production (X-Sendfile / signed URLs if needed)
│  └─ documents/
│
├─ render.yaml                      # for Render (web service + DB + envs)
└─ Procfile                         # e.g., web: gunicorn hospital_management.wsgi


### Technology Stack
- **Backend**: Django 4.x + Django REST Framework
- **Database**: PostgreSQL (production) / SQLite (development)
- **AI Integration**: Groq API for medical assistance
- **Authentication**: Token-based authentication
- **File Storage**: Django FileField (with Whitenoise for static files)
- **Deployment**: Render.com (with Gunicorn)

### Key Features
- User role management (Doctor/Patient)
- Appointment booking system
- Medical document management
- AI-powered prescription analysis
- Visit notes and medical history
- RESTful API endpoints

## 📊 Database Schema

### Entity Relationship Diagram

```
User (Django's built-in)
│
├─ Profile (1:1)
   │
   ├─ Doctor (1:1)
   │  └─ Appointment (1:N)
   │     ├─ VisitNote (1:N)
   │     └─ Document (1:N)
   │
   └─ Patient (1:1)
      ├─ Appointment (1:N)
      ├─ VisitNote (1:N)
      └─ Document (1:N)
```

### Database Tables

#### 1. **auth_user** (Django's built-in User model)
```sql
- id (PK)
- username (unique)
- email
- first_name
- last_name
- password
- is_active
- date_joined
- last_login
```

#### 2. **app_profile**
```sql
- id (PK)
- user_id (FK → auth_user.id, unique)
- role (choices: 'doctor', 'patient')
- dob (nullable)
- gender (nullable)
- phone (nullable)
```

#### 3. **app_doctor**
```sql
- id (PK)
- profile_id (FK → app_profile.id, unique)
- specialization
- bio (text, nullable)
- available (boolean, default=True)
```

#### 4. **app_patient**
```sql
- id (PK)
- profile_id (FK → app_profile.id, unique)
```

#### 5. **app_appointment**
```sql
- id (PK)
- patient_id (FK → app_patient.id)
- doctor_id (FK → app_doctor.id)
- date
- slot (time)
- status (choices: 'booked', 'cancelled', 'completed')
- prescription (text, nullable, deprecated)
- created_at (auto)
- UNIQUE(doctor_id, date, slot)
```

#### 6. **app_visitnote**
```sql
- id (PK)
- appointment_id (FK → app_appointment.id, nullable)
- patient_id (FK → app_patient.id)
- doctor_id (FK → app_doctor.id)
- visit_date (auto)
- notes (text)
- prescription (file, nullable)
```

#### 7. **app_document**
```sql
- id (PK)
- patient_id (FK → app_patient.id)
- appointment_id (FK → app_appointment.id, nullable)
- file (FileField)
- doc_type (choices: 'lab', 'scan', 'prescription', 'other')
- description (nullable)
- uploaded_at (auto)
```

## 📁 Module & Class Breakdown

### Core Application Structure

```
hospital_management/
├─ app/                          # Main Django application
├─ hospital_management/          # Project configuration
├─ frontend/                     # Static HTML templates
├─ media/                        # Uploaded files storage
└─ Configuration files
```

### 🎯 app/models.py Classes

#### **Profile**
- **Purpose**: Extends Django's User model with additional fields
- **Key Fields**: `role`, `dob`, `gender`, `phone`
- **Relationships**: OneToOne with User

#### **Doctor**
- **Purpose**: Doctor-specific information and availability
- **Key Fields**: `specialization`, `bio`, `available`
- **Relationships**: OneToOne with Profile

#### **Patient**
- **Purpose**: Patient-specific information (minimal for now)
- **Relationships**: OneToOne with Profile

#### **Appointment**
- **Purpose**: Manages appointment scheduling between doctors and patients
- **Key Fields**: `date`, `slot`, `status`
- **Business Logic**: Prevents double-booking with unique constraint
- **Relationships**: ForeignKey to Patient and Doctor

#### **VisitNote**
- **Purpose**: Records doctor's notes and prescriptions after visits
- **Key Fields**: `notes`, `prescription` (file upload)
- **Relationships**: ForeignKey to Patient, Doctor, and optional Appointment

#### **Document**
- **Purpose**: Manages medical document uploads (lab reports, scans, etc.)
- **Key Fields**: `file`, `doc_type`, `description`
- **Relationships**: ForeignKey to Patient and optional Appointment

### 🔧 app/views.py Architecture

#### **Authentication Views**
- `RegisterView`: User registration with role selection
- `LoginView`: Token-based authentication
- `LogoutView`: Token cleanup

#### **Profile Management**
- `ProfileView`: User profile CRUD operations
- Role-specific profile creation (Doctor/Patient)

#### **Appointment System**
- `AppointmentListCreateView`: List and create appointments
- `AppointmentDetailView`: Retrieve, update, delete appointments
- Business logic for preventing conflicts

#### **Medical Records**
- `VisitNoteViewSet`: Complete CRUD for visit notes
- `DocumentViewSet`: File upload and management
- Permission-based access control

#### **AI Integration**
- `PrescriptionAnalysisView`: Groq AI integration for prescription analysis
- Medical document interpretation

### 🔗 app/serializers.py Components

#### **UserRegistrationSerializer**
- Handles user creation with profile setup
- Validates role selection and creates appropriate related models

#### **Model Serializers**
- `ProfileSerializer`: User profile data
- `DoctorSerializer`: Doctor-specific information
- `PatientSerializer`: Patient information
- `AppointmentSerializer`: Appointment data with nested relationships
- `VisitNoteSerializer`: Visit notes with file handling
- `DocumentSerializer`: Document uploads with metadata

### 🎨 Frontend Structure

#### **Templates**
- `login.html`: User authentication interface
- `signup.html`: Registration form with role selection
- `doctor_dashboard.html`: Doctor's appointment and patient management
- `patient_dashboard.html`: Patient's appointment booking and history
- `patient_detail.html`: Detailed patient information view

#### **JavaScript Integration**
- AJAX calls to Django REST API
- Token-based authentication handling
- File upload functionality
- Dynamic content updates

### 🤖 AI Integration (app/ai_groq.py)

#### **Groq API Integration**
- Medical document analysis
- Prescription interpretation
- Health insights generation
- Error handling and fallbacks

#### **Prompt Engineering (app/prompts.py)**
- Medical analysis prompts
- Context-aware questioning
- Structured response formatting

### 🔐 Security Features

#### **Authentication & Authorization**
- Token-based authentication via DRF
- Role-based access control
- User permission validation

#### **Data Protection**
- File upload validation
- SQL injection prevention (Django ORM)
- CSRF protection
- Environment variable configuration

### 📡 API Endpoints Structure

#### **Authentication**
- `POST /api/register/` - User registration
- `POST /api/login/` - User authentication
- `POST /api/logout/` - Token cleanup

#### **User Management**
- `GET/PUT /api/profile/` - User profile operations

#### **Appointments**
- `GET/POST /api/appointments/` - List/Create appointments
- `GET/PUT/DELETE /api/appointments/{id}/` - Appointment details

#### **Medical Records**
- `GET/POST /api/visitnotes/` - Visit notes management
- `GET/POST /api/documents/` - Document upload/retrieval

#### **AI Features**
- `POST /api/analyze-prescription/` - AI prescription analysis

## 🚀 Deployment Configuration

### **Requirements (requirements.txt)**
```
django
djangorestframework
drf-authtoken
python-decouple
groq
pytz
gunicorn
whitenoise
```

### **Render.com Deployment (render.yaml)**
- Web service configuration
- PostgreSQL database setup
- Environment variable management
- Static file serving

### **Environment Variables (.env.example)**
```
SECRET_KEY=your-secret-key
DEBUG=False
DATABASE_URL=postgresql://...
GROQ_API_KEY=your-groq-api-key
```

## 📈 Scalability Considerations

### **Database Optimization**
- Indexed foreign keys
- Efficient query patterns
- File storage optimization

### **Performance**
- Django's built-in caching
- Database connection pooling
- Static file optimization with Whitenoise

### **Future Enhancements**
- Real-time notifications
- Advanced AI features
- Mobile app integration
- Telehealth capabilities

## 🔧 Development Setup

1. **Clone and setup virtual environment**
2. **Install dependencies**: `pip install -r requirements.txt`
3. **Configure environment variables**
4. **Run migrations**: `python manage.py migrate`
5. **Create superuser**: `python manage.py createsuperuser`
6. **Start development server**: `python manage.py runserver`

## 📞 Support & Maintenance

- Regular security updates
- Database backup strategies
- Monitoring and logging
- Performance optimization
- Feature enhancement roadmap