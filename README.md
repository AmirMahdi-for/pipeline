# Document Ingest & Thumbnail Pipeline

A Django REST API for handling file uploads with asynchronous processing and thumbnail generation.

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+ (for local development)

### Setup & Run
```bash
# 1. Clone and setup
git clone git@github.com:AmirMahdi-for/pipeline.git
cd pipeline

# 2. Create environment file
cp .env.example .env
# Edit .env with your values

# 3 Run the Project
# You can run the project with or without MinIO depending on your setup:

# Option 1 — Run without MinIO
docker-compose up -d --build

#Option 2 — Run with MinIO
docker compose --profile minio up -d --build

# 4. Run migrations
docker-compose exec app python manage.py migrate

# 5. Create superuser (optional)
docker-compose exec app python manage.py createsuperuser

# 6. Access the application
# API: http://localhost:8000/api/
# Docs: http://localhost:8000/api/docs/
# MinIO Console: http://localhost:9001 (if using local MinIO)
```

---

### 🔧 Environment Variables
Create a `.env` file with the following variables:
```env
# Django
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# Database
DB_NAME=your-db
DB_USER=user-db
DB_PASSWORD=pass-db
DB_HOST=db
DB_PORT=5432

# MinIO Storage
MINIO_ENDPOINT=
MINIO_ACCESS_KEY=
MINIO_SECRET_KEY=
MINIO_BUCKET=

# Celery
CELERY_BROKER_URL=
CELERY_RESULT_BACKEND=r
```

---

## 📡 API Endpoints

### Authentication
```bash
# Get JWT Token
curl -X POST http://localhost:8000/api/token/   -H "Content-Type: application/json"   -d '{"username": "your-username", "password": "your-password"}'

# Response: {"refresh": "...", "access": "..."}

# Refresh Token
curl -X POST http://localhost:8000/api/token/refresh/   -H "Content-Type: application/json"   -d '{"refresh": "your-refresh-token"}'
```

### File Upload
```bash
# Upload TXT, PNG, or JPEG file (max 10MB)
curl -X POST http://localhost:8000/api/upload/   -H "Authorization: Bearer your-access-token"   -F "file=@test.png"
```

Response:
```json
{
  "id": 1,
  "original_filename": "test.png",
  "file_size": 10240,
  "extension": "png",
  "status": "pending",
  "created_at": "2025-10-23T10:00:00Z",
  "user": 1
}
```

### Document Management
```bash
# List all documents (with pagination and filtering)
curl -H "Authorization: Bearer your-token"   "http://localhost:8000/api/documents/?extension=png&page=1"

# Get specific document
curl -H "Authorization: Bearer your-token"   http://localhost:8000/api/documents/1/

# Daily upload report (last 14 days)
curl -H "Authorization: Bearer your-token"   http://localhost:8000/api/report/
```

Example Response:
```json
[
  {"date": "2025-10-10", "count": 2},
  {"date": "2025-10-11", "count": 0}
]
```

---

## 🏗️ Architecture

**Flow:**
```
Client → Django API → MinIO (File Storage)
               ↓
           Celery Worker → Thumbnail Generation → MinIO
               ↓
           PostgreSQL (Metadata)
```

### File Processing Flow
1. **Upload:** User uploads file → stored in MinIO  
2. **Async Task:** Celery task triggered for processing  
3. **Image Processing:** Thumbnail generated (256px max side)  
4. **Completion:** Status updated to 'done'  

### Supported File Types
- TXT: Stored as-is, no thumbnail  
- PNG/JPEG: Original + thumbnail stored in MinIO

---

## 🔍 Monitoring & Debugging

```bash
# View all containers
docker-compose ps

# View logs
docker-compose logs app
docker-compose logs celery_worker
docker-compose logs minio

# Follow specific service logs
docker-compose logs -f celery_worker
```

### Common Issues
```bash
# Reset everything (warning: deletes data)
docker-compose down -v
docker-compose up -d --build

# Run tests
docker-compose exec app python manage.py test

# Check Celery tasks
docker-compose exec app python manage.py shell
>>> from documents.tasks import process_file_task
>>> process_file_task.delay(1)  # Test with document ID
```

---

## 🐳 Docker Services

| Service | Port | Purpose |
|----------|------|----------|
| app | 8000 | Django REST API |
| db | 5432 | PostgreSQL Database |
| minio | 9000 | File Storage API |
| minio-console | 9001 | MinIO Web Interface |
| redis | 6379 | Celery Broker |

---

## 📊 Database Schema

### Document Model
- id, user (ForeignKey)
- original_filename, file_size, extension
- original_storage_path, thumbnail_storage_path
- status (pending/processing/done/failed)
- created_at, updated_at, error_message

### ProcessingLog Model
- Audit trail for file processing operations

---

## 🛠️ Development

### Local Development (without Docker)
```bash
# Setup virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run services manually
redis-server
python manage.py runserver
celery -A core worker --loglevel=info
```

---

## 📈 API Documentation

- Swagger UI: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)
- Schema: [http://localhost:8000/api/schema/](http://localhost:8000/api/schema/)

---

## 🎯 Features

✅ JWT Authentication  
✅ File Upload (TXT, PNG, JPEG)  
✅ Async Processing with Celery  
✅ Thumbnail Generation for Images  
✅ MinIO S3-Compatible Storage  
✅ PostgreSQL Database  
✅ Daily Upload Reports  
✅ API Documentation  
✅ Docker Containerization

