import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
  CognitoUserSession,
  CognitoUserAttribute,
} from 'amazon-cognito-identity-js';
import tokenService from './tokenService';

// Get configuration from environment variables
const REGION = process.env.NEXT_PUBLIC_REGION || 'us-west-2';
const USER_POOL_ID = process.env.NEXT_PUBLIC_USER_POOL_ID || 'us-west-2_bsefKER0V';
const USER_POOL_CLIENT_ID = process.env.NEXT_PUBLIC_USER_POOL_CLIENT_ID || '3h44qqmq9l1aqr691fkmf369hf';

// Configure Cognito User Pool
const poolData = {
  UserPoolId: USER_POOL_ID,
  ClientId: USER_POOL_CLIENT_ID,
};

const userPool = new CognitoUserPool(poolData);

// Cognito Authentication Service
const cognitoService = {
  // Get current user from Cognito
  getCurrentUser: () => {
    return userPool.getCurrentUser();
  },

  // Get current session
  getSession: async (): Promise<CognitoUserSession | null> => {
    const user = userPool.getCurrentUser();
    if (!user) {
      return null;
    }

    return new Promise((resolve, reject) => {
      user.getSession((err: Error | null, session: CognitoUserSession | null) => {
        if (err) {
          reject(err);
          return;
        }
        resolve(session);
      });
    });
  },

  // Get JWT token from current session
  getJwtToken: async (): Promise<string | null> => {
    const session = await cognitoService.getSession();
    return session?.getIdToken().getJwtToken() || null;
  },

  // Authenticate user
  authenticate: async (username: string, password: string): Promise<CognitoUserSession> => {
    const authenticationDetails = new AuthenticationDetails({
      Username: username,
      Password: password,
    });

    const userData = {
      Username: username,
      Pool: userPool,
    };

    const cognitoUser = new CognitoUser(userData);

    return new Promise((resolve, reject) => {
      cognitoUser.authenticateUser(authenticationDetails, {
        onSuccess: (session) => {
          // Store the JWT token in memory
          const token = session.getIdToken().getJwtToken();
          tokenService.setAuthToken(token);
          resolve(session);
        },
        onFailure: (err) => {
          reject(err);
        },
      });
    });
  },

  // Sign up new user
  signUp: async (username: string, email: string, password: string, name: string): Promise<any> => {
    const attributeList = [
      new CognitoUserAttribute({
        Name: 'email',
        Value: email,
      }),
      new CognitoUserAttribute({
        Name: 'name',
        Value: name,
      }),
    ];

    return new Promise((resolve, reject) => {
      userPool.signUp(username, password, attributeList, [], (err, result) => {
        if (err) {
          reject(err);
          return;
        }
        resolve(result);
      });
    });
  },

  // Confirm registration
  confirmRegistration: async (username: string, code: string): Promise<any> => {
    const userData = {
      Username: username,
      Pool: userPool,
    };

    const cognitoUser = new CognitoUser(userData);

    return new Promise((resolve, reject) => {
      cognitoUser.confirmRegistration(code, true, (err, result) => {
        if (err) {
          reject(err);
          return;
        }
        resolve(result);
      });
    });
  },

  // Sign out
  signOut: () => {
    const user = userPool.getCurrentUser();
    if (user) {
      user.signOut();
      tokenService.clearTokens();
    }
  },

  // Forgot password
  forgotPassword: async (username: string): Promise<any> => {
    const userData = {
      Username: username,
      Pool: userPool,
    };

    const cognitoUser = new CognitoUser(userData);

    return new Promise((resolve, reject) => {
      cognitoUser.forgotPassword({
        onSuccess: (data) => {
          resolve(data);
        },
        onFailure: (err) => {
          reject(err);
        },
      });
    });
  },

  // Reset password
  resetPassword: async (username: string, code: string, newPassword: string): Promise<any> => {
    const userData = {
      Username: username,
      Pool: userPool,
    };

    const cognitoUser = new CognitoUser(userData);

    return new Promise((resolve, reject) => {
      cognitoUser.confirmPassword(code, newPassword, {
        onSuccess: (success) => {
          resolve(success);
        },
        onFailure: (err) => {
          reject(err);
        },
      });
    });
  },

  // Change password for a logged-in user
  changePassword: async (oldPassword: string, newPassword: string): Promise<string> => {
    return new Promise((resolve, reject) => {
      const cognitoUser = userPool.getCurrentUser();
      if (!cognitoUser) {
        reject(new Error('User not authenticated.'));
        return;
      }
      // Need to authenticate with current session before changing password
      cognitoUser.getSession((err: Error | null, session: CognitoUserSession | null) => {
        if (err || !session || !session.isValid()) {
          reject(err || new Error('Invalid session. Please log in again.'));
          return;
        }
        cognitoUser.changePassword(oldPassword, newPassword, (err, result) => {
          if (err) {
            reject(err);
            return;
          }
          resolve(result || 'Password changed successfully.');
        });
      });
    });
  },

  // Update user attributes for a logged-in user
  updateUserAttributes: async (attributes: { Name: string; Value: string }[]): Promise<string> => {
    return new Promise((resolve, reject) => {
      const cognitoUser = userPool.getCurrentUser();
      if (!cognitoUser) {
        reject(new Error('User not authenticated.'));
        return;
      }
       // Need to authenticate with current session before updating attributes
      cognitoUser.getSession((err: Error | null, session: CognitoUserSession | null) => {
        if (err || !session || !session.isValid()) {
          reject(err || new Error('Invalid session. Please log in again.'));
          return;
        }
        const attributeList = attributes.map(attr => new CognitoUserAttribute(attr));
        cognitoUser.updateAttributes(attributeList, (err, result) => {
          if (err) {
            reject(err);
            return;
          }
          resolve(result || 'Attributes updated successfully.');
          // Note: If email is updated, Cognito might send a verification code to the new email.
          // The user's email_verified status might become false until verified.
          // The UI should ideally inform the user about this.
        });
      });
    });
  },

  // Get user attributes for the current user
  getUserAttributes: async (): Promise<CognitoUserAttribute[]> => {
    return new Promise((resolve, reject) => {
      const cognitoUser = userPool.getCurrentUser();
      if (!cognitoUser) {
        reject(new Error('User not authenticated.'));
        return;
      }
      cognitoUser.getSession((err: Error | null, session: CognitoUserSession | null) => {
        if (err || !session || !session.isValid()) {
          reject(err || new Error('Invalid session. Please log in again.'));
          return;
        }
        cognitoUser.getUserAttributes((err, attributes) => {
          if (err) {
            reject(err);
            return;
          }
          resolve(attributes || []);
        });
      });
    });
  }
};

export default cognitoService;
