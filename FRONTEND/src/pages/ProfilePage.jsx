import { useState, useEffect } from 'react';
import { User, Mail, Shield, Calendar, Activity, Upload, MessageSquare, HardDrive, Loader } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

function ProfilePage() {
  const { t } = useTranslation();
  const { user: authUser, isLoading: authLoading, accessToken } = useAuth();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!authLoading && accessToken) {
      loadProfile();
    }
  }, [authLoading, accessToken]);

  const loadProfile = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get('/users/me');
      setProfile(response.data);
    } catch (err) {
      console.error('Failed to load profile:', err);
      setError('Failed to load profile data');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const formatDateTime = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
  };

  // Show loading screen while authentication is in progress
  if (authLoading) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '60vh',
        gap: '1rem'
      }}>
        <Loader size={48} className="spinner-icon" style={{ animation: 'spin 1s linear infinite' }} />
        <p style={{ color: '#a0aec0', fontSize: '1.1rem' }}>{t('auth.loading')}</p>
      </div>
    );
  }

  if (loading) {
    return <div className="spinner"></div>;
  }

  if (error) {
    return (
      <div className="card">
        <div style={{ textAlign: 'center', padding: '2rem', color: '#f56565' }}>
          <p>{error}</p>
          <button onClick={loadProfile} className="btn btn-primary" style={{ marginTop: '1rem' }}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="card">
        <div style={{ textAlign: 'center', padding: '2rem', color: '#a0aec0' }}>
          <p>No profile data available</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Profile Header */}
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '2rem' }}>
          {/* Avatar */}
          <div style={{
            width: '120px',
            height: '120px',
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0
          }}>
            <User size={60} style={{ color: 'white' }} />
          </div>

          {/* User Info */}
          <div style={{ flex: 1 }}>
            <h1 style={{ fontSize: '2rem', fontWeight: 700, marginBottom: '0.5rem', color: '#2d3748' }}>
              {profile.name || 'User'}
            </h1>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '1rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: '#4a5568' }}>
                <Mail size={18} />
                <span>{profile.email}</span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: '#4a5568' }}>
                <Shield size={18} />
                <span style={{
                  textTransform: 'capitalize',
                  fontWeight: 600,
                  color: profile.role === 'admin' ? '#667eea' : '#48bb78'
                }}>
                  {profile.role}
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: '#4a5568' }}>
                <Calendar size={18} />
                <span>Member since {formatDate(profile.created_at)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Statistics Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
        gap: '1.5rem',
        marginTop: '1.5rem'
      }}>
        {/* Total Uploads */}
        <div className="card" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{
              width: '60px',
              height: '60px',
              borderRadius: '12px',
              background: 'rgba(255, 255, 255, 0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <Upload size={32} style={{ color: 'white' }} />
            </div>
            <div>
              <p style={{ fontSize: '0.875rem', color: 'rgba(255, 255, 255, 0.9)', margin: 0 }}>
                Total Uploads
              </p>
              <p style={{ fontSize: '2rem', fontWeight: 700, color: 'white', margin: 0 }}>
                {profile.statistics.total_uploads}
              </p>
            </div>
          </div>
        </div>

        {/* Total Queries */}
        <div className="card" style={{ background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{
              width: '60px',
              height: '60px',
              borderRadius: '12px',
              background: 'rgba(255, 255, 255, 0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <MessageSquare size={32} style={{ color: 'white' }} />
            </div>
            <div>
              <p style={{ fontSize: '0.875rem', color: 'rgba(255, 255, 255, 0.9)', margin: 0 }}>
                Total Queries
              </p>
              <p style={{ fontSize: '2rem', fontWeight: 700, color: 'white', margin: 0 }}>
                {profile.statistics.total_queries}
              </p>
            </div>
          </div>
        </div>

        {/* Storage Used */}
        <div className="card" style={{ background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{
              width: '60px',
              height: '60px',
              borderRadius: '12px',
              background: 'rgba(255, 255, 255, 0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <HardDrive size={32} style={{ color: 'white' }} />
            </div>
            <div>
              <p style={{ fontSize: '0.875rem', color: 'rgba(255, 255, 255, 0.9)', margin: 0 }}>
                Storage Used
              </p>
              <p style={{ fontSize: '2rem', fontWeight: 700, color: 'white', margin: 0 }}>
                {formatFileSize(profile.statistics.total_storage_bytes)}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Activity Information */}
      <div className="card" style={{ marginTop: '1.5rem' }}>
        <h2 className="card-title">
          <Activity size={28} />
          Activity Information
        </h2>

        <div style={{ display: 'grid', gap: '1.5rem' }}>
          <div style={{
            padding: '1.5rem',
            background: '#f7fafc',
            borderRadius: '8px',
            border: '1px solid #e2e8f0'
          }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem' }}>
              <div>
                <p style={{ fontSize: '0.875rem', color: '#718096', marginBottom: '0.5rem' }}>
                  Last Activity
                </p>
                <p style={{ fontSize: '1rem', fontWeight: 600, color: '#2d3748', margin: 0 }}>
                  {formatDateTime(profile.statistics.last_activity)}
                </p>
              </div>

              <div>
                <p style={{ fontSize: '0.875rem', color: '#718096', marginBottom: '0.5rem' }}>
                  Account Created
                </p>
                <p style={{ fontSize: '1rem', fontWeight: 600, color: '#2d3748', margin: 0 }}>
                  {formatDateTime(profile.created_at)}
                </p>
              </div>

              <div>
                <p style={{ fontSize: '0.875rem', color: '#718096', marginBottom: '0.5rem' }}>
                  Last Updated
                </p>
                <p style={{ fontSize: '1rem', fontWeight: 600, color: '#2d3748', margin: 0 }}>
                  {formatDateTime(profile.updated_at)}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Account Details */}
      <div className="card" style={{ marginTop: '1.5rem' }}>
        <h2 className="card-title">
          <Shield size={28} />
          Account Details
        </h2>

        <div style={{ display: 'grid', gap: '1rem' }}>
          <div style={{
            padding: '1rem',
            background: '#f7fafc',
            borderRadius: '6px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <span style={{ color: '#718096', fontSize: '0.875rem' }}>User ID</span>
            <span style={{ fontFamily: 'monospace', color: '#4a5568', fontSize: '0.875rem' }}>
              {profile.id}
            </span>
          </div>

          <div style={{
            padding: '1rem',
            background: '#f7fafc',
            borderRadius: '6px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <span style={{ color: '#718096', fontSize: '0.875rem' }}>Auth0 ID</span>
            <span style={{ fontFamily: 'monospace', color: '#4a5568', fontSize: '0.875rem' }}>
              {profile.auth0_id}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ProfilePage;
