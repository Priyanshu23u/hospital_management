# 🏥 Hospital Management System (Django + DRF + AI Integration)

This is a Hospital Management System built with **Django** and **Django REST Framework**, featuring:
- API-based management of hospital entities (patients, appointments, documents, etc.)
- AI-assisted functionalities using **Groq API**
- Environment variable support via `.env`
- Token-based authentication

---

##  [DEPLOYED LINK](https://hospital-management-eqhx.onrender.com)
##  [GITHUB LINK](https://github.com/Priyanshu23u/hospital_management)
## 🚀 Features
- **Authentication**: Token-based (DRF Token Authentication)
- **Patient Management**: Create, view, update, delete patient records
- **Appointment Scheduling**
- **Document Uploads**
- **AI-powered** medical assistant using Groq
- **RESTful APIs** with DRF serializers
- **Environment Variables** managed with `python-decouple`

---

## 💻 Tech Stack

### Backend
- **Django 4.x** - Web framework
- **Django REST Framework (DRF)** - API development
- **Python 3.8+** - Programming language
- **SQLite/PostgreSQL** - Database (SQLite for dev, PostgreSQL for production)

### AI & Machine Learning
- **Groq API** - AI-powered medical assistance
- **Custom Prompts** - Healthcare-specific AI interactions

### Authentication & Security
- **DRF Token Authentication** - API authentication
- **Django's built-in security** - CSRF protection, SQL injection prevention
- **python-decouple** - Environment variable management

### Deployment & Production
- **Gunicorn** - WSGI HTTP Server
- **Whitenoise** - Static file serving
- **Render.com** - Cloud deployment platform
- **PostgreSQL** - Production database

### Frontend (Optional)
- **HTML/CSS/JavaScript** - Basic frontend templates
- **Bootstrap** - UI framework (if used)

### Development & Tools
- **pip** - Package management
- **Virtual Environment** - Dependency isolation
- **Git** - Version control

---

## 📂 Project Structure
```
hospital_management/
│── app/                # Main Django app with models, views, serializers, etc.
│── hospital_management/ # Project settings and URLs
│── manage.py
│── db.sqlite3
│── .env               # Environment variables
│── requirements.txt
```

---

## ⚙️ Installation

### 1️⃣ Clone the repository
```bash
git clone <repo-url>
cd hospital_management
```

### 2️⃣ Create & activate virtual environment
```bash
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
```

### 3️⃣ Install dependencies
```bash
pip install -r requirements.txt
```

---

## 🧠 AI Features and Chatbot Integration

This project integrates Groq AI API to assist in generating responses for healthcare-related prompts.
You must set GROQ_API_KEY in .env for AI features to work.