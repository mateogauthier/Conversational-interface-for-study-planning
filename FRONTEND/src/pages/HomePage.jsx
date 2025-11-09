import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Upload, MessageCircle, Files, Database, BookOpen, Zap } from 'lucide-react';
import { ragApi, llmApi } from '../services/api';

function HomePage() {
  const [stats, setStats] = useState(null);
  const [llmStatus, setLlmStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);
      const [ragStatsResponse, llmStatusResponse] = await Promise.all([
        ragApi.getStats().catch(() => null),
        llmApi.getStatus().catch(() => null),
      ]);

      setStats(ragStatsResponse);
      setLlmStatus(llmStatusResponse);
    } catch (error) {
      console.error('Failed to load stats:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="card">
        <h2 className="card-title">
          <BookOpen size={28} />
          Welcome to Study Planning Assistant
        </h2>
        <p style={{ lineHeight: '1.8', marginBottom: '2rem', color: '#4a5568' }}>
          This is a RAG-powered (Retrieval-Augmented Generation) study planning system that helps you organize
          and query your study materials. Upload documents, and ask questions to get intelligent answers based
          on your uploaded content.
        </p>

        {loading ? (
          <div className="spinner"></div>
        ) : (
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-value">{stats?.document_count || 0}</div>
              <div className="stat-label">Documents Uploaded</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats?.total_chunks || 0}</div>
              <div className="stat-label">Document Chunks</div>
            </div>
            <div className="stat-card">
              <div className={`stat-value ${llmStatus?.is_available ? '' : 'text-error'}`}>
                {llmStatus?.is_available ? '✓' : '✗'}
              </div>
              <div className="stat-label">LLM Status</div>
            </div>
          </div>
        )}
      </div>

      <div className="card">
        <h3 className="card-title">
          <Zap size={24} />
          Quick Actions
        </h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1rem' }}>
          <Link to="/upload" className="btn btn-primary">
            <Upload size={20} />
            Upload Documents
          </Link>
          <Link to="/query" className="btn btn-primary">
            <MessageCircle size={20} />
            Query Documents
          </Link>
          <Link to="/files" className="btn btn-secondary">
            <Files size={20} />
            Manage Files
          </Link>
        </div>
      </div>

      <div className="card">
        <h3 className="card-title">
          <Database size={24} />
          System Information
        </h3>
        <div style={{ display: 'grid', gap: '1rem' }}>
          {stats && (
            <>
              <InfoRow label="Collection Name" value={stats.collection_name} />
              <InfoRow label="Embedding Model" value={stats.embedding_model} />
            </>
          )}
          {llmStatus && (
            <>
              <InfoRow label="LLM Service" value={llmStatus.service || 'Ollama'} />
              <InfoRow label="Base URL" value={llmStatus.base_url} />
              <InfoRow label="Default Model" value={llmStatus.default_model} />
            </>
          )}
        </div>
      </div>

      <div className="card">
        <h3 className="card-title">How It Works</h3>
        <ol style={{ lineHeight: '2', paddingLeft: '1.5rem', color: '#4a5568' }}>
          <li><strong>Upload:</strong> Upload your study materials (PDF, Word, Excel, Text, Markdown)</li>
          <li><strong>Processing:</strong> Documents are split into chunks and converted to embeddings</li>
          <li><strong>Query:</strong> Ask questions about your materials in natural language</li>
          <li><strong>Retrieval:</strong> The system finds relevant chunks from your documents</li>
          <li><strong>Generation:</strong> An LLM generates answers based on the retrieved context</li>
        </ol>
      </div>
    </div>
  );
}

function InfoRow({ label, value }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0.75rem', backgroundColor: '#f7fafc', borderRadius: '6px' }}>
      <span style={{ fontWeight: 600, color: '#2d3748' }}>{label}:</span>
      <span style={{ color: '#4a5568', fontFamily: 'monospace', fontSize: '0.9rem' }}>{value}</span>
    </div>
  );
}

export default HomePage;
