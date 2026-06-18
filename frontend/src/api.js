import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Setup Axios client
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to attach Bearer JWT token automatically
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('rag_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

export const signupUser = async (username, password) => {
  const response = await apiClient.post('/signup', { username, password });
  return response.data;
};

export const loginUser = async (username, password) => {
  const params = new URLSearchParams();
  params.append('username', username);
  params.append('password', password);
  
  const response = await apiClient.post('/login', params, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    }
  });
  return response.data;
};

export const checkHealth = async () => {
  const response = await apiClient.get('/health');
  return response.data;
};

export const uploadDocument = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await apiClient.post('/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const fetchSessions = async () => {
  const response = await apiClient.get('/sessions');
  return response.data;
};

export const fetchSessionHistory = async (sessionId) => {
  const response = await apiClient.get(`/history/${sessionId}`);
  return response.data;
};

export const deleteSession = async (sessionId) => {
  const response = await apiClient.delete(`/session/${sessionId}`);
  return response.data;
};

export const fetchAdminStats = async () => {
  const response = await apiClient.get('/admin/stats');
  return response.data;
};

/**
 * Handles async POST streaming of RAG queries using raw fetch and ReadableStream reader.
 * Necessary because EventSource does not support POST requests or custom Headers.
 */
export const queryStream = async (
  question, 
  sessionId, 
  onToken, 
  onSources, 
  onError, 
  onDone
) => {
  const token = localStorage.getItem('rag_token');
  
  try {
    const response = await fetch(`${API_BASE_URL}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
      },
      body: JSON.stringify({
        question,
        session_id: sessionId
      })
    });
    
    if (!response.ok) {
      const errText = await response.text();
      let errParsed;
      try {
        errParsed = JSON.parse(errText);
      } catch {
        errParsed = { detail: errText };
      }
      throw new Error(errParsed.detail || "Query execution failed.");
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop(); // save trailing partial line in buffer
      
      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const parsed = JSON.parse(line);
          if (parsed.type === "sources") {
            onSources(parsed.data);
          } else if (parsed.type === "content") {
            onToken(parsed.data);
          } else if (parsed.type === "done") {
            onDone();
          }
        } catch (e) {
          console.error("Failed to parse stream line:", line, e);
        }
      }
    }
  } catch (err) {
    onError(err);
  }
};
