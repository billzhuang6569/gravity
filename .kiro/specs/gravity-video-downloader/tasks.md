# Implementation Plan

- [x] 1. Set up project structure and core dependencies
  - Create directory structure for backend, frontend, and deployment files
  - Initialize Python project with requirements.txt including FastAPI, Celery, Redis, yt-dlp dependencies
  - Set up basic project configuration files and environment variables
  - _Requirements: 7.1, 7.4_

- [x] 2. Implement core data models and validation
  - [x] 2.1 Create Pydantic models for DownloadTask, DownloadOptions, and API request/response schemas
    - Write TaskStatus enum with PENDING, DOWNLOADING, COMPLETED, FAILED states
    - Implement DownloadOptions model with quality, format, and audio_format fields
    - Create DownloadTask model with all required fields including URL field and validation
    - Write VideoInfoRequest, VideoInfoResponse, and VideoFormat models for info parsing
    - Write API request/response models for consistent JSON formatting with URL field included
    - _Requirements: 9.4, 9.6, 6.4_

  - [x] 2.2 Implement URL validation and platform detection
    - Write URL validation functions for Bilibili and YouTube platforms
    - Create platform detection logic to identify supported video sources
    - Implement error handling for invalid or unsupported URLs
    - Write unit tests for URL validation and platform detection
    - _Requirements: 1.1, 1.6_

- [x] 3. Create Redis data layer and task management
  - [x] 3.1 Implement Redis connection and configuration
    - Set up Redis client with connection pooling and error handling
    - Create Redis configuration with appropriate timeouts and retry logic
    - Implement health check functionality for Redis connectivity
    - Write connection failure handling and graceful degradation
    - _Requirements: 9.5, 7.5_

  - [x] 3.2 Implement task storage and retrieval in Redis
    - Create functions to store DownloadTask objects as Redis hashes
    - Implement task retrieval by task_id with proper error handling
    - Add task status update functionality with timestamp tracking
    - Create TTL management for task data (7 days expiration)
    - Write unit tests for Redis task operations
    - _Requirements: 9.1, 9.3, 9.4_

  - [x] 3.3 Implement download history management
    - Create sorted set operations for maintaining download history
    - Implement automatic trimming to keep only 20 most recent records
    - Add history retrieval functionality with proper sorting
    - Write functions to add completed tasks to history
    - Create unit tests for history management operations
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [-] 4. Implement yt-dlp service encapsulation
  - [x] 4.1 Create DownloaderService class for yt-dlp integration
    - Implement DownloaderService class with pinned yt-dlp version (2023.12.30)
    - Create get_video_info method for synchronous video metadata extraction
    - Implement download_video method with progress callback support
    - Add error parsing method to convert yt-dlp errors to user-friendly Chinese messages
    - Create error type mapping for common download failures
    - Write unit tests for DownloaderService functionality
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

- [ ] 5. Implement Celery task processing system
  - [ ] 5.1 Set up Celery configuration and worker setup
    - Configure Celery with Redis as broker and result backend
    - Set up worker concurrency based on CPU cores (cores * 2) and task timeout (30 minutes)
    - Implement Celery app initialization with proper settings and retry policy
    - Create worker startup and shutdown handling
    - Configure Celery Beat for scheduled tasks
    - _Requirements: 9.2, 10.1, 10.2, 7.4_

  - [ ] 5.2 Implement core video download task
    - Create download_video_task Celery task with proper error handling using DownloaderService
    - Implement enhanced file naming logic with task_id: {sanitized_title}_{task_id}.{ext}
    - Add file storage logic following design conventions
    - Implement task status updates during download process
    - Create error handling and retry logic for failed downloads
    - Write unit tests for download task functionality
    - _Requirements: 1.4, 2.1, 2.2, 2.3, 2.4, 3.3, 9.5_

  - [ ] 5.3 Implement progress tracking and status updates
    - Create progress callback function for yt-dlp integration
    - Implement real-time status updates to Redis during download
    - Add progress percentage calculation and formatting
    - Create completion and failure status handling
    - Write tests for progress tracking functionality
    - _Requirements: 2.2, 2.3, 2.4, 2.5_

  - [ ] 5.4 Implement file cleanup and resource management
    - Create cleanup_old_files Celery task for automatic file deletion
    - Implement daily scheduled task using Celery Beat to remove files older than 7 days
    - Add disk space monitoring and cleanup logic
    - Create resource usage tracking for memory and CPU
    - Write unit tests for cleanup functionality
    - _Requirements: 10.3, 10.4, 10.5_

- [ ] 6. Create FastAPI backend service
  - [ ] 6.1 Implement core FastAPI application setup
    - Create FastAPI app with CORS configuration and middleware
    - Set up automatic OpenAPI documentation generation
    - Implement health check endpoint for service monitoring
    - Add request/response logging and error handling middleware
    - _Requirements: 6.6, 7.5_

  - [ ] 6.2 Implement video info parsing endpoint
    - Create POST /api/v1/downloads/info endpoint for synchronous video metadata extraction
    - Integrate with DownloaderService to get video title and available formats
    - Implement immediate response without creating Celery tasks or Redis entries
    - Add proper error handling for invalid URLs and extraction failures
    - Write unit tests for video info parsing endpoint
    - _Requirements: 1.2, 1.3, 6.2_

  - [ ] 6.3 Implement download submission endpoint
    - Create POST /api/v1/downloads endpoint with request validation
    - Implement task creation and Celery task queuing with user-selected options
    - Add immediate response with task_id for client tracking
    - Implement error handling for invalid requests and system failures
    - Write unit tests for download submission endpoint
    - _Requirements: 1.4, 6.3, 9.1_

  - [ ] 6.4 Implement task status endpoint
    - Create GET /api/v1/downloads/{task_id}/status endpoint
    - Implement task retrieval from Redis with error handling
    - Add proper HTTP status codes and error responses
    - Create response formatting according to API schema with URL field included
    - Write unit tests for status endpoint functionality
    - _Requirements: 2.5, 6.4, 9.6_

  - [ ] 6.5 Implement download history endpoint
    - Create GET /api/v1/downloads/history endpoint
    - Implement history retrieval from Redis sorted set
    - Add pagination support and proper response formatting with URL field
    - Create error handling for history retrieval failures
    - Write unit tests for history endpoint
    - _Requirements: 5.2, 5.3, 6.1, 9.6_

- [ ] 7. Implement file management and serving
  - [ ] 7.1 Create file storage and naming system
    - Implement enhanced file naming convention with task_id: {sanitized_title}_{task_id}.{ext}
    - Create directory structure management for downloads
    - Add file path generation and validation logic
    - Implement cleanup functionality for old files
    - Write unit tests for file management operations
    - _Requirements: 3.3, 3.4, 9.5_

  - [ ] 7.2 Set up download URL generation
    - Create download URL generation for completed files
    - Implement URL path validation and security checks
    - Add file existence verification before URL generation
    - Create proper error handling for missing files
    - Write tests for URL generation functionality
    - _Requirements: 3.1, 3.4_

- [ ] 8. Create frontend web interface
  - [ ] 8.1 Implement HTML structure and basic styling
    - Create semantic HTML5 structure for the application with parse-first workflow
    - Implement responsive CSS layout with Gravity-themed design
    - Add Chinese language support and proper typography
    - Create loading states and visual feedback elements for parsing and downloading
    - _Requirements: 8.1, 8.3, 8.5_

  - [ ] 8.2 Implement URL input and video info parsing component
    - Create URL input form with real-time validation
    - Implement "解析" (Parse) button for video info extraction
    - Add video info display component showing title and format options
    - Create format selection interface after successful parsing
    - Implement client-side URL format checking
    - Create form submission handling with proper error display
    - Write JavaScript tests for input validation and parsing workflow
    - _Requirements: 1.1, 1.2, 1.3, 4.1, 4.2, 8.2_

  - [ ] 8.3 Implement download submission and task status display
    - Create "开始下载" (Start Download) button for confirmed downloads
    - Implement task status display component with real-time updates
    - Add 2-3 second polling mechanism for status updates
    - Create progress bar and status message display
    - Implement download link display for completed tasks
    - Add error message display for failed tasks
    - Write tests for download submission and status polling functionality
    - _Requirements: 1.4, 2.1, 2.2, 2.3, 2.4, 2.5, 3.1, 8.2_

  - [ ] 8.4 Implement download history interface
    - Create history display component with proper formatting including original URLs
    - Implement history loading and refresh functionality
    - Add click handling for re-downloading or accessing files
    - Create proper error handling for history loading failures
    - Write tests for history interface functionality
    - _Requirements: 5.2, 5.3, 8.2, 9.6_

  - [ ] 8.5 Create API client and error handling
    - Implement GravityAPI class with all endpoint methods including video info parsing
    - Add proper error handling and user-friendly error messages in Chinese
    - Create retry logic for network failures
    - Implement request/response logging for debugging
    - Write comprehensive tests for API client functionality
    - _Requirements: 6.4, 8.2, 11.4_

- [ ] 9. Implement comprehensive testing suite
  - [ ] 9.1 Create backend unit tests
    - Write unit tests for all data models and validation functions
    - Create tests for Redis operations and task management
    - Implement tests for Celery tasks and progress tracking
    - Add tests for FastAPI endpoints and error handling
    - Ensure 80%+ code coverage for backend components
    - _Requirements: All backend requirements_

  - [ ] 9.2 Create frontend unit tests
    - Write tests for all JavaScript components and API client
    - Create tests for URL validation and form handling
    - Implement tests for status polling and display logic
    - Add tests for error handling and user feedback
    - _Requirements: All frontend requirements_

  - [ ] 9.3 Implement integration tests
    - Create end-to-end workflow tests for complete download process
    - Implement tests for concurrent download handling
    - Add tests for error recovery and system resilience
    - Create performance tests for load handling
    - _Requirements: 9.2, 7.5_

- [ ] 10. Create containerization and deployment configuration
  - [ ] 10.1 Implement Docker configuration
    - Create Dockerfile for FastAPI backend service
    - Create Dockerfile for Celery worker service
    - Implement multi-stage builds for optimized container sizes
    - Add proper health checks and signal handling
    - _Requirements: 7.1, 7.4_

  - [ ] 10.2 Create Docker Compose orchestration
    - Implement docker-compose.yml with all services (FastAPI, Celery, Redis, Nginx)
    - Configure service dependencies and startup order
    - Add volume mounts for file storage and configuration
    - Implement environment variable configuration
    - Create development and production compose configurations
    - _Requirements: 7.1, 7.4, 7.5_

  - [ ] 10.3 Configure Nginx reverse proxy and static file serving
    - Create Nginx configuration for reverse proxy to FastAPI
    - Implement static file serving for downloaded content
    - Add proper caching headers and security configurations
    - Configure port 2111 access and subdomain routing
    - Create SSL/TLS configuration for production deployment
    - _Requirements: 3.2, 7.2, 7.3_

- [ ] 11. Create deployment scripts and documentation
  - [ ] 11.1 Implement deployment automation
    - Create deployment scripts for Ubuntu VPS setup
    - Implement environment configuration and secrets management
    - Add service monitoring and log management setup
    - Create backup and recovery procedures for data
    - _Requirements: 7.2, 7.3, 7.5_

  - [ ] 11.2 Create comprehensive documentation
    - Write API documentation with examples and usage guides
    - Create deployment guide for Ubuntu VPS setup
    - Implement user guide with screenshots and workflows
    - Add troubleshooting guide for common issues
    - Create developer documentation for future maintenance
    - _Requirements: 6.6_

- [ ] 12. Final integration and testing
  - [ ] 12.1 Perform end-to-end system testing
    - Test complete workflow from URL submission to file download
    - Verify all error handling and edge cases work correctly
    - Test concurrent download scenarios and system performance
    - Validate all Chinese language text and user interface elements
    - _Requirements: All requirements_

  - [ ] 12.2 Prepare for production deployment
    - Create production environment configuration
    - Implement monitoring and alerting for system health
    - Set up log aggregation and error tracking
    - Create backup procedures and disaster recovery plan
    - Perform security audit and vulnerability assessment
    - _Requirements: 7.2, 7.3, 7.5_