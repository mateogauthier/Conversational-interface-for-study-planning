import React, { useState } from 'react';
import { ChevronDown, ChevronRight, Copy, Check } from 'lucide-react';

const JsonArtifact = ({ artifact }) => {
  const [copied, setCopied] = useState(false);
  const [expandedPaths, setExpandedPaths] = useState(new Set(['root']));

  let parsedData;
  try {
    parsedData = JSON.parse(artifact.content);
  } catch (err) {
    return (
      <div className="json-artifact-error">
        Invalid JSON: {err.message}
      </div>
    );
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(parsedData, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const togglePath = (path) => {
    const newExpanded = new Set(expandedPaths);
    if (newExpanded.has(path)) {
      newExpanded.delete(path);
    } else {
      newExpanded.add(path);
    }
    setExpandedPaths(newExpanded);
  };

  const renderValue = (value, key, path) => {
    const currentPath = `${path}.${key}`;

    if (value === null) {
      return <span className="json-null">null</span>;
    }

    if (typeof value === 'boolean') {
      return <span className="json-boolean">{value.toString()}</span>;
    }

    if (typeof value === 'number') {
      return <span className="json-number">{value}</span>;
    }

    if (typeof value === 'string') {
      return <span className="json-string">"{value}"</span>;
    }

    if (Array.isArray(value)) {
      const isExpanded = expandedPaths.has(currentPath);
      return (
        <div className="json-array">
          <button
            className="json-toggle"
            onClick={() => togglePath(currentPath)}
          >
            {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            <span className="json-bracket">[</span>
            {!isExpanded && <span className="json-preview">{value.length} items</span>}
          </button>
          {isExpanded && (
            <div className="json-children">
              {value.map((item, idx) => (
                <div key={idx} className="json-item">
                  <span className="json-key">{idx}:</span>
                  {renderValue(item, idx, currentPath)}
                </div>
              ))}
              <span className="json-bracket">]</span>
            </div>
          )}
        </div>
      );
    }

    if (typeof value === 'object') {
      const isExpanded = expandedPaths.has(currentPath);
      const keys = Object.keys(value);
      return (
        <div className="json-object">
          <button
            className="json-toggle"
            onClick={() => togglePath(currentPath)}
          >
            {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
            <span className="json-bracket">{'{'}</span>
            {!isExpanded && <span className="json-preview">{keys.length} keys</span>}
          </button>
          {isExpanded && (
            <div className="json-children">
              {keys.map((k) => (
                <div key={k} className="json-item">
                  <span className="json-key">{k}:</span>
                  {renderValue(value[k], k, currentPath)}
                </div>
              ))}
              <span className="json-bracket">{'}'}</span>
            </div>
          )}
        </div>
      );
    }

    return <span>{String(value)}</span>;
  };

  return (
    <div className="json-artifact">
      <div className="json-artifact-header">
        <span className="json-label">JSON</span>
        <button
          onClick={handleCopy}
          className="copy-button"
          title={copied ? 'Copied!' : 'Copy JSON'}
        >
          {copied ? <Check size={16} /> : <Copy size={16} />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <div className="json-content">
        {renderValue(parsedData, 'root', '')}
      </div>
    </div>
  );
};

export default JsonArtifact;
