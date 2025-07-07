import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle token expiration
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API calls
export const authAPI = {
  login: async (credentials) => {
    const formData = new URLSearchParams();
    formData.append('username', credentials.username);
    formData.append('password', credentials.password);
    
    const response = await axios.post(`${API_BASE_URL}/auth/login`, formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    return response.data;
  },

  register: async (userData) => {
    const response = await axios.post(`${API_BASE_URL}/auth/register`, userData);
    return response.data;
  },

  getCurrentUser: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },
};

// Chat API calls
export const chatAPI = {
  getChats: async () => {
    const response = await api.get('/chats/');
    return response.data;
  },

  createChat: async (title) => {
    console.log('🔄 API: Opretter chat med titel:', title);
    try {
      const response = await api.post('/chats/', { title });
      console.log('✅ API: Chat oprettet, response:', response.data);
      return response.data;
    } catch (error) {
      console.error('❌ API: Fejl ved oprettelse af chat:', error);
      console.error('Response data:', error.response?.data);
      console.error('Response status:', error.response?.status);
      throw error;
    }
  },

  getChat: async (chatId) => {
    const response = await api.get(`/chats/${chatId}`);
    return response.data;
  },

  sendMessage: async (chatId, content) => {
    const response = await api.post(`/chats/${chatId}/message`, { content });
    return response.data;
  },

  deleteChat: async (chatId) => {
    const response = await api.delete(`/chats/${chatId}`);
    return response.data;
  },
};

export default api;
