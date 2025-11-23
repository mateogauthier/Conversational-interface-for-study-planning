import { useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { LogIn, Loader } from 'lucide-react';
import { useTranslation } from 'react-i18next';

function LoginPage() {
  const { t } = useTranslation();
  const { isAuthenticated, isLoading, login } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // Redirect to home if already authenticated
    if (isAuthenticated && !isLoading) {
      navigate('/');
    }
  }, [isAuthenticated, isLoading, navigate]);

  const handleLogin = async () => {
    try {
      await login();
    } catch (error) {
      console.error('Login error:', error);
    }
  };

  if (isLoading) {
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
        <p style={{ color: '#a0aec0', fontSize: '1.1rem' }}>{t('auth.loading')}</p>
      </div>
    );
  }

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      width: '100%',
      backgroundImage: 'url(/backgrounds/login.png)',
      backgroundSize: 'cover',
      backgroundPosition: 'center',
      backgroundRepeat: 'no-repeat',
      padding: '2rem',
      margin: 0,
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0
    }}>
      <div className="card" style={{
        maxWidth: '500px',
        width: '100%',
        textAlign: 'center',
        boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)'
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'center',
          marginBottom: '2rem'
        }}>
          <img
            src="/icons/logo.svg"
            alt="Logo"
            style={{ width: '80px', height: '80px' }}
          />
        </div>

        <h1 style={{
          fontSize: '2rem',
          fontWeight: 700,
          marginBottom: '1rem',
          color: '#2d3748'
        }}>
          {t('auth.welcome')}
        </h1>

        <p style={{
          fontSize: '1.1rem',
          color: '#718096',
          marginBottom: '2rem',
          lineHeight: '1.6'
        }}>
          {t('auth.subtitle')}
        </p>

        <div style={{
          background: '#f7fafc',
          padding: '1.5rem',
          borderRadius: '8px',
          marginBottom: '2rem',
          textAlign: 'left'
        }}>
          <h3 style={{
            fontSize: '1rem',
            fontWeight: 600,
            marginBottom: '1rem',
            color: '#2d3748'
          }}>
            {t('auth.features')}:
          </h3>
          <ul style={{
            listStyle: 'none',
            padding: 0,
            margin: 0,
            display: 'flex',
            flexDirection: 'column',
            gap: '0.75rem'
          }}>
            <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#4a5568' }}>
              <span style={{ color: '#667eea', fontSize: '1.2rem' }}>✓</span>
              {t('auth.feature1')}
            </li>
            <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#4a5568' }}>
              <span style={{ color: '#667eea', fontSize: '1.2rem' }}>✓</span>
              {t('auth.feature2')}
            </li>
            <li style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#4a5568' }}>
              <span style={{ color: '#667eea', fontSize: '1.2rem' }}>✓</span>
              {t('auth.feature3')}
            </li>
          </ul>
        </div>

        <button
          onClick={handleLogin}
          className="btn btn-primary"
          style={{
            width: '100%',
            fontSize: '1.1rem',
            padding: '1rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.75rem'
          }}
        >
          <LogIn size={24} />
          {t('auth.loginButton')}
        </button>

        <p style={{
          marginTop: '1.5rem',
          fontSize: '0.9rem',
          color: '#a0aec0'
        }}>
          {t('auth.securedBy')} <strong>Auth0</strong>
        </p>
      </div>
    </div>
  );
}

export default LoginPage;
