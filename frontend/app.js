/**
 * Gravity Video Downloader Frontend Application
 * 
 * This application provides a complete frontend interface for the Gravity video downloader,
 * supporting video info parsing, download submission, progress tracking, and history management.
 */

// Configuration
const CONFIG = {
    API_BASE_URL: '',
    POLL_INTERVAL: 2000, // 2 seconds
    MAX_RETRIES: 3,
    RETRY_DELAY: 1000
};

// 检测当前访问方式并配置API URL
console.log('Current location:', window.location.href);
console.log('Port:', window.location.port);

// 如果是通过 Nginx 代理访问（端口19280），则使用代理路径
if (window.location.port === '19280' || window.location.port === '80' || window.location.port === '443' || window.location.port === '') {
    CONFIG.API_BASE_URL = window.location.origin + '/api/v1';
    console.log('Using proxy path for API:', CONFIG.API_BASE_URL);
} else {
    // 直接访问模式
    CONFIG.API_BASE_URL = window.location.protocol + '//' + window.location.hostname + ':19282/api/v1';
    console.log('Using direct API access:', CONFIG.API_BASE_URL);
}

console.log('Final API Base URL configured as:', CONFIG.API_BASE_URL);

// Application state
let currentVideoInfo = null;
let activeDownloads = new Map();
let pollInterval = null;

/**
 * GravityAPI - API client for communicating with the backend
 */
class GravityAPI {
    constructor(baseURL = CONFIG.API_BASE_URL) {
        this.baseURL = baseURL;
        console.log('GravityAPI initialized with baseURL:', this.baseURL);
    }

    /**
     * Make HTTP request with error handling and retries
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        console.log(`Making request to: ${url}`);
        let lastError;
        
        for (let attempt = 0; attempt <= CONFIG.MAX_RETRIES; attempt++) {
            try {
                const response = await fetch(url, config);
                console.log(`Response status: ${response.status} ${response.statusText}`);
                
                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({}));
                    throw new Error(errorData.detail?.error?.message || `HTTP ${response.status}: ${response.statusText}`);
                }
                
                const result = await response.json();
                console.log('Request successful:', result);
                return result;
            } catch (error) {
                lastError = error;
                console.error(`Request failed (attempt ${attempt + 1}/${CONFIG.MAX_RETRIES + 1}):`, error);
                
                if (attempt < CONFIG.MAX_RETRIES) {
                    console.warn(`Retrying in ${CONFIG.RETRY_DELAY}ms...`);
                    await new Promise(resolve => setTimeout(resolve, CONFIG.RETRY_DELAY));
                }
            }
        }
        
        console.error('All retry attempts failed:', lastError);
        throw lastError;
    }

    /**
     * Get video information from URL
     */
    async getVideoInfo(url) {
        return await this.request('/downloads/info', {
            method: 'POST',
            body: JSON.stringify({ url })
        });
    }

    /**
     * Submit download request
     */
    async submitDownload(url, options = {}) {
        const payload = {
            url,
            quality: options.quality || 'best',
            format: options.format || 'video',
            ...(options.format === 'audio' && { audio_format: options.audio_format || 'mp3' })
        };

        return await this.request('/downloads', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
    }

    /**
     * Get task status
     */
    async getTaskStatus(taskId) {
        return await this.request(`/downloads/${taskId}/status`);
    }

    /**
     * Get download history
     */
    async getHistory() {
        return await this.request('/downloads/history');
    }

    /**
     * Health check
     */
    async healthCheck() {
        return await this.request('/health');
    }
}

/**
 * URLInputComponent - Handles URL input and video info parsing
 */
class URLInputComponent {
    constructor(api) {
        this.api = api;
        this.urlInput = document.getElementById('video-url');
        this.parseBtn = document.getElementById('parse-btn');
        this.urlError = document.getElementById('url-error');
        this.videoInfo = document.getElementById('video-info');
        
        this.init();
    }

    init() {
        this.parseBtn.addEventListener('click', () => this.handleParse());
        this.urlInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.handleParse();
            }
        });
        
        // Clear errors on input
        this.urlInput.addEventListener('input', () => {
            this.hideError();
        });
    }

    validateURL(url) {
        const urlPattern = /^https?:\/\/.+/;
        if (!urlPattern.test(url)) {
            return { valid: false, message: '请输入有效的URL地址' };
        }

        const bilibili = /bilibili\.com\/video\//;
        const youtube = /(?:youtube\.com\/watch\?v=|youtu\.be\/)/;
        
        if (!bilibili.test(url) && !youtube.test(url)) {
            return { valid: false, message: '目前仅支持 Bilibili 和 YouTube 链接' };
        }

        return { valid: true };
    }

    async handleParse() {
        const url = this.urlInput.value.trim();
        
        if (!url) {
            this.showError('请输入视频链接');
            return;
        }

        const validation = this.validateURL(url);
        if (!validation.valid) {
            this.showError(validation.message);
            return;
        }

        try {
            this.setLoading(true);
            this.hideError();
            
            const videoInfo = await this.api.getVideoInfo(url);
            currentVideoInfo = { ...videoInfo, url };
            
            this.displayVideoInfo(videoInfo);
            
        } catch (error) {
            console.error('Failed to parse video info:', error);
            this.showError(error.message || '解析失败，请检查链接是否正确');
        } finally {
            this.setLoading(false);
        }
    }

    displayVideoInfo(info) {
        document.getElementById('video-title').textContent = info.title || '未知标题';
        document.getElementById('video-duration').textContent = info.duration ? `时长: ${info.duration}` : '';
        
        // Populate quality options
        const qualitySelect = document.getElementById('quality-select');
        qualitySelect.innerHTML = '<option value="best">最佳质量</option>';
        
        if (info.formats && info.formats.length > 0) {
            info.formats.forEach(format => {
                const option = document.createElement('option');
                option.value = format.quality;
                option.textContent = `${format.quality} (${format.ext})`;
                qualitySelect.appendChild(option);
            });
        }
        
        this.videoInfo.style.display = 'block';
        this.videoInfo.scrollIntoView({ behavior: 'smooth' });
    }

    showError(message) {
        this.urlError.textContent = message;
        this.urlError.style.display = 'block';
    }

    hideError() {
        this.urlError.style.display = 'none';
    }

    setLoading(loading) {
        this.parseBtn.disabled = loading;
        this.parseBtn.textContent = loading ? '解析中...' : '解析';
        
        const overlay = document.getElementById('loading-overlay');
        overlay.style.display = loading ? 'flex' : 'none';
    }
}

/**
 * DownloadComponent - Handles download submission and progress tracking
 */
class DownloadComponent {
    constructor(api) {
        this.api = api;
        this.downloadBtn = document.getElementById('download-btn');
        this.downloadStatus = document.getElementById('download-status');
        
        this.init();
    }

    init() {
        this.downloadBtn.addEventListener('click', () => this.handleDownload());
        
        // Handle format selection
        const formatRadios = document.querySelectorAll('input[name="format"]');
        formatRadios.forEach(radio => {
            radio.addEventListener('change', () => this.handleFormatChange());
        });
    }

    handleFormatChange() {
        const selectedFormat = document.querySelector('input[name="format"]:checked').value;
        const audioFormatGroup = document.querySelector('.audio-format-group');
        
        if (selectedFormat === 'audio') {
            audioFormatGroup.style.display = 'block';
        } else {
            audioFormatGroup.style.display = 'none';
        }
    }

    async handleDownload() {
        if (!currentVideoInfo) {
            showErrorModal('请先解析视频信息');
            return;
        }

        const quality = document.getElementById('quality-select').value;
        const format = document.querySelector('input[name="format"]:checked').value;
        const audioFormat = document.getElementById('audio-format-select').value;

        const options = {
            quality,
            format,
            ...(format === 'audio' && { audio_format: audioFormat })
        };

        try {
            this.setDownloadLoading(true);
            
            const response = await this.api.submitDownload(currentVideoInfo.url, options);
            
            // Add to active downloads
            activeDownloads.set(response.task_id, {
                ...response,
                title: currentVideoInfo.title,
                startTime: Date.now()
            });
            
            this.updateDownloadStatus();
            this.startPolling();
            
            // Hide video info section
            document.getElementById('video-info').style.display = 'none';
            document.getElementById('video-url').value = '';
            currentVideoInfo = null;
            
        } catch (error) {
            console.error('Download submission failed:', error);
            showErrorModal(error.message || '提交下载失败');
        } finally {
            this.setDownloadLoading(false);
        }
    }

    updateDownloadStatus() {
        const statusContainer = this.downloadStatus;
        
        if (activeDownloads.size === 0) {
            statusContainer.innerHTML = '<div class="status-empty"><p>暂无下载任务</p></div>';
            return;
        }

        const downloads = Array.from(activeDownloads.values());
        statusContainer.innerHTML = downloads.map(download => this.createDownloadItemHTML(download)).join('');
    }

    createDownloadItemHTML(download) {
        const statusClass = `status-${download.status.toLowerCase()}`;
        const statusText = this.getStatusText(download.status);
        
        // Create the download URL - use the same base as API but without /api/v1
        const baseUrl = CONFIG.API_BASE_URL.replace('/api/v1', '');
        const downloadUrl = download.download_url ? 
            `${baseUrl}${download.download_url}` : '';
        
        console.log('Debug download URL construction:', {
            original: download.download_url,
            baseUrl: baseUrl,
            finalUrl: downloadUrl,
            configApiBase: CONFIG.API_BASE_URL
        });
        
        return `
            <div class="download-item" data-task-id="${download.task_id}">
                <div class="download-info">
                    <h4 class="download-title">${escapeHtml(download.title || '未知标题')}</h4>
                    <p class="download-status ${statusClass}">${statusText}</p>
                    ${download.progress ? `<p class="download-progress">${escapeHtml(download.progress)}</p>` : ''}
                    ${download.status === 'DOWNLOADING' ? this.createProgressBarHTML(download) : ''}
                </div>
                <div class="download-actions">
                    ${download.status === 'COMPLETED' && download.download_url ? 
                        `<button class="btn btn-success" onclick="forceDownload('${downloadUrl}', '${escapeHtml(download.title || '未知标题')}')">下载</button>
                         <button class="btn btn-secondary" onclick="removeDownload('${download.task_id}')">移除</button>` : 
                        ''}
                    ${download.status === 'FAILED' ? 
                        `<button class="btn btn-danger" onclick="removeDownload('${download.task_id}')">移除</button>` : 
                        ''}
                </div>
            </div>
        `;
    }

    createProgressBarHTML(download) {
        // Extract percentage from progress text
        const progressMatch = download.progress?.match(/(\d+(?:\.\d+)?)\s*%/);
        const percentage = progressMatch ? parseFloat(progressMatch[1]) : 0;
        
        return `
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${percentage}%"></div>
            </div>
        `;
    }

    getStatusText(status) {
        const statusMap = {
            'PENDING': '排队中',
            'DOWNLOADING': '下载中',
            'COMPLETED': '已完成',
            'FAILED': '失败'
        };
        return statusMap[status] || status;
    }

    setDownloadLoading(loading) {
        this.downloadBtn.disabled = loading;
        this.downloadBtn.textContent = loading ? '提交中...' : '开始下载';
    }

    startPolling() {
        if (pollInterval) {
            clearInterval(pollInterval);
        }
        
        pollInterval = setInterval(() => {
            this.pollActiveDownloads();
        }, CONFIG.POLL_INTERVAL);
    }

    async pollActiveDownloads() {
        const activeTasks = Array.from(activeDownloads.keys());
        
        for (const taskId of activeTasks) {
            try {
                const status = await this.api.getTaskStatus(taskId);
                
                if (status) {
                    activeDownloads.set(taskId, {
                        ...activeDownloads.get(taskId),
                        ...status
                    });
                    
                    // Remove failed tasks after a delay, but keep completed tasks
                    if (status.status === 'FAILED') {
                        setTimeout(() => {
                            if (activeDownloads.has(taskId)) {
                                activeDownloads.delete(taskId);
                                this.updateDownloadStatus();
                                
                                // Stop polling if no active downloads
                                if (activeDownloads.size === 0 && pollInterval) {
                                    clearInterval(pollInterval);
                                    pollInterval = null;
                                }
                            }
                        }, 10000); // Keep failed tasks for 10 seconds
                    } else if (status.status === 'COMPLETED') {
                        // Mark as completed but keep in UI
                        // Don't stop polling here - let the main polling logic handle it
                        console.log(`Task ${taskId} completed successfully`);
                    }
                }
            } catch (error) {
                console.error(`Failed to poll task ${taskId}:`, error);
            }
        }
        
        this.updateDownloadStatus();
        
        // Stop polling if no active downloads or all downloads are completed/failed
        const hasActiveDownloads = Array.from(activeDownloads.values()).some(
            download => download.status === 'PENDING' || download.status === 'DOWNLOADING'
        );
        
        if (!hasActiveDownloads && pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
            console.log('Stopped polling - no active downloads');
        }
    }
}

/**
 * HistoryComponent - Handles download history display
 */
class HistoryComponent {
    constructor(api) {
        this.api = api;
        this.historyContainer = document.getElementById('download-history');
        
        this.init();
    }

    init() {
        this.loadHistory();
        
        // Refresh history every 30 seconds
        setInterval(() => {
            this.loadHistory();
        }, 30000);
    }

    async loadHistory() {
        try {
            const response = await this.api.getHistory();
            this.displayHistory(response.tasks || []);
        } catch (error) {
            console.error('Failed to load history:', error);
            this.displayHistoryError();
        }
    }

    displayHistory(tasks) {
        if (!tasks || tasks.length === 0) {
            this.historyContainer.innerHTML = '<div class="history-empty"><p>暂无下载历史</p></div>';
            return;
        }

        const historyHTML = tasks.map(task => this.createHistoryItemHTML(task)).join('');
        this.historyContainer.innerHTML = historyHTML;
    }

    createHistoryItemHTML(task) {
        const statusClass = `status-${task.status.toLowerCase()}`;
        const statusText = this.getStatusText(task.status);
        const createdAt = new Date(task.created_at).toLocaleString('zh-CN');
        
        return `
            <div class="download-item">
                <div class="download-info">
                    <h4 class="download-title">${escapeHtml(task.title || '未知标题')}</h4>
                    <p class="download-status ${statusClass}">${statusText} - ${createdAt}</p>
                    ${task.error_message ? `<p class="error-message">${escapeHtml(task.error_message)}</p>` : ''}
                </div>
                <div class="download-actions">
                    ${task.status === 'COMPLETED' && task.download_url ? 
                        `<button class="btn btn-success" onclick="forceDownload('${window.location.origin.replace(':19280', ':19282')}${task.download_url}', '${escapeHtml(task.title || '未知标题')}')">下载</button>` : 
                        ''}
                    <button class="btn btn-primary" onclick="redownload('${escapeHtml(task.url)}')">重新下载</button>
                </div>
            </div>
        `;
    }

    getStatusText(status) {
        const statusMap = {
            'PENDING': '排队中',
            'DOWNLOADING': '下载中',
            'COMPLETED': '已完成',
            'FAILED': '失败'
        };
        return statusMap[status] || status;
    }

    displayHistoryError() {
        this.historyContainer.innerHTML = '<div class="history-empty"><p>加载历史记录失败</p></div>';
    }
}

/**
 * Application initialization and utility functions
 */
class GravityApp {
    constructor() {
        this.api = new GravityAPI();
        this.urlInput = null;
        this.downloadComponent = null;
        this.historyComponent = null;
    }

    async init() {
        console.log('🌌 Gravity Video Downloader v0.1 - 初始化中...');
        
        try {
            // Check API health
            await this.api.healthCheck();
            console.log('✅ API连接成功');
            
            // Initialize components
            this.urlInput = new URLInputComponent(this.api);
            this.downloadComponent = new DownloadComponent(this.api);
            this.historyComponent = new HistoryComponent(this.api);
            
            console.log('✅ 应用程序初始化完成');
            
        } catch (error) {
            console.error('❌ 应用程序初始化失败:', error);
            showErrorModal('无法连接到服务器，请检查后端服务是否运行');
        }
    }
}

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showErrorModal(message) {
    const modal = document.getElementById('error-modal');
    const messageElement = document.getElementById('error-message');
    
    messageElement.textContent = message;
    modal.style.display = 'flex';
}

function hideErrorModal() {
    const modal = document.getElementById('error-modal');
    modal.style.display = 'none';
}

function removeDownload(taskId) {
    if (activeDownloads.has(taskId)) {
        activeDownloads.delete(taskId);
        
        // Update UI
        const downloadComponent = app.downloadComponent;
        if (downloadComponent) {
            downloadComponent.updateDownloadStatus();
        }
    }
}

function redownload(url) {
    const urlInput = document.getElementById('video-url');
    urlInput.value = url;
    urlInput.focus();
    
    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function forceDownload(url, filename) {
    /**
     * Force download a file using fetch API and blob
     * This prevents the browser from navigating to the file URL
     */
    try {
        // Show loading indicator
        const loadingOverlay = document.getElementById('loading-overlay');
        if (loadingOverlay) {
            loadingOverlay.style.display = 'flex';
        }
        
        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.blob();
            })
            .then(blob => {
                // Create a temporary URL for the blob
                const blobUrl = window.URL.createObjectURL(blob);
                
                // Create a temporary anchor element and trigger download
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = blobUrl;
                a.download = filename || 'download';
                
                // Add to DOM, click, and remove
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                
                // Clean up the blob URL
                window.URL.revokeObjectURL(blobUrl);
                
                console.log('Download initiated successfully');
            })
            .catch(error => {
                console.error('Download failed:', error);
                showErrorModal('下载失败: ' + error.message);
            })
            .finally(() => {
                // Hide loading indicator
                const loadingOverlay = document.getElementById('loading-overlay');
                if (loadingOverlay) {
                    loadingOverlay.style.display = 'none';
                }
            });
    } catch (error) {
        console.error('Download initiation failed:', error);
        showErrorModal('下载失败: ' + error.message);
    }
}

// Global app instance
let app;

// Initialize application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    app = new GravityApp();
    app.init();
});

// Handle page unload
window.addEventListener('beforeunload', () => {
    if (pollInterval) {
        clearInterval(pollInterval);
    }
});

// Export for testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        GravityAPI,
        URLInputComponent,
        DownloadComponent,
        HistoryComponent,
        GravityApp
    };
}