import axios from 'axios';
import { Intent, Secret, SystemStatus } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const raverApi = {
  // Intent operations
  async processIntent(userId: string, command: string, context?: any) {
    const response = await api.post('/api/v1/intent', {
      user_id: userId,
      command,
      context,
    });
    return response.data;
  },

  // Vault operations
  async storeSecret(userId: string, service: string, label: string, secretData: string) {
    const response = await api.post('/api/v1/vault/store', {
      user_id: userId,
      service,
      label,
      secret_data: secretData,
    });
    return response.data;
  },

  async retrieveSecret(userId: string, secretId: string, userRoles: string[]) {
    const response = await api.post('/api/v1/vault/retrieve', {
      user_id: userId,
      secret_id: secretId,
      user_roles: userRoles,
    });
    return response.data;
  },

  async listSecrets(userId: string, userRoles: string[]) {
    const response = await api.get(`/api/v1/vault/secrets?user_id=${userId}&user_roles=${userRoles.join(',')}`);
    return response.data;
  },

  // System operations
  async pauseSystem(userId: string) {
    const response = await api.post('/api/v1/system/pause', { user_id: userId });
    return response.data;
  },

  async resumeSystem(userId: string) {
    const response = await api.post('/api/v1/system/resume', { user_id: userId });
    return response.data;
  },

  async getSystemStatus(): Promise<SystemStatus> {
    const response = await api.get('/api/v1/system/status');
    return response.data;
  },
};
