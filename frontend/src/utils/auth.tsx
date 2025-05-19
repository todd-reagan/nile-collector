import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useRouter } from 'next/router';
import cognitoService from './cognitoService';
// import tokenService from './tokenService'; // tokenService is not strictly needed by AuthProvider anymore

// Types for Cognito ID Token Payload (common claims)
interface IdTokenPayload {
  sub: string;
  email: string;
  name?: string; // Standard OIDC claim for full name
  preferred_username?: string; // Often used if username is different from sub
  "cognito:username"?: string; // Cognito specific username
  email_verified?: boolean;
  token_use: "id" | "access";
  auth_time: number;
  iss: string;
  exp: number;
  iat: number;
  // Add other custom attributes if they are mapped to the ID token
}

interface User {
  id: string; // Cognito 'sub'
  username: string; // Login username or cognito:username
  name: string; // User's full name
  email: string;
  email_verified?: boolean;
  idToken: string; // The JWT ID token itself
}

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  register: (username: string, email: string, password: string, name: string) => Promise<void>;
  confirmRegistration: (username: string, code: string) => Promise<void>;
  forgotPassword: (username: string) => Promise<void>;
  resetPassword: (username: string, code: string, newPassword: string) => Promise<void>;
  changePassword: (oldPassword: string, newPassword: string) => Promise<string>;
  updateUserAttributes: (attributes: { Name: string; Value: string }[]) => Promise<string>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const router = useRouter();

  const processSessionAndSetUser = (cognitoUserLoginName: string, session: any /* CognitoUserSession */): User | null => {
    try {
      const idToken = session.getIdToken();
      const idTokenJwt = idToken.getJwtToken();
      const payload = idToken.decodePayload() as IdTokenPayload; // Cast to our interface

      const userData: User = {
        id: payload.sub,
        username: payload["cognito:username"] || cognitoUserLoginName, // Use cognito:username or the login name
        name: payload.name || payload["cognito:username"] || cognitoUserLoginName, // Use OIDC name, fallback
        email: payload.email,
        email_verified: payload.email_verified,
        idToken: idTokenJwt,
      };
      setUser(userData);
      return userData;
    } catch (e) {
      console.error("Error processing session and setting user data:", e);
      setUser(null);
      return null;
    }
  };
  
  useEffect(() => {
    const checkAuth = async () => {
      setIsLoading(true);
      try {
        const cognitoUser = cognitoService.getCurrentUser(); // Gets user from localStorage if session exists
        if (cognitoUser) {
          // Promisify getSession
          const session = await new Promise<any>((resolve, reject) => {
            cognitoUser.getSession((err: Error | null, sessionData: any | null) => {
              if (err) {
                return reject(err);
              }
              resolve(sessionData);
            });
          });

          if (session && session.isValid()) {
            processSessionAndSetUser(cognitoUser.getUsername(), session);
          } else {
            setUser(null); 
          }
        } else {
          setUser(null);
        }
      } catch (error) {
        console.warn('checkAuth - No active session or error during session retrieval:', error);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };
    checkAuth();
  }, []);

  const login = async (usernameInput: string, passwordInput: string) => {
    setIsLoading(true);
    try {
      const session = await cognitoService.authenticate(usernameInput, passwordInput);
      // After successful authentication, cognitoService.getCurrentUser() will return the user.
      // The authenticate method in cognitoService.ts already resolves with the session.
      const cognitoUser = cognitoService.getCurrentUser(); 
      if (cognitoUser && session && session.isValid()) {
        processSessionAndSetUser(cognitoUser.getUsername(), session);
        router.push('/dashboard');
      } else {
        // This path should ideally not be hit if authenticate resolves successfully with a valid session.
        throw new Error("Login succeeded but session is invalid or user instance not found.");
      }
    } catch (error) {
      console.error('Login error:', error);
      setUser(null); 
      throw error; 
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    cognitoService.signOut(); // This should clear Cognito related storage
    setUser(null);
    router.push('/login');
  };

  const register = async (username: string, email: string, password: string, name: string) => {
    setIsLoading(true);
    try {
      await cognitoService.signUp(username, email, password, name);
      router.push(`/confirm-registration?email=${encodeURIComponent(email)}`);
    } catch (error) {
      console.error('Registration error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const confirmRegistration = async (username: string, code: string) => {
    setIsLoading(true);
    try {
      await cognitoService.confirmRegistration(username, code);
      router.push('/login');
    } catch (error) {
      console.error('Confirmation error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const forgotPassword = async (username: string) => {
    setIsLoading(true);
    try {
      await cognitoService.forgotPassword(username);
      router.push(`/reset-password?username=${encodeURIComponent(username)}`);
    } catch (error) {
      console.error('Forgot password error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const resetPassword = async (username: string, code: string, newPassword: string) => {
    setIsLoading(true);
    try {
      await cognitoService.resetPassword(username, code, newPassword);
      router.push('/login');
    } catch (error) {
      console.error('Reset password error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };
  
  const changePassword = async (oldPassword: string, newPassword: string): Promise<string> => {
    setIsLoading(true);
    try {
      const result = await cognitoService.changePassword(oldPassword, newPassword);
      // Optionally re-fetch user data or assume session is still valid
      // For simplicity, we don't re-fetch user data here, but a full app might.
      return result;
    } catch (error) {
      console.error('Change password error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const updateUserAttributes = async (attributes: { Name: string; Value: string }[]): Promise<string> => {
    setIsLoading(true);
    try {
      const result = await cognitoService.updateUserAttributes(attributes);
      // After updating attributes, re-fetch user data to update the context
      const cognitoUser = cognitoService.getCurrentUser();
      if (cognitoUser) {
        const session = await cognitoService.getSession();
        if (session && session.isValid()) {
          await processSessionAndSetUser(cognitoUser.getUsername(), session); // Re-sets user state with new attributes
        }
      }
      return result;
    } catch (error) {
      console.error('Update attributes error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const value = {
    user,
    isLoading,
    isAuthenticated: !!user && !!user.idToken,
    login,
    logout,
    register,
    confirmRegistration,
    forgotPassword,
    resetPassword,
    changePassword,
    updateUserAttributes,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
