import React, { useState } from 'react';
import { X, ChevronLeft, ChevronRight } from 'lucide-react';
import CodeArtifact from './artifacts/CodeArtifact';
import HtmlArtifact from './artifacts/HtmlArtifact';
import TableArtifact from './artifacts/TableArtifact';
import JsonArtifact from './artifacts/JsonArtifact';
import MermaidArtifact from './artifacts/MermaidArtifact';

const ArtifactViewer = ({ artifacts, onClose }) => {
  const [currentIndex, setCurrentIndex] = useState(0);

  if (!artifacts || artifacts.length === 0) {
    return null;
  }

  const currentArtifact = artifacts[currentIndex];
  const hasMultiple = artifacts.length > 1;

  const handlePrevious = () => {
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : artifacts.length - 1));
  };

  const handleNext = () => {
    setCurrentIndex((prev) => (prev < artifacts.length - 1 ? prev + 1 : 0));
  };

  const renderArtifact = (artifact) => {
    switch (artifact.type) {
      case 'code':
        return <CodeArtifact artifact={artifact} />;
      case 'html':
        return <HtmlArtifact artifact={artifact} />;
      case 'table':
        return <TableArtifact artifact={artifact} />;
      case 'json':
        return <JsonArtifact artifact={artifact} />;
      case 'mermaid':
        return <MermaidArtifact artifact={artifact} />;
      default:
        return (
          <div className="unknown-artifact">
            <p>Unsupported artifact type: {artifact.type}</p>
            <pre>{artifact.content}</pre>
          </div>
        );
    }
  };

  return (
    <div className="artifact-viewer">
      <div className="artifact-viewer-header">
        <div className="artifact-title">
          <h3>{currentArtifact.title || `${currentArtifact.type} artifact`}</h3>
          {hasMultiple && (
            <span className="artifact-counter">
              {currentIndex + 1} of {artifacts.length}
            </span>
          )}
        </div>
        <div className="artifact-controls">
          {hasMultiple && (
            <>
              <button
                onClick={handlePrevious}
                className="artifact-nav-button"
                title="Previous artifact"
              >
                <ChevronLeft size={20} />
              </button>
              <button
                onClick={handleNext}
                className="artifact-nav-button"
                title="Next artifact"
              >
                <ChevronRight size={20} />
              </button>
            </>
          )}
          <button
            onClick={onClose}
            className="artifact-close-button"
            title="Close artifact viewer"
          >
            <X size={20} />
          </button>
        </div>
      </div>
      <div className="artifact-viewer-content">
        {renderArtifact(currentArtifact)}
      </div>
    </div>
  );
};

export default ArtifactViewer;
