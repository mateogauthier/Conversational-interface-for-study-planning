/**
 * Markdown Parser Service
 *
 * Extracts artifacts (code blocks, tables, diagrams) from LLM-generated markdown.
 * This client-side approach is more reliable than forcing LLMs to generate
 * structured outputs with Instructor.
 */

import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import { visit } from 'unist-util-visit';

/**
 * Extracts artifacts from markdown using AST parsing.
 *
 * @param {string} markdown - The markdown text from LLM
 * @returns {{cleanText: string, artifacts: Array}} Clean text and extracted artifacts
 */
export function extractArtifactsFromMarkdown(markdown) {
  if (!markdown || typeof markdown !== 'string') {
    return { cleanText: markdown || '', artifacts: [] };
  }

  const artifacts = [];

  try {
    // Parse markdown to AST
    const processor = unified()
      .use(remarkParse)
      .use(remarkGfm);

    const tree = processor.parse(markdown);

    // Extract code blocks and tables from AST
    visit(tree, (node) => {
      // Code blocks (including mermaid diagrams)
      if (node.type === 'code') {
        const language = node.lang || 'text';
        const isMermaid = language === 'mermaid';

        artifacts.push({
          type: isMermaid ? 'mermaid' : 'code',
          language: language,
          title: isMermaid ? 'Diagram' : `${capitalizeFirst(language)} Code`,
          content: isMermaid ? sanitizeMermaid(node.value) : node.value
        });
      }

      // Tables (GFM tables)
      if (node.type === 'table') {
        artifacts.push({
          type: 'html',
          language: null,
          title: 'Table',
          content: convertTableToHtml(node)
        });
      }
    });

    // Remove code blocks and tables from markdown text
    let cleanText = markdown;

    // Remove code fences
    cleanText = cleanText.replace(/```[\s\S]*?```/g, '');

    // Remove markdown tables
    cleanText = cleanText.replace(/\|[^\n]+\|\n\|[-:\s|]+\|\n(?:\|[^\n]+\|\n?)*/g, '');

    // Clean up excessive newlines
    cleanText = cleanText.replace(/\n{3,}/g, '\n\n').trim();

    console.log(`Extracted ${artifacts.length} artifact(s) from markdown`);

    return { cleanText, artifacts };

  } catch (error) {
    console.error('Markdown AST parsing failed:', error);
    // Fallback to regex extraction
    return extractWithRegex(markdown);
  }
}

/**
 * Auto-fix common Mermaid syntax errors.
 *
 * @param {string} content - Raw mermaid diagram code
 * @returns {string} Sanitized mermaid code
 */
function sanitizeMermaid(content) {
  let fixed = content;

  // Fix 1: Unquoted node text in flowcharts
  // Problem: A[Text] should be A["Text"]
  // Match: NodeID[text that isn't quoted]
  fixed = fixed.replace(
    /\b([A-Z0-9]+)\[([^\]"]+)\]/g,
    (match, nodeId, text) => {
      // Don't fix if already quoted or if it's an edge label
      if (text.includes('"') || text.includes('-->') || text.includes('---')) {
        return match;
      }
      // Escape quotes in text
      const escapedText = text.replace(/"/g, '\\"');
      return `${nodeId}["${escapedText}"]`;
    }
  );

  // Fix 2: Ensure xychart uses xychart-beta
  fixed = fixed.replace(/^xychart\s/gm, 'xychart-beta ');

  // Fix 3: Remove invalid "label" syntax in xychart
  // Problem: line [1,2,3] label "Text" is invalid - should be just line [1,2,3]
  // Match: (line|bar) [...] label "..."
  fixed = fixed.replace(
    /(line|bar)\s*(\[[^\]]+\])\s+label\s+"[^"]*"/gi,
    '$1 $2'
  );

  // Fix 4: Remove comments from mermaid diagrams
  // Problem: // comments are not valid in mermaid syntax
  // Remove anything after // on each line
  fixed = fixed.split('\n').map(line => {
    const commentIndex = line.indexOf('//');
    if (commentIndex !== -1) {
      return line.substring(0, commentIndex).trimEnd();
    }
    return line;
  }).join('\n');

  // Fix 5: Remove common trailing spaces/newlines
  fixed = fixed.trim();

  return fixed;
}

/**
 * Convert remark table node to HTML.
 *
 * @param {Object} tableNode - Remark AST table node
 * @returns {string} HTML table string
 */
function convertTableToHtml(tableNode) {
  if (!tableNode || !tableNode.children) {
    return '<table></table>';
  }

  const rows = tableNode.children;
  if (rows.length === 0) {
    return '<table></table>';
  }

  // First row is header
  const headerRow = rows[0];
  const bodyRows = rows.slice(1);

  let html = '<table border="1" style="border-collapse: collapse; width: 100%;">\n';

  // Header
  if (headerRow && headerRow.children) {
    html += '  <thead>\n    <tr>\n';
    headerRow.children.forEach(cell => {
      const cellText = extractTextFromNode(cell);
      html += `      <th style="padding: 8px; background-color: #f2f2f2;">${cellText}</th>\n`;
    });
    html += '    </tr>\n  </thead>\n';
  }

  // Body
  if (bodyRows.length > 0) {
    html += '  <tbody>\n';
    bodyRows.forEach(row => {
      if (row && row.children) {
        html += '    <tr>\n';
        row.children.forEach(cell => {
          const cellText = extractTextFromNode(cell);
          html += `      <td style="padding: 8px;">${cellText}</td>\n`;
        });
        html += '    </tr>\n';
      }
    });
    html += '  </tbody>\n';
  }

  html += '</table>';

  return html;
}

/**
 * Extract text content from remark node.
 *
 * @param {Object} node - Remark AST node
 * @returns {string} Text content
 */
function extractTextFromNode(node) {
  if (!node) return '';

  if (node.type === 'text') {
    return node.value || '';
  }

  if (node.children) {
    return node.children.map(extractTextFromNode).join('');
  }

  return '';
}

/**
 * Fallback regex-based extraction (when AST parsing fails).
 *
 * @param {string} markdown - Markdown text
 * @returns {{cleanText: string, artifacts: Array}}
 */
function extractWithRegex(markdown) {
  const artifacts = [];
  let cleanText = markdown;

  // Extract code blocks
  const codeBlockPattern = /```(\w+)?\n([\s\S]*?)```/g;
  let match;

  while ((match = codeBlockPattern.exec(markdown)) !== null) {
    const language = match[1] || 'text';
    const content = match[2].trim();
    const isMermaid = language === 'mermaid';

    artifacts.push({
      type: isMermaid ? 'mermaid' : 'code',
      language: language,
      title: isMermaid ? 'Diagram' : `${capitalizeFirst(language)} Code`,
      content: isMermaid ? sanitizeMermaid(content) : content
    });
  }

  // Remove code blocks from text
  cleanText = cleanText.replace(codeBlockPattern, '');

  // Extract markdown tables
  const tablePattern = /\|[^\n]+\|\n\|[-:\s|]+\|\n(?:\|[^\n]+\|\n?)*/g;
  const tables = cleanText.match(tablePattern);

  if (tables) {
    tables.forEach(tableMarkdown => {
      artifacts.push({
        type: 'html',
        language: null,
        title: 'Table',
        content: convertMarkdownTableToHtml(tableMarkdown)
      });
    });

    // Remove tables from text
    cleanText = cleanText.replace(tablePattern, '');
  }

  // Extract raw HTML tables (as fallback)
  const htmlTablePattern = /<table[\s\S]*?<\/table>/gi;
  const htmlTables = cleanText.match(htmlTablePattern);

  if (htmlTables) {
    htmlTables.forEach(tableHtml => {
      artifacts.push({
        type: 'html',
        language: null,
        title: 'Table',
        content: tableHtml
      });
    });

    // Remove HTML tables from text
    cleanText = cleanText.replace(htmlTablePattern, '');
  }

  // Clean up
  cleanText = cleanText.replace(/\n{3,}/g, '\n\n').trim();

  console.log(`Regex fallback: extracted ${artifacts.length} artifact(s)`);

  return { cleanText, artifacts };
}

/**
 * Convert markdown table string to HTML.
 *
 * @param {string} markdown - Markdown table
 * @returns {string} HTML table
 */
function convertMarkdownTableToHtml(markdown) {
  const lines = markdown.trim().split('\n');
  if (lines.length < 2) return '<table></table>';

  // Parse header
  const headers = lines[0].split('|').map(h => h.trim()).filter(h => h);

  // Parse rows (skip separator line at index 1)
  const rows = [];
  for (let i = 2; i < lines.length; i++) {
    const cells = lines[i].split('|').map(c => c.trim()).filter(c => c);
    if (cells.length > 0) {
      rows.push(cells);
    }
  }

  // Build HTML
  let html = '<table border="1" style="border-collapse: collapse; width: 100%;">\n';
  html += '  <thead>\n    <tr>\n';
  headers.forEach(header => {
    html += `      <th style="padding: 8px; background-color: #f2f2f2;">${header}</th>\n`;
  });
  html += '    </tr>\n  </thead>\n  <tbody>\n';

  rows.forEach(row => {
    html += '    <tr>\n';
    row.forEach(cell => {
      html += `      <td style="padding: 8px;">${cell}</td>\n`;
    });
    html += '    </tr>\n';
  });

  html += '  </tbody>\n</table>';

  return html;
}

/**
 * Capitalize first letter of string.
 */
function capitalizeFirst(str) {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1);
}

export default extractArtifactsFromMarkdown;
