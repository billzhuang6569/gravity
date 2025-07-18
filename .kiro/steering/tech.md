# Technology Stack

## Backend
- **Framework**: FastAPI 0.104.1 with Uvicorn ASGI server
- **Task Queue**: Celery 5.3.4 with Redis broker
- **Database**: Redis 5.0.1 (for caching and task results)
- **Video Processing**: yt-dlp 2023.12.30 for multi-platform downloads
- **Configuration**: Pydantic Settings with environment variables
- **Testing**: pytest with async support

## Frontend
- **Core**: Vanilla JavaScript (ES6+), HTML5, CSS3
- **Language**: Chinese (zh-CN) as primary language
- **Architecture**: Single-page application with direct API communication

## Infrastructure
- **Containerization**: Docker with multi-service compose setup
- **Deployment**: Ubuntu VPS with Nginx reverse proxy
- **Process Management**: Separate worker and beat scheduler processes

## Development Commands

### Local Development
```bash
# Backend setup - IMPORTANT: Use virtual environment
cd backend

# Activate virtual environment (required for all operations)
source venv/bin/activate  # On macOS/Linux
# or: venv\Scripts\activate  # On Windows

# Install dependencies in virtual environment
pip install -r requirements.txt
cp .env.example .env

# Start FastAPI server (with venv activated)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start Celery worker (with venv activated)
python worker.py

# Start Celery beat scheduler (with venv activated)
python beat.py
```

### Testing
```bash
# Run all tests (with virtual environment activated)
cd backend
source venv/bin/activate  # Ensure venv is activated
pytest

# Run specific test file
pytest test_downloader.py -v

# Run with coverage
pytest --cov=app tests/
```

### Docker Deployment
```bash
# Build and start all services
cd deployment
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Key Libraries
- **fastapi**: Web framework and API
- **celery**: Distributed task queue
- **redis**: In-memory data store and message broker
- **yt-dlp**: Video downloading engine
- **pydantic**: Data validation and settings
- **psutil**: System monitoring
- **httpx**: HTTP client for async requests