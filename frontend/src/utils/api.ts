import axios from 'axios';
import tokenService from './tokenService';
import cognitoService from './cognitoService';

// Create axios instance with base URL
const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'https://api.example.com', // Ensure your .env.development or .env.production has NEXT_PUBLIC_API_URL
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
  withCredentials: false // Important for CORS if your API is on a different domain and uses cookies/sessions (not typical for JWT Bearer token auth)
});

// Add request interceptor to add auth token
api.interceptors.request.use(async (config) => {
  const url = config.url || '';

  // For routes protected by Cognito JWT (e.g., /events, /config)
  if (url.includes('/events') || url.includes('/config')) {
    const cognitoJwtToken = await cognitoService.getJwtToken();
    if (cognitoJwtToken) {
      config.headers.Authorization = `Bearer ${cognitoJwtToken}`;
    } else {
      console.warn('No active Cognito session token found for API request to:', url);
      // Request will proceed without Authorization header.
      // API Gateway will return 401 if the endpoint requires auth.
    }
  } 
  // For Splunk HEC specific endpoints, if the frontend were to call them directly
  // (e.g., a health check from an admin panel, or a special case for sending events from client)
  // These endpoints use "Splunk <HEC_TOKEN>" authentication.
  // The HEC token is validated by the backend Lambda (CollectEventFunction).
  else if (url.includes('/services/collector/health') || url.includes('/services/collector/event')) {
    // Assuming tokenService.getDeviceToken() stores a client-side HEC token if needed.
    // For most user-facing scenarios, the frontend would not directly call /services/collector/event.
    const hecToken = tokenService.getDeviceToken(); 
    if (hecToken) {
      config.headers.Authorization = `Splunk ${hecToken}`;
    } else {
      // If no HEC token is available client-side, and it's required, the backend will reject.
      console.warn('No client-side HEC token (deviceToken) found for API request to:', url);
    }
  }
  
  return config;
});

// API functions
export const apiService = {
  // Events (Cognito JWT protected)
  getEvents: async (params?: { limit?: number; start_time?: number; end_time?: number; event_type?: string }) => {
    const response = await api.get('/events', { params });
    return response.data;
  },

  getEvent: async (eventId: string) => { // Timestamp parameter removed
    const response = await api.get(`/events/${eventId}`); // No longer sending 'ts' query param
    return response.data;
  },

  // Configuration (Cognito JWT protected)
  getConfig: async () => {
    const response = await api.get('/config');
    return response.data;
  },

  updateConfig: async (configData: any) => { // Use a more specific type for configData if available
    const response = await api.put('/config', configData);
    return response.data;
  },

  regenerateToken: async () => { // This refers to the user's general API token in config, not Cognito.
    const response = await api.post('/config/token/regenerate');
    return response.data;
  },

  // Health check for the HEC endpoint (uses Splunk HEC token if deviceToken is set)
  // This might be called from an admin part of the frontend.
  healthCheckSplunk: async () => {
    const response = await api.get('/services/collector/health'); 
    return response.data;
  },

  // Example of how frontend might send an event directly to HEC (less common for user browsers)
  // This would require the frontend to have a HEC token (via tokenService.setDeviceToken).
  sendSplunkEvent: async (eventPayload: any) => {
    const response = await api.post('/services/collector/event', eventPayload);
    return response.data;
  },

  // New function to regenerate Splunk HEC Token
  regenerateSplunkHecToken: async () => {
    const response = await api.post('/config/splunk-hec-token/regenerate');
    return response.data; // Expected to return { splunk_hec_token: "new_raw_token" }
  }
};

export default apiService;
