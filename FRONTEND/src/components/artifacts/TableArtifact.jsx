import React from 'react';

const TableArtifact = ({ artifact }) => {
  // Try to parse the content as CSV or pipe-delimited table
  const parseTable = (content) => {
    const lines = content.trim().split('\n');

    // Detect delimiter (comma or pipe)
    const delimiter = content.includes('|') ? '|' : ',';

    return lines.map(line => {
      return line
        .split(delimiter)
        .map(cell => cell.trim())
        .filter(cell => cell !== ''); // Remove empty cells from pipe tables
    });
  };

  try {
    const rows = parseTable(artifact.content);

    if (rows.length === 0) {
      return <div className="table-artifact-error">No table data found</div>;
    }

    const headers = rows[0];
    const dataRows = rows.slice(1).filter(row =>
      // Filter out separator rows (like |----|----| in markdown tables)
      !row.every(cell => /^-+$/.test(cell))
    );

    return (
      <div className="table-artifact">
        <div className="table-container">
          <table>
            <thead>
              <tr>
                {headers.map((header, idx) => (
                  <th key={idx}>{header}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {dataRows.map((row, rowIdx) => (
                <tr key={rowIdx}>
                  {row.map((cell, cellIdx) => (
                    <td key={cellIdx}>{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  } catch (err) {
    return (
      <div className="table-artifact-error">
        Failed to parse table: {err.message}
      </div>
    );
  }
};

export default TableArtifact;
