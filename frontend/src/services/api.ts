import axios from 'axios';
import { DashboardStats, ApprovalRequest, Integration, AuditLog, User } from '../types';

const API_BASE = '/api';

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach JWT token from localStorage if present
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('opspilot_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const api = {
  // Auth
  login: async (email: string, password: string): Promise<{ access_token: string; user: User }> => {
    const res = await apiClient.post('/auth/login', { email, password });
    return res.data;
  },
  getMe: async (): Promise<User> => {
    const res = await apiClient.get('/auth/me');
    return res.data;
  },

  // Dashboard
  getDashboardStats: async (): Promise<DashboardStats> => {
    const res = await apiClient.get('/dashboard/stats');
    return res.data;
  },

  // Chat
  sendMessage: async (message: string, conversationId?: string) => {
    const res = await apiClient.post('/chat/message', {
      message,
      conversation_id: conversationId,
    });
    return res.data;
  },

  getConversations: async () => {
    const res = await apiClient.get('/chat/conversations');
    return res.data;
  },

  getMessages: async (conversationId: string) => {
    const res = await apiClient.get(`/chat/conversations/${conversationId}/messages`);
    return res.data;
  },

  // Approvals
  getApprovals: async (statusFilter?: string): Promise<ApprovalRequest[]> => {
    const res = await apiClient.get('/approvals', {
      params: statusFilter ? { status_filter: statusFilter } : {},
    });
    return res.data;
  },

  getApprovalDetails: async (approvalId: string): Promise<ApprovalRequest> => {
    const res = await apiClient.get(`/approvals/${approvalId}`);
    return res.data;
  },

  approveAction: async (approvalId: string) => {
    const res = await apiClient.post(`/approvals/${approvalId}/approve`);
    return res.data;
  },

  rejectAction: async (approvalId: string, reason?: string) => {
    const res = await apiClient.post(`/approvals/${approvalId}/reject`, { reason });
    return res.data;
  },

  // Integrations
  getIntegrations: async (): Promise<{ integrations: Integration[]; total_tools: number }> => {
    const res = await apiClient.get('/integrations');
    return res.data;
  },

  // Audit Logs
  getAuditLogs: async (systemFilter?: string, actionFilter?: string): Promise<AuditLog[]> => {
    const res = await apiClient.get('/audit', {
      params: {
        system_filter: systemFilter,
        action_filter: actionFilter,
      },
    });
    return res.data;
  },
};
