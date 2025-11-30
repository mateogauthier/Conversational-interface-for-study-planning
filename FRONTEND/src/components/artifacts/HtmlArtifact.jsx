import React, { useState, useMemo } from 'react';
import { Code } from 'lucide-react';

const HtmlArtifact = ({ artifact }) => {
  const [showSource, setShowSource] = useState(false);

  // Generate the complete HTML document with styling
  const htmlDoc = useMemo(() => {
    return `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
          body {
            margin: 0;
            padding: 16px;
            font-family: system-ui, -apple-system, sans-serif;
            color: #1f2937;
            background: #ffffff;
          }
          table {
            width: 100%;
            border-collapse: collapse;
            margin: 0;
            background: #ffffff;
          }
          th, td {
            padding: 12px;
            text-align: left;
            border: 1px solid #e5e7eb;
          }
          th {
            background-color: #f9fafb;
            font-weight: 600;
            color: #111827;
          }
          tr:nth-child(even) {
            background-color: #f9fafb;
          }
          tr:hover {
            background-color: #f3f4f6;
          }
        </style>
      </head>
      <body>
        ${artifact.content}
      </body>
      </html>
    `;
  }, [artifact.content]);

  return (
    <div className="html-artifact">
      <div className="html-artifact-header">
        <button
          onClick={() => setShowSource(!showSource)}
          className="toggle-source-button"
        >
          <Code size={16} />
          {showSource ? 'Show Preview' : 'Show Source'}
        </button>
      </div>
      {showSource ? (
        <pre className="html-source">
          <code>{artifact.content}</code>
        </pre>
      ) : (
        <iframe
          className="html-preview"
          sandbox="allow-same-origin"
          title="HTML Preview"
          srcDoc={htmlDoc}
        />
      )}
    </div>
  );
};

export default HtmlArtifact;
