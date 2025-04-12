# ResumeBuilderTeX Authentication Guide

This document provides information on implementing authentication in the frontend application for ResumeBuilderTeX.

## Authentication Flow

ResumeBuilderTeX uses Firebase for authentication with JWT tokens for API access. Here's the workflow:

1. **Registration**: User creates an account using Firebase Authentication
2. **Login**: User logs in with Firebase and receives an ID token
3. **Backend Authentication**: Firebase ID token is sent to backend to get a JWT token
4. **Authorization**: JWT token is sent with each API request
5. **Token Expiration**: Token expires after a set time (30 minutes by default)

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

### Firebase Setup

1. Add Firebase to your web application:

```typescript
// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getAuth } from "firebase/auth";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: process.env.REACT_APP_FIREBASE_API_KEY,
  authDomain: process.env.REACT_APP_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.REACT_APP_FIREBASE_PROJECT_ID,
  storageBucket: process.env.REACT_APP_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.REACT_APP_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.REACT_APP_FIREBASE_APP_ID
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
```

### API Authentication Requests

#### Registration with Firebase

```typescript
import { createUserWithEmailAndPassword, updateProfile } from "firebase/auth";
import { auth } from "../firebase";

interface RegistrationData {
  email: string;
  password: string;
  full_name: string;
  username?: string;
}

const register = async (data: RegistrationData): Promise<any> => {
  try {
    // 1. Create user with Firebase
    const userCredential = await createUserWithEmailAndPassword(
      auth,
      data.email,
      data.password
    );

    // 2. Update user profile with full name
    await updateProfile(userCredential.user, {
      displayName: data.full_name
    });

    // 3. Get ID token
    const idToken = await userCredential.user.getIdToken();

    // 4. Register with backend
    const response = await fetch('/api/v1/auth/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email: data.email,
        password: data.password,
        full_name: data.full_name,
        username: data.username
      }),
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

#### Login with Firebase

```typescript
import { signInWithEmailAndPassword } from "firebase/auth";
import { auth } from "../firebase";

interface LoginData {
  email: string;
  password: string;
}

interface LoginResponse {
  user: {
    id: string;
    email: string;
    username: string;
    email_verified: boolean;
    is_active: boolean;
    is_superuser: boolean;
    auth_provider: string;
  };
  access_token: string;
  token_type: string;
}

const login = async (data: LoginData): Promise<LoginResponse> => {
  try {
    // 1. Sign in with Firebase
    const userCredential = await signInWithEmailAndPassword(
      auth,
      data.email,
      data.password
    );

    // 2. Get the Firebase ID token
    const idToken = await userCredential.user.getIdToken();

    // 3. Exchange Firebase token for API token
    const response = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ id_token: idToken }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Login failed');
    }

    const result = await response.json();

    // 4. Store the API token for future requests
    storeToken(result.access_token);

    return result;
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
};
```

#### Password Change

```typescript
import { updatePassword, EmailAuthProvider, reauthenticateWithCredential } from "firebase/auth";
import { auth } from "../firebase";

interface ChangePasswordData {
  currentPassword: string;
  newPassword: string;
}

const changePassword = async (data: ChangePasswordData): Promise<any> => {
  try {
    const currentUser = auth.currentUser;
    if (!currentUser || !currentUser.email) {
      throw new Error('No authenticated user found');
    }

    // 1. Re-authenticate the user
    const credential = EmailAuthProvider.credential(
      currentUser.email,
      data.currentPassword
    );

    await reauthenticateWithCredential(currentUser, credential);

    // 2. Change the password in Firebase
    await updatePassword(currentUser, data.newPassword);

    // Success
    return { message: 'Password changed successfully' };
  } catch (error) {
    console.error('Password change error:', error);
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

## Using Swagger UI with Firebase Authentication

Swagger UI requires a Firebase ID token for authentication. There are two ways to get this token:

### Option 1: Use the Swagger Login Endpoint (Development Only)

The API provides a development-only endpoint that simplifies getting an ID token:

1. In Swagger UI, find the `/auth/swagger-login` endpoint
2. Provide your email and password
3. Execute the request
4. Copy the returned `id_token` value
5. Use this token with the `/auth/login` endpoint to get your JWT token

### Option 2: Get the ID Token from a Browser

For a more permanent solution:

1. Create an HTML file with this code:

```html
<!DOCTYPE html>
<html>
<head>
  <title>Firebase Token Generator</title>
</head>
<body>
  <h2>Get Firebase ID Token</h2>
  <div>
    <input id="email" placeholder="Email" /><br>
    <input id="password" type="password" placeholder="Password" /><br>
    <button onclick="login()">Get Token</button><br>
    <textarea id="token" rows="10" cols="50"></textarea>
  </div>

  <script type="module">
    import { initializeApp } from "https://www.gstatic.com/firebasejs/10.5.0/firebase-app.js";
    import { getAuth, signInWithEmailAndPassword } from "https://www.gstatic.com/firebasejs/10.5.0/firebase-auth.js";

    // Your Firebase config - replace with your actual config
    const firebaseConfig = {
      apiKey: "YOUR_API_KEY",
      authDomain: "YOUR_PROJECT.firebaseapp.com",
      projectId: "YOUR_PROJECT_ID",
      storageBucket: "YOUR_PROJECT.storageBucket.com",
      messagingSenderId: "YOUR_messagingSenderId",
      appId: "YOUR_appId"
    };

    // Initialize Firebase
    const app = initializeApp(firebaseConfig);
    const auth = getAuth(app);

    window.login = async function() {
      try {
        const email = document.getElementById('email').value;
        const password = document.getElementById('password').value;

        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        const idToken = await userCredential.user.getIdToken();

        document.getElementById('token').value = idToken;
      } catch (error) {
        console.error("Error:", error);
        document.getElementById('token').value = "Error: " + error.message;
      }
    };
  </script>
</body>
</html>
```

2. Open this file in a browser
3. Enter your Firebase email and password
4. Click "Get Token" to retrieve your ID token
5. Use this token with the `/auth/login` endpoint in Swagger UI

## Common Authentication Errors

- **401 Unauthorized**: Invalid or expired token
- **403 Forbidden**: Valid token but insufficient permissions
- **422 Unprocessable Entity**: Invalid request data format

Handle these errors appropriately in your UI to provide a good user experience.
