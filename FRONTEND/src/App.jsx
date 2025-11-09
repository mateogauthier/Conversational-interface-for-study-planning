import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import { BookOpen } from 'lucide-react';
import './App.css';

// Import pages
import HomePage from './pages/HomePage';
import UploadPage from './pages/UploadPage';
import QueryPage from './pages/QueryPage';
import FilesPage from './pages/FilesPage';

function App() {
  return (
    <Router>
      <div className="app">
        <header className="header">
          <div className="header-content">
            <h1>
              <BookOpen size={32} />
              Study Planning Assistant
            </h1>
            <nav className="nav">
              <NavLink
                to="/"
                className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                end
              >
                Home
              </NavLink>
              <NavLink
                to="/upload"
                className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
              >
                Upload
              </NavLink>
              <NavLink
                to="/query"
                className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
              >
                Query
              </NavLink>
              <NavLink
                to="/files"
                className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
              >
                Files
              </NavLink>
            </nav>
          </div>
        </header>

        <main className="main-content">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/query" element={<QueryPage />} />
            <Route path="/files" element={<FilesPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
