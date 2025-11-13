import { useState, useEffect } from 'react';
import { Settings, Globe, CheckCircle, Cpu, Loader, Download, Plus } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { llmApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

function SettingsPage() {
  const { t, i18n } = useTranslation();
  const { isLoading: authLoading, accessToken } = useAuth();
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState(null);
  const [userProfile, setUserProfile] = useState(null);

  // Model pulling state
  const [newModelName, setNewModelName] = useState('');
  const [pullingModel, setPullingModel] = useState(false);
  const [showAddModel, setShowAddModel] = useState(false);

  // User preferences
  const [language, setLanguage] = useState(
    localStorage.getItem('interfaceLanguage') || 'en'
  );
  const [preferredModel, setPreferredModel] = useState(
    localStorage.getItem('preferredModel') || ''
  );
  const [preferredChunks, setPreferredChunks] = useState(
    localStorage.getItem('preferredChunks') || '5'
  );
  const [useRAG, setUseRAG] = useState(
    localStorage.getItem('useRAG') !== 'false' // Default to true
  );

  // Wait for authentication to complete before loading data
  useEffect(() => {
    if (!authLoading && accessToken) {
      loadSettings();
    }
  }, [authLoading, accessToken]);

  const loadSettings = async () => {
    try {
      setLoading(true);

      // Load user profile to get role
      const profileRes = await api.get('/users/me');
      setUserProfile(profileRes.data);

      const modelsRes = await llmApi.listModels().catch(() => ({ models: [] }));
      setModels(modelsRes.models || []);

      // Set default preferred model if not set
      if (!preferredModel && modelsRes.models && modelsRes.models.length > 0) {
        const defaultModel = modelsRes.models[0].name || modelsRes.models[0];
        setPreferredModel(defaultModel);
        localStorage.setItem('preferredModel', defaultModel);
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLanguageChange = (e) => {
    const newLanguage = e.target.value;
    setLanguage(newLanguage);
    localStorage.setItem('interfaceLanguage', newLanguage);
    // Also set the LLM language to match
    localStorage.setItem('preferredLanguage', newLanguage === 'en' ? 'english' : 'spanish');
    i18n.changeLanguage(newLanguage);
    setMessage({ type: 'success', text: t('settings.languageSaved') });
  };

  const handleModelSelect = (modelName) => {
    setPreferredModel(modelName);
    localStorage.setItem('preferredModel', modelName);
    setMessage({ type: 'success', text: t('settings.modelSaved') });
  };

  const handleChunksChange = (e) => {
    const newChunks = e.target.value;
    setPreferredChunks(newChunks);
    localStorage.setItem('preferredChunks', newChunks);
    setMessage({ type: 'success', text: t('settings.chunksSaved') });
  };

  const handleRAGToggle = (e) => {
    const newValue = e.target.checked;
    setUseRAG(newValue);
    localStorage.setItem('useRAG', newValue.toString());
    setMessage({ type: 'success', text: t('settings.ragSaved') });
  };

  const handlePullModel = async (e) => {
    e.preventDefault();
    if (!newModelName.trim() || pullingModel) return;

    setPullingModel(true);
    setMessage(null);

    try {
      await llmApi.ensureModel(newModelName.trim());
      setMessage({ type: 'success', text: t('settings.modelPullSuccess', { model: newModelName }) });
      setNewModelName('');
      setShowAddModel(false);

      // Reload models list
      const modelsRes = await llmApi.listModels().catch(() => ({ models: [] }));
      setModels(modelsRes.models || []);
    } catch (error) {
      console.error('Failed to pull model:', error);
      const errorMsg = error.response?.data?.detail || error.message || 'Unknown error';
      setMessage({ type: 'error', text: t('settings.modelPullError', { error: errorMsg }) });
    } finally {
      setPullingModel(false);
    }
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

  return (
    <div>
      <div className="card">
        <h2 className="card-title">
          <Settings size={28} />
          {t('settings.title')}
        </h2>

        {message && (
          <div className={`alert alert-${message.type}`}>
            {message.type === 'success' && <CheckCircle size={20} />}
            {message.text}
          </div>
        )}

        <div style={{ display: 'grid', gap: '2rem' }}>
          {/* User Preferences Section */}
          <section>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', fontSize: '1.25rem' }}>
              <Globe size={24} />
              {t('settings.userPreferences')}
            </h3>

            <div style={{ backgroundColor: '#f7fafc', padding: '1.5rem', borderRadius: '8px' }}>
              <div style={{ display: 'grid', gap: '1.5rem' }}>
                {/* Language Preference */}
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">
                    {t('settings.defaultLanguage')}
                  </label>
                  <select
                    className="select"
                    value={language}
                    onChange={handleLanguageChange}
                  >
                    <option value="en">{t('languages.english')}</option>
                    <option value="es">{t('languages.spanish')}</option>
                  </select>
                  <p style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: '#718096' }}>
                    {t('settings.languageHint')}
                  </p>
                </div>

                {/* Chunks Preference */}
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label">
                    {t('settings.contextChunks')}
                  </label>
                  <select
                    className="select"
                    value={preferredChunks}
                    onChange={handleChunksChange}
                  >
                    {Array.from({ length: 15 }, (_, i) => i + 1).map(num => (
                      <option key={num} value={num.toString()}>
                        {num} {num === 1 ? t('chunks.chunk') : t('chunks.chunks')}
                      </option>
                    ))}
                  </select>
                  <p style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: '#718096' }}>
                    {t('settings.contextChunksHint')}
                  </p>
                </div>

                {/* RAG Toggle */}
                <div className="form-group" style={{ marginBottom: 0 }}>
                  <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <input
                      type="checkbox"
                      id="useRAG"
                      checked={useRAG}
                      onChange={handleRAGToggle}
                      style={{ cursor: 'pointer', width: '18px', height: '18px' }}
                    />
                    {t('settings.useRAG')}
                  </label>
                  <p style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: '#718096' }}>
                    {t('settings.useRAGHint')}
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Available Models Section */}
          <section>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0, fontSize: '1.25rem' }}>
                <Cpu size={24} />
                {t('settings.preferredModel')}
              </h3>
              {userProfile?.role === 'admin' && (
                <button
                  onClick={() => setShowAddModel(!showAddModel)}
                  className="btn btn-primary"
                  style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem' }}
                >
                  <Plus size={18} />
                  {t('settings.addModel')}
                </button>
              )}
            </div>

            <p style={{ marginBottom: '1rem', fontSize: '0.875rem', color: '#718096' }}>
              {t('settings.preferredModelHint')}
            </p>

            {/* Add Model Form */}
            {showAddModel && userProfile?.role === 'admin' && (
              <div style={{ backgroundColor: '#f7fafc', padding: '1.5rem', borderRadius: '8px', marginBottom: '1rem', border: '1px solid #e2e8f0' }}>
                <h4 style={{ margin: '0 0 0.75rem 0', fontSize: '1rem', fontWeight: 600 }}>
                  {t('settings.pullNewModel')}
                </h4>
                <p style={{ marginBottom: '1rem', fontSize: '0.875rem', color: '#718096' }}>
                  {t('settings.pullModelHint')}
                </p>
                <form onSubmit={handlePullModel} style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    <input
                      type="text"
                      className="input"
                      value={newModelName}
                      onChange={(e) => setNewModelName(e.target.value)}
                      placeholder={t('settings.modelNamePlaceholder')}
                      disabled={pullingModel}
                      style={{ width: '100%' }}
                    />
                    <p style={{ marginTop: '0.25rem', fontSize: '0.75rem', color: '#718096' }}>
                      {t('settings.modelNameExample')}
                    </p>
                  </div>
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={!newModelName.trim() || pullingModel}
                    style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', minWidth: '120px', justifyContent: 'center' }}
                  >
                    {pullingModel ? (
                      <>
                        <Loader size={18} className="spinner-icon" style={{ animation: 'spin 1s linear infinite' }} />
                        {t('settings.pulling')}
                      </>
                    ) : (
                      <>
                        <Download size={18} />
                        {t('settings.pullModel')}
                      </>
                    )}
                  </button>
                </form>
              </div>
            )}

            {models.length === 0 ? (
              <p style={{ color: '#718096', fontStyle: 'italic' }}>{t('settings.noModels')}</p>
            ) : (
              <div style={{ display: 'grid', gap: '0.75rem' }}>
                {models.map((model, idx) => {
                  const modelName = model.name || model;
                  const isSelected = modelName === preferredModel;
                  return (
                    <div
                      key={idx}
                      onClick={() => handleModelSelect(modelName)}
                      style={{
                        padding: '1rem',
                        backgroundColor: isSelected ? '#e6f7ff' : '#f7fafc',
                        borderRadius: '6px',
                        border: isSelected ? '2px solid #667eea' : '1px solid #e2e8f0',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease'
                      }}
                      onMouseEnter={(e) => {
                        if (!isSelected) {
                          e.currentTarget.style.borderColor = '#667eea';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (!isSelected) {
                          e.currentTarget.style.borderColor = '#e2e8f0';
                        }
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <div style={{ fontWeight: 600, color: '#2d3748', flex: 1 }}>{modelName}</div>
                        {isSelected && (
                          <span style={{ color: '#667eea', fontSize: '0.875rem', fontWeight: 600 }}>
                            {t('settings.selected')}
                          </span>
                        )}
                      </div>
                      {model.size && (
                        <div style={{ fontSize: '0.875rem', color: '#718096', marginTop: '0.25rem' }}>
                          Size: {model.size}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}

export default SettingsPage;
