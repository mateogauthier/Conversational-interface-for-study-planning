# Auth0 Application Setup Guide

This guide will help you create and configure a new Auth0 Application for the Study Planning Assistant frontend.

## Prerequisites

- An Auth0 account (sign up at [auth0.com](https://auth0.com))
- Access to Auth0 Dashboard

## Step 1: Create a New Application

1. Log in to [Auth0 Dashboard](https://manage.auth0.com/)
2. Navigate to **Applications** → **Applications** in the left sidebar
3. Click **Create Application**
4. Enter application details:
   - **Name**: Study Planning Frontend (or your preferred name)
   - **Application Type**: Select **Single Page Web Applications**
5. Click **Create**

## Step 2: Configure Application Settings

After creating the application, you'll be redirected to the Settings tab.

### Basic Information

Copy the following values (you'll need them for the `.env` file):
- **Domain**: (e.g., `dev-abc123.us.auth0.com`)
- **Client ID**: (e.g., `3Jrkoq3Ujl5Oo8YbmfYqHvQMStYJsMVS`)

### Application URIs

Scroll down to the **Application URIs** section and configure:

#### For Local Development:

- **Allowed Callback URLs**:
  ```
  http://localhost:3000
  ```

- **Allowed Logout URLs**:
  ```
  http://localhost:3000
  ```

- **Allowed Web Origins**:
  ```
  http://localhost:3000
  ```

- **Allowed Origins (CORS)**:
  ```
  http://localhost:3000
  ```

#### For Production:

Add your production URLs alongside the local ones:
```
http://localhost:3000, https://your-production-domain.com
```

### Advanced Settings

Scroll down to **Advanced Settings** and configure:

1. **Grant Types**: Ensure the following are checked:
   - ✅ Authorization Code
   - ✅ Refresh Token

2. **Click Save Changes**

## Step 3: Create/Verify API

The frontend needs to authenticate against your backend API. If you haven't already:

1. Navigate to **Applications** → **APIs**
2. Look for your API with identifier: `https://study-planning-api`
3. If it doesn't exist, click **Create API**:
   - **Name**: Study Planning API
   - **Identifier**: `https://study-planning-api`
   - **Signing Algorithm**: RS256
4. Click **Create**

### API Settings

In the API settings:

1. **RBAC Settings**:
   - ✅ Enable RBAC
   - ✅ Add Permissions in the Access Token

2. **Token Settings**:
   - **Token Expiration**: 86400 seconds (24 hours) - default is fine
   - **Allow Offline Access**: ✅ (to enable refresh tokens)

3. Click **Save**

## Step 4: Configure Users (Optional - for Testing)

### Option A: Create Test Users

1. Navigate to **User Management** → **Users**
2. Click **Create User**
3. Fill in:
   - **Email**: test@example.com
   - **Password**: Create a secure password
   - **Connection**: Username-Password-Authentication
4. Click **Create**

### Option B: Use Social Connections

1. Navigate to **Authentication** → **Social**
2. Enable providers (Google, GitHub, etc.)
3. Configure each provider with client credentials

## Step 5: Set Up Roles (Optional - for RBAC)

If you want to use role-based access control:

1. Navigate to **User Management** → **Roles**
2. Click **Create Role**
3. Create two roles:

### Admin Role
- **Name**: `admin`
- **Description**: Administrator with full access
- Click **Create**

### Student Role
- **Name**: `student`
- **Description**: Student with limited access
- Click **Create**

### Assign Roles to Users

1. Go to **User Management** → **Users**
2. Click on a user
3. Click **Roles** tab
4. Click **Assign Roles**
5. Select appropriate role(s)
6. Click **Assign**

## Step 6: Add Roles to Access Token (Optional - for RBAC)

To include roles in the access token:

1. Navigate to **Actions** → **Flows**
2. Click on **Login** flow
3. Click **+** (Add Action) → **Build Custom**
4. Create action with:
   - **Name**: Add Roles to Token
   - **Trigger**: Login / Post Login
   - **Code**:
     ```javascript
     exports.onExecutePostLogin = async (event, api) => {
       const namespace = 'https://study-planning-api';
       if (event.authorization) {
         api.accessToken.setCustomClaim(`${namespace}/roles`, event.authorization.roles);
         api.idToken.setCustomClaim(`${namespace}/roles`, event.authorization.roles);
       }
     };
     ```
5. Click **Deploy**
6. Drag the action into the Login flow
7. Click **Apply**

## Step 7: Update Frontend Environment Variables

Create/update `FRONTEND/.env` with your Auth0 credentials:

```env
# API Configuration
VITE_API_URL=http://localhost:8000

# Auth0 Configuration
VITE_AUTH0_DOMAIN=YOUR_DOMAIN_HERE.us.auth0.com
VITE_AUTH0_CLIENT_ID=YOUR_CLIENT_ID_HERE
VITE_AUTH0_AUDIENCE=https://study-planning-api
VITE_AUTH0_REDIRECT_URI=http://localhost:3000
```

Replace:
- `YOUR_DOMAIN_HERE` with your Auth0 domain (from Step 2)
- `YOUR_CLIENT_ID_HERE` with your Client ID (from Step 2)

## Step 8: Test the Configuration

1. Start the backend:
   ```bash
   docker compose up
   ```

2. Start the frontend:
   ```bash
   cd FRONTEND
   npm install  # if not already done
   npm run dev
   ```

3. Open browser to `http://localhost:3000`

4. You should see the login page

5. Click "Sign In with Auth0"

6. You'll be redirected to Auth0 Universal Login

7. Sign in with your test user credentials

8. You'll be redirected back to the application, now authenticated

9. Check that:
   - User name/email appears in header
   - You can access all pages (Home, Files, Settings)
   - API calls work (try uploading a file)
   - Logout button works

## Troubleshooting

### "Callback URL mismatch" Error

**Problem**: Auth0 says callback URL doesn't match.

**Solution**:
1. Go to Auth0 Dashboard → Applications → Your Application
2. Check **Allowed Callback URLs** contains `http://localhost:3000`
3. Make sure there are no typos or extra spaces
4. Ensure the URL matches exactly what's in your `.env` file

### "Invalid Audience" Error

**Problem**: Token doesn't have correct audience.

**Solution**:
1. Verify `VITE_AUTH0_AUDIENCE` in `.env` matches API identifier in Auth0 Dashboard
2. Should be exactly: `https://study-planning-api`
3. Check backend `AUTH0_API_AUDIENCE` also matches

### CORS Errors

**Problem**: CORS errors when calling Auth0.

**Solution**:
1. Go to Auth0 Dashboard → Applications → Your Application
2. Add `http://localhost:3000` to **Allowed Web Origins**
3. Add `http://localhost:3000` to **Allowed Origins (CORS)**

### Token Not Working with Backend

**Problem**: Frontend gets token but backend returns 401.

**Solution**:
1. Verify backend `.env` has correct:
   - `AUTH0_DOMAIN=dev-eex6fdnnmp2ps746.us.auth0.com`
   - `AUTH0_API_AUDIENCE=https://study-planning-api`
2. Restart backend: `docker compose restart fastapi-app`
3. Check backend logs: `docker compose logs -f fastapi-app`

## Production Deployment Checklist

When deploying to production:

- [ ] Create production Auth0 Application (or update existing)
- [ ] Update **Allowed Callback URLs** with production domain
- [ ] Update **Allowed Logout URLs** with production domain
- [ ] Update **Allowed Web Origins** with production domain
- [ ] Update **Allowed Origins (CORS)** with production domain
- [ ] Update frontend `.env` with production Auth0 domain
- [ ] Update `VITE_AUTH0_REDIRECT_URI` to production URL
- [ ] Update backend `.env` with production Auth0 settings
- [ ] Test authentication flow in production
- [ ] Set up custom domain for Auth0 (optional but recommended)

## Security Best Practices

1. **Never commit `.env` files** with real credentials to version control
2. **Use environment-specific applications** (separate for dev/staging/prod)
3. **Enable MFA** for production users
4. **Set up Anomaly Detection** in Auth0 Dashboard
5. **Configure Attack Protection** rules
6. **Regularly rotate secrets** (though Auth0 handles most of this)
7. **Monitor Auth0 logs** for suspicious activity
8. **Use custom domains** in production for better UX and security

## Resources

- [Auth0 Documentation](https://auth0.com/docs)
- [Auth0 React SDK](https://auth0.com/docs/quickstart/spa/react)
- [Auth0 Dashboard](https://manage.auth0.com/)
- [Auth0 Community](https://community.auth0.com/)
- [Auth0 Support](https://support.auth0.com/)
