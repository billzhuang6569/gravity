# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

Gravity Video Downloader is a multi-platform video downloading service with real-time progress tracking and file management. The application follows a microservices architecture with FastAPI backend, Celery task queue, and vanilla JavaScript frontend.

### Core Components

- **FastAPI Backend** (`backend/app/`): RESTful API with async/await patterns, Redis integration, and lifespan management
- **Celery Task Queue**: Distributed task processing with Redis broker, priority queues (downloads, maintenance, health), and comprehensive error handling
- **Task Storage**: Redis-based storage with hash structures, sorted sets for history, and 7-day TTL
- **Frontend**: Pure JavaScript SPA with real-time progress updates and file management

### Key Services

- **Task Storage** (`services/task_storage.py`): Async Redis operations with atomic transactions and UTF-8 support
- **Video Downloader** (`services/downloader.py`): yt-dlp wrapper with progress tracking and metadata extraction
- **Redis Client** (`services/redis_client.py`): Connection pooling, health checks, and graceful shutdown
- **Validation** (`services/validation.py`): URL validation and sanitization for supported platforms

## Development Commands

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
```

### Running Services
```bash
# Start all services with Docker
cd deployment && docker-compose up -d

# Development mode (separate terminals)
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload  # API server
python worker.py                                           # Celery worker
python beat.py                                             # Celery beat scheduler
```

### Testing
```bash
cd backend
pytest                                    # Run all tests
pytest test_models.py                     # Test specific module
pytest -v                                 # Verbose output
pytest test_celery_config.py              # Test Celery configuration
```

## Configuration

### Environment Variables
- Copy `backend/.env.example` to `backend/.env` for local development
- Settings are managed through `app/config.py` using Pydantic Settings
- Automatic path detection: uses `/opt/gravity/` in production, local directories in development

### Celery Configuration
- **Queues**: `downloads` (main), `maintenance` (cleanup), `health` (monitoring)
- **Retry Policy**: 3 retries with exponential backoff
- **Timeouts**: 30min soft, 31min hard limits
- **Concurrency**: Dynamic based on CPU cores (cores × 2)
- **Memory Management**: 200MB per child, restart after 50 tasks

## Task Architecture

### Task Categories
1. **Download Tasks** (`tasks/download_tasks.py`): Video downloads with progress tracking
2. **Cleanup Tasks** (`tasks/cleanup_tasks.py`): File retention and system maintenance

### Task Patterns
- All tasks use `bind=True` for self-referencing
- Comprehensive error handling with Chinese error messages
- Real-time progress updates via Redis
- Automatic retry with exponential backoff

### Scheduled Tasks
- Daily cleanups at 2 AM, 3 AM, 4 AM
- Health checks every 15 minutes
- File retention policy: 7 days

## Project Structure Patterns

### Backend Structure
```
backend/app/
├── api/          # API endpoints (future)
├── models/       # Pydantic schemas
├── services/     # Business logic services
├── tasks/        # Celery task definitions
├── config.py     # Application configuration
└── main.py       # FastAPI application
```

### Testing Patterns
- Async test functions for all services
- Mock Redis connections for unit tests
- Comprehensive error handling tests
- Configuration validation tests

## Key Implementation Details

### Redis Integration
- Connection pooling with 20 max connections
- Health checks with graceful degradation
- Atomic operations with retry mechanisms
- UTF-8 support for Chinese content

### Error Handling
- Custom exception classes for different error types
- Comprehensive logging with structured format
- Graceful shutdown handling for all services
- Chinese error messages for user-facing errors

### File Management
- Automatic directory creation and validation
- Configurable retention policies
- Atomic file operations
- Progress tracking for downloads

## Technology Stack

- **Backend**: FastAPI 0.104.1, Celery 5.3.4, Redis 5.0.1
- **Video Processing**: yt-dlp 2023.12.30
- **Testing**: pytest 7.4.3, pytest-asyncio 0.21.1
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Infrastructure**: Docker, Docker Compose

## Development Memories

- Always remember to use the python env in the project folder.