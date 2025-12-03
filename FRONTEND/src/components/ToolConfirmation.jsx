import { useState } from 'react';
import { AlertTriangle, Check, X, Loader } from 'lucide-react';
import { agentApi } from '../services/api';

/**
 * ToolConfirmation component - User confirmation dialog for agent actions
 *
 * Displays a warning and details about pending tool executions that require
 * user approval (e.g., file deletion, conversation deletion).
 */
function ToolConfirmation({ pendingConfirmations, onConfirmed, onCancelled }) {
  const [processingId, setProcessingId] = useState(null);
  const [error, setError] = useState(null);

  if (!pendingConfirmations || pendingConfirmations.length === 0) {
    return null;
  }

  const handleConfirm = async (confirmation, approved) => {
    setProcessingId(confirmation.confirmation_id);
    setError(null);

    try {
      const response = await agentApi.confirm(confirmation.confirmation_id, approved);

      // Call parent callback with response
      if (approved) {
        onConfirmed?.(response);
      } else {
        onCancelled?.(response);
      }
    } catch (err) {
      console.error('Confirmation error:', err);
      setError(err.response?.data?.detail || 'Failed to process confirmation');
    } finally {
      setProcessingId(null);
    }
  };

  return (
    <div
      style={{
        marginTop: '1rem',
        padding: '1rem',
        backgroundColor: '#fffbeb',
        border: '1px solid #fcd34d',
        borderRadius: '0.5rem',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
        <AlertTriangle size={20} style={{ color: '#f59e0b' }} />
        <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: '#92400e' }}>
          Action Requires Confirmation
        </h4>
      </div>

      {/* Error message */}
      {error && (
        <div
          style={{
            padding: '0.75rem',
            backgroundColor: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: '0.375rem',
            marginBottom: '1rem',
          }}
        >
          <div style={{ fontSize: '0.875rem', color: '#991b1b' }}>{error}</div>
        </div>
      )}

      {/* Confirmations list */}
      {pendingConfirmations.map((confirmation) => (
        <div
          key={confirmation.confirmation_id}
          style={{
            padding: '1rem',
            backgroundColor: '#fff',
            border: '1px solid #e2e8f0',
            borderRadius: '0.5rem',
            marginBottom: pendingConfirmations.length > 1 ? '1rem' : '0',
          }}
        >
          {/* Warning message */}
          <div style={{ marginBottom: '1rem' }}>
            <div style={{ fontSize: '0.875rem', fontWeight: 600, color: '#2d3748', marginBottom: '0.5rem' }}>
              {confirmation.warning_message}
            </div>

            {/* Tool details */}
            <div style={{ fontSize: '0.75rem', color: '#718096' }}>
              Tool: <span style={{ fontFamily: 'monospace', fontWeight: 600 }}>{confirmation.tool_name}</span>
            </div>

            {/* Parameters */}
            {Object.keys(confirmation.parameters).length > 0 && (
              <div style={{ marginTop: '0.5rem' }}>
                <div style={{ fontSize: '0.75rem', color: '#718096', marginBottom: '0.25rem' }}>
                  Parameters:
                </div>
                <pre
                  style={{
                    fontSize: '0.7rem',
                    backgroundColor: '#f7fafc',
                    padding: '0.5rem',
                    borderRadius: '0.25rem',
                    overflow: 'auto',
                    margin: 0,
                  }}
                >
                  {JSON.stringify(confirmation.parameters, null, 2)}
                </pre>
              </div>
            )}
          </div>

          {/* Action buttons */}
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <button
              onClick={() => handleConfirm(confirmation, true)}
              disabled={processingId === confirmation.confirmation_id}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: processingId === confirmation.confirmation_id ? '#cbd5e0' : '#10b981',
                color: '#fff',
                border: 'none',
                borderRadius: '0.375rem',
                fontSize: '0.875rem',
                fontWeight: 600,
                cursor: processingId === confirmation.confirmation_id ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                transition: 'background-color 0.2s',
              }}
              onMouseEnter={(e) => {
                if (processingId !== confirmation.confirmation_id) {
                  e.currentTarget.style.backgroundColor = '#059669';
                }
              }}
              onMouseLeave={(e) => {
                if (processingId !== confirmation.confirmation_id) {
                  e.currentTarget.style.backgroundColor = '#10b981';
                }
              }}
            >
              {processingId === confirmation.confirmation_id ? (
                <>
                  <Loader size={16} className="spinner-icon" style={{ animation: 'spin 1s linear infinite' }} />
                  Processing...
                </>
              ) : (
                <>
                  <Check size={16} />
                  Approve
                </>
              )}
            </button>

            <button
              onClick={() => handleConfirm(confirmation, false)}
              disabled={processingId === confirmation.confirmation_id}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: processingId === confirmation.confirmation_id ? '#f3f4f6' : '#fff',
                color: processingId === confirmation.confirmation_id ? '#9ca3af' : '#6b7280',
                border: '1px solid #d1d5db',
                borderRadius: '0.375rem',
                fontSize: '0.875rem',
                fontWeight: 600,
                cursor: processingId === confirmation.confirmation_id ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                if (processingId !== confirmation.confirmation_id) {
                  e.currentTarget.style.backgroundColor = '#f3f4f6';
                  e.currentTarget.style.borderColor = '#9ca3af';
                }
              }}
              onMouseLeave={(e) => {
                if (processingId !== confirmation.confirmation_id) {
                  e.currentTarget.style.backgroundColor = '#fff';
                  e.currentTarget.style.borderColor = '#d1d5db';
                }
              }}
            >
              <X size={16} />
              Cancel
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

export default ToolConfirmation;
