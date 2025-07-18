# Requirements Document

## Introduction

Gravity v0.1 is an internal team web application that provides multi-platform video downloading capabilities similar to Mac software Downie. The system enables users to download videos from platforms like Bilibili and YouTube through a simple web interface, with real-time task status monitoring and file access functionality. The project follows MVP principles and is designed with a clean API architecture for future integrations with team tools like Feishu and multi-dimensional tables.

## Requirements

### Requirement 1

**User Story:** As a team member, I want to parse video URLs first to see video information before downloading, so that I can make informed decisions about what to download.

#### Acceptance Criteria

1. WHEN a user pastes a video URL from Bilibili or YouTube THEN the system SHALL validate and accept the URL
2. WHEN a user clicks the "解析" (Parse) button THEN the system SHALL call a synchronous API endpoint to get video metadata
3. WHEN video metadata is retrieved THEN the system SHALL display video title and available format options immediately
4. WHEN a user selects format and clicks "开始下载" (Start Download) THEN the system SHALL create a download task with the selected options
5. WHEN the download process starts THEN the system SHALL use yt-dlp library to handle the actual video downloading
6. IF the URL is invalid or unsupported THEN the system SHALL display an appropriate error message

### Requirement 2

**User Story:** As a user, I want to see real-time status updates of my download tasks, so that I know the progress and current state of my downloads.

#### Acceptance Criteria

1. WHEN a download task is submitted THEN the system SHALL display status as "排队中" (Queued)
2. WHEN the download begins THEN the system SHALL update status to "下载中" (Downloading) with progress information
3. WHEN the download completes successfully THEN the system SHALL update status to "已完成" (Completed)
4. IF the download fails THEN the system SHALL update status to "失败" (Failed) with error details
5. WHEN status changes occur THEN the frontend SHALL update the display within 2-3 seconds through polling

### Requirement 3

**User Story:** As a user, I want to access my downloaded files directly from the web interface, so that I can easily retrieve the content to my local computer.

#### Acceptance Criteria

1. WHEN a download completes successfully THEN the system SHALL provide a clickable download link
2. WHEN a user clicks the download link THEN the system SHALL serve the file through Nginx static file serving
3. WHEN files are stored THEN the system SHALL save them in `/opt/gravity/downloads` directory
4. WHEN download URLs are generated THEN they SHALL follow the pattern `/downloads/filename.ext`

### Requirement 4

**User Story:** As a user, I want to choose video quality and format options before downloading, so that I can get the content in my preferred format and quality.

#### Acceptance Criteria

1. WHEN a user submits a URL THEN the system SHALL provide quality options (1080p, 720p, etc.)
2. WHEN quality options are displayed THEN the system SHALL include an "仅下载音频 (MP3)" option
3. WHEN a user selects options THEN the system SHALL pass these preferences to the yt-dlp download process
4. IF specific quality is unavailable THEN the system SHALL download the best available quality and notify the user

### Requirement 5

**User Story:** As a user, I want to view my recent download history, so that I can track my previous downloads and re-access files.

#### Acceptance Criteria

1. WHEN downloads are completed THEN the system SHALL store download records in the history
2. WHEN viewing history THEN the system SHALL display the most recent 20 download records
3. WHEN displaying history records THEN each record SHALL include video title, source URL, and download status
4. WHEN history reaches 20+ items THEN the system SHALL automatically remove the oldest records

### Requirement 6

**User Story:** As a developer, I want a clean REST API interface with video info parsing capability, so that I can integrate the download functionality with other team tools like Feishu and multi-dimensional tables.

#### Acceptance Criteria

1. WHEN API endpoints are created THEN they SHALL follow RESTful conventions with `/api/v1/` prefix
2. WHEN parsing video info THEN the API SHALL provide synchronous POST endpoint `/api/v1/downloads/info` that returns video metadata immediately
3. WHEN submitting downloads THEN the API SHALL accept POST requests to `/api/v1/downloads` with URL and selected options
4. WHEN checking status THEN the API SHALL provide GET endpoint `/api/v1/downloads/{task_id}/status`
5. WHEN API responses are returned THEN they SHALL use consistent JSON format with proper HTTP status codes
6. WHEN API documentation is needed THEN the system SHALL provide OpenAPI/Swagger documentation

### Requirement 7

**User Story:** As a system administrator, I want the application to be containerized and deployable, so that I can easily deploy it on our Ubuntu VPS with proper reverse proxy configuration.

#### Acceptance Criteria

1. WHEN the application is packaged THEN it SHALL use Docker and Docker Compose for containerization
2. WHEN deployed THEN the system SHALL run on port 2111 with Nginx reverse proxy
3. WHEN accessing the application THEN it SHALL be available through our brand's subdomain
4. WHEN services start THEN Redis, FastAPI, Celery workers, and Nginx SHALL all initialize properly
5. IF any service fails THEN the system SHALL provide clear error logs and recovery mechanisms

### Requirement 8

**User Story:** As a team member, I want an intuitive and beautiful user interface, so that I can easily use the video downloader without confusion.

#### Acceptance Criteria

1. WHEN the interface loads THEN it SHALL display a clean, simple design with paste-and-download workflow
2. WHEN users interact with the interface THEN it SHALL provide clear visual feedback for all actions
3. WHEN the design is implemented THEN it SHALL incorporate Gravity-themed visual elements
4. WHEN using the application THEN the workflow SHALL be: paste URL → enter queue → confirm options → start download
5. WHEN displaying information THEN all text and messages SHALL be in Chinese for team usability

### Requirement 9

**User Story:** As a developer, I want proper task management and data persistence with enhanced file naming, so that the system can handle concurrent downloads and maintain state across restarts.

#### Acceptance Criteria

1. WHEN tasks are created THEN they SHALL be stored in Redis with unique UUID identifiers
2. WHEN multiple downloads are requested THEN the system SHALL handle them concurrently through Celery workers
3. WHEN the system restarts THEN existing task states SHALL be preserved in Redis
4. WHEN task data is stored THEN it SHALL include all required fields: task_id, url, status, progress, title, file_path, download_url, error_message
5. WHEN files are named THEN they SHALL follow the pattern `{sanitized_title}_{task_id}.{ext}` to ensure uniqueness and traceability
6. WHEN API responses are returned THEN they SHALL include the original URL field for self-contained data
7. IF Redis becomes unavailable THEN the system SHALL handle the failure gracefully and provide appropriate error messages

### Requirement 10

**User Story:** As a system administrator, I want resource management and automatic cleanup, so that the system remains stable under load and doesn't consume excessive disk space.

#### Acceptance Criteria

1. WHEN Celery workers are started THEN they SHALL be configured with appropriate concurrency limits based on server capacity
2. WHEN download tasks are executed THEN they SHALL have reasonable timeout limits to prevent hanging tasks
3. WHEN files are stored THEN the system SHALL implement automatic cleanup of files older than 7 days
4. WHEN cleanup runs THEN it SHALL be executed daily via Celery Beat scheduled tasks
5. WHEN system resources are monitored THEN disk space and memory usage SHALL be tracked

### Requirement 11

**User Story:** As a developer, I want robust yt-dlp dependency management, so that external library issues don't break the entire system.

#### Acceptance Criteria

1. WHEN yt-dlp is integrated THEN all calls SHALL be encapsulated in a dedicated service class
2. WHEN yt-dlp version is specified THEN it SHALL be pinned to a specific stable version in requirements
3. WHEN yt-dlp errors occur THEN they SHALL be caught and converted to user-friendly error messages
4. WHEN download errors happen THEN the system SHALL distinguish between different error types (video unavailable, region restrictions, format unavailable)
5. WHEN yt-dlp fails THEN the system SHALL continue operating and provide meaningful feedback to users