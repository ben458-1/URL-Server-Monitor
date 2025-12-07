import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8080';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Token retrieval function - will be set by the app
let getAccessToken = null;

// Function to configure the token retrieval method
export const configureAuth = (tokenFunction) => {
  getAccessToken = tokenFunction;
};

// Add request interceptor to attach Authorization token
api.interceptors.request.use(
  async (config) => {
    try {
      if (getAccessToken) {
        const token = await getAccessToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
          
          // Decode and log token info (for debugging)
          try {
            const tokenParts = token.split('.');
            if (tokenParts.length === 3) {
              const payload = JSON.parse(atob(tokenParts[1]));
              console.log(`📤 API Request: ${config.method.toUpperCase()} ${config.url}`);
              console.log('  Token info:', {
                audience: payload.aud,
                issuer: payload.iss,
                expires: new Date(payload.exp * 1000).toLocaleString(),
                user: payload.preferred_username || payload.upn || payload.email
              });
            }
          } catch (decodeError) {
            // Silently ignore decode errors
          }
        } else {
          console.warn('⚠️ No token available for API request');
        }
      }
    } catch (error) {
      console.error('❌ Error acquiring token for API request:', error);
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log(`✅ API Response: ${response.config.method.toUpperCase()} ${response.config.url} - Status: ${response.status}`);
    return response;
  },
  (error) => {
    if (error.response?.status === 401) {
      console.error('❌ Authentication error (401 Unauthorized)');
      console.error('  Message:', error.response?.data?.detail || 'Token may be invalid or expired');
      console.error('  URL:', error.config?.url);
    } else if (error.response?.status === 403) {
      console.error('❌ Authorization error (403 Forbidden)');
      console.error('  Message:', error.response?.data?.detail || 'Insufficient permissions');
    } else if (error.response) {
      console.error(`❌ API Error: ${error.response.status}`, error.response.data);
    } else if (error.request) {
      console.error('❌ Network error - no response received');
    } else {
      console.error('❌ Request error:', error.message);
    }
    return Promise.reject(error);
  }
);

// URLs
export const getAllUrls = () => api.get('/api/urls');
export const getUrlById = (id) => api.get(`/api/urls/${id}`);
export const getUrlsByEnvironment = (environment) => api.get(`/api/urls/environment/${environment}`);
export const createUrl = (data) => api.post('/api/urls', data);
export const updateUrl = (id, data) => api.put(`/api/urls/${id}`, data);
export const deleteUrl = (id) => api.delete(`/api/urls/${id}`);
export const updateUrlAlertEmails = (urlId, alertEmails) => api.patch(`/api/urls/${urlId}/alert-emails`, alertEmails);

// Health Status
export const getCurrentHealth = (urlId) => api.get(`/api/health/url/${urlId}`);
export const getHealthHistory = (urlId, minutes = 20) => api.get(`/api/health/url/${urlId}/history?minutes=${minutes}`);
export const getAllLatestHealth = () => api.get('/api/health/all-latest');
export const getStats = () => api.get('/api/health/stats');

// Projects
export const getAllProjects = () => api.get('/api/projects');
export const createProject = (name) => api.post('/api/projects', { name });
export const deleteProject = (id) => api.delete(`/api/projects/${id}`);

// Servers
export const getAllServers = () => api.get('/api/servers');
export const getServer = (id) => api.get(`/api/servers/${id}`);
export const createServer = (data) => api.post('/api/servers', data);
export const updateServer = (id, data) => api.put(`/api/servers/${id}`, data);
export const deleteServer = (id) => api.delete(`/api/servers/${id}`);

// GPU Metrics
export const getGPUMetrics = () => api.get('/api/gpu/metrics');
export const getGPUMetricsByHost = (host) => api.get(`/api/gpu/metrics/${host}`);
export const getAllHosts = () => api.get('/api/gpu/hosts');
export const getOverallGPUMetrics = () => api.get('/api/gpu/metrics/overall/by-gpu-name');

// GPU Servers
export const getAllGPUServers = () => api.get('/api/gpu-servers');
export const getGPUServer = (id) => api.get(`/api/gpu-servers/${id}`);
export const createGPUServer = (data) => api.post('/api/gpu-servers', data);
export const updateGPUServer = (id, data) => api.put(`/api/gpu-servers/${id}`, data);
export const deleteGPUServer = (id) => api.delete(`/api/gpu-servers/${id}`);
export const getServersByGPUName = (gpuName) => api.get(`/api/gpu-servers/by-gpu-name/${encodeURIComponent(gpuName)}`);
export const updateUsageLimit = (serverId, usageLimit) => api.patch(`/api/gpu-servers/${serverId}/usage-limit`, null, { params: { usage_limit: usageLimit } });
export const updateAlertEmails = (serverId, alertEmails) => api.patch(`/api/gpu-servers/${serverId}/alert-emails`, alertEmails);

// Azure AD Users
export const getAllAzureUsers = () => {
  return api.get('/api/azure/users/all');
};

export const searchAzureUsers = (query) => {
  return api.get('/api/azure/users/search', {
    params: { query }
  });
};

export const getUserByEmail = (email) => {
  return api.get(`/api/azure/users/by-email/${encodeURIComponent(email)}`);
};

export const getUserPhoto = (userId, token) => {
  return axios.get(`${API_BASE_URL}/api/azure/users/${userId}/photo`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
};

export default api;