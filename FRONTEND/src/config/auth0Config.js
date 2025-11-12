/**
 * Auth0 configuration
 */

// Debug: Log environment variables (remove in production)
console.log('=== Auth0 Config Debug ===');
console.log('VITE_AUTH0_DOMAIN:', import.meta.env.VITE_AUTH0_DOMAIN);
console.log('VITE_AUTH0_CLIENT_ID:', import.meta.env.VITE_AUTH0_CLIENT_ID);
console.log('VITE_AUTH0_AUDIENCE:', import.meta.env.VITE_AUTH0_AUDIENCE);
console.log('VITE_AUTH0_REDIRECT_URI:', import.meta.env.VITE_AUTH0_REDIRECT_URI);
console.log('All env vars:', import.meta.env);
console.log('========================');

export const auth0Config = {
  domain: import.meta.env.VITE_AUTH0_DOMAIN,
  clientId: import.meta.env.VITE_AUTH0_CLIENT_ID,
  authorizationParams: {
    redirect_uri: import.meta.env.VITE_AUTH0_REDIRECT_URI || window.location.origin,
    audience: import.meta.env.VITE_AUTH0_AUDIENCE,
    scope: 'openid profile email'
  },
  cacheLocation: 'localstorage',
  useRefreshTokens: true
};

// Debug: Log final config
console.log('Final auth0Config:', auth0Config);
