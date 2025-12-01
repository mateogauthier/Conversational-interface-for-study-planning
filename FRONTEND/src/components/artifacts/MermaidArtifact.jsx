import React, { useEffect, useRef } from 'react';
import mermaid from 'mermaid';
import { Copy, Check } from 'lucide-react';

const MermaidArtifact = ({ artifact }) => {
  const containerRef = useRef(null);
  const [copied, setCopied] = React.useState(false);

  useEffect(() => {
    // Initialize mermaid
    mermaid.initialize({
      startOnLoad: true,
      theme: 'default',
      securityLevel: 'loose',
      flowchart: {
        useMaxWidth: true,
        htmlLabels: true,
      },
    });

    // Render the diagram
    if (containerRef.current && artifact.content) {
      // Clear previous content
      containerRef.current.innerHTML = '';

      // Create a unique ID for this diagram
      const id = `mermaid-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

      // Render using mermaid
      mermaid.render(id, artifact.content).then(({ svg }) => {
        if (containerRef.current) {
          containerRef.current.innerHTML = svg;
        }
      }).catch((error) => {
        console.error('Mermaid rendering error:', error);
        if (containerRef.current) {
          containerRef.current.innerHTML = `
            <div style="padding: 1rem; color: #e53e3e; background-color: #fff5f5; border: 1px solid #fc8181; border-radius: 0.5rem;">
              <strong>Error rendering diagram:</strong>
              <pre style="margin-top: 0.5rem; font-size: 0.875rem; white-space: pre-wrap;">${error.message}</pre>
            </div>
          `;
        }
      });
    }
  }, [artifact.content]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(artifact.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Toolbar */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '0.75rem 1rem',
        borderBottom: '1px solid #e2e8f0',
        backgroundColor: '#f8fafc',
      }}>
        <div style={{
          fontSize: '0.875rem',
          color: '#718096',
          fontWeight: 500,
        }}>
          Mermaid Diagram
        </div>
        <button
          onClick={handleCopy}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.5rem 0.75rem',
            backgroundColor: copied ? '#48bb78' : '#ffffff',
            color: copied ? '#ffffff' : '#4a5568',
            border: '1px solid #cbd5e0',
            borderRadius: '0.375rem',
            cursor: 'pointer',
            fontSize: '0.875rem',
            transition: 'all 0.2s',
          }}
          onMouseEnter={(e) => {
            if (!copied) {
              e.currentTarget.style.backgroundColor = '#f7fafc';
              e.currentTarget.style.borderColor = '#a0aec0';
            }
          }}
          onMouseLeave={(e) => {
            if (!copied) {
              e.currentTarget.style.backgroundColor = '#ffffff';
              e.currentTarget.style.borderColor = '#cbd5e0';
            }
          }}
        >
          {copied ? (
            <>
              <Check size={16} />
              Copied!
            </>
          ) : (
            <>
              <Copy size={16} />
              Copy Source
            </>
          )}
        </button>
      </div>

      {/* Diagram Container */}
      <div style={{
        flex: 1,
        overflow: 'auto',
        padding: '2rem',
        backgroundColor: '#ffffff',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
      }}>
        <div
          ref={containerRef}
          style={{
            width: '100%',
            minHeight: '200px',
          }}
        />
      </div>
    </div>
  );
};

export default MermaidArtifact;
