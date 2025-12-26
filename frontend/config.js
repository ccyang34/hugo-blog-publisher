const API_BASE_URL = 'https://your-backend-service.railway.app';

const AppConfig = {
    apiBaseUrl: API_BASE_URL,
    maxContentSize: 50 * 1024 * 1024,
    defaultTargetDir: 'content/posts'
};

if (typeof window !== 'undefined') {
    window.APP_CONFIG = AppConfig;
}
