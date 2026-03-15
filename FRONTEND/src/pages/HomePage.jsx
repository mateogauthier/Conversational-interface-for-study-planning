import { useState, useEffect, useRef } from 'react';
import { Send, FileText, Loader, MessageCircle, Plus, Trash2, Menu, X, ThumbsUp, ThumbsDown, Download, ChevronDown, ChevronUp, User, Bot } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { ragApi, llmApi, conversationApi, feedbackApi, fileApi, agentApi } from '../services/api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import mermaid from 'mermaid';
import AgentSteps from '../components/AgentSteps';
import ToolConfirmation from '../components/ToolConfirmation';
import { getErrorMessage, maybeTranslateAgentError } from '../utils/errorMessages';

// Mermaid diagram component
function MermaidDiagram({ chart }) {
  const ref = useRef(null);

  // Sanitize mermaid code to remove common syntax errors
  const sanitizeMermaid = (code) => {
    let fixed = code;

    // Remove // comments
    fixed = fixed.split('\n').map(line => {
      const commentIndex = line.indexOf('//');
      if (commentIndex !== -1) {
        return line.substring(0, commentIndex).trimEnd();
      }
      return line;
    }).join('\n');

    // Remove # comments ONLY in xychart data lines (not in other contexts)
    // Pattern: line [...] # comment or bar [...] # comment
    fixed = fixed.replace(/(line|bar)\s*(\[[^\]]+\])\s*#[^\n]*/gi, '$1 $2');

    return fixed.trim();
  };

  useEffect(() => {
    if (ref.current) {
      try {
        const sanitizedChart = sanitizeMermaid(chart);
        mermaid.initialize({ startOnLoad: false, theme: 'default' });
        mermaid.render('mermaid-' + Math.random().toString(36).substring(2, 11), sanitizedChart).then(({ svg }) => {
          ref.current.innerHTML = svg;
        }).catch((error) => {
          console.error('Mermaid rendering error:', error);
          ref.current.innerHTML = `<pre style="color: red;">Mermaid Error: ${error.message}</pre>`;
        });
      } catch (error) {
        console.error('Mermaid initialization error:', error);
        ref.current.innerHTML = `<pre style="color: red;">Mermaid Error: ${error.message}</pre>`;
      }
    }
  }, [chart]);

  return <div ref={ref} className="mermaid-diagram" />;
}

function HomePage() {
  const { t, i18n } = useTranslation();
  const { accessToken } = useAuth();

  const formatError = (detail) => getErrorMessage(detail, t, i18n.language);
  const normalizeAnswer = (text) => maybeTranslateAgentError(text, t, i18n.language);

  // Query state
  const [messages, setMessages] = useState([]);
  const [query, setQuery] = useState('');
  const [queryLoading, setQueryLoading] = useState(false);
  // Read useRAG from localStorage (default to true)
  const useRAG = localStorage.getItem('useRAG') !== 'false';
  // Read enableAgent from localStorage (default to true)
  const enableAgent = localStorage.getItem('enableAgent') !== 'false';

  // Conversation state
  const [currentConversationId, setCurrentConversationId] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [conversationsLoading, setConversationsLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Agent state
  const [pendingConfirmations, setPendingConfirmations] = useState([]);
  const [pendingQuestions, setPendingQuestions] = useState([]);
  const [currentQuestionId, setCurrentQuestionId] = useState(null);

  // Library renders everything inline - no separate artifact panel needed

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

      console.log('Loading conversation:', conversationId);
      console.log('Response messages:', response.messages);

      // Convert messages to chat format
      const chatMessages = response.messages.map(msg => {
        console.log('Message role:', msg.role, 'Content:', msg.content.substring(0, 50));
        return {
          id: msg._id || msg.id,
          type: msg.role, // Keep the role as-is (user/assistant)
          content: msg.content,
          timestamp: new Date(msg.timestamp),
          model: msg.model_used,
          sources: msg.source_files || [],
          feedback: msg.feedback,
          isLoadedFromHistory: true, // Mark as loaded from history
          // Note: chunks are not stored in message history
        };
      });

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

  // Query handlers: sendQuery(text) does the actual send; handleQuerySubmit is for the form.
  const sendQuery = async (queryText) => {
    const text = (typeof queryText === 'string' ? queryText : query).trim();
    if (!text || queryLoading) return;

    const userMessage = {
      type: 'user',
      content: text,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setQuery('');
    setQueryLoading(true);
    const currentQuery = text;

    try {
      // Get preferences from localStorage
      const preferredModel = localStorage.getItem('preferredModel');
      const preferredLanguage = localStorage.getItem('preferredLanguage') || 'auto';
      const preferredChunks = parseInt(localStorage.getItem('preferredChunks') || '5');

      let response;

      if (useRAG) {
        // Use agent API if enabled, otherwise standard RAG
        const apiToUse = enableAgent ? agentApi : ragApi;

        response = await apiToUse.query(currentQuery, {
          conversationId: currentConversationId,
          nResults: preferredChunks,
          language: preferredLanguage === 'auto' ? null : preferredLanguage,
          model: preferredModel || null,
          enableAgent: enableAgent,
        });

        // Update conversation ID from response
        setCurrentConversationId(response.conversation_id);

        // Check for pending confirmations (agent only)
        if (response.pending_confirmations && response.pending_confirmations.length > 0) {
          setPendingConfirmations(response.pending_confirmations);
        } else {
          setPendingConfirmations([]);
        }

        // Check for pending questions (agent only)
        if (response.pending_questions && response.pending_questions.length > 0) {
          setPendingQuestions(response.pending_questions);
          setCurrentQuestionId(response.pending_questions[0].question_id);
        } else {
          setPendingQuestions([]);
          setCurrentQuestionId(null);
        }

        // Create assistant message with agent-specific fields
        const assistantMessage = {
          id: response.message_id,
          type: 'assistant',
          content: normalizeAnswer(response.answer),
          sources: response.sources || [],
          chunks: response.relevant_chunks || [],
          model: response.model_used,
          timestamp: new Date(),
          // Agent-specific fields
          agentSteps: response.agent_steps || [],
          toolsExecuted: response.tools_executed || [],
          requiresConfirmation: response.requires_confirmation || false,
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
          content: normalizeAnswer(response.response),
          model: response.model_used,
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, assistantMessage]);
      }
    } catch (error) {
      const errorMessage = {
        type: 'assistant',
        content: formatError(error.response?.data?.detail),
        error: true,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setQueryLoading(false);
    }
  };

  const handleQuerySubmit = (e) => {
    e.preventDefault();
    sendQuery(query);
  };

  // Agent confirmation handlers
  const handleConfirmationApproved = (response) => {
    // Clear pending confirmations
    setPendingConfirmations([]);

    // Add agent response to messages
    const assistantMessage = {
      id: response.message_id,
      type: 'assistant',
      content: normalizeAnswer(response.answer),
      sources: response.sources || [],
      model: response.model_used,
      timestamp: new Date(),
      agentSteps: response.agent_steps || [],
      toolsExecuted: response.tools_executed || [],
    };

    setMessages((prev) => [...prev, assistantMessage]);

    // Reload conversations if needed
    if (currentConversationId) {
      loadConversations();
    }
  };

  const handleConfirmationCancelled = (response) => {
    // Clear pending confirmations
    setPendingConfirmations([]);

    // Add cancellation message
    const assistantMessage = {
      type: 'assistant',
      content: normalizeAnswer(response.answer || 'Action cancelled.'),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, assistantMessage]);
  };

  // Agent question handlers
  const handleQuestionAnswer = async (answer) => {
    if (!currentQuestionId) return;

    // Add user's answer to chat
    const userMessage = {
      type: 'user',
      content: answer,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMessage]);

    // Clear pending questions
    setPendingQuestions([]);
    setQueryLoading(true);

    try {
      // Get current question
      const question = pendingQuestions[0];

      // Send answer back to agent
      const preferredModel = localStorage.getItem('preferredModel');
      const preferredLanguage = localStorage.getItem('preferredLanguage') || 'auto';
      const preferredChunks = parseInt(localStorage.getItem('preferredChunks') || '5');

      const response = await agentApi.query(question.question, {
        conversationId: currentConversationId,
        nResults: preferredChunks,
        language: preferredLanguage === 'auto' ? null : preferredLanguage,
        model: preferredModel || null,
        enableAgent: true,
        questionId: currentQuestionId,
        answerToQuestion: answer,
      });

      // Update conversation ID
      setCurrentConversationId(response.conversation_id);

      // Check for more questions
      if (response.pending_questions && response.pending_questions.length > 0) {
        setPendingQuestions(response.pending_questions);
        setCurrentQuestionId(response.pending_questions[0].question_id);
      } else {
        setCurrentQuestionId(null);
      }

      // Add agent response
      const assistantMessage = {
        id: response.message_id,
        type: 'assistant',
        content: response.answer,
        sources: response.sources || [],
        chunks: response.relevant_chunks || [],
        model: response.model_used,
        timestamp: new Date(),
        agentSteps: response.agent_steps || [],
        toolsExecuted: response.tools_executed || [],
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // Reload conversations
      loadConversations();
    } catch (error) {
      const errorMessage = {
        type: 'assistant',
        content: formatError(error.response?.data?.detail),
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

      {/* Main Content Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'row', minWidth: 0 }}>
        {/* Chat Area */}
        <div style={{
          flex: '1 1 100%',
          display: 'flex',
          flexDirection: 'column',
          minWidth: 0,
        }}>
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
            padding: '1.5rem',
            backgroundColor: '#f8fafc',
            display: 'flex',
            flexDirection: 'column',
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

              {/* Quick-start conversation prompts */}
              <div style={{
                marginTop: '2rem',
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
                gap: '1rem',
                maxWidth: '800px',
                margin: '2rem auto 0',
                padding: '0 1rem'
              }}>
                {[
                  { icon: '🎓', text: t('home.quickButton1Text'), query: t('home.quickButton1Query') },
                  { icon: '📊', text: t('home.quickButton2Text'), query: t('home.quickButton2Query') },
                  { icon: '📋', text: t('home.quickButton3Text'), query: t('home.quickButton3Query') },
                  { icon: '✅', text: t('home.quickButton4Text'), query: t('home.quickButton4Query') },
                ].map((starter, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setQuery(starter.query);
                      setTimeout(() => sendQuery(starter.query), 150);
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.75rem',
                      padding: '1rem 1.25rem',
                      backgroundColor: 'white',
                      border: '2px solid #e2e8f0',
                      borderRadius: '0.75rem',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      fontSize: '1rem',
                      fontWeight: 500,
                      color: '#2d3748',
                      boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = '#667eea';
                      e.currentTarget.style.transform = 'translateY(-2px)';
                      e.currentTarget.style.boxShadow = '0 4px 6px rgba(102, 126, 234, 0.1)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = '#e2e8f0';
                      e.currentTarget.style.transform = 'translateY(0)';
                      e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.05)';
                    }}
                  >
                    <span style={{ fontSize: '1.5rem' }}>{starter.icon}</span>
                    <span style={{ textAlign: 'left', flex: 1 }}>{starter.text}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((message, index) => (
            <ChatMessage
              key={message.id || index}
              message={message}
            />
          ))}

          {queryLoading && (
            <div style={{
              display: 'flex',
              gap: '0.75rem',
              padding: '1rem',
              marginBottom: '0.75rem',
              alignItems: 'flex-start'
            }}>
              <div style={{
                width: '36px',
                height: '36px',
                borderRadius: '50%',
                backgroundColor: '#667eea',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}>
                <Bot size={20} color="white" />
              </div>
              <div style={{
                flex: 1,
                backgroundColor: 'white',
                padding: '1rem 1.25rem',
                borderRadius: '1rem',
                border: '1px solid #e2e8f0',
                boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: '#718096' }}>
                  {/* Animated typing dots */}
                  <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                    {[0, 1, 2].map((i) => (
                      <div
                        key={i}
                        style={{
                          width: '8px',
                          height: '8px',
                          borderRadius: '50%',
                          backgroundColor: '#667eea',
                          animation: 'typingDot 1.4s infinite',
                          animationDelay: `${i * 0.2}s`,
                        }}
                      />
                    ))}
                  </div>
                  <span>{t('home.thinking')}</span>
                </div>
              </div>
            </div>
          )}

          {/* Add CSS animation for typing dots */}
          <style>{`
            @keyframes typingDot {
              0%, 60%, 100% {
                opacity: 0.3;
                transform: translateY(0);
              }
              30% {
                opacity: 1;
                transform: translateY(-6px);
              }
            }
          `}</style>

          {/* Agent tool confirmation dialog */}
          {pendingConfirmations.length > 0 && (
            <div style={{
              display: 'flex',
              gap: '0.75rem',
              padding: '1rem',
              marginBottom: '0.75rem',
              alignItems: 'flex-start'
            }}>
              <div style={{
                width: '36px',
                height: '36px',
                borderRadius: '50%',
                backgroundColor: '#667eea',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}>
                <Bot size={20} color="white" />
              </div>
              <div style={{ flex: 1 }}>
                <ToolConfirmation
                  pendingConfirmations={pendingConfirmations}
                  onConfirmed={handleConfirmationApproved}
                  onCancelled={handleConfirmationCancelled}
                />
              </div>
            </div>
          )}

          {pendingQuestions.length > 0 && (
            <div style={{
              display: 'flex',
              gap: '0.75rem',
              backgroundColor: '#f0f9ff',
              borderRadius: '12px',
              padding: '1rem',
              marginBottom: '0.75rem',
              alignItems: 'flex-start',
              border: '1px solid #b3e0ff'
            }}>
              <div style={{
                width: '36px',
                height: '36px',
                borderRadius: '50%',
                backgroundColor: '#2196f3',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0
              }}>
                <Bot size={20} color="white" />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ marginBottom: '12px' }}>
                  <div style={{ fontSize: '14px', fontWeight: '500', marginBottom: '8px', color: '#2196f3' }}>
                    ❓ {pendingQuestions[0].question}
                  </div>
                  {pendingQuestions[0].context && (
                    <div style={{ fontSize: '13px', color: '#666', marginBottom: '12px' }}>
                      {pendingQuestions[0].context}
                    </div>
                  )}
                </div>

                {pendingQuestions[0].options && pendingQuestions[0].options.length > 0 ? (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {pendingQuestions[0].options.map((option, index) => (
                      <button
                        key={index}
                        onClick={() => handleQuestionAnswer(option)}
                        disabled={queryLoading}
                        className="btn-secondary"
                        style={{
                          padding: '8px 16px',
                          fontSize: '14px',
                          borderRadius: '8px'
                        }}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                ) : (
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <input
                      type="text"
                      placeholder="Your answer..."
                      className="input"
                      style={{ flex: 1 }}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && e.target.value.trim()) {
                          handleQuestionAnswer(e.target.value);
                          e.target.value = '';
                        }
                      }}
                      disabled={queryLoading}
                    />
                    <button
                      onClick={(e) => {
                        const input = e.target.previousSibling;
                        if (input.value.trim()) {
                          handleQuestionAnswer(input.value);
                          input.value = '';
                        }
                      }}
                      disabled={queryLoading}
                      className="btn-primary"
                      style={{ padding: '8px 16px' }}
                    >
                      <Send size={16} />
                    </button>
                  </div>
                )}
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
  const [sourcesExpanded, setSourcesExpanded] = useState(false);

  const isUser = message.type === 'user';
  const isAssistant = message.type === 'assistant';

  // Format file name helper function
  const formatFileName = (filename) => {
    const nameWithoutExt = filename.replace(/\.[^/.]+$/, '');
    let formatted = nameWithoutExt.replace(/[-_]/g, ' ');
    formatted = formatted.split(' ').map(word => {
      if (word.length === 0) return word;
      return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
    }).join(' ');
    const extMatch = filename.match(/\.[^/.]+$/);
    const extension = extMatch ? extMatch[0].toUpperCase().replace('.', '') : '';
    return { display: formatted, extension };
  };

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
    <div style={{
      display: 'flex',
      gap: '0.75rem',
      padding: '0.5rem',
      marginBottom: '0.75rem',
      alignItems: 'flex-start',
      flexDirection: isUser ? 'row-reverse' : 'row',
    }}>
      {/* Avatar */}
      <div style={{
        width: '36px',
        height: '36px',
        borderRadius: '50%',
        backgroundColor: isUser ? '#48bb78' : '#667eea',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
      }}>
        {isUser ? <User size={20} color="white" /> : <Bot size={20} color="white" />}
      </div>

      {/* Message Content */}
      <div style={{
        flex: 1,
        maxWidth: '75%',
        display: 'flex',
        flexDirection: 'column',
        alignItems: isUser ? 'flex-end' : 'flex-start',
      }}>
        {/* Message Bubble */}
        <div style={{
          backgroundColor: isUser ? '#48bb78' : 'white',
          color: isUser ? 'white' : '#2d3748',
          padding: '1rem 1.25rem',
          borderRadius: '1rem',
          border: isUser ? 'none' : '1px solid #e2e8f0',
          boxShadow: isUser ? '0 2px 8px rgba(72, 187, 120, 0.2)' : '0 1px 3px rgba(0,0,0,0.1)',
          width: '100%',
          wordBreak: 'break-word',
        }}>
          <div className="chat-message-content">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeRaw]}
              components={{
                code({ node, inline, className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || '');
                  const language = match ? match[1] : '';
                  const code = String(children).replace(/\n$/, '');

                  // Render mermaid diagrams with custom component
                  if (language === 'mermaid') {
                    return <MermaidDiagram chart={code} />;
                  }

                  // Regular code blocks
                  return !inline ? (
                    <pre className={className} style={{
                      background: isUser ? 'rgba(255,255,255,0.2)' : '#f5f5f5',
                      padding: '1rem',
                      borderRadius: '0.5rem',
                      overflow: 'auto',
                      color: isUser ? 'white' : '#2d3748'
                    }}>
                      <code className={className} {...props}>
                        {children}
                      </code>
                    </pre>
                  ) : (
                    <code className={className} style={{
                      backgroundColor: isUser ? 'rgba(255,255,255,0.2)' : '#f0f0f0',
                      padding: '0.2rem 0.4rem',
                      borderRadius: '0.25rem',
                      fontSize: '0.9em',
                    }} {...props}>
                      {children}
                    </code>
                  );
                }
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>

          {/* Sources */}
          {message.sources && message.sources.length > 0 && (
            <div style={{
              marginTop: '1rem',
              paddingTop: '1rem',
              borderTop: `1px solid ${isUser ? 'rgba(255,255,255,0.3)' : '#e2e8f0'}`,
            }}>
              <div
                style={{
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontWeight: 600,
                  fontSize: '0.875rem',
                  color: isUser ? 'rgba(255,255,255,0.9)' : '#4a5568',
                }}
                onClick={() => setSourcesExpanded(!sourcesExpanded)}
              >
                <div>
                  <FileText size={14} style={{ display: 'inline', marginRight: '0.25rem' }} />
                  {t('home.sources')} ({message.sources.length})
                </div>
                {sourcesExpanded ?
                  <ChevronUp size={16} /> :
                  <ChevronDown size={16} />
                }
              </div>
              {sourcesExpanded && (
                <div style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '0.5rem',
                  marginTop: '0.75rem'
                }}>
                  {message.sources.map((source, idx) => {
                    const formatted = formatFileName(source);
                    return (
                      <button
                        key={idx}
                        onClick={() => fileApi.download(source)}
                        title={t('home.downloadSource') || 'Click to download'}
                        style={{
                          cursor: 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.375rem',
                          transition: 'all 0.2s',
                          padding: '0.375rem 0.625rem',
                          backgroundColor: isUser ? 'rgba(255,255,255,0.2)' : '#e2e8f0',
                          border: 'none',
                          borderRadius: '0.375rem',
                          fontSize: '0.8rem',
                          color: isUser ? 'white' : '#2d3748',
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.backgroundColor = isUser ? 'rgba(255,255,255,0.3)' : '#cbd5e0';
                          e.currentTarget.style.transform = 'translateY(-1px)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = isUser ? 'rgba(255,255,255,0.2)' : '#e2e8f0';
                          e.currentTarget.style.transform = 'translateY(0)';
                        }}
                      >
                        <Download size={12} />
                        <span style={{ fontWeight: '500' }}>{formatted.display}</span>
                        <span style={{
                          fontSize: '0.7rem',
                          backgroundColor: isUser ? 'rgba(255,255,255,0.3)' : '#cbd5e0',
                          padding: '0.125rem 0.25rem',
                          borderRadius: '3px',
                          fontWeight: '600'
                        }}>
                          {formatted.extension}
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Agent execution steps */}
          {message.agentSteps && message.agentSteps.length > 0 && (
            <div style={{ marginTop: '1rem' }}>
              <AgentSteps
                steps={message.agentSteps}
                toolsExecuted={message.toolsExecuted}
              />
            </div>
          )}
        </div>

        {/* Metadata and Feedback */}
        {isAssistant && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginTop: '0.5rem',
            width: '100%',
            paddingLeft: '0.5rem',
            gap: '1rem',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              {message.model && (
                <div style={{ fontSize: '0.75rem', color: '#a0aec0' }}>
                  {t('home.model')}: {message.model}
                </div>
              )}
            </div>

            {/* Feedback buttons (only for newly received messages, not loaded from history) */}
            {message.id && !message.isLoadedFromHistory && !showCommentBox && (
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
        )}

        {/* Comment box for feedback */}
        {showCommentBox && isAssistant && message.id && (
          <div style={{
            marginTop: '0.75rem',
            padding: '1rem',
            backgroundColor: '#f8fafc',
            borderRadius: '0.75rem',
            border: '1px solid #e2e8f0',
            width: '100%',
          }}>
            <div style={{ marginBottom: '0.5rem', fontSize: '0.875rem', color: '#4a5568' }}>
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
                backgroundColor: '#ffffff',
                border: '1px solid #cbd5e0',
                borderRadius: '0.5rem',
                color: '#2d3748',
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
                  borderRadius: '0.5rem',
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
                  backgroundColor: '#ffffff',
                  color: '#718096',
                  border: '1px solid #cbd5e0',
                  borderRadius: '0.5rem',
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
    </div>
  );
}

export default HomePage;
