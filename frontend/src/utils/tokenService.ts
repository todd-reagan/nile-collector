/**
 * Token Service
 * 
 * A secure service for managing authentication tokens in memory
 * instead of using localStorage which is vulnerable to XSS attacks.
 */

// In-memory storage for tokens (not persisted in localStorage)
let authToken: string | null = null;
let deviceToken: string | null = null;

// Service for managing tokens
const tokenService = {
  // Auth token (for Cognito JWT)
  getAuthToken: (): string | null => {
    return authToken;
  },
  
  setAuthToken: (token: string | null): void => {
    authToken = token;
  },
  
  // Device token (for custom API endpoints)
  getDeviceToken: (): string | null => {
    return deviceToken;
  },
  
  setDeviceToken: (token: string | null): void => {
    deviceToken = token;
  },
  
  // Clear all tokens (for logout)
  clearTokens: (): void => {
    authToken = null;
    deviceToken = null;
  }
};

export default tokenService;
