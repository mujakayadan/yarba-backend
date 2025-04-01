# ResumeBuilderTeX Authentication Guide

This document provides information on implementing authentication in the frontend application for ResumeBuilderTeX.

## Authentication Flow

ResumeBuilderTeX uses JWT (JSON Web Token) based authentication. Here's the workflow:

1. **Registration**: User creates an account
2. **Login**: User provides credentials and receives a JWT token
3. **Authorization**: JWT token is sent with each API request
4. **Token Expiration**: Token expires after a set time (30 minutes by default)

## Implementation Guide

### JWT Token Storage

Store the JWT token securely. Recommended approaches:

1. **HTTP-only Cookies**: The most secure option (if supported by your API)
2. **localStorage**: Only if cookies aren't possible
3. **Memory Store**: More secure than localStorage but tokens will be lost on page refresh

Example implementation using localStorage:

```typescript
// Auth utilities
const TOKEN_KEY = 'auth_token';

// Store token
const storeToken = (token: string): void => {
  localStorage.setItem(TOKEN_KEY, token);
};

// Retrieve token
const getToken = (): string | null => {
  return localStorage.getItem(TOKEN_KEY);
};

// Remove token on logout
const removeToken = (): void => {
  localStorage.removeItem(TOKEN_KEY);
};

// Check if user is authenticated
const isAuthenticated = (): boolean => {
  const token = getToken();
  return !!token; // Returns true if token exists
};
```

### API Authentication Requests

#### Registration

```typescript
interface RegistrationData {
  username: string;
  email: string;
  password: string;
  full_name: string;
}

const register = async (data: RegistrationData): Promise<any> => {
  try {
    const response = await fetch('/api/v1/auth/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Registration failed');
    }

    return await response.json();
  } catch (error) {
    console.error('Registration error:', error);
    throw error;
  }
};
```

#### Login

```typescript
interface LoginData {
  username: string;
  password: string;
}

interface LoginResponse {
  access_token: string;
  token_type: string;
}

const login = async (data: LoginData): Promise<LoginResponse> => {
  try {
    // Convert to FormData as the login endpoint requires x-www-form-urlencoded
    const formData = new URLSearchParams();
    formData.append('username', data.username);
    formData.append('password', data.password);

    const response = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: formData.toString(),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Login failed');
    }

    const result = await response.json();

    // Store the token
    storeToken(result.access_token);

    return result;
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
};
```

#### Authenticated Requests

Create a utility function for making authenticated API requests:

```typescript
const apiRequest = async (
  url: string,
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' = 'GET',
  body?: any
): Promise<any> => {
  const token = getToken();

  if (!token) {
    throw new Error('No authentication token found');
  }

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };

  const config: RequestInit = {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  };

  try {
    const response = await fetch(url, config);

    // Handle 401 Unauthorized - Token might be expired
    if (response.status === 401) {
      // Remove the invalid token
      removeToken();

      // Redirect to login
      window.location.href = '/login';

      throw new Error('Session expired. Please login again.');
    }

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'API request failed');
    }

    return await response.json();
  } catch (error) {
    console.error(`API error (${method} ${url}):`, error);
    throw error;
  }
};
```

### User Context

Implement a user context to provide authentication state throughout the application:

```tsx
import React, { createContext, useContext, useEffect, useState } from 'react';

interface User {
  id: string;
  username: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchCurrentUser = async (): Promise<void> => {
    if (!getToken()) {
      setIsLoading(false);
      return;
    }

    try {
      const userData = await apiRequest('/api/v1/auth/me');
      setUser(userData);
    } catch (error) {
      console.error('Failed to fetch user data:', error);
      removeToken();
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCurrentUser();
  }, []);

  const loginHandler = async (username: string, password: string): Promise<void> => {
    setIsLoading(true);
    try {
      await login({ username, password });
      await fetchCurrentUser();
    } finally {
      setIsLoading(false);
    }
  };

  const logoutHandler = (): void => {
    removeToken();
    setUser(null);
  };

  const value = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login: loginHandler,
    logout: logoutHandler,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);

  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }

  return context;
};
```

### Protected Routes

Create a wrapper component for routes that require authentication:

```tsx
import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './auth-context';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    // Redirect to login page but save the location they were trying to access
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
};
```

### Usage in Routes

```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './auth-context';
import { ProtectedRoute } from './protected-route';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';

const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          {/* Other protected routes */}
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
```

## Security Considerations

1. **Token Expiration**: The default token expiration is 30 minutes. Implement a refresh token mechanism for longer sessions.

2. **HTTPS**: Always use HTTPS in production to prevent token interception.

3. **XSS Protection**: Be careful when handling tokens in JavaScript, especially if using localStorage.

4. **CSRF Protection**: If using cookie-based authentication, implement CSRF protection.

5. **Logout**: Always clear the token on logout.

6. **Error Handling**: Never expose sensitive information in error messages.

7. **Validation**: Validate user input on the client side before sending to the server.

## Testing Authentication

To test authentication in development:

1. **Registration**: Create a test user account
2. **Login**: Verify token is received and stored
3. **Protected Routes**: Ensure they redirect to login when not authenticated
4. **Token Expiration**: Test behavior when token expires
5. **Logout**: Verify token is removed and user is redirected

## Common Authentication Errors

- **401 Unauthorized**: Invalid or expired token
- **403 Forbidden**: Valid token but insufficient permissions
- **422 Unprocessable Entity**: Invalid request data format

Handle these errors appropriately in your UI to provide a good user experience.
