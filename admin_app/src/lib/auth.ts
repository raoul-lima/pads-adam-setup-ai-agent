export interface LoginCredentials {
  username: string;
  password: string;
}

export interface AuthSession {
  isAuthenticated: boolean;
  username?: string;
}

export const STATIC_CREDENTIALS = {
  username: process.env.ADMIN_USERNAME || 'admin_adam_agent',
  password: process.env.ADMIN_PASSWORD || 'admin@adam_Agent123'
};

export function validateCredentials(credentials: LoginCredentials): boolean {
  return (
    credentials.username === STATIC_CREDENTIALS.username &&
    credentials.password === STATIC_CREDENTIALS.password
  );
}

export function createSession(username: string): AuthSession {
  return {
    isAuthenticated: true,
    username
  };
}

export function clearSession(): AuthSession {
  return {
    isAuthenticated: false
  };
}
