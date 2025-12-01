import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';

const CodeArtifact = ({ artifact }) => {
  const [copied, setCopied] = useState(false);

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
    <div className="code-artifact">
      <div className="code-artifact-header">
        <span className="code-language">
          {artifact.language || 'code'}
        </span>
        <button
          onClick={handleCopy}
          className="copy-button"
          title={copied ? 'Copied!' : 'Copy code'}
        >
          {copied ? <Check size={16} /> : <Copy size={16} />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre className="code-content">
        <code className={artifact.language ? `language-${artifact.language}` : ''}>
          {artifact.content}
        </code>
      </pre>
    </div>
  );
};

export default CodeArtifact;
