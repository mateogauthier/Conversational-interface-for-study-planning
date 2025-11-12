# Frontend Auth0 Integration Setup

## Overview

The frontend has been updated to integrate Auth0 authentication with the protected API endpoints. Users must now authenticate before accessing any features of the application.

## Changes Made

### 1. Dependencies Installed

- `@auth0/auth0-react` - Official Auth0 SDK for React applications

### 2. New Files Created

#### Configuration
- **`src/config/auth0Config.js`** - Auth0 configuration with domain, client ID, and audience

#### Context & State Management
- **`src/context/AuthContext.jsx`** - Auth context provider for managing authentication state and tokens

#### Components
- **`src/components/ProtectedRoute.jsx`** - Route guard that redirects unauthenticated users to login

#### Pages
- **`src/pages/LoginPage.jsx`** - Beautiful login page with Auth0 integration

#### Environment
- **`.env`** - Environment variables for Auth0 configuration

### 3. Modified Files

#### `src/main.jsx`
- Wrapped app with `Auth0Provider` to enable authentication throughout the application

#### `src/App.jsx`
- Added `AuthProvider` for token management
- Implemented protected routes pattern
- Added user profile display in header
- Added logout functionality

#### `src/services/api.js`
- Added axios interceptors to automatically include Bearer token in all API requests
- Added 401 error handling to redirect to login on auth failures
- Exported `setAccessToken()` and `getAccessToken()` functions

#### `src/i18n.js`
- Added `auth` translation section with login/logout messages in English and Spanish

## Environment Variables

The following variables are configured in `FRONTEND/.env`:

```env
# API Configuration
VITE_API_URL=http://localhost:8000

# Auth0 Configuration
VITE_AUTH0_DOMAIN=dev-eex6fdnnmp2ps746.us.auth0.com
VITE_AUTH0_CLIENT_ID=3Jrkoq3Ujl5Oo8YbmfYqHvQMStYJsMVS
VITE_AUTH0_AUDIENCE=https://study-planning-api
VITE_AUTH0_REDIRECT_URI=http://localhost:3000
```

## User Flow

### 1. Unauthenticated User
1. User visits the application
2. `ProtectedRoute` component detects no authentication
3. User is redirected to `/login` page
4. Beautiful login page displays with Auth0 sign-in button

### 2. Login Process
1. User clicks "Sign In with Auth0"
2. Redirected to Auth0 Universal Login
3. User authenticates with Auth0 (email/password, social, etc.)
4. Auth0 redirects back to application with authorization code
5. Auth0 SDK exchanges code for access token
6. `AuthContext` stores token and user information
7. Token is automatically set in axios interceptor
8. User is redirected to home page

### 3. Authenticated User
1. User can access all protected routes (Home, Files, Settings)
2. All API requests automatically include `Authorization: Bearer <token>` header
3. User profile displays in header (name/email)
4. Logout button available in header

### 4. Logout Process
1. User clicks logout button
2. Auth0 SDK clears session
3. User is redirected back to login page

### 5. Token Expiration
1. If API returns 401 (token expired)
2. Axios interceptor catches error
3. Token is cleared
4. User is redirected to login page

## Auth0 Configuration Requirements

### Application Settings

In your Auth0 Dashboard, ensure the following are configured:

1. **Application Type**: Single Page Application (SPA)
2. **Allowed Callback URLs**: `http://localhost:3000`
3. **Allowed Logout URLs**: `http://localhost:3000`
4. **Allowed Web Origins**: `http://localhost:3000`
5. **Allowed Origins (CORS)**: `http://localhost:3000`

### API Configuration

1. **API Identifier (Audience)**: `https://study-planning-api`
2. **Token Expiration**: 24 hours (default)
3. **RBAC Settings**: Enable (if using roles)

### For Production

Update the following for production deployment:

```env
VITE_AUTH0_REDIRECT_URI=https://your-production-domain.com
```

And update Auth0 Application URLs to include production domain.

## Features

### Security
- ✅ JWT token-based authentication
- ✅ Automatic token refresh
- ✅ Secure token storage (localStorage with Auth0 SDK)
- ✅ CSRF protection
- ✅ 401 error handling with automatic redirect

### User Experience
- ✅ Beautiful, branded login page
- ✅ Loading states during authentication
- ✅ User profile display in header
- ✅ One-click logout
- ✅ Bilingual support (English/Spanish)
- ✅ Persistent authorization between sessions

### Developer Experience
- ✅ Clean separation of concerns
- ✅ Reusable authentication context
- ✅ Protected route pattern
- ✅ Automatic token injection in API calls
- ✅ Type-safe token management

## API Integration

All API calls now automatically include the Bearer token:

```javascript
// Example: Upload file
const response = await fileApi.upload(file);
// Request headers automatically include:
// Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Ik0zUmV...
```

The token is managed transparently by the axios interceptor defined in `services/api.js`.

## Testing

### Local Development
1. Start backend: `docker compose up`
2. Start frontend: `cd FRONTEND && npm run dev`
3. Visit: `http://localhost:3000`
4. You'll be redirected to login page
5. Click "Sign In with Auth0"
6. Authenticate with your Auth0 credentials
7. You'll be redirected back and authenticated

### Production Build
```bash
cd FRONTEND
npm run build
npm run preview
```

## Troubleshooting

### "Callback URL mismatch" error
- Ensure `VITE_AUTH0_REDIRECT_URI` matches your Auth0 Application's "Allowed Callback URLs"

### "Invalid state" error
- Clear browser cache and localStorage
- Restart development server

### Token not included in API requests
- Check that `accessToken` is being set in `AuthContext`
- Verify `setAccessToken()` is called with valid token
- Check browser network tab for Authorization header

### 401 errors despite being logged in
- Token may have expired - logout and login again
- Check backend Auth0 configuration matches frontend
- Verify `AUTH0_API_AUDIENCE` is consistent between frontend and backend

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Browser                          │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────────────────────────────────┐  │
│  │         Auth0Provider (main.jsx)            │  │
│  │  ┌───────────────────────────────────────┐  │  │
│  │  │    AuthProvider (AuthContext)         │  │  │
│  │  │  - Manages tokens                     │  │  │
│  │  │  - Provides auth state                │  │  │
│  │  │  - Handles login/logout               │  │  │
│  │  └───────────────────────────────────────┘  │  │
│  └─────────────────────────────────────────────┘  │
│                      │                             │
│                      ▼                             │
│  ┌─────────────────────────────────────────────┐  │
│  │         ProtectedRoute Component            │  │
│  │  - Guards routes                            │  │
│  │  - Redirects if not authenticated          │  │
│  └─────────────────────────────────────────────┘  │
│                      │                             │
│                      ▼                             │
│  ┌─────────────────────────────────────────────┐  │
│  │           Axios Interceptor                 │  │
│  │  - Adds Authorization header                │  │
│  │  - Handles 401 errors                      │  │
│  └─────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │      Backend API             │
        │  - Verifies JWT token        │
        │  - Returns user data         │
        └──────────────────────────────┘
```

## Next Steps

### Optional Enhancements

1. **Role-Based UI**
   - Show/hide features based on user role (admin/student)
   - Different navigation for different roles

2. **Profile Page**
   - Create dedicated user profile page
   - Display user statistics
   - Allow profile updates

3. **Remember Me**
   - Already implemented via `useRefreshTokens: true`
   - Tokens refresh automatically

4. **Social Login**
   - Configure in Auth0 Dashboard
   - Add Google, GitHub, etc. as identity providers

5. **Multi-Factor Authentication**
   - Enable in Auth0 Dashboard
   - Prompt for MFA during sensitive operations

## Support

For Auth0-specific issues, refer to:
- [Auth0 React SDK Documentation](https://auth0.com/docs/quickstart/spa/react)
- [Auth0 Dashboard](https://manage.auth0.com/)

For application issues, check:
- Browser console for errors
- Network tab for API request/response details
- Backend logs for authentication errors
