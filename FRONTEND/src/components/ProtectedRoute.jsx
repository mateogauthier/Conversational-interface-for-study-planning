import { useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Loader } from 'lucide-react';
import { useTranslation } from 'react-i18next';

function ProtectedRoute({ children }) {
  const { t } = useTranslation();
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  // Debug logging
  useEffect(() => {
    console.log('🛡️ ProtectedRoute check:', { isAuthenticated, isLoading, path: location.pathname });
  }, [isAuthenticated, isLoading, location.pathname]);

  if (isLoading) {
    console.log('⏳ Still loading authentication...');
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        gap: '1rem'
      }}>
        <Loader size={48} className="spinner-icon" style={{ animation: 'spin 1s linear infinite' }} />
        <p style={{ color: '#a0aec0', fontSize: '1.1rem' }}>{t('auth.checking')}</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    console.log('🚫 Not authenticated, redirecting to login');
    // Redirect to login page but save the attempted location
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  console.log('✅ Authenticated, rendering protected content');
  return children;
}

export default ProtectedRoute;
