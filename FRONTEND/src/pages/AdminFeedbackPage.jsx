import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  MessageSquare,
  ThumbsUp,
  ThumbsDown,
  Filter,
  Download,
  Sparkles,
  TrendingUp,
  Users,
  FileText,
  Calendar,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import { adminFeedbackApi } from '../services/api';

function AdminFeedbackPage() {
  const { t, i18n } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState([]);
  const [stats, setStats] = useState(null);
  const [summary, setSummary] = useState(null);
  const [generatingSummary, setGeneratingSummary] = useState(false);

  // Pagination
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const itemsPerPage = 20;

  // Filters
  const [filters, setFilters] = useState({
    rating: '',
    user_id: '',
    filename: '',
    start_date: '',
    end_date: '',
  });
  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    loadFeedback();
    loadStats();
  }, [page, filters]);

  const loadFeedback = async () => {
    try {
      setLoading(true);
      const skip = (page - 1) * itemsPerPage;
      const params = {
        skip,
        limit: itemsPerPage,
        ...Object.fromEntries(Object.entries(filters).filter(([_, v]) => v !== '')),
      };

      const data = await adminFeedbackApi.getAllFeedback(params);
      setFeedback(data.items || []);
      setTotalPages(data.pages || 1);
      setTotalItems(data.total || 0);
    } catch (error) {
      console.error('Failed to load feedback:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const data = await adminFeedbackApi.getStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  const handleGenerateSummary = async () => {
    try {
      setGeneratingSummary(true);
      const params = Object.fromEntries(Object.entries(filters).filter(([_, v]) => v !== ''));
      // Add language preference
      params.language = i18n.language; // 'es' or 'en'
      const data = await adminFeedbackApi.generateSummary(params);
      setSummary(data);
    } catch (error) {
      console.error('Failed to generate summary:', error);
      alert('Failed to generate summary. Please try again.');
    } finally {
      setGeneratingSummary(false);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
    setPage(1); // Reset to first page when filters change
  };

  const clearFilters = () => {
    setFilters({
      rating: '',
      user_id: '',
      filename: '',
      start_date: '',
      end_date: '',
    });
    setPage(1);
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  return (
    <div>
      <div className="card">
        <h2 className="card-title">
          <MessageSquare size={28} />
          {t('feedback.title')}
        </h2>
        <p style={{ color: '#718096', marginBottom: '1.5rem' }}>
          {t('feedback.subtitle')}
        </p>

        {/* Statistics Cards */}
        {stats && (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '1rem',
            marginBottom: '1.5rem',
          }}>
            <StatCard
              title={t('feedback.totalFeedback')}
              value={stats.total_feedback}
              icon={<MessageSquare size={24} />}
              color="#667eea"
            />
            <StatCard
              title={t('feedback.positiveFeedback')}
              value={stats.total_likes}
              icon={<ThumbsUp size={24} />}
              color="#48bb78"
            />
            <StatCard
              title={t('feedback.negativeFeedback')}
              value={stats.total_dislikes}
              icon={<ThumbsDown size={24} />}
              color="#f56565"
            />
            <StatCard
              title={t('feedback.withComments')}
              value={stats.total_with_comments}
              icon={<FileText size={24} />}
              color="#764ba2"
            />
          </div>
        )}

        {/* Filters and Actions */}
        <div style={{
          backgroundColor: '#f7fafc',
          borderRadius: '0.5rem',
          padding: '1rem',
          marginBottom: '1.5rem',
          border: '1px solid #e2e8f0',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: showFilters ? '1rem' : 0 }}>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="btn btn-secondary"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}
            >
              <Filter size={18} />
              {showFilters ? t('feedback.hideFilters') : t('feedback.showFilters')}
            </button>
            <button
              onClick={handleGenerateSummary}
              disabled={generatingSummary}
              className="btn btn-primary"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                opacity: generatingSummary ? 0.6 : 1,
              }}
            >
              <Sparkles size={18} />
              {generatingSummary ? t('feedback.generating') : t('feedback.generateSummary')}
            </button>
          </div>

          {showFilters && (
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
              gap: '1rem',
            }}>
              <div className="form-group">
                <label className="form-label">{t('feedback.rating')}</label>
                <select
                  className="select"
                  value={filters.rating}
                  onChange={(e) => handleFilterChange('rating', e.target.value)}
                >
                  <option value="">{t('feedback.all')}</option>
                  <option value="like">👍 {t('feedback.like')}</option>
                  <option value="dislike">👎 {t('feedback.dislike')}</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">{t('feedback.userId')}</label>
                <input
                  className="input"
                  type="text"
                  value={filters.user_id}
                  onChange={(e) => handleFilterChange('user_id', e.target.value)}
                  placeholder={t('feedback.filterByUser')}
                />
              </div>

              <div className="form-group">
                <label className="form-label">{t('feedback.filename')}</label>
                <input
                  className="input"
                  type="text"
                  value={filters.filename}
                  onChange={(e) => handleFilterChange('filename', e.target.value)}
                  placeholder={t('feedback.filterByFile')}
                />
              </div>

              <div className="form-group">
                <label className="form-label">{t('feedback.startDate')}</label>
                <input
                  className="input"
                  type="date"
                  value={filters.start_date}
                  onChange={(e) => handleFilterChange('start_date', e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label">{t('feedback.endDate')}</label>
                <input
                  className="input"
                  type="date"
                  value={filters.end_date}
                  onChange={(e) => handleFilterChange('end_date', e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                <button
                  onClick={clearFilters}
                  className="btn btn-danger"
                  style={{ width: '100%' }}
                >
                  {t('feedback.clearFilters')}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* AI Summary */}
        {summary && (
          <div style={{
            backgroundColor: '#f0e7ff',
            borderRadius: '0.5rem',
            padding: '1.5rem',
            marginBottom: '1.5rem',
            border: '2px solid #764ba2',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
              <Sparkles size={24} style={{ color: '#764ba2' }} />
              <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#2d3748' }}>{t('feedback.aiSummary')}</h3>
            </div>
            <div style={{
              whiteSpace: 'pre-wrap',
              lineHeight: '1.6',
              color: '#2d3748',
              marginBottom: '1rem',
            }}>
              {summary.summary}
            </div>
            <div style={{ fontSize: '0.75rem', color: '#718096' }}>
              {t('feedback.basedOn')} {summary.item_count} {t('feedback.items')} | {t('feedback.generated')}: {formatDate(summary.generated_at)}
            </div>
          </div>
        )}

        {/* Feedback List */}
        <div style={{ marginTop: '1.5rem' }}>
          <h3 style={{ fontSize: '1.25rem', fontWeight: 'bold', marginBottom: '1rem', color: '#2d3748' }}>
            {t('feedback.feedbackList')} ({totalItems})
          </h3>

          {loading ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: '#718096' }}>
              {t('feedback.loading')}
            </div>
          ) : feedback.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: '#718096' }}>
              {t('feedback.noFeedback')}
            </div>
          ) : (
            <>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {feedback.map((item) => (
                  <FeedbackCard key={item._id} feedback={item} />
                ))}
              </div>

              {/* Pagination */}
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginTop: '1.5rem',
                paddingTop: '1.5rem',
                borderTop: '1px solid #e2e8f0',
              }}>
                <div style={{ color: '#718096', fontSize: '0.875rem' }}>
                  {t('feedback.showing')} {((page - 1) * itemsPerPage) + 1} - {Math.min(page * itemsPerPage, totalItems)} {t('feedback.of')} {totalItems}
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                    onClick={() => setPage(page - 1)}
                    disabled={page === 1}
                    className="btn btn-secondary"
                    style={{
                      padding: '0.5rem 1rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.25rem',
                    }}
                  >
                    <ChevronLeft size={18} />
                    {t('feedback.previous')}
                  </button>
                  <span style={{ padding: '0.5rem 1rem', color: '#2d3748', display: 'flex', alignItems: 'center' }}>
                    {t('feedback.page')} {page} {t('feedback.of')} {totalPages}
                  </span>
                  <button
                    onClick={() => setPage(page + 1)}
                    disabled={page === totalPages}
                    className="btn btn-secondary"
                    style={{
                      padding: '0.5rem 1rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.25rem',
                    }}
                  >
                    {t('feedback.next')}
                    <ChevronRight size={18} />
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon, color }) {
  return (
    <div style={{
      backgroundColor: 'white',
      borderRadius: '0.5rem',
      padding: '1.5rem',
      display: 'flex',
      alignItems: 'center',
      gap: '1rem',
      boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
      border: '1px solid #e2e8f0',
    }}>
      <div style={{ color, fontSize: '2rem' }}>
        {icon}
      </div>
      <div>
        <div style={{ fontSize: '0.875rem', color: '#718096', marginBottom: '0.25rem' }}>
          {title}
        </div>
        <div style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#2d3748' }}>
          {value}
        </div>
      </div>
    </div>
  );
}

function FeedbackCard({ feedback }) {
  const { t } = useTranslation();

  const getRatingColor = (rating) => {
    if (rating === 'like') return '#48bb78';
    if (rating === 'dislike') return '#f56565';
    return '#718096';
  };

  const getRatingIcon = (rating) => {
    if (rating === 'like') return '👍';
    if (rating === 'dislike') return '👎';
    return '💬';
  };

  return (
    <div style={{
      backgroundColor: 'white',
      borderRadius: '0.5rem',
      padding: '1rem',
      borderLeft: `4px solid ${getRatingColor(feedback.rating)}`,
      boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
      border: '1px solid #e2e8f0',
      borderLeftWidth: '4px',
    }}>
      <div style={{ display: 'flex', alignItems: 'start', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span style={{ fontSize: '1.25rem' }}>{getRatingIcon(feedback.rating)}</span>
          <div>
            <div style={{ fontWeight: '600', color: '#2d3748' }}>
              {feedback.user_email || 'Anonymous'}
            </div>
            <div style={{ fontSize: '0.75rem', color: '#718096' }}>
              {feedback.created_at ? new Date(feedback.created_at).toLocaleString() : 'N/A'}
            </div>
          </div>
        </div>
        {feedback.rating && (
          <span style={{
            padding: '0.25rem 0.75rem',
            backgroundColor: getRatingColor(feedback.rating) + '20',
            color: getRatingColor(feedback.rating),
            borderRadius: '9999px',
            fontSize: '0.75rem',
            fontWeight: '600',
            textTransform: 'uppercase',
          }}>
            {feedback.rating}
          </span>
        )}
      </div>

      {feedback.comment && (
        <div style={{
          backgroundColor: '#f7fafc',
          padding: '0.75rem',
          borderRadius: '0.25rem',
          marginBottom: '0.75rem',
          lineHeight: '1.5',
          color: '#2d3748',
          border: '1px solid #e2e8f0',
        }}>
          "{feedback.comment}"
        </div>
      )}

      {feedback.files_referenced && feedback.files_referenced.length > 0 && (
        <div style={{ marginBottom: '0.5rem' }}>
          <div style={{ fontSize: '0.75rem', color: '#718096', marginBottom: '0.25rem' }}>
            {t('feedback.filesReferenced')}:
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
            {feedback.files_referenced.map((file, idx) => (
              <span
                key={idx}
                className="source-badge"
              >
                {file}
              </span>
            ))}
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: '1rem', fontSize: '0.75rem', color: '#718096' }}>
        {feedback.message_id && (
          <div>{t('feedback.messageId')}: {feedback.message_id.substring(0, 8)}...</div>
        )}
        {feedback.conversation_id && (
          <div>{t('feedback.conversation')}: {feedback.conversation_id.substring(0, 8)}...</div>
        )}
      </div>
    </div>
  );
}

export default AdminFeedbackPage;
