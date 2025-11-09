import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import { BookOpen, Home, FolderOpen, Settings } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import './App.css';

// Import pages
import HomePage from './pages/HomePage';
import FilesPage from './pages/FilesPage';
import SettingsPage from './pages/SettingsPage';

function App() {
  const { t } = useTranslation();

  return (
    <Router>
      <div className="app">
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
          </div>
        </header>

        <main className="main-content">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/home" element={<HomePage />} />
            <Route path="/files" element={<FilesPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
