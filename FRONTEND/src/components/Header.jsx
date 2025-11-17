import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { BookOpen, Home, FolderOpen, Settings, LogOut, User, Menu, X, MessageSquare } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import './Header.css';

function Header() {
  const { t } = useTranslation();
  const { user, userProfile, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Check if user is admin
  const isAdmin = userProfile?.role === 'admin';

  const handleProfileClick = () => {
    navigate('/profile');
    setMobileMenuOpen(false);
  };

  const handleLogout = () => {
    logout();
    setMobileMenuOpen(false);
  };

  const closeMobileMenu = () => {
    setMobileMenuOpen(false);
  };

  return (
    <header className="header-new">
      <div className="header-container">
        {/* Logo/Brand */}
        <div className="header-brand">
          <BookOpen size={28} className="header-logo-icon" />
          <h1 className="header-title">{t('appTitle')}</h1>
        </div>

        {/* Desktop Navigation */}
        <nav className="header-nav desktop-nav">
          <NavLink
            to="/"
            className={({ isActive }) => `header-nav-link ${isActive ? 'active' : ''}`}
            end
          >
            <Home size={18} />
            <span>{t('nav.home')}</span>
          </NavLink>
          <NavLink
            to="/files"
            className={({ isActive }) => `header-nav-link ${isActive ? 'active' : ''}`}
          >
            <FolderOpen size={18} />
            <span>{t('nav.files')}</span>
          </NavLink>
          {isAdmin && (
            <NavLink
              to="/admin/feedback"
              className={({ isActive }) => `header-nav-link ${isActive ? 'active' : ''}`}
            >
              <MessageSquare size={18} />
              <span>Feedback</span>
            </NavLink>
          )}
          <NavLink
            to="/settings"
            className={({ isActive }) => `header-nav-link ${isActive ? 'active' : ''}`}
          >
            <Settings size={18} />
            <span>{t('nav.settings')}</span>
          </NavLink>
        </nav>

        {/* User Section - Desktop */}
        {isAuthenticated && user && (
          <div className="header-user desktop-user">
            <button
              onClick={handleProfileClick}
              className="header-user-button"
              title="View Profile"
            >
              <User size={18} />
              <span className="header-user-name">{user.name || user.email}</span>
            </button>
            <button
              onClick={logout}
              className="header-logout-button"
              title={t('auth.logout')}
            >
              <LogOut size={18} />
              <span>{t('auth.logout')}</span>
            </button>
          </div>
        )}

        {/* Mobile Menu Toggle */}
        <button
          className="mobile-menu-toggle"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          aria-label="Toggle menu"
        >
          {mobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
        </button>
      </div>

      {/* Mobile Menu Overlay */}
      {mobileMenuOpen && (
        <div className="mobile-menu-overlay" onClick={closeMobileMenu}>
          <div className="mobile-menu" onClick={(e) => e.stopPropagation()}>
            {/* User Info - Mobile */}
            {isAuthenticated && user && (
              <div className="mobile-menu-user">
                <div className="mobile-user-info">
                  <User size={24} className="mobile-user-icon" />
                  <div>
                    <div className="mobile-user-name">{user.name || user.email}</div>
                    <div className="mobile-user-email">{user.email}</div>
                  </div>
                </div>
              </div>
            )}

            {/* Navigation Links - Mobile */}
            <nav className="mobile-menu-nav">
              <NavLink
                to="/"
                className={({ isActive }) => `mobile-nav-link ${isActive ? 'active' : ''}`}
                onClick={closeMobileMenu}
                end
              >
                <Home size={20} />
                <span>{t('nav.home')}</span>
              </NavLink>
              <NavLink
                to="/files"
                className={({ isActive }) => `mobile-nav-link ${isActive ? 'active' : ''}`}
                onClick={closeMobileMenu}
              >
                <FolderOpen size={20} />
                <span>{t('nav.files')}</span>
              </NavLink>
              {isAdmin && (
                <NavLink
                  to="/admin/feedback"
                  className={({ isActive }) => `mobile-nav-link ${isActive ? 'active' : ''}`}
                  onClick={closeMobileMenu}
                >
                  <MessageSquare size={20} />
                  <span>Feedback</span>
                </NavLink>
              )}
              <NavLink
                to="/settings"
                className={({ isActive }) => `mobile-nav-link ${isActive ? 'active' : ''}`}
                onClick={closeMobileMenu}
              >
                <Settings size={20} />
                <span>{t('nav.settings')}</span>
              </NavLink>
              {isAuthenticated && (
                <>
                  <NavLink
                    to="/profile"
                    className={({ isActive }) => `mobile-nav-link ${isActive ? 'active' : ''}`}
                    onClick={closeMobileMenu}
                  >
                    <User size={20} />
                    <span>Profile</span>
                  </NavLink>
                  <button
                    onClick={handleLogout}
                    className="mobile-nav-link mobile-logout-button"
                  >
                    <LogOut size={20} />
                    <span>{t('auth.logout')}</span>
                  </button>
                </>
              )}
            </nav>
          </div>
        </div>
      )}
    </header>
  );
}

export default Header;
