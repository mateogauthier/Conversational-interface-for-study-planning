import { useState, useEffect, useRef } from 'react';
import { Send, FileText, Loader, MessageCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { ragApi, llmApi } from '../services/api';

function HomePage() {
  const { t } = useTranslation();

  // Query state
  const [messages, setMessages] = useState([]);
  const [query, setQuery] = useState('');
  const [queryLoading, setQueryLoading] = useState(false);
  const [useRAG, setUseRAG] = useState(
    localStorage.getItem('useRAG') !== 'false' // Default to true
  );
  const messagesEndRef = useRef(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Handle RAG toggle change
  const handleRAGToggle = (e) => {
    const newValue = e.target.checked;
    setUseRAG(newValue);
    localStorage.setItem('useRAG', newValue.toString());
  };

  // Query handlers
  const handleQuerySubmit = async (e) => {
    e.preventDefault();
    if (!query.trim() || queryLoading) return;

    const userMessage = {
      type: 'user',
      content: query,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setQuery('');
    setQueryLoading(true);

    try {
      // Get preferences from localStorage
      const preferredModel = localStorage.getItem('preferredModel');
      const preferredLanguage = localStorage.getItem('preferredLanguage') || 'auto';
      const preferredChunks = parseInt(localStorage.getItem('preferredChunks') || '5');

      let response;

      if (useRAG) {
        // RAG-enabled query
        response = await ragApi.query(query, {
          nResults: preferredChunks,
          language: preferredLanguage === 'auto' ? null : preferredLanguage,
          model: preferredModel || null,
        });

        const assistantMessage = {
          type: 'assistant',
          content: response.answer,
          sources: response.sources,
          chunks: response.relevant_chunks,
          model: response.model_used,
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMessage]);
      } else {
        // Direct LLM query (no RAG)
        response = await llmApi.query(query, preferredModel || null);

        const assistantMessage = {
          type: 'assistant',
          content: response.response,
          model: response.model_used,
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMessage]);
      }
    } catch (error) {
      const errorMessage = {
        type: 'assistant',
        content:
          error.response?.data?.detail ||
          'Sorry, I encountered an error while processing your query. Please try again.',
        error: true,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setQueryLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([]);
  };

  return (
    <div>
      {/* Query Section */}
      <div className="card">
        <h2 className="card-title">
          <MessageCircle size={28} />
          {t('home.title')}
        </h2>

        {/* RAG Toggle */}
        <div style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <input
            type="checkbox"
            id="useRAG"
            checked={useRAG}
            onChange={handleRAGToggle}
            style={{ cursor: 'pointer', width: '18px', height: '18px' }}
          />
          <label htmlFor="useRAG" style={{ cursor: 'pointer', fontSize: '0.95rem', userSelect: 'none' }}>
            {t('home.useRAG')}
          </label>
          <span style={{ color: '#a0aec0', fontSize: '0.85rem', marginLeft: '0.25rem' }}>
            {useRAG ? t('home.ragEnabled') : t('home.ragDisabled')}
          </span>
        </div>

        <div className="chat-container">
          <div className="chat-messages">
            {messages.length === 0 && (
              <div style={{ textAlign: 'center', padding: '3rem 1rem', color: '#a0aec0' }}>
                <MessageCircle size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
                <p style={{ fontSize: '1.1rem', fontWeight: 500 }}>
                  {t('home.noMessages')}
                </p>
                <p style={{ marginTop: '0.5rem', fontSize: '0.9rem' }}>
                  {t('home.configureSettings')}
                </p>
              </div>
            )}

            {messages.map((message, index) => (
              <ChatMessage key={index} message={message} />
            ))}

            {queryLoading && (
              <div className="chat-message assistant">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Loader size={20} className="spinner-icon" style={{ animation: 'spin 1s linear infinite' }} />
                  <span>{t('home.thinking')}</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          <form onSubmit={handleQuerySubmit} className="chat-input-container">
            <input
              type="text"
              className="input chat-input"
              placeholder={t('home.placeholder')}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={queryLoading}
            />
            <button
              type="submit"
              className="btn btn-primary"
              disabled={queryLoading || !query.trim()}
            >
              <Send size={20} />
              {t('home.send')}
            </button>
          </form>

          {messages.length > 0 && (
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
              <button onClick={clearChat} className="btn btn-secondary" style={{ fontSize: '0.9rem' }}>
                {t('home.clearChat')}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ChatMessage({ message }) {
  const { t } = useTranslation();

  return (
    <div className={`chat-message ${message.type}`}>
      <div className="chat-message-content">
        {message.content}
      </div>

      {message.sources && message.sources.length > 0 && (
        <div className="chat-sources">
          <div className="chat-sources-title">
            <FileText size={14} style={{ display: 'inline', marginRight: '0.25rem' }} />
            {t('home.sources')} ({message.sources.length})
          </div>
          <div className="chat-sources-list">
            {message.sources.map((source, idx) => (
              <span key={idx} className="source-badge">
                {source}
              </span>
            ))}
          </div>
        </div>
      )}

      {message.model && (
        <div style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: '#a0aec0' }}>
          {t('home.model')}: {message.model}
        </div>
      )}
    </div>
  );
}

export default HomePage;
