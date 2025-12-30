# Healthcare Backend API

Django REST Framework API for managing doctors, patients, and their assignments with JWT authentication.

## Quick Setup

### Prerequisites
- Python 3.11+
- PostgreSQL 15 (or Docker)

### Installation

1. **Install dependencies**
```bash
pip install -r requirements.txt
```

2. **Configure `.env` file**
```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=healthcare_db
DB_USER=postgres
DB_PASSWORD=postgres123
DB_HOST=localhost
DB_PORT=5432
```

3. **Start PostgreSQL with Docker**
```bash
docker-compose up -d db
```

4. **Run migrations**
```bash
python manage.py migrate
```

5. **Start server**
```bash
python manage.py runserver
```

API available at: `http://localhost:8000/api/`

## 📦 Import Postman Collection

### Step 1: Import Files
1. Open Postman
2. Click **"Import"** button
3. Drag & drop or select these files:
   - `Healthcare_API.postman_collection.json`
   - `Healthcare_API.postman_environment.json`

### Step 2: Select Environment
- Top-right corner dropdown → Select **"Healthcare API - Local"**

### Step 3: Start Testing
1. Run **"Register Admin"** or **"Login Admin"** first
2. Token automatically saved to environment
3. Test any endpoint - authorization is automatic!

## API Endpoints

### Authentication (No token required)
- `POST /api/auth/register/` - Register user
- `POST /api/auth/login/` - Login (get token)
- `POST /api/auth/token/refresh/` - Refresh token

### Doctors
- `GET /api/doctors/` - List all
- `POST /api/doctors/` - Create
- `GET /api/doctors/{id}/` - Get details
- `PATCH /api/doctors/{id}/` - Update
- `DELETE /api/doctors/{id}/` - Delete

### Patients
- `GET /api/patients/` - List all
- `POST /api/patients/` - Create
- `GET /api/patients/{id}/` - Get details
- `PATCH /api/patients/{id}/` - Update
- `DELETE /api/patients/{id}/` - Delete

### Mappings (Assign Doctor to Patient)
- `GET /api/mappings/` - List all
- `POST /api/mappings/` - Create
- `GET /api/mappings/patient/{patient_id}/` - Get patient's doctors
- `DELETE /api/mappings/{id}/` - Delete

## Quick Test

```bash
python quick_test.py
```

## Docker Commands

```bash
# Start PostgreSQL only
docker-compose up -d db

# Start everything (PostgreSQL + Django)
docker-compose up -d

# Stop all
docker-compose down

# Reset database (WARNING: deletes all data)
docker-compose down -v
```

## Authentication

All endpoints require JWT token except register/login.

**Header format:**
```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

## Tech Stack

- Django 5.2.9
- Django REST Framework 3.16.1
- JWT Authentication
- PostgreSQL 15
- Docker

## Documentation Files

- `API_CURL_COMMANDS.md` - Complete cURL examples
- `Healthcare_API.postman_collection.json` - Postman collection (20+ requests)
- `Healthcare_API.postman_environment.json` - Postman environment with variables

---

**Ready to test!** Import Postman collection and start making API calls.
