import axios from 'axios';

// Create axios instance with default config
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 200000, // 200 seconds (3min 20s) for LLM responses - allows buffer for backend timeout
  headers: {
    'Content-Type': 'application/json',
  },
});

// Token management
let accessToken = null;

export const setAccessToken = (token) => {
  accessToken = token;
};

export const getAccessToken = () => {
  return accessToken;
};

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for handling auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid - clear it and redirect to login
      accessToken = null;
      window.location.href = '/';
    }
    return Promise.reject(error);
  }
);

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

  // Download a file
  download: async (filename) => {
    const response = await api.get(`/files/${encodeURIComponent(filename)}/download`, {
      responseType: 'blob',
    });

    // Create a blob URL and trigger download
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
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
      conversation_id: options.conversationId || null,
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

// Conversation API
export const conversationApi = {
  // List user's conversations
  list: async (limit = 50, skip = 0) => {
    const response = await api.get('/conversations/', {
      params: { limit, skip },
    });
    return response.data;
  },

  // Get specific conversation with messages
  get: async (conversationId) => {
    const response = await api.get(`/conversations/${conversationId}`);
    return response.data;
  },

  // Delete conversation
  delete: async (conversationId) => {
    const response = await api.delete(`/conversations/${conversationId}`);
    return response.data;
  },
};

// Feedback API
export const feedbackApi = {
  // Submit feedback for a message (with optional comment)
  submitFeedback: async (messageId, feedback, comment = null) => {
    const response = await api.post('/feedback/message', {
      message_id: messageId,
      feedback: feedback, // 'like' or 'dislike'
      comment: comment, // optional written feedback
    });
    return response.data;
  },

  // Submit general feedback (not tied to specific message)
  submitGeneralFeedback: async (comment, rating = null, messageId = null, conversationId = null) => {
    const response = await api.post('/feedback/', {
      comment: comment,
      rating: rating, // optional 'like' or 'dislike'
      message_id: messageId,
      conversation_id: conversationId,
    });
    return response.data;
  },
};

// Admin Feedback API
export const adminFeedbackApi = {
  // Get paginated list of all feedback
  getAllFeedback: async (params = {}) => {
    const { skip = 0, limit = 50, rating, user_id, filename, start_date, end_date } = params;
    const queryParams = new URLSearchParams();
    queryParams.append('skip', skip);
    queryParams.append('limit', limit);
    if (rating) queryParams.append('rating', rating);
    if (user_id) queryParams.append('user_id', user_id);
    if (filename) queryParams.append('filename', filename);
    if (start_date) queryParams.append('start_date', start_date);
    if (end_date) queryParams.append('end_date', end_date);

    const response = await api.get(`/admin/feedback?${queryParams.toString()}`);
    return response.data;
  },

  // Get aggregated feedback statistics
  getStats: async () => {
    const response = await api.get('/admin/feedback/stats');
    return response.data;
  },

  // Generate LLM summary of feedback
  generateSummary: async (params = {}) => {
    const { rating, user_id, filename, start_date, end_date, max_items = 100, language = 'en' } = params;
    const queryParams = new URLSearchParams();
    if (rating) queryParams.append('rating', rating);
    if (user_id) queryParams.append('user_id', user_id);
    if (filename) queryParams.append('filename', filename);
    if (start_date) queryParams.append('start_date', start_date);
    if (end_date) queryParams.append('end_date', end_date);
    queryParams.append('max_items', max_items);
    queryParams.append('language', language);

    const response = await api.post(`/admin/feedback/summary?${queryParams.toString()}`);
    return response.data;
  },

  // Get feedback for specific file
  getFeedbackByFile: async (filename) => {
    const response = await api.get(`/admin/feedback/file/${encodeURIComponent(filename)}`);
    return response.data;
  },
};

// Agent API
export const agentApi = {
  // Execute agent-powered query with tool execution
  query: async (prompt, options = {}) => {
    const {
      conversationId = null,
      nResults = 5,
      language = null,
      model = null,
      instructions = null,
      enableAgent = true,
      autoApproveTools = false,
      enableArtifacts = true,
    } = options;

    const response = await api.post('/agent/query', {
      prompt,
      conversation_id: conversationId,
      n_results: nResults,
      language,
      model,
      instructions,
      enable_agent: enableAgent,
      auto_approve_tools: autoApproveTools,
      enable_artifacts: enableArtifacts,
    });
    return response.data;
  },

  // Confirm or deny pending agent action
  confirm: async (confirmationId, approved) => {
    const response = await api.post('/agent/confirm', {
      confirmation_id: confirmationId,
      approved,
    });
    return response.data;
  },

  // Get list of tools available to current user
  getTools: async () => {
    const response = await api.get('/agent/tools');
    return response.data;
  },

  // Check agent service health
  health: async () => {
    const response = await api.get('/agent/health');
    return response.data;
  },
};

// Academic API
export const academicApi = {
  // Get all degrees
  getDegrees: async () => {
    const response = await api.get('/academic/degrees');
    return response.data;
  },

  // Get specific degree
  getDegree: async (degreeId) => {
    const response = await api.get(`/academic/degrees/${degreeId}`);
    return response.data;
  },

  // Get degree curriculum
  getCurriculum: async (degreeId) => {
    const response = await api.get(`/academic/degrees/${degreeId}/curriculum`);
    return response.data;
  },

  // Get all subjects
  getAllSubjects: async () => {
    const response = await api.get('/academic/subjects');
    return response.data;
  },

  // Get subjects for a specific degree
  getDegreeSubjects: async (degreeId) => {
    const response = await api.get(`/academic/degrees/${degreeId}/subjects`);
    return response.data;
  },

  // Get student's transcript
  getMySchooling: async (degreeId) => {
    const response = await api.get(`/academic/students/me/schooling/${degreeId}`);
    return response.data;
  },

  // Upload schooling data
  uploadSchooling: async (degreeId, subjects) => {
    const response = await api.post(`/academic/students/me/schooling/${degreeId}/upload`, subjects);
    return response.data;
  },

  // Get student's study plan
  getMyPlan: async (degreeId) => {
    const response = await api.get(`/academic/students/me/plan/${degreeId}`);
    return response.data;
  },

  // Update student's study plan
  updateMyPlan: async (degreeId, planData) => {
    const response = await api.patch(`/academic/students/me/plan/${degreeId}`, planData);
    return response.data;
  },
};

export default api;
