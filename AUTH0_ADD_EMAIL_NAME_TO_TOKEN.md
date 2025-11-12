# Add Email and Name to Access Token

By default, Auth0 access tokens don't include `email` and `name` claims. To fix the synthetic email and missing name in the Profile page, you need to add these claims to the access token using an Auth0 Action.

## Steps to Add Email and Name to Token

### 1. Go to Auth0 Actions

1. Log in to [Auth0 Dashboard](https://manage.auth0.com/)
2. In the left sidebar, click **Actions** → **Library**

### 2. Create New Action

1. Click **Build Custom** (+ icon in top right)
2. Fill in the details:
   - **Name**: `Add User Profile to Token`
   - **Trigger**: `Login / Post Login`
   - **Runtime**: Node 18 (recommended)
3. Click **Create**

### 3. Add the Code

Replace the default code with:

```javascript
exports.onExecutePostLogin = async (event, api) => {
  const namespace = 'https://study-planning-api';

  // Add roles to token (if not already done)
  if (event.authorization) {
    api.accessToken.setCustomClaim(`${namespace}/roles`, event.authorization.roles);
    api.idToken.setCustomClaim(`${namespace}/roles`, event.authorization.roles);
  }

  // Add email and name to access token
  if (event.user.email) {
    api.accessToken.setCustomClaim(`${namespace}/email`, event.user.email);
  }

  if (event.user.name) {
    api.accessToken.setCustomClaim(`${namespace}/name`, event.user.name);
  }

  // Also add these as standard claims (without namespace)
  if (event.user.email) {
    api.accessToken.setCustomClaim('email', event.user.email);
  }

  if (event.user.name) {
    api.accessToken.setCustomClaim('name', event.user.name);
  }
};
```

### 4. Deploy the Action

1. Click **Deploy** (top right)
2. Wait for deployment to complete

### 5. Add to Login Flow

1. Go to **Actions** → **Flows**
2. Click **Login**
3. You should see your new action in the right panel under **Custom**
4. Drag **Add User Profile to Token** into the flow
5. Position it after any existing actions (e.g., "Add Roles to Token")
6. Click **Apply** (top right)

### 6. Test the Changes

1. Log out of the application
2. Clear your browser's local storage (F12 → Application → Local Storage → Clear)
3. Log back in
4. Navigate to the Profile page
5. You should now see:
   - Your real email address (not `@users.example.com`)
   - Your name (from Auth0 profile)

## Updating Both Actions (If You Have "Add Roles to Token")

If you already have an "Add Roles to Token" action, you can combine them into one:

```javascript
exports.onExecutePostLogin = async (event, api) => {
  const namespace = 'https://study-planning-api';

  // Add roles to token
  if (event.authorization) {
    api.accessToken.setCustomClaim(`${namespace}/roles`, event.authorization.roles);
    api.idToken.setCustomClaim(`${namespace}/roles`, event.authorization.roles);
  }

  // Add email to token
  if (event.user.email) {
    api.accessToken.setCustomClaim(`${namespace}/email`, event.user.email);
    api.accessToken.setCustomClaim('email', event.user.email);
  }

  // Add name to token
  if (event.user.name) {
    api.accessToken.setCustomClaim(`${namespace}/name`, event.user.name);
    api.accessToken.setCustomClaim('name', event.user.name);
  }
};
```

Then:
1. Go to **Actions** → **Library**
2. Find your existing "Add Roles to Token" action
3. Click on it to edit
4. Replace the code with the combined version above
5. Click **Deploy**
6. The action should already be in your Login flow, so no need to add it again

## Why This Is Needed

- **Access tokens** are used for API authorization (what we send to the backend)
- **ID tokens** are used for user information (what the frontend uses)
- By default, access tokens only contain minimal claims (sub, aud, exp, etc.)
- Custom claims must be added via Auth0 Actions to include user profile data

## Verification

After implementing this change, log out and back in. Then check the Profile page - you should see your actual email and name instead of synthetic values.

You can also verify the token contents by:
1. Opening browser DevTools (F12)
2. Going to Console
3. Looking for the console logs from `AuthContext` that show token details
4. Or decode your access token at [jwt.io](https://jwt.io) to see all claims
