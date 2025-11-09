import { useState, useEffect, useRef } from 'react';
import { Upload, File, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { fileApi } from '../services/api';

function UploadPage() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [message, setMessage] = useState(null);
  const [supportedExtensions, setSupportedExtensions] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    loadSupportedExtensions();
  }, []);

  const loadSupportedExtensions = async () => {
    try {
      const response = await fileApi.getSupportedExtensions();
      setSupportedExtensions(response);
    } catch (error) {
      console.error('Failed to load supported extensions:', error);
    }
  };

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
    setMessage(null);
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
    setMessage(null);
    setUploadProgress(0);

    try {
      const response = await fileApi.upload(selectedFile, (progress) => {
        setUploadProgress(progress);
      });

      setMessage({
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
    } catch (error) {
      setMessage({
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

  return (
    <div>
      <div className="card">
        <h2 className="card-title">
          <Upload size={28} />
          Upload Study Materials
        </h2>

        {message && (
          <div className={`alert alert-${message.type}`}>
            {message.type === 'success' && <CheckCircle size={20} />}
            {message.type === 'error' && <XCircle size={20} />}
            {message.type === 'warning' && <AlertCircle size={20} />}
            {message.text}
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
          accept={supportedExtensions?.supported_extensions.map(ext => `.${ext}`).join(',')}
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
      </div>

      {supportedExtensions && (
        <div className="card">
          <h3 className="card-title">
            <File size={24} />
            Supported File Types
          </h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
            {supportedExtensions.supported_extensions.map((ext) => (
              <span key={ext} className="source-badge">
                .{ext}
              </span>
            ))}
          </div>
          <p style={{ marginTop: '1rem', color: '#718096', fontSize: '0.9rem' }}>
            Maximum file size: {supportedExtensions.max_file_size_mb} MB
          </p>
        </div>
      )}

      <div className="card">
        <h3 className="card-title">Upload Tips</h3>
        <ul style={{ lineHeight: '2', paddingLeft: '1.5rem', color: '#4a5568' }}>
          <li>Files are automatically processed and indexed for searching</li>
          <li>Larger files may take longer to process</li>
          <li>PDF files work best when they contain selectable text</li>
          <li>You can upload multiple files and query across all of them</li>
          <li>Files can be managed and deleted from the Files page</li>
        </ul>
      </div>
    </div>
  );
}

export default UploadPage;
