import { useState, useEffect } from 'react';
import { Users, TrendingUp, TrendingDown, Database } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import api from '../services/api';
import './StatsPage.css';

function StatsPage() {
  const { t, i18n } = useTranslation();
  const [users, setUsers] = useState([]);
  const [topLikedFiles, setTopLikedFiles] = useState([]);
  const [topDislikedFiles, setTopDislikedFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [systemStats, setSystemStats] = useState(null);

  const isSpanish = i18n.language === 'es';

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch users
      const usersResponse = await api.get('/admin/users?limit=100');
      setUsers(usersResponse.data.users || []);

      // Fetch system stats
      const statsResponse = await api.get('/admin/stats');
      setSystemStats(statsResponse.data);

      // Fetch feedback stats for file data
      const feedbackResponse = await api.get('/admin/feedback/stats');
      const topFiles = feedbackResponse.data.top_files || [];

      // Sort files by likes (top 5)
      const sortedByLikes = [...topFiles]
        .sort((a, b) => b.likes - a.likes)
        .slice(0, 5);
      setTopLikedFiles(sortedByLikes);

      // Sort files by dislikes (top 5)
      const sortedByDislikes = [...topFiles]
        .sort((a, b) => b.dislikes - a.dislikes)
        .slice(0, 5);
      setTopDislikedFiles(sortedByDislikes);

    } catch (err) {
      console.error('Error fetching stats:', err);
      setError(isSpanish
        ? 'Error al cargar las estadísticas'
        : 'Error loading statistics');
    } finally {
      setLoading(false);
    }
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString) => {
    if (!dateString) return isSpanish ? 'N/A' : 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString(isSpanish ? 'es-ES' : 'en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="stats-page">
        <div className="stats-loading">
          <div className="loading-spinner"></div>
          <p>{isSpanish ? 'Cargando estadísticas...' : 'Loading statistics...'}</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="stats-page">
        <div className="stats-error">
          <p>{error}</p>
          <button onClick={fetchData} className="retry-button">
            {isSpanish ? 'Reintentar' : 'Retry'}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="stats-page">
      <div className="stats-header">
        <div className="stats-title-section">
          <Database size={32} />
          <h1>{isSpanish ? 'Estadísticas del Sistema' : 'System Statistics'}</h1>
        </div>
        <button onClick={fetchData} className="refresh-button">
          {isSpanish ? 'Actualizar' : 'Refresh'}
        </button>
      </div>

      {/* System Overview Cards */}
      {systemStats && (
        <div className="stats-overview">
          <div className="overview-card">
            <div className="overview-icon users-icon">
              <Users size={24} />
            </div>
            <div className="overview-content">
              <h3>{isSpanish ? 'Total Usuarios' : 'Total Users'}</h3>
              <p className="overview-number">{systemStats.total_users || 0}</p>
            </div>
          </div>
          <div className="overview-card">
            <div className="overview-icon queries-icon">
              <Database size={24} />
            </div>
            <div className="overview-content">
              <h3>{isSpanish ? 'Total Consultas' : 'Total Queries'}</h3>
              <p className="overview-number">{systemStats.total_queries || 0}</p>
            </div>
          </div>
          <div className="overview-card">
            <div className="overview-icon storage-icon">
              <Database size={24} />
            </div>
            <div className="overview-content">
              <h3>{isSpanish ? 'Almacenamiento Total' : 'Total Storage'}</h3>
              <p className="overview-number">{formatBytes(systemStats.total_storage || 0)}</p>
            </div>
          </div>
        </div>
      )}

      {/* Users Table */}
      <div className="stats-section">
        <h2 className="section-title">
          <Users size={24} />
          {isSpanish ? 'Usuarios del Sistema' : 'System Users'}
        </h2>
        <div className="table-container">
          <table className="users-table">
            <thead>
              <tr>
                <th>{isSpanish ? 'Nombre' : 'Name'}</th>
                <th>{isSpanish ? 'Email' : 'Email'}</th>
                <th>{isSpanish ? 'Rol' : 'Role'}</th>
                <th>{isSpanish ? 'Archivos Subidos' : 'Uploads'}</th>
                <th>{isSpanish ? 'Consultas' : 'Queries'}</th>
                <th>{isSpanish ? 'Almacenamiento' : 'Storage'}</th>
                <th>{isSpanish ? 'Última Actividad' : 'Last Activity'}</th>
                <th>{isSpanish ? 'Creado' : 'Created'}</th>
              </tr>
            </thead>
            <tbody>
              {users.length === 0 ? (
                <tr>
                  <td colSpan="8" className="empty-row">
                    {isSpanish ? 'No hay usuarios' : 'No users found'}
                  </td>
                </tr>
              ) : (
                users.map((user) => (
                  <tr key={user.id}>
                    <td className="user-name">{user.name || 'N/A'}</td>
                    <td className="user-email">{user.email}</td>
                    <td>
                      <span className={`role-badge ${user.role}`}>
                        {user.role === 'admin'
                          ? (isSpanish ? 'Administrador' : 'Admin')
                          : (isSpanish ? 'Estudiante' : 'Student')}
                      </span>
                    </td>
                    <td className="stat-number">{user.statistics?.total_uploads || 0}</td>
                    <td className="stat-number">{user.statistics?.total_queries || 0}</td>
                    <td className="stat-number">{formatBytes(user.statistics?.total_storage_bytes || 0)}</td>
                    <td className="date-cell">{formatDate(user.statistics?.last_activity)}</td>
                    <td className="date-cell">{formatDate(user.created_at)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* File Statistics Cards */}
      <div className="file-stats-section">
        {/* Most Liked Files Card */}
        <div className="file-stat-card liked-card">
          <div className="card-header">
            <TrendingUp size={24} />
            <h2>{isSpanish ? 'Archivos Más Valorados Positivamente' : 'Most Liked Files'}</h2>
          </div>
          <div className="card-content">
            {topLikedFiles.length === 0 ? (
              <p className="empty-message">
                {isSpanish ? 'No hay datos de valoraciones' : 'No feedback data available'}
              </p>
            ) : (
              <ul className="file-list">
                {topLikedFiles.map((file, index) => (
                  <li key={file._id || index} className="file-item">
                    <div className="file-rank">{index + 1}</div>
                    <div className="file-info">
                      <div className="file-name">{file._id}</div>
                      <div className="file-stats-row">
                        <span className="like-stat">
                          👍 {file.likes} {isSpanish ? 'me gusta' : 'likes'}
                        </span>
                        <span className="dislike-stat">
                          👎 {file.dislikes} {isSpanish ? 'no me gusta' : 'dislikes'}
                        </span>
                        <span className="feedback-total">
                          {file.feedback_count} {isSpanish ? 'total' : 'total'}
                        </span>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* Most Disliked Files Card */}
        <div className="file-stat-card disliked-card">
          <div className="card-header">
            <TrendingDown size={24} />
            <h2>{isSpanish ? 'Archivos Más Valorados Negativamente' : 'Most Disliked Files'}</h2>
          </div>
          <div className="card-content">
            {topDislikedFiles.length === 0 ? (
              <p className="empty-message">
                {isSpanish ? 'No hay datos de valoraciones' : 'No feedback data available'}
              </p>
            ) : (
              <ul className="file-list">
                {topDislikedFiles.map((file, index) => (
                  <li key={file._id || index} className="file-item">
                    <div className="file-rank">{index + 1}</div>
                    <div className="file-info">
                      <div className="file-name">{file._id}</div>
                      <div className="file-stats-row">
                        <span className="dislike-stat">
                          👎 {file.dislikes} {isSpanish ? 'no me gusta' : 'dislikes'}
                        </span>
                        <span className="like-stat">
                          👍 {file.likes} {isSpanish ? 'me gusta' : 'likes'}
                        </span>
                        <span className="feedback-total">
                          {file.feedback_count} {isSpanish ? 'total' : 'total'}
                        </span>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default StatsPage;
