import { useState, useEffect, useRef } from 'react';
import { Files, Trash2, RefreshCw, File, CheckCircle, XCircle, Upload, AlertCircle, Loader } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { fileApi } from '../services/api';
import { useAuth } from '../context/AuthContext';

function FilesPage() {
  const { t } = useTranslation();
  const { isLoading: authLoading, accessToken } = useAuth();
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState(null);
  const [deleting, setDeleting] = useState(null);

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
    if (!confirm(`${t('files.deleteConfirm')} "${filename}"?`)) {
      return;
    }

    try {
      setDeleting(filename);
      await fileApi.delete(filename);
      setMessage({
        type: 'success',
        text: `"${filename}" ${t('files.deleteSuccess')}`,
      });
      await loadFiles();
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || `${t('files.deleteError')} "${filename}".`,
      });
    } finally {
      setDeleting(null);
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

        {loading ? (
          <div className="spinner"></div>
        ) : files.length === 0 ? (
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
            <div style={{ marginBottom: '1rem', color: '#718096' }}>
              {t('files.totalFiles')}: {files.length}
            </div>

            <div className="file-list">
              {files.map((file) => (
                <div key={file.filename} className="file-item">
                  <div className="file-info">
                    <div className="file-name">
                      <File size={18} style={{ display: 'inline', marginRight: '0.5rem' }} />
                      {file.filename}
                    </div>
                    <div className="file-meta">
                      {formatFileSize(file.file_size)} • {file.chunk_count} {file.chunk_count === 1 ? 'chunk' : 'chunks'} •
                      {t('files.uploaded')}: {formatDate(file.uploaded_at)}
                    </div>
                    {file.chunk_count === 0 && (
                      <div style={{ marginTop: '0.25rem', color: '#f59e0b', fontSize: '0.875rem' }}>
                        ⚠ {t('files.unsupported')}
                      </div>
                    )}
                  </div>

                  <div className="file-actions">
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
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default FilesPage;
