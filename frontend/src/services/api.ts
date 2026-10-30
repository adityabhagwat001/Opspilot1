import axios from 'axios';
import { 
  DashboardStats, 
  ApprovalRequest, 
  Integration, 
  AuditLog, 
  User,
  GitHubAccount,
  GitHubRepository,
  GitHubEventItem,
  WorkflowFailureItem,
  FixProposalItem,
  GitHubHealth,
  GitHubNotificationItem
} from '../types';

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

  getConversations: async (): Promise<Array<{ id: string; title: string; created_at: string; updated_at: string }>> => {
    const res = await apiClient.get('/chat/conversations');
    return res.data;
  },

  getMessages: async (conversationId: string) => {
    const res = await apiClient.get(`/chat/conversations/${conversationId}/messages`);
    return res.data;
  },

  createConversation: async (title?: string) => {
    const res = await apiClient.post('/chat/conversations', { title: title || 'New Chat' });
    return res.data;
  },

  deleteConversation: async (conversationId: string) => {
    const res = await apiClient.delete(`/chat/conversations/${conversationId}`);
    return res.data;
  },

  updateConversationTitle: async (conversationId: string, title: string) => {
    const res = await apiClient.patch(`/chat/conversations/${conversationId}`, { title });
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
  deleteApproval: async (approvalId: string) => {
    const res = await apiClient.delete(`/approvals/${approvalId}`);
    return res.data;
  },

  purgeApprovals: async () => {
    const res = await apiClient.post('/approvals/purge');
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

  getGitHubAccount: async (): Promise<GitHubAccount> => {
    const res = await apiClient.get('/github/account');
    return res.data;
  },

  connectGitHub: async (payload: { token: string; username?: string; default_repo?: string }): Promise<{
    success: boolean;
    message: string;
    account: GitHubAccount;
    repositories: GitHubRepository[];
  }> => {
    const res = await apiClient.post('/github/connect', payload);
    return res.data;
  },

  disconnectGitHub: async (): Promise<{ success: boolean; message: string; account: GitHubAccount }> => {
    const res = await apiClient.post('/github/disconnect');
    return res.data;
  },

  getGitHubRepositories: async (): Promise<{ count: number; repositories: GitHubRepository[] }> => {
    const res = await apiClient.get('/github/repositories');
    return res.data;
  },

  toggleRepositoryMonitor: async (
    repoFullName: string,
    isMonitored: boolean,
    defaultBranch = 'main'
  ): Promise<{ status: string; repo_full_name: string; is_monitored: boolean }> => {
    const res = await apiClient.post('/github/repositories/monitor', {
      repo_full_name: repoFullName,
      is_monitored: isMonitored,
      default_branch: defaultBranch,
    });
    return res.data;
  },

  getGitHubActivity: async (
    limit = 30,
    repoName?: string
  ): Promise<GitHubEventItem[]> => {
    const res = await apiClient.get('/github/activity', {
      params: { limit, ...(repoName ? { repo_name: repoName } : {}) },
    });
    return Array.isArray(res.data) ? res.data : (res.data?.events || []);
  },

  getGitHubFailures: async (
    limit = 20,
    status?: string
  ): Promise<WorkflowFailureItem[]> => {
    const res = await apiClient.get('/github/failures', {
      params: { limit, ...(status ? { status } : {}) },
    });
    return Array.isArray(res.data) ? res.data : (res.data?.failures || []);
  },

  getGitHubFailureDetail: async (failureId: string): Promise<WorkflowFailureItem> => {
    const res = await apiClient.get(`/github/failures/${failureId}`);
    return res.data;
  },

  analyzeFailure: async (
    failureId: string
  ): Promise<{
    failure_id: string;
    root_cause: string;
    suggested_fix: string;
    failing_step?: string;
    analysis_summary?: string;
  }> => {
    const res = await apiClient.post(`/github/failures/${failureId}/analyze`);
    return res.data;
  },

  proposeFix: async (
    failureId: string
  ): Promise<{
    status: string;
    proposal_id: string;
    approval_id?: string;
    files_changed?: string[];
    diff_content?: string;
    branch_name?: string;
  }> => {
    const res = await apiClient.post(`/github/failures/${failureId}/propose-fix`);
    return res.data;
  },

  getGitHubProposals: async (statusFilter?: string): Promise<FixProposalItem[]> => {
    const res = await apiClient.get('/github/proposals', {
      params: statusFilter ? { status_filter: statusFilter } : {},
    });
    return res.data;
  },

  executeProposal: async (
    proposalId: string
  ): Promise<{
    status: string;
    proposal_id: string;
    pr_url: string;
    pr_number?: number;
    message: string;
  }> => {
    const res = await apiClient.post(`/github/proposals/${proposalId}/execute`);
    return res.data;
  },

  deleteGitHubProposal: async (proposalId: string): Promise<{ status: string; deleted_id: string }> => {
    const res = await apiClient.delete(`/github/proposals/${proposalId}`);
    return res.data;
  },

  deleteGitHubFailure: async (failureId: string): Promise<{ status: string; deleted_id: string }> => {
    const res = await apiClient.delete(`/github/failures/${failureId}`);
    return res.data;
  },

  getGitHubHealth: async (): Promise<GitHubHealth> => {
    const res = await apiClient.get('/github/health');
    return res.data;
  },

  getNotifications: async (
    unreadOnly = false
  ): Promise<{ unread_count: number; notifications: GitHubNotificationItem[] }> => {
    const res = await apiClient.get('/github/notifications', {
      params: { unread_only: unreadOnly },
    });
    return res.data;
  },

  markNotificationRead: async (notificationId: string): Promise<{ status: string; id: string }> => {
    const res = await apiClient.post(`/github/notifications/${notificationId}/read`);
    return res.data;
  },

  markAllNotificationsRead: async (): Promise<{ status: string }> => {
    const res = await apiClient.post('/github/notifications/read-all');
    return res.data;
  },

  syncGitHubData: async (): Promise<{
    status: string;
    synced_repositories: number;
    new_items_synced: number;
    synced_at: string;
  }> => {
    const res = await apiClient.post('/github/sync');
    return res.data;
  },
};
