# Product Overview

Gravity Video Downloader is a web-based video downloading service that supports multiple platforms including Bilibili and YouTube. The application provides real-time progress tracking, file management, and a clean web interface for users to download videos efficiently.

## Key Features
- Multi-platform video downloading (Bilibili, YouTube via yt-dlp)
- Real-time download progress tracking
- File management with automatic cleanup
- Web-based interface with responsive design
- Asynchronous task processing with Celery
- Redis-backed task queuing and result storage

## Target Users
- Content creators needing to download videos from various platforms
- Users requiring reliable video downloading with progress tracking
- Anyone needing a self-hosted video downloading solution

## Architecture Philosophy
- Microservices approach with FastAPI backend and vanilla JS frontend
- Async task processing for long-running downloads
- Clean separation between API, business logic, and task processing
- Docker-based deployment for easy scaling and management