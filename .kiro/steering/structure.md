# Project Structure

## Directory Organization

```
├── backend/                 # FastAPI backend service
│   ├── app/                # Application code
│   │   ├── api/           # API endpoints (REST routes)
│   │   ├── models/        # Pydantic data models and schemas
│   │   ├── services/      # Business logic layer
│   │   ├── tasks/         # Celery task definitions
│   │   ├── config.py      # Application configuration
│   │   └── main.py        # FastAPI app entry point
│   ├── worker.py          # Celery worker startup script
│   ├── beat.py            # Celery beat scheduler startup
│   ├── requirements.txt   # Python dependencies
│   ├── Dockerfile         # Backend container definition
│   └── test_*.py          # Unit tests (pytest format)
├── frontend/              # Web interface
│   ├── index.html         # Main HTML entry point
│   ├── app.js            # JavaScript application logic
│   └── styles.css        # CSS styling
├── deployment/            # Infrastructure as code
│   └── docker-compose.yml # Multi-service orchestration
├── downloads/             # Downloaded video files (runtime)
├── temp/                  # Temporary processing files (runtime)
├── logs/                  # Application logs (runtime)
└── .kiro/                 # Kiro IDE configuration
    ├── specs/             # Feature specifications
    └── steering/          # AI assistant guidance rules
```

## Code Organization Patterns

### Backend Structure
- **Layered Architecture**: API → Services → Tasks
- **Separation of Concerns**: Each module has single responsibility
- **Configuration Management**: Centralized in `config.py` with environment variables
- **Error Handling**: Custom exceptions with proper HTTP status codes

### Service Layer (`app/services/`)
- `downloader.py`: Core video downloading logic
- `task_storage.py`: Task state management
- `redis_client.py`: Redis connection and operations
- `validation.py`: Input validation and sanitization

### Task Layer (`app/tasks/`)
- `download_tasks.py`: Async video download operations
- `cleanup_tasks.py`: Maintenance and cleanup operations

### Testing Conventions
- Test files prefixed with `test_`
- One test file per service/module
- Use pytest fixtures for setup/teardown
- Mock external dependencies (yt-dlp, Redis)

## File Naming Conventions
- **Python**: snake_case for files, classes use PascalCase
- **JavaScript**: camelCase for variables, kebab-case for files
- **Configuration**: lowercase with extensions (.env, .yml, .json)
- **Documentation**: lowercase with hyphens (README.md)

## Import Organization
```python
# Standard library imports
import os
import sys

# Third-party imports
from fastapi import FastAPI
from celery import Celery

# Local application imports
from app.config import settings
from app.services.downloader import DownloaderService
```

## Environment-Specific Paths
- **Production**: `/opt/gravity/` prefix for all data directories
- **Development**: Local project directories (`./downloads`, `./temp`, `./logs`)
- **Configuration**: Auto-detection based on `/opt/gravity` existence