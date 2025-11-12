import { createContext, useContext, useEffect, useState } from 'react';
import { useAuth0 } from '@auth0/auth0-react';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const {
    user,
    isAuthenticated,
    isLoading,
    loginWithRedirect,
    logout,
    getAccessTokenSilently
  } = useAuth0();

  const [accessToken, setAccessToken] = useState(null);
  const [tokenLoading, setTokenLoading] = useState(false);

  // Get access token when authenticated
  useEffect(() => {
    const getToken = async () => {
      if (isAuthenticated && !tokenLoading) {
        console.log('🔐 User is authenticated, fetching access token...');
        setTokenLoading(true);
        try {
          const token = await getAccessTokenSilently({
            authorizationParams: {
              audience: import.meta.env.VITE_AUTH0_AUDIENCE,
            }
          });
          console.log('✅ Access token retrieved successfully');
          setAccessToken(token);
        } catch (error) {
          console.error('❌ Error getting access token:', error);
          console.error('Error details:', error.error, error.error_description);
          // Even if token fetch fails, user is still authenticated
          // They just won't be able to call the API
        } finally {
          setTokenLoading(false);
        }
      }
    };

    getToken();
  }, [isAuthenticated, getAccessTokenSilently]);

  const login = async () => {
    await loginWithRedirect({
      authorizationParams: {
        audience: import.meta.env.VITE_AUTH0_AUDIENCE,
        scope: 'openid profile email'
      }
    });
  };

  const handleLogout = () => {
    logout({
      logoutParams: {
        returnTo: window.location.origin
      }
    });
    setAccessToken(null);
  };

  const value = {
    user,
    isAuthenticated,
    isLoading: isLoading || tokenLoading,
    accessToken,
    login,
    logout: handleLogout,
    getAccessToken: async () => {
      try {
        return await getAccessTokenSilently({
          authorizationParams: {
            audience: import.meta.env.VITE_AUTH0_AUDIENCE,
          }
        });
      } catch (error) {
        console.error('Error getting access token:', error);
        return null;
      }
    }
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
