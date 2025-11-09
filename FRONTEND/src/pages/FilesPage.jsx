import { useState, useEffect } from 'react';
import { Files, Trash2, RefreshCw, File, CheckCircle, XCircle } from 'lucide-react';
import { fileApi } from '../services/api';

function FilesPage() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState(null);
  const [deleting, setDeleting] = useState(null);

  useEffect(() => {
    loadFiles();
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

      <div className="card">
        <h3 className="card-title">File Management Tips</h3>
        <ul style={{ lineHeight: '2', paddingLeft: '1.5rem', color: '#4a5568' }}>
          <li>Deleting a file will remove it from the system and the RAG index</li>
          <li>You cannot undo file deletions</li>
          <li>Files are automatically processed for RAG upon upload</li>
          <li>Only supported file types can be queried via RAG</li>
          <li>The system maintains metadata for all uploaded files</li>
        </ul>
      </div>
    </div>
  );
}

export default FilesPage;
