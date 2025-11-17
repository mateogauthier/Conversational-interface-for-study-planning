import { useState, useEffect, useRef } from 'react';
import { Files, Trash2, RefreshCw, File, CheckCircle, XCircle, Upload, AlertCircle, Loader, ChevronLeft, ChevronRight, Download } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { fileApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

function FilesPage() {
  const { t } = useTranslation();
  const { isLoading: authLoading, accessToken } = useAuth();
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState(null);
  const [deleting, setDeleting] = useState(null);
  const [downloading, setDownloading] = useState(null);
  const [userProfile, setUserProfile] = useState(null);

  // Tab and pagination state
  const [activeTab, setActiveTab] = useState('public'); // 'public' or 'private'
  const [currentPage, setCurrentPage] = useState(1);
  const filesPerPage = 10;

  // Upload state
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadMessage, setUploadMessage] = useState(null);
  const [supportedExtensions, setSupportedExtensions] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  // Wait for authentication to complete before loading data
  useEffect(() => {
    if (!authLoading && accessToken) {
      loadFiles();
      loadSupportedExtensions();
    }
  }, [authLoading, accessToken]);

  const loadFiles = async () => {
    try {
      setLoading(true);
      setMessage(null);

      // Load user profile to get user ID and role
      const profileRes = await api.get('/users/me');
      setUserProfile(profileRes.data);

      const response = await fileApi.list();
      // API returns array directly, not {files: [...]}
      setFiles(response || []);
    } catch (error) {
      setMessage({
        type: 'error',
        text: 'Failed to load files. Please try again.',
      });
    } finally {
      setLoading(false);
    }
  };

  const loadSupportedExtensions = async () => {
    try {
      const response = await fileApi.getSupportedExtensions();
      setSupportedExtensions(response);
    } catch (error) {
      console.error('Failed to load supported extensions:', error);
    }
  };

  const handleDelete = async (filename) => {
    const formatted = formatFileName(filename);
    const displayName = `${formatted.display} (${formatted.extension})`;

    if (!confirm(`${t('files.deleteConfirm')} "${displayName}"?`)) {
      return;
    }

    try {
      setDeleting(filename);
      await fileApi.delete(filename);
      setMessage({
        type: 'success',
        text: `"${displayName}" ${t('files.deleteSuccess')}`,
      });
      await loadFiles();
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || `${t('files.deleteError')} "${displayName}".`,
      });
    } finally {
      setDeleting(null);
    }
  };

  const handleDownload = async (filename) => {
    try {
      setDownloading(filename);
      await fileApi.download(filename);
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || t('files.downloadError') || `Error downloading "${filename}".`,
      });
    } finally {
      setDownloading(null);
    }
  };

  // Upload handlers
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleFileSelect = (file) => {
    setSelectedFile(file);
    setUploadMessage(null);
    setUploadProgress(0);
  };

  const handleFileInputChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploading(true);
    setUploadMessage(null);
    setUploadProgress(0);

    try {
      const response = await fileApi.upload(selectedFile, (progress) => {
        setUploadProgress(progress);
      });

      setUploadMessage({
        type: 'success',
        text: response.processed_for_rag
          ? t('files.uploadSuccess')
          : t('files.uploadSuccessNoRag'),
      });

      setSelectedFile(null);
      setUploadProgress(0);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }

      // Reload files after upload
      await loadFiles();
    } catch (error) {
      setUploadMessage({
        type: 'error',
        text: error.response?.data?.detail || t('files.uploadError'),
      });
    } finally {
      setUploading(false);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  const formatDate = (dateString) => {
    // API returns ISO datetime string, not Unix timestamp
    return new Date(dateString).toLocaleString();
  };

  const formatFileName = (filename) => {
    // Remove file extension
    const nameWithoutExt = filename.replace(/\.[^/.]+$/, '');

    // Replace hyphens and underscores with spaces
    let formatted = nameWithoutExt.replace(/[-_]/g, ' ');

    // Capitalize first letter of each word
    formatted = formatted.split(' ').map(word => {
      if (word.length === 0) return word;
      return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
    }).join(' ');

    // Get file extension
    const extMatch = filename.match(/\.[^/.]+$/);
    const extension = extMatch ? extMatch[0] : '';

    return {
      display: formatted,
      extension: extension.toUpperCase().replace('.', '')
    };
  };

  // Check if user can delete a file
  const canDeleteFile = (file) => {
    if (!userProfile) return false;
    // Admins can delete any public file
    if (userProfile.role === 'admin') return file.is_public;
    // Students can only delete their own files
    return file.user_id === userProfile.id;
  };

  // Filter files based on active tab
  const filteredFiles = files.filter(file => {
    if (activeTab === 'public') {
      return file.is_public === true;
    } else {
      return file.is_public === false;
    }
  });

  // Pagination
  const totalPages = Math.ceil(filteredFiles.length / filesPerPage);
  const startIndex = (currentPage - 1) * filesPerPage;
  const endIndex = startIndex + filesPerPage;
  const paginatedFiles = filteredFiles.slice(startIndex, endIndex);

  // Reset to page 1 when changing tabs
  const handleTabChange = (tab) => {
    setActiveTab(tab);
    setCurrentPage(1);
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

  return (
    <div>
      {/* Upload Section */}
      <div className="card">
        <h2 className="card-title">
          <Upload size={28} />
          {t('files.uploadTitle')}
        </h2>

        {uploadMessage && (
          <div className={`alert alert-${uploadMessage.type}`}>
            {uploadMessage.type === 'success' && <CheckCircle size={20} />}
            {uploadMessage.type === 'error' && <XCircle size={20} />}
            {uploadMessage.type === 'warning' && <AlertCircle size={20} />}
            {uploadMessage.text}
          </div>
        )}

        <div
          className={`upload-zone ${dragActive ? 'drag-active' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <div className="upload-icon">
            <Upload size={48} />
          </div>
          <div className="upload-text">
            {selectedFile ? selectedFile.name : t('files.uploadHint')}
          </div>
          <div className="upload-hint">
            {selectedFile
              ? `${t('files.uploadHintSelected')}: ${formatFileSize(selectedFile.size)}`
              : t('files.supportedFormats')}
          </div>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          onChange={handleFileInputChange}
          style={{ display: 'none' }}
          accept={supportedExtensions?.supported_extensions && Array.isArray(supportedExtensions.supported_extensions)
            ? supportedExtensions.supported_extensions.map(ext => `.${ext}`).join(',')
            : undefined}
        />

        {selectedFile && (
          <div style={{ marginTop: '1.5rem' }}>
            {uploading && (
              <div>
                <div className="progress-bar">
                  <div
                    className="progress-bar-fill"
                    style={{ width: `${uploadProgress}%` }}
                  ></div>
                </div>
                <p style={{ textAlign: 'center', color: '#4a5568', marginTop: '0.5rem' }}>
                  {t('files.uploading')} {uploadProgress}%
                </p>
              </div>
            )}

            {!uploading && (
              <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
                <button
                  onClick={handleUpload}
                  className="btn btn-primary"
                  disabled={uploading}
                >
                  <Upload size={20} />
                  {t('files.uploadButton')}
                </button>
                <button
                  onClick={() => {
                    setSelectedFile(null);
                    if (fileInputRef.current) {
                      fileInputRef.current.value = '';
                    }
                  }}
                  className="btn btn-secondary"
                >
                  {t('files.cancel')}
                </button>
              </div>
            )}
          </div>
        )}

        {supportedExtensions && supportedExtensions.supported_extensions && Array.isArray(supportedExtensions.supported_extensions) && (
          <div style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '1px solid #e2e8f0' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.5rem' }}>
              {supportedExtensions.supported_extensions.map((ext) => (
                <span key={ext} className="source-badge">
                  .{ext}
                </span>
              ))}
            </div>
            <p style={{ color: '#718096', fontSize: '0.9rem', margin: 0 }}>
              {t('files.maxFileSize')}: {supportedExtensions.max_file_size_mb} MB
            </p>
          </div>
        )}
      </div>

      {/* Files List Section */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h2 className="card-title" style={{ marginBottom: 0 }}>
            <Files size={28} />
            {t('files.manageTitle')}
          </h2>
          <button
            onClick={loadFiles}
            className="btn btn-secondary"
            disabled={loading}
          >
            <RefreshCw size={20} />
            {t('files.refresh')}
          </button>
        </div>

        {message && (
          <div className={`alert alert-${message.type}`}>
            {message.type === 'success' && <CheckCircle size={20} />}
            {message.type === 'error' && <XCircle size={20} />}
            {message.text}
          </div>
        )}

        {/* Tabs */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', borderBottom: '2px solid #e2e8f0' }}>
          <button
            onClick={() => handleTabChange('public')}
            style={{
              padding: '0.75rem 1.5rem',
              background: 'none',
              border: 'none',
              borderBottom: activeTab === 'public' ? '3px solid #667eea' : '3px solid transparent',
              color: activeTab === 'public' ? '#667eea' : '#718096',
              fontWeight: activeTab === 'public' ? 600 : 400,
              cursor: 'pointer',
              transition: 'all 0.2s',
              marginBottom: '-2px',
            }}
          >
            {t('files.publicFiles')}
          </button>
          {userProfile?.role !== 'admin' && (
            <button
              onClick={() => handleTabChange('private')}
              style={{
                padding: '0.75rem 1.5rem',
                background: 'none',
                border: 'none',
                borderBottom: activeTab === 'private' ? '3px solid #667eea' : '3px solid transparent',
                color: activeTab === 'private' ? '#667eea' : '#718096',
                fontWeight: activeTab === 'private' ? 600 : 400,
                cursor: 'pointer',
                transition: 'all 0.2s',
                marginBottom: '-2px',
              }}
            >
              {t('files.privateFiles')}
            </button>
          )}
        </div>

        {loading ? (
          <div className="spinner"></div>
        ) : filteredFiles.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem 1rem', color: '#a0aec0' }}>
            <File size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
            <p style={{ fontSize: '1.1rem', fontWeight: 500 }}>
              {t('files.noFiles')}
            </p>
            <p style={{ marginTop: '0.5rem', fontSize: '0.9rem' }}>
              {t('files.noFilesHint')}
            </p>
          </div>
        ) : (
          <>
            <div style={{ marginBottom: '1rem', color: '#718096', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>
                {t('files.showing')} {startIndex + 1}-{Math.min(endIndex, filteredFiles.length)} {t('files.of')} {filteredFiles.length}
              </span>
              <span style={{ fontSize: '0.9rem' }}>
                {t('files.totalFiles')}: {files.length} ({files.filter(f => f.is_public).length} {t('files.public')}, {files.filter(f => !f.is_public).length} {t('files.private')})
              </span>
            </div>

            <div className="file-list">
              {paginatedFiles.map((file) => {
                const formattedName = formatFileName(file.filename);
                return (
                <div key={file.filename} className="file-item">
                  <div className="file-info">
                    <div className="file-name">
                      <File size={18} style={{ display: 'inline', marginRight: '0.5rem' }} />
                      <span>{formattedName.display}</span>
                      <span style={{
                        marginLeft: '0.5rem',
                        padding: '0.125rem 0.375rem',
                        backgroundColor: '#e2e8f0',
                        color: '#4a5568',
                        borderRadius: '4px',
                        fontSize: '0.75rem',
                        fontWeight: '600',
                        textTransform: 'uppercase'
                      }}>
                        {formattedName.extension}
                      </span>
                    </div>
                    <div className="file-meta">
                      {formatFileSize(file.file_size)} • {file.chunk_count} {file.chunk_count === 1 ? 'chunk' : 'chunks'} •
                      {t('files.uploaded')}: {formatDate(file.uploaded_at)}
                    </div>
                    {file.feedback_stats && (
                      <div style={{ marginTop: '0.5rem', display: 'flex', gap: '1rem', fontSize: '0.875rem', color: '#718096' }}>
                        <span title="Times used in conversations">
                          📊 Used: {file.feedback_stats.total_uses}
                        </span>
                        <span title="Likes received" style={{ color: '#48bb78' }}>
                          👍 {file.feedback_stats.total_likes}
                        </span>
                        <span title="Dislikes received" style={{ color: '#f56565' }}>
                          👎 {file.feedback_stats.total_dislikes}
                        </span>
                      </div>
                    )}
                    {file.chunk_count === 0 && (
                      <div style={{ marginTop: '0.25rem', color: '#f59e0b', fontSize: '0.875rem' }}>
                        ⚠ {t('files.unsupported')}
                      </div>
                    )}
                  </div>

                  <div className="file-actions">
                    <button
                      onClick={() => handleDownload(file.filename)}
                      className="btn btn-primary"
                      disabled={downloading === file.filename}
                      style={{ padding: '0.5rem 1rem', marginRight: '0.5rem' }}
                    >
                      {downloading === file.filename ? (
                        <Loader size={16} className="spinner" />
                      ) : (
                        <>
                          <Download size={16} />
                          {t('files.download') || 'Download'}
                        </>
                      )}
                    </button>
                    {canDeleteFile(file) && (
                      <button
                        onClick={() => handleDelete(file.filename)}
                        className="btn btn-danger"
                        disabled={deleting === file.filename}
                        style={{ padding: '0.5rem 1rem' }}
                      >
                        {deleting === file.filename ? (
                          <>{t('files.deleting')}</>
                        ) : (
                          <>
                            <Trash2 size={16} />
                            {t('files.delete')}
                          </>
                        )}
                      </button>
                    )}
                  </div>
                </div>
              );
              })}
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '1rem', marginTop: '1.5rem' }}>
                <button
                  onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                  disabled={currentPage === 1}
                  className="btn btn-secondary"
                  style={{ padding: '0.5rem 1rem' }}
                >
                  <ChevronLeft size={18} />
                  {t('files.previous')}
                </button>

                <span style={{ color: '#718096', fontSize: '0.9rem' }}>
                  {t('files.page')} {currentPage} {t('files.of')} {totalPages}
                </span>

                <button
                  onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                  disabled={currentPage === totalPages}
                  className="btn btn-secondary"
                  style={{ padding: '0.5rem 1rem' }}
                >
                  {t('files.next')}
                  <ChevronRight size={18} />
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default FilesPage;
