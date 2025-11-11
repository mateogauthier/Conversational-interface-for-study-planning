import axios from 'axios';

// Create axios instance with default config
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 200000, // 200 seconds (3min 20s) for LLM responses - allows buffer for backend timeout
  headers: {
    'Content-Type': 'application/json',
  },
});

// File Management API
export const fileApi = {
  // Upload a file
  upload: async (file, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: onProgress ? (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(percentCompleted);
      } : undefined,
    });
    return response.data;
  },

  // List all files
  list: async () => {
    const response = await api.get('/files/');
    return response.data;
  },

  // Get file details
  getDetails: async (filename) => {
    const response = await api.get(`/files/${filename}`);
    return response.data;
  },

  // Delete a file
  delete: async (filename) => {
    const response = await api.delete(`/files/${filename}`);
    return response.data;
  },

  // Get supported extensions
  getSupportedExtensions: async () => {
    const response = await api.get('/files/supported/extensions');
    return response.data;
  },
};

// RAG API
export const ragApi = {
  // Search documents
  search: async (prompt, nResults = 5, useLlm = false) => {
    const response = await api.post('/rag/search', {
      prompt,
      n_results: nResults,
      use_llm: useLlm,
    });
    return response.data;
  },

  // Query with LLM
  query: async (prompt, options = {}) => {
    const response = await api.post('/rag/query', {
      prompt,
      n_results: options.nResults || 5,
      model: options.model || null,
      language: options.language || null,
      instructions: options.instructions || null,
    });
    return response.data;
  },

  // Get RAG stats
  getStats: async () => {
    const response = await api.get('/rag/stats');
    return response.data;
  },

  // Reset RAG collection
  reset: async () => {
    const response = await api.post('/rag/reset');
    return response.data;
  },

  // Health check
  health: async () => {
    const response = await api.get('/rag/health');
    return response.data;
  },
};

// LLM API
export const llmApi = {
  // Direct LLM query
  query: async (prompt, model = null) => {
    const response = await api.post('/llm/query', {
      prompt,
      model,
    });
    return response.data;
  },

  // Get LLM status
  getStatus: async () => {
    const response = await api.get('/llm/status');
    return response.data;
  },

  // List available models
  listModels: async () => {
    const response = await api.get('/llm/models');
    return response.data;
  },

  // Ensure model is available
  ensureModel: async (modelName) => {
    const response = await api.post(`/llm/models/${modelName}/ensure`);
    return response.data;
  },

  // Health check
  health: async () => {
    const response = await api.get('/llm/health');
    return response.data;
  },
};

export default api;
