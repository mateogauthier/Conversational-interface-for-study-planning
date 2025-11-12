import { useState, useEffect, useRef } from 'react';
import { Send, FileText, Loader, MessageCircle, Plus, Trash2, Menu, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { ragApi, llmApi, conversationApi } from '../services/api';

function HomePage() {
  const { t } = useTranslation();
  const { accessToken } = useAuth();

  // Query state
  const [messages, setMessages] = useState([]);
  const [query, setQuery] = useState('');
  const [queryLoading, setQueryLoading] = useState(false);
  // Read useRAG from localStorage (default to true)
  const useRAG = localStorage.getItem('useRAG') !== 'false';

  // Conversation state
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [conversationsLoading, setConversationsLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const messagesEndRef = useRef(null);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Only load conversations when authenticated
    if (accessToken) {
      loadConversations();
    }
  }, [accessToken]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadConversations = async () => {
    setConversationsLoading(true);
    try {
      const response = await conversationApi.list(50, 0);
      console.log('Conversations response:', response);
      console.log('First conversation:', response.conversations[0]);
      setConversations(response.conversations);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    } finally {
      setConversationsLoading(false);
    }
  };

  const loadConversation = async (conversationId) => {
    try {
      const response = await conversationApi.get(conversationId);

      // Convert messages to chat format
      const chatMessages = response.messages.map(msg => ({
        type: msg.role === 'user' ? 'user' : 'assistant',
        content: msg.content,
        timestamp: new Date(msg.timestamp),
        model: msg.model_used,
        // Note: sources and chunks are not stored in message history
      }));

      setMessages(chatMessages);
      setCurrentConversationId(conversationId);
    } catch (error) {
      console.error('Failed to load conversation:', error);
      alert('Failed to load conversation. Please try again.');
    }
  };

  const startNewConversation = () => {
    setMessages([]);
    setCurrentConversationId(null);
  };

  const deleteConversation = async (conversationId, e) => {
    e.stopPropagation(); // Prevent triggering loadConversation

    if (!confirm('Are you sure you want to delete this conversation?')) {
      return;
    }

    try {
      await conversationApi.delete(conversationId);

      // If deleted conversation was active, start new conversation
      if (conversationId === currentConversationId) {
        startNewConversation();
      }

      // Reload conversations list
      loadConversations();
    } catch (error) {
      console.error('Failed to delete conversation:', error);
      alert('Failed to delete conversation. Please try again.');
    }
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
    const currentQuery = query;
    setQuery('');
    setQueryLoading(true);

    try {
      // Get preferences from localStorage
      const preferredModel = localStorage.getItem('preferredModel');
      const preferredLanguage = localStorage.getItem('preferredLanguage') || 'auto';
      const preferredChunks = parseInt(localStorage.getItem('preferredChunks') || '5');

      let response;

      if (useRAG) {
        // RAG-enabled query (with conversation support)
        response = await ragApi.query(currentQuery, {
          nResults: preferredChunks,
          language: preferredLanguage === 'auto' ? null : preferredLanguage,
          model: preferredModel || null,
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

        // Reload conversations list if this was a new conversation
        if (!currentConversationId) {
          loadConversations();
        }
      } else {
        // Direct LLM query (no RAG)
        response = await llmApi.query(currentQuery, preferredModel || null);

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

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 80px)', gap: '0', position: 'relative' }}>
      {/* Sidebar */}
      <div
        style={{
          width: sidebarOpen ? '280px' : '0',
          minWidth: sidebarOpen ? '280px' : '0',
          backgroundColor: '#ffffff',
          borderRight: sidebarOpen ? '1px solid #e2e8f0' : 'none',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          transition: 'all 0.3s ease',
        }}
      >
        {/* Sidebar Header */}
        <div
          style={{
            padding: '1rem',
            borderBottom: '1px solid #e2e8f0',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: '#2d3748' }}>
            Conversations
          </h3>
          <button
            onClick={() => setSidebarOpen(false)}
            className="btn btn-secondary"
            style={{ padding: '0.25rem', minWidth: 'auto' }}
            title="Close sidebar"
          >
            <X size={16} />
          </button>
        </div>

        {/* New Conversation Button */}
        <div style={{ padding: '1rem' }}>
          <button
            onClick={startNewConversation}
            className="btn btn-primary"
            style={{ width: '100%', display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center' }}
          >
            <Plus size={18} />
            New Conversation
          </button>
        </div>

        {/* Conversations List */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '0 1rem 1rem' }}>
          {conversationsLoading ? (
            <div style={{ textAlign: 'center', padding: '2rem 0', color: '#718096' }}>
              <Loader size={24} className="spinner-icon" style={{ animation: 'spin 1s linear infinite' }} />
              <p style={{ marginTop: '0.5rem', fontSize: '0.9rem' }}>Loading conversations...</p>
            </div>
          ) : conversations.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '2rem 1rem', color: '#718096' }}>
              <MessageCircle size={32} style={{ marginBottom: '0.5rem', opacity: 0.5 }} />
              <p style={{ fontSize: '0.9rem' }}>No conversations yet</p>
              <p style={{ fontSize: '0.8rem', marginTop: '0.25rem' }}>Start a new one!</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {conversations.map((conv) => (
                <div
                  key={conv._id || conv.id}
                  onClick={() => loadConversation(conv._id || conv.id)}
                  style={{
                    padding: '0.75rem',
                    backgroundColor: currentConversationId === (conv._id || conv.id) ? '#e6f2ff' : '#f8fafc',
                    borderRadius: '0.5rem',
                    cursor: 'pointer',
                    transition: 'background-color 0.2s',
                    border: currentConversationId === (conv._id || conv.id) ? '1px solid #667eea' : '1px solid #e2e8f0',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    gap: '0.5rem',
                  }}
                  onMouseEnter={(e) => {
                    if (currentConversationId !== (conv._id || conv.id)) {
                      e.currentTarget.style.backgroundColor = '#e6f2ff';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (currentConversationId !== (conv._id || conv.id)) {
                      e.currentTarget.style.backgroundColor = '#f8fafc';
                    }
                  }}
                >
                  <div style={{ flex: 1, overflow: 'hidden' }}>
                    <p
                      style={{
                        margin: 0,
                        fontSize: '0.9rem',
                        fontWeight: 500,
                        color: '#2d3748',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                    >
                      {conv.title}
                    </p>
                    <p
                      style={{
                        margin: '0.25rem 0 0 0',
                        fontSize: '0.75rem',
                        color: '#718096',
                      }}
                    >
                      {conv.message_count} messages
                    </p>
                  </div>
                  <button
                    onClick={(e) => deleteConversation(conv._id || conv.id, e)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#e53e3e',
                      cursor: 'pointer',
                      padding: '0.25rem',
                      display: 'flex',
                      alignItems: 'center',
                      opacity: 0.7,
                      transition: 'opacity 0.2s',
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.opacity = '1')}
                    onMouseLeave={(e) => (e.currentTarget.style.opacity = '0.7')}
                    title="Delete conversation"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Header */}
        <div
          style={{
            padding: '1rem 1.5rem',
            borderBottom: '1px solid #e2e8f0',
            backgroundColor: '#ffffff',
            display: 'flex',
            alignItems: 'center',
            gap: '1rem',
          }}
        >
          {!sidebarOpen && (
            <button
              onClick={() => setSidebarOpen(true)}
              className="btn btn-secondary"
              style={{ padding: '0.5rem', minWidth: 'auto' }}
              title="Open sidebar"
            >
              <Menu size={20} />
            </button>
          )}
          <div style={{ flex: 1 }}>
            <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <MessageCircle size={24} />
              {currentConversationId ? 'Continue Conversation' : t('home.title')}
            </h2>
          </div>
        </div>

        {/* Chat Messages */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '1.5rem',
            backgroundColor: '#f8fafc',
          }}
        >
          {messages.length === 0 && (
            <div style={{ textAlign: 'center', padding: '3rem 1rem', color: '#718096' }}>
              <MessageCircle size={64} style={{ marginBottom: '1rem', opacity: 0.3 }} />
              <p style={{ fontSize: '1.25rem', fontWeight: 500 }}>
                {t('home.noMessages')}
              </p>
              <p style={{ marginTop: '0.5rem', fontSize: '1rem', color: '#718096' }}>
                {currentConversationId ? 'Continue the conversation below' : 'Start a new conversation or select one from the sidebar'}
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

        {/* Chat Input */}
        <div
          style={{
            padding: '1rem 1.5rem',
            backgroundColor: '#ffffff',
            borderTop: '1px solid #e2e8f0',
          }}
        >
          <form onSubmit={handleQuerySubmit} style={{ display: 'flex', gap: '0.75rem' }}>
            <input
              type="text"
              className="input chat-input"
              placeholder={t('home.placeholder')}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              disabled={queryLoading}
              style={{ flex: 1 }}
            />
            <button
              type="submit"
              className="btn btn-primary"
              disabled={queryLoading || !query.trim()}
              style={{ minWidth: '100px' }}
            >
              <Send size={20} />
              {t('home.send')}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

function ChatMessage({ message }) {
  const { t } = useTranslation();

  return (
    <div className={`chat-message ${message.type}`} style={{ marginBottom: '1rem' }}>
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
