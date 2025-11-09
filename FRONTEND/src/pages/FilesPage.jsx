import { useState, useEffect, useRef } from 'react';
import { Files, Trash2, RefreshCw, File, CheckCircle, XCircle, Upload, AlertCircle } from 'lucide-react';
import { fileApi } from '../services/api';

function FilesPage() {
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

  useEffect(() => {
    loadFiles();
    loadSupportedExtensions();
  }, []);

  const loadFiles = async () => {
    try {
      setLoading(true);
      setMessage(null);
      const response = await fileApi.list();
      setFiles(response.files || []);
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
    if (!confirm(`Are you sure you want to delete "${filename}"?`)) {
      return;
    }

    try {
      setDeleting(filename);
      await fileApi.delete(filename);
      setMessage({
        type: 'success',
        text: `File "${filename}" deleted successfully.`,
      });
      await loadFiles();
    } catch (error) {
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || `Failed to delete "${filename}".`,
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
          ? `File uploaded and processed successfully!`
          : `File uploaded but could not be processed for RAG.`,
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
        text: error.response?.data?.detail || 'Upload failed. Please try again.',
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

  const formatDate = (timestamp) => {
    return new Date(timestamp * 1000).toLocaleString();
  };

  return (
    <div>
      {/* Upload Section */}
      <div className="card">
        <h2 className="card-title">
          <Upload size={28} />
          Upload Study Materials
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
            {selectedFile ? selectedFile.name : 'Click or drag file to upload'}
          </div>
          <div className="upload-hint">
            {selectedFile
              ? `Size: ${formatFileSize(selectedFile.size)}`
              : 'Supports PDF, Word, Excel, Text, and Markdown files'}
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
                  Uploading... {uploadProgress}%
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
                  Upload File
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
                  Cancel
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
              Maximum file size: {supportedExtensions.max_file_size_mb} MB
            </p>
          </div>
        )}
      </div>

      {/* Files List Section */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h2 className="card-title" style={{ marginBottom: 0 }}>
            <Files size={28} />
            Manage Files
          </h2>
          <button
            onClick={loadFiles}
            className="btn btn-secondary"
            disabled={loading}
          >
            <RefreshCw size={20} />
            Refresh
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
              No files uploaded yet
            </p>
            <p style={{ marginTop: '0.5rem', fontSize: '0.9rem' }}>
              Upload some documents to get started
            </p>
          </div>
        ) : (
          <>
            <div style={{ marginBottom: '1rem', color: '#718096' }}>
              Total files: {files.length}
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
                      {file.file_type} • {formatFileSize(file.size_bytes)} •
                      Uploaded: {formatDate(file.created_at)}
                    </div>
                    {!file.is_supported && (
                      <div style={{ marginTop: '0.25rem', color: '#f56565', fontSize: '0.875rem' }}>
                        ⚠ File type not supported for RAG processing
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
                        <>Deleting...</>
                      ) : (
                        <>
                          <Trash2 size={16} />
                          Delete
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
