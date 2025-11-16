import { useState, useEffect, useRef } from 'react';
import { Send, FileText, Loader, MessageCircle, Plus, Trash2, Menu, X, ThumbsUp, ThumbsDown } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { ragApi, llmApi, conversationApi, feedbackApi } from '../services/api';

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
        id: msg._id || msg.id,
        type: msg.role === 'user' ? 'user' : 'assistant',
        content: msg.content,
        timestamp: new Date(msg.timestamp),
        model: msg.model_used,
        sources: msg.source_files || [],
        feedback: msg.feedback,
        // Note: chunks are not stored in message history
      }));

      setMessages(chatMessages);
      setCurrentConversationId(conversationId);
    } catch (error) {
      console.error('Failed to load conversation:', error);
      alert(t('home.loadError'));
    }
  };

  const startNewConversation = () => {
    setMessages([]);
    setCurrentConversationId(null);
  };

  const deleteConversation = async (conversationId, e) => {
    e.stopPropagation(); // Prevent triggering loadConversation

    if (!confirm(t('home.deleteConfirm'))) {
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
      alert(t('home.deleteError'));
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
          id: response.message_id,
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
          t('home.errorMessage'),
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
            {t('home.conversations')}
          </h3>
          <button
            onClick={() => setSidebarOpen(false)}
            className="btn btn-secondary"
            style={{ padding: '0.25rem', minWidth: 'auto' }}
            title={t('home.closeSidebar')}
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
            {t('home.newConversation')}
          </button>
        </div>

        {/* Conversations List */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '0 1rem 1rem' }}>
          {conversationsLoading ? (
            <div style={{ textAlign: 'center', padding: '2rem 0', color: '#718096' }}>
              <Loader size={24} className="spinner-icon" style={{ animation: 'spin 1s linear infinite' }} />
              <p style={{ marginTop: '0.5rem', fontSize: '0.9rem' }}>{t('home.loadingConversations')}</p>
            </div>
          ) : conversations.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '2rem 1rem', color: '#718096' }}>
              <MessageCircle size={32} style={{ marginBottom: '0.5rem', opacity: 0.5 }} />
              <p style={{ fontSize: '0.9rem' }}>{t('home.noConversations')}</p>
              <p style={{ fontSize: '0.8rem', marginTop: '0.25rem' }}>{t('home.startNew')}</p>
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
                      {conv.message_count} {t('home.messages')}
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
                    title={t('home.deleteConversation')}
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
              title={t('home.openSidebar')}
            >
              <Menu size={20} />
            </button>
          )}
          <div style={{ flex: 1 }}>
            <h2 style={{ margin: 0, fontSize: '1.25rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <MessageCircle size={24} />
              {currentConversationId ? t('home.continueConversation') : t('home.title')}
            </h2>
          </div>
        </div>

        {/* Chat Messages */}
        <div
          style={{
            flex: 1,
            overflowY: 'auto',
            padding: '0',
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
                {currentConversationId ? t('home.continueBelow') : t('home.startOrSelect')}
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
  const [feedback, setFeedback] = useState(message.feedback || null);
  const [submittingFeedback, setSubmittingFeedback] = useState(false);
  const [showCommentBox, setShowCommentBox] = useState(false);
  const [comment, setComment] = useState('');
  const [pendingFeedback, setPendingFeedback] = useState(null);

  const handleFeedback = async (newFeedback) => {
    if (submittingFeedback || !message.id) return;

    // Show comment box and save pending feedback
    setPendingFeedback(newFeedback);
    setShowCommentBox(true);
  };

  const submitFeedbackWithComment = async () => {
    if (submittingFeedback || !message.id || !pendingFeedback) return;

    try {
      setSubmittingFeedback(true);
      // Submit with optional comment (empty string will be ignored by backend)
      await feedbackApi.submitFeedback(message.id, pendingFeedback, comment.trim() || null);
      setFeedback(pendingFeedback);
      setShowCommentBox(false);
      setComment('');
      setPendingFeedback(null);
    } catch (error) {
      console.error('Failed to submit feedback:', error);
      // Optionally show error message to user
    } finally {
      setSubmittingFeedback(false);
    }
  };

  const cancelFeedback = () => {
    setShowCommentBox(false);
    setComment('');
    setPendingFeedback(null);
  };

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

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '0.5rem' }}>
        <div>
          {message.model && (
            <div style={{ fontSize: '0.75rem', color: '#a0aec0' }}>
              {t('home.model')}: {message.model}
            </div>
          )}
        </div>

        {/* Feedback buttons for assistant messages */}
        {message.type === 'assistant' && message.id && !showCommentBox && (
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <button
              onClick={() => handleFeedback('like')}
              disabled={submittingFeedback}
              style={{
                background: 'none',
                border: 'none',
                cursor: submittingFeedback ? 'not-allowed' : 'pointer',
                padding: '0.25rem',
                display: 'flex',
                alignItems: 'center',
                color: feedback === 'like' ? '#48bb78' : '#a0aec0',
                transition: 'color 0.2s',
                opacity: submittingFeedback ? 0.5 : 1,
              }}
              onMouseEnter={(e) => !submittingFeedback && feedback !== 'like' && (e.currentTarget.style.color = '#48bb78')}
              onMouseLeave={(e) => feedback !== 'like' && (e.currentTarget.style.color = '#a0aec0')}
              title={t('home.like')}
            >
              <ThumbsUp size={16} fill={feedback === 'like' ? '#48bb78' : 'none'} />
            </button>
            <button
              onClick={() => handleFeedback('dislike')}
              disabled={submittingFeedback}
              style={{
                background: 'none',
                border: 'none',
                cursor: submittingFeedback ? 'not-allowed' : 'pointer',
                padding: '0.25rem',
                display: 'flex',
                alignItems: 'center',
                color: feedback === 'dislike' ? '#f56565' : '#a0aec0',
                transition: 'color 0.2s',
                opacity: submittingFeedback ? 0.5 : 1,
              }}
              onMouseEnter={(e) => !submittingFeedback && feedback !== 'dislike' && (e.currentTarget.style.color = '#f56565')}
              onMouseLeave={(e) => feedback !== 'dislike' && (e.currentTarget.style.color = '#a0aec0')}
              title={t('home.dislike')}
            >
              <ThumbsDown size={16} fill={feedback === 'dislike' ? '#f56565' : 'none'} />
            </button>
          </div>
        )}
      </div>

      {/* Comment box for feedback */}
      {showCommentBox && message.type === 'assistant' && message.id && (
        <div style={{
          marginTop: '1rem',
          padding: '1rem',
          backgroundColor: '#2d3748',
          borderRadius: '0.5rem',
          border: '1px solid #4a5568',
        }}>
          <div style={{ marginBottom: '0.5rem', fontSize: '0.875rem', color: '#a0aec0' }}>
            {pendingFeedback === 'like' ? '👍 ' : '👎 '}
            Add a comment (optional)
          </div>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Share your thoughts about this response..."
            style={{
              width: '100%',
              minHeight: '80px',
              padding: '0.5rem',
              backgroundColor: '#1a202c',
              border: '1px solid #4a5568',
              borderRadius: '0.25rem',
              color: '#e2e8f0',
              fontSize: '0.875rem',
              resize: 'vertical',
              fontFamily: 'inherit',
            }}
          />
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
            <button
              onClick={submitFeedbackWithComment}
              disabled={submittingFeedback}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: pendingFeedback === 'like' ? '#48bb78' : '#f56565',
                color: 'white',
                border: 'none',
                borderRadius: '0.25rem',
                cursor: submittingFeedback ? 'not-allowed' : 'pointer',
                fontSize: '0.875rem',
                opacity: submittingFeedback ? 0.6 : 1,
              }}
            >
              {submittingFeedback ? 'Submitting...' : 'Submit Feedback'}
            </button>
            <button
              onClick={cancelFeedback}
              disabled={submittingFeedback}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: 'transparent',
                color: '#a0aec0',
                border: '1px solid #4a5568',
                borderRadius: '0.25rem',
                cursor: submittingFeedback ? 'not-allowed' : 'pointer',
                fontSize: '0.875rem',
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default HomePage;
