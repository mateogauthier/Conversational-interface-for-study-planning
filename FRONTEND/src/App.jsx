import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink, useNavigate } from 'react-router-dom';
import { BookOpen, Home, FolderOpen, Settings, LogOut, User } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import './App.css';

// Auth
import { AuthProvider, useAuth } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import { setAccessToken } from './services/api';

// Import pages
import LoginPage from './pages/LoginPage';
import HomePage from './pages/HomePage';
import FilesPage from './pages/FilesPage';
import SettingsPage from './pages/SettingsPage';
import ProfilePage from './pages/ProfilePage';

function HeaderContent() {
  const { t } = useTranslation();
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();

  const handleProfileClick = () => {
    navigate('/profile');
  };

  return (
    <header className="header">
      <div className="header-content">
        <h1>
          <BookOpen size={32} />
          {t('appTitle')}
        </h1>
        <nav className="nav">
          <NavLink
            to="/"
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            end
          >
            <Home size={20} />
            {t('nav.home')}
          </NavLink>
          <NavLink
            to="/files"
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
          >
            <FolderOpen size={20} />
            {t('nav.files')}
          </NavLink>
          <NavLink
            to="/settings"
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
          >
            <Settings size={20} />
            {t('nav.settings')}
          </NavLink>
        </nav>
        {isAuthenticated && user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginLeft: 'auto' }}>
            <button
              onClick={handleProfileClick}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                background: 'transparent',
                border: 'none',
                color: '#e2e8f0',
                cursor: 'pointer',
                padding: '0.5rem',
                borderRadius: '6px',
                transition: 'background 0.2s ease',
                fontSize: '0.9rem'
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
              title="View Profile"
            >
              <User size={18} />
              <span>{user.name || user.email}</span>
            </button>
            <button
              onClick={logout}
              className="btn btn-secondary"
              style={{ fontSize: '0.9rem', padding: '0.5rem 1rem' }}
              title={t('auth.logout')}
            >
              <LogOut size={18} />
              {t('auth.logout')}
            </button>
          </div>
        )}
      </div>
    </header>
  );
}

function AppContent() {
  const { accessToken } = useAuth();

  // Update API token when it changes
  useEffect(() => {
    if (accessToken) {
      setAccessToken(accessToken);
    }
  }, [accessToken]);

  return (
    <Router>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <div className="app">
                <HeaderContent />
                <main className="main-content">
                  <Routes>
                    <Route path="/" element={<HomePage />} />
                    <Route path="/home" element={<HomePage />} />
                    <Route path="/files" element={<FilesPage />} />
                    <Route path="/settings" element={<SettingsPage />} />
                    <Route path="/profile" element={<ProfilePage />} />
                  </Routes>
                </main>
              </div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </Router>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
