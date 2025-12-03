import { useState } from 'react';
import { ChevronDown, ChevronUp, Zap, CheckCircle, XCircle, AlertCircle, Clock } from 'lucide-react';

/**
 * AgentSteps component - Displays agent execution timeline
 *
 * Shows the step-by-step process of agent tool execution including:
 * - Agent thoughts/reasoning
 * - Tool calls with parameters
 * - Execution results
 * - Errors and warnings
 */
function AgentSteps({ steps, toolsExecuted }) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (!steps || steps.length === 0) {
    return null;
  }

  return (
    <div
      style={{
        marginTop: '1rem',
        border: '1px solid #e2e8f0',
        borderRadius: '0.5rem',
        backgroundColor: '#f8fafc',
        overflow: 'hidden',
      }}
    >
      {/* Header - clickable to expand/collapse */}
      <div
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          padding: '0.75rem 1rem',
          backgroundColor: '#eef2ff',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: isExpanded ? '1px solid #e2e8f0' : 'none',
          transition: 'background-color 0.2s',
        }}
        onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#e0e7ff')}
        onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = '#eef2ff')}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Zap size={16} style={{ color: '#667eea' }} />
          <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#4c51bf' }}>
            Agent Execution ({steps.length} steps)
          </span>
          {toolsExecuted && toolsExecuted.length > 0 && (
            <span style={{ fontSize: '0.75rem', color: '#718096' }}>
              • Used: {toolsExecuted.join(', ')}
            </span>
          )}
        </div>
        {isExpanded ? (
          <ChevronUp size={16} style={{ color: '#667eea' }} />
        ) : (
          <ChevronDown size={16} style={{ color: '#667eea' }} />
        )}
      </div>

      {/* Steps list - collapsible */}
      {isExpanded && (
        <div style={{ padding: '1rem' }}>
          {steps.map((step, index) => (
            <Step key={index} step={step} isLast={index === steps.length - 1} />
          ))}
        </div>
      )}
    </div>
  );
}

function Step({ step, isLast }) {
  const getStepIcon = () => {
    switch (step.step_type) {
      case 'thought':
        return <AlertCircle size={14} style={{ color: '#667eea' }} />;
      case 'tool_call':
        return <Zap size={14} style={{ color: '#f59e0b' }} />;
      case 'result':
        return <CheckCircle size={14} style={{ color: '#10b981' }} />;
      case 'error':
        return <XCircle size={14} style={{ color: '#ef4444' }} />;
      case 'confirmation_required':
        return <Clock size={14} style={{ color: '#f59e0b' }} />;
      default:
        return <AlertCircle size={14} style={{ color: '#9ca3af' }} />;
    }
  };

  const getStepColor = () => {
    switch (step.step_type) {
      case 'thought':
        return '#667eea';
      case 'tool_call':
        return '#f59e0b';
      case 'result':
        return '#10b981';
      case 'error':
        return '#ef4444';
      case 'confirmation_required':
        return '#f59e0b';
      default:
        return '#9ca3af';
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        gap: '0.75rem',
        paddingBottom: isLast ? '0' : '1rem',
        position: 'relative',
      }}
    >
      {/* Timeline line */}
      {!isLast && (
        <div
          style={{
            position: 'absolute',
            left: '7px',
            top: '24px',
            bottom: '0',
            width: '2px',
            backgroundColor: '#e2e8f0',
          }}
        />
      )}

      {/* Step number and icon */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', minWidth: '24px' }}>
        <div
          style={{
            width: '24px',
            height: '24px',
            borderRadius: '50%',
            backgroundColor: '#fff',
            border: `2px solid ${getStepColor()}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '0.75rem',
            fontWeight: 600,
            color: getStepColor(),
            position: 'relative',
            zIndex: 1,
          }}
        >
          {getStepIcon()}
        </div>
      </div>

      {/* Step content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: '0.875rem', color: '#2d3748', marginBottom: '0.25rem' }}>
          <strong style={{ color: getStepColor() }}>
            {step.step_type.replace('_', ' ').toUpperCase()}
          </strong>
          {' '}
          {step.content}
        </div>

        {/* Tool call details */}
        {step.tool_call && (
          <div
            style={{
              marginTop: '0.5rem',
              padding: '0.75rem',
              backgroundColor: '#fff',
              borderRadius: '0.375rem',
              border: '1px solid #e2e8f0',
            }}
          >
            <div style={{ fontSize: '0.75rem', fontWeight: 600, color: '#4a5568', marginBottom: '0.5rem' }}>
              Tool: {step.tool_call.tool_name}
            </div>

            {/* Parameters */}
            {Object.keys(step.tool_call.parameters).length > 0 && (
              <div style={{ marginBottom: '0.5rem' }}>
                <div style={{ fontSize: '0.7rem', color: '#718096', marginBottom: '0.25rem' }}>
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
                  {JSON.stringify(step.tool_call.parameters, null, 2)}
                </pre>
              </div>
            )}

            {/* Result */}
            {step.tool_call.result && (
              <div>
                <div style={{ fontSize: '0.7rem', color: '#718096', marginBottom: '0.25rem' }}>
                  Result:
                </div>
                <pre
                  style={{
                    fontSize: '0.7rem',
                    backgroundColor: '#f0fdf4',
                    padding: '0.5rem',
                    borderRadius: '0.25rem',
                    overflow: 'auto',
                    margin: 0,
                    maxHeight: '200px',
                  }}
                >
                  {typeof step.tool_call.result === 'object'
                    ? JSON.stringify(step.tool_call.result, null, 2)
                    : step.tool_call.result}
                </pre>
              </div>
            )}

            {/* Error */}
            {step.tool_call.error && (
              <div>
                <div style={{ fontSize: '0.7rem', color: '#ef4444', marginBottom: '0.25rem' }}>
                  Error:
                </div>
                <div
                  style={{
                    fontSize: '0.7rem',
                    backgroundColor: '#fef2f2',
                    color: '#991b1b',
                    padding: '0.5rem',
                    borderRadius: '0.25rem',
                  }}
                >
                  {step.tool_call.error}
                </div>
              </div>
            )}

            {/* Execution time */}
            {step.tool_call.execution_time_ms && (
              <div style={{ fontSize: '0.7rem', color: '#9ca3af', marginTop: '0.5rem' }}>
                Executed in {step.tool_call.execution_time_ms}ms
              </div>
            )}
          </div>
        )}

        {/* Timestamp */}
        {step.timestamp && (
          <div style={{ fontSize: '0.7rem', color: '#9ca3af', marginTop: '0.25rem' }}>
            {new Date(step.timestamp).toLocaleTimeString()}
          </div>
        )}
      </div>
    </div>
  );
}

export default AgentSteps;
