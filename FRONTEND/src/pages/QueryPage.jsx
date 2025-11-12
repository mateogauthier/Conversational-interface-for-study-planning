import { useState, useRef, useEffect } from 'react';
import { Send, MessageCircle, FileText, Loader } from 'lucide-react';
import { ragApi } from '../services/api';

function QueryPage() {
  const [messages, setMessages] = useState([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [nResults, setNResults] = useState(5);
  const [language, setLanguage] = useState('auto');

  // Conversation state
  const [currentConversationId, setCurrentConversationId] = useState(null);

  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    const userMessage = {
      type: 'user',
      content: query,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setQuery('');
    setLoading(true);

    try {
      const response = await ragApi.query(query, {
        nResults,
        language: language === 'auto' ? null : language,
        conversationId: currentConversationId, // Pass conversation ID
      });

      // Update conversation ID from response
      setCurrentConversationId(response.conversation_id);

      const assistantMessage = {
        type: 'assistant',
        content: response.answer,
        sources: response.sources,
        chunks: response.relevant_chunks,
        model: response.model_used,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
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
      setLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([]);
    setCurrentConversationId(null); // Reset conversation when clearing chat
  };

  return (
    <div>
      <div className="card">
        <h2 className="card-title">
          <MessageCircle size={28} />
          Query Your Documents
        </h2>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Number of Chunks</label>
            <select
              className="select"
              value={nResults}
              onChange={(e) => setNResults(parseInt(e.target.value))}
            >
              <option value={3}>3 chunks</option>
              <option value={5}>5 chunks</option>
              <option value={10}>10 chunks</option>
              <option value={15}>15 chunks</option>
            </select>
          </div>

          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label">Response Language</label>
            <select
              className="select"
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
            >
              <option value="auto">Auto-detect</option>
              <option value="english">English</option>
              <option value="spanish">Spanish</option>
            </select>
          </div>
        </div>

        <div className="chat-container">
          <div className="chat-messages">
            {messages.length === 0 && (
              <div style={{ textAlign: 'center', padding: '3rem 1rem', color: '#a0aec0' }}>
                <MessageCircle size={48} style={{ marginBottom: '1rem', opacity: 0.5 }} />
                <p style={{ fontSize: '1.1rem', fontWeight: 500 }}>
                  No messages yet. Ask a question about your documents!
                </p>
              </div>
            )}

            {messages.map((message, index) => (
              <ChatMessage key={index} message={message} />
            ))}

            {loading && (
              <div className="chat-message assistant">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Loader size={20} className="spinner-icon" style={{ animation: 'spin 1s linear infinite' }} />
                  <span>Thinking...</span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          <form onSubmit={handleSubmit} className="chat-input-container">
            <input
              type="text"
              className="input chat-input"
              placeholder="Ask a question about your documents..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={loading}
            />
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading || !query.trim()}
            >
              <Send size={20} />
              Send
            </button>
          </form>

          {messages.length > 0 && (
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
              <button onClick={clearChat} className="btn btn-secondary" style={{ fontSize: '0.9rem' }}>
                Clear Chat
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <h3 className="card-title">Query Tips</h3>
        <ul style={{ lineHeight: '2', paddingLeft: '1.5rem', color: '#4a5568' }}>
          <li>Ask specific questions about your study materials</li>
          <li>The system will search through all uploaded documents</li>
          <li>More chunks means more context but slower responses</li>
          <li>Language is auto-detected but you can force a specific language</li>
          <li>Answers are generated based on the content of your documents</li>
        </ul>
      </div>
    </div>
  );
}

function ChatMessage({ message }) {
  return (
    <div className={`chat-message ${message.type}`}>
      <div className="chat-message-content">
        {message.content}
      </div>

      {message.sources && message.sources.length > 0 && (
        <div className="chat-sources">
          <div className="chat-sources-title">
            <FileText size={14} style={{ display: 'inline', marginRight: '0.25rem' }} />
            Sources ({message.sources.length})
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
          Model: {message.model}
        </div>
      )}
    </div>
  );
}

export default QueryPage;
