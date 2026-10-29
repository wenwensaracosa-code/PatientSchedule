# eDoc Doctor Appointment Booking System (Python & Flask)

![eDoc Preview](Screenshots/Screenshot%20(1).png)

**eDoc** is a comprehensive, responsive web application for managing doctor appointments, schedules, patients, and bookings. Originally developed in PHP, this project has been fully **refactored into Python using Flask and Jinja2** with parameterized database support for MySQL and SQLite.

---

## 🌟 Key Features

### 👨‍💼 Administrator
- **Dashboard**: High-level status overview, stats (Doctors, Patients, Bookings, Sessions), and 7-day upcoming sessions and appointments.
- **Doctor Management**: Search, add, view, edit, and delete doctor accounts and credentials with specialty assignment.
- **Schedule Management**: Create and schedule doctor consultation sessions with patient limits, view sessions, and see registered patients.
- **Appointment Management**: View and filter patient appointments by date and doctor, and cancel appointments.
- **Patient Management**: Search and inspect full patient contact and personal details.

### 🩺 Doctor
- **Dashboard**: Personal status cards and upcoming sessions.
- **Appointments**: View booked patient appointments and filter by date.
- **Sessions**: Manage scheduled sessions, check registered patients against quota, and remove sessions.
- **Patients**: Browse all patients or filter to "My Patients Only" who have booked appointments.
- **Settings**: View account details, edit profile / change password, or delete account.

### 🧑‍🦰 Patient
- **Home**: Quick search for doctors and sessions, view upcoming personal bookings.
- **Browse Doctors**: Search doctors by name or medical specialty, view credentials, and redirect directly to their sessions.
- **Scheduled Sessions**: Browse available sessions in responsive cards and book appointments.
- **Booking Flow**: Real-time calculated appointment number, fee calculation, and one-click booking confirmation.
- **My Bookings**: Review booking history with reference numbers and date filters, and cancel bookings.
- **Settings**: View and edit personal profile (address, phone, password), or delete account.

---

## 🔐 Default Login Credentials

| Role | Email | Password |
| :--- | :--- | :--- |
| **Administrator** | `admin@edoc.com` | `123` |
| **Doctor** | `doctor@edoc.com` | `123` |
| **Patient** | `patient@edoc.com` | `123` |

---

## 🚀 Getting Started (Run Locally)

### 1. Requirements
- Python 3.8+ (Tested with Python 3.10 - 3.14)
- (Optional) MySQL / MariaDB server (SQLite is supported out-of-the-box with automatic initialization)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

*(Dependencies: `Flask`, `PyMySQL`)*

### 3. Configure Database (.env)
The application reads configuration from `.env`. By default, it connects to your local MySQL database:

```env
# Database Type: 'mysql' or 'sqlite'
DB_TYPE=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=admin123
DB_NAME=edoc

# Server
PORT=5000
FLASK_DEBUG=True
```

> **Note**: If MySQL is not running or if you set `DB_TYPE=sqlite`, the application **automatically falls back to SQLite** (`edoc.db`) and seeds all default tables, specialties, and demo accounts with zero configuration required!

If using MySQL, you can import the initial schema using:
```bash
mysql -u root -p edoc < SQL_Database_edoc.sql
```

### 4. Run the Application
Run via Python:
```bash
python run.py
```
*(or `python app.py`)*

Open your browser and navigate to:
```
http://127.0.0.1:8000
```

---

## 📁 Project Structure

```
PATIENT-SCHED/
├── app.py                 # Main Flask application and URL routing
├── db.py                  # Database abstraction (MySQL & SQLite fallback)
├── run.py                 # Application runner script
├── requirements.txt       # Python package dependencies
├── .env                   # Local environment configuration
├── .env.example           # Environment configuration template
├── SQL_Database_edoc.sql  # MySQL database dump reference
├── css/                   # Stylesheets and font assets
├── img/                   # SVG and PNG icons and images
├── templates/             # Jinja2 HTML templates
│   ├── index.html         # Landing page
│   ├── login.html         # Login page
│   ├── signup.html        # Registration Step 1
│   ├── create_account.html# Registration Step 2
│   ├── admin/             # Administrator dashboard & management views
│   ├── doctor/            # Doctor dashboard, appointments, sessions & settings
│   └── patient/           # Patient dashboard, booking flow, appointments & settings
└── Screenshots/           # UI screenshots
```

---

## 🛡️ Security Improvements
- **SQL Injection Prevention**: All queries in the Python codebase use parameterized queries instead of PHP's raw string interpolation.
- **Session Security**: Server-side session management with configurable secret key.
- **Role-Based Access Control**: Strict route decorators verifying user authentication and permission role (`admin`, `doctor`, `patient`).
