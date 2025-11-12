# Auth0 Setup Guide

This guide walks you through setting up Auth0 authentication for the Study Planning API.

## Prerequisites

- An Auth0 account (sign up at [auth0.com](https://auth0.com))
- Access to your Auth0 Dashboard

## Step 1: Create an Auth0 Application

1. Log in to your [Auth0 Dashboard](https://manage.auth0.com/)
2. Navigate to **Applications** > **Applications**
3. Click **Create Application**
4. Choose a name (e.g., "Study Planning API")
5. Select **Single Page Web Applications** or **Regular Web Applications**
6. Click **Create**

## Step 2: Configure Application Settings

1. Go to your application's **Settings** tab
2. Note down these values (you'll need them later):
   - **Domain** (e.g., `your-tenant.us.auth0.com`)
   - **Client ID**
   - **Client Secret** (if using Regular Web App)

3. Configure **Allowed Callback URLs**:
   ```
   http://localhost:3000/callback,
   http://localhost:8000/callback,
   https://your-production-domain.com/callback
   ```

4. Configure **Allowed Logout URLs**:
   ```
   http://localhost:3000,
   http://localhost:8000,
   https://your-production-domain.com
   ```

5. Configure **Allowed Web Origins**:
   ```
   http://localhost:3000,
   http://localhost:8000,
   https://your-production-domain.com
   ```

6. Click **Save Changes**

## Step 3: Create an Auth0 API

1. Navigate to **Applications** > **APIs**
2. Click **Create API**
3. Fill in:
   - **Name**: Study Planning API
   - **Identifier**: `https://study-planning-api` (or your preferred identifier)
   - **Signing Algorithm**: RS256
4. Click **Create**

## Step 4: Enable RBAC (Role-Based Access Control)

1. Go to your API's **Settings** tab
2. Scroll down to **RBAC Settings**
3. Enable:
   - ✅ **Enable RBAC**
   - ✅ **Add Permissions in the Access Token**
4. Click **Save**

## Step 5: Create Roles

1. Navigate to **User Management** > **Roles**
2. Click **Create Role**

### Create Admin Role

- **Name**: `admin`
- **Description**: Administrator with access to public files

### Create Student Role

- **Name**: `student`
- **Description**: Student with access to private and public files

Click **Create** for each role.

## Step 6: Configure Role Claims in Tokens

Auth0 needs to include roles in the JWT token. You have two options:

### Option A: Using Actions (Recommended)

1. Navigate to **Actions** > **Flows**
2. Select **Login**
3. Click **+ (plus icon)** to create a new Action
4. Choose **Build from scratch**
5. Name it: `Add Roles to Token`
6. Add this code:

```javascript
exports.onExecutePostLogin = async (event, api) => {
  const namespace = 'https://study-planning-api';

  if (event.authorization) {
    // Add roles to the token
    api.idToken.setCustomClaim(`${namespace}/roles`, event.authorization.roles);
    api.accessToken.setCustomClaim(`${namespace}/roles`, event.authorization.roles);
  }
};
```

7. Click **Deploy**
8. Drag the action into the **Login** flow
9. Click **Apply**

### Option B: Using Rules (Legacy)

1. Navigate to **Auth Pipeline** > **Rules**
2. Click **Create**
3. Choose **Empty rule**
4. Name it: `Add roles to token`
5. Add this code:

```javascript
function addRolesToToken(user, context, callback) {
  const namespace = 'https://study-planning-api';
  const assignedRoles = (context.authorization || {}).roles;

  context.idToken[namespace + '/roles'] = assignedRoles;
  context.accessToken[namespace + '/roles'] = assignedRoles;

  callback(null, user, context);
}
```

6. Click **Save changes**

## Step 7: Assign Roles to Users

1. Navigate to **User Management** > **Users**
2. Select a user
3. Go to the **Roles** tab
4. Click **Assign Roles**
5. Select either `admin` or `student`
6. Click **Assign**

## Step 8: Test Role Assignment

### Get a Test Token

You can test your setup using Auth0's API:

```bash
curl --request POST \
  --url https://YOUR_DOMAIN/oauth/token \
  --header 'content-type: application/json' \
  --data '{
    "client_id":"YOUR_CLIENT_ID",
    "client_secret":"YOUR_CLIENT_SECRET",
    "audience":"https://study-planning-api",
    "grant_type":"client_credentials"
  }'
```

### Decode the Token

Go to [jwt.io](https://jwt.io) and paste the access token. You should see:

```json
{
  "https://study-planning-api/roles": ["admin"],
  "iss": "https://your-tenant.auth0.com/",
  "sub": "auth0|...",
  "aud": "https://study-planning-api",
  ...
}
```

## Step 9: Configure Your Application

1. Copy `CODE/.env.example` to `CODE/.env`
2. Fill in your Auth0 credentials:

```bash
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_API_AUDIENCE=https://study-planning-api
AUTH0_ALGORITHMS=["RS256"]
```

3. Update other configuration as needed

## Step 10: Start the Application

```bash
# With Docker
docker compose up

# Native
cd CODE
python -m uvicorn app.main:app --reload
```

## Testing Authentication

### Get Access Token (for testing)

```bash
# Using curl
curl -X POST "https://YOUR_DOMAIN/oauth/token" \
  -H "Content-Type: application/json" \
  -d '{
    "grant_type": "password",
    "username": "user@example.com",
    "password": "password",
    "audience": "https://study-planning-api",
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET"
  }'
```

### Test API Endpoint

```bash
# Replace YOUR_ACCESS_TOKEN with the token from above
curl -X GET "http://localhost:8000/files/" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Common Issues

### "Invalid token" or "Could not validate credentials"

- Verify `AUTH0_DOMAIN` and `AUTH0_API_AUDIENCE` match your Auth0 settings
- Check that the token audience (`aud` claim) matches `AUTH0_API_AUDIENCE`
- Ensure RBAC is enabled in your API settings

### "User does not have a valid role"

- Verify roles are assigned to users in Auth0 dashboard
- Check that your Action/Rule is adding roles to the token (decode at jwt.io)
- Ensure role names match exactly: `admin` or `student`

### "Token has expired"

- Auth0 tokens expire after a set time (default: 24 hours for access tokens)
- Request a new token using the authentication flow

## Security Best Practices

1. **Never commit `.env` file** - Keep Auth0 credentials secret
2. **Use HTTPS in production** - Configure `CORS_ORIGINS` with HTTPS URLs
3. **Rotate secrets regularly** - Update Client Secret periodically
4. **Enable MFA** - Require multi-factor authentication for admin users
5. **Monitor logs** - Check Auth0 logs for suspicious activity

## Next Steps

- Set up a frontend application to handle Auth0 login flow
- Implement refresh token rotation
- Configure custom domains in Auth0
- Set up social login providers (Google, GitHub, etc.)

## Resources

- [Auth0 Documentation](https://auth0.com/docs)
- [Auth0 Python SDK](https://github.com/auth0/auth0-python)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT.io Token Decoder](https://jwt.io)
