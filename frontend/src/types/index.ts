export interface User {
  id: string;
  email: string;
  full_name: string;
  role: 'admin' | 'operator' | 'viewer';
}

export interface DashboardStats {
  user: { name: string; role: string };
  connected_systems: number;
  total_mcp_tools: number;
  pending_approvals: number;
  operations: {
    total_incidents: number;
    open_incidents: number;
    critical_incidents: number;
    total_tasks: number;
    active_tasks: number;
    system_status: string;
  };
  recent_activity: {
    id: string;
    action_type: string;
    target_system: string;
    tool_name: string;
    summary: string;
    status: string;
    created_at: string;
  }[];
}

export interface ApprovalRequest {
  id: string;
  execution_id: string;
  target_system: string;
  tool_name: string;
  action_summary: string;
  arguments: Record<string, any>;
  approval_status: 'pending' | 'approved' | 'rejected' | 'expired';
  action_hash?: string;
  created_at: string;
  expires_at: string;
  approved_by?: string;
  approved_at?: string;
  execution_result?: any;
}

export interface Integration {
  id: string;
  provider: string;
  name: string;
  status: 'connected' | 'disconnected' | 'error';
  tool_count: number;
  tools: string[];
  notes: string;
  last_sync_at: string;
}

export interface AuditLog {
  id: string;
  user_id: string;
  action_type: string;
  target_system: string;
  tool_name: string;
  parameters: Record<string, any>;
  approval_id?: string;
  result_summary: string;
  status: 'success' | 'failure' | 'rejected' | 'pending';
  created_at: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  tool_calls?: any[];
  tool_results?: any[];
  pending_approval?: ApprovalRequest | null;
  timestamp: string;
}

export interface GitHubAccount {
  status: string;
  connected: boolean;
  login?: string;
  name?: string;
  avatar_url?: string;
  html_url?: string;
  public_repos?: number;
  total_private_repos?: number;
  scopes?: string[];
  note?: string;
  message?: string;
  error?: string;
}

export interface GitHubRepository {
  id: number;
  name: string;
  full_name: string;
  owner: string;
  description: string;
  html_url: string;
  default_branch: string;
  private: boolean;
  is_monitored: boolean;
  health_score: number;
  last_synced_at?: string | null;
}

export interface GitHubEventItem {
  id: string;
  delivery_id: string;
  repo_name: string;
  event_type: string;
  action: string;
  actor: string;
  summary: string;
  created_at: string;
  payload?: any;
}

export interface WorkflowFailureItem {
  id: string;
  repo_name: string;
  workflow_name: string;
  run_id: number;
  commit_sha?: string;
  commit_message?: string;
  branch: string;
  sender: string;
  html_url?: string;
  failing_step?: string;
  error_snippet?: string;
  root_cause?: string;
  suggested_fix?: string;
  status: 'detected' | 'analyzed' | 'fix_proposed' | 'fix_applied' | 'resolved';
  detected_at: string;
  analysis?: any;
  proposal?: any;
}

export interface FixProposalItem {
  id: string;
  failure_id: string;
  repo_name: string;
  branch_name: string;
  title: string;
  description: string;
  diff_content: string;
  status: 'proposed' | 'pending' | 'approved' | 'applied' | 'rejected' | 'failed';
  approval_id?: string;
  pr_url?: string;
  pr_number?: number;
  created_at: string;
}

export interface GitHubHealth {
  monitored_repositories_count: number;
  total_failures_detected: number;
  active_failures_count: number;
  resolved_failures_count: number;
  total_events_ingested: number;
  overall_health_score: number;
  status: 'OPTIMAL' | 'WARNING' | 'CRITICAL';
  repositories: {
    repo_full_name: string;
    owner: string;
    repo_name: string;
    default_branch: string;
    health_score: number;
    active_failures: number;
    last_synced_at?: string | null;
  }[];
}

export interface GitHubNotificationItem {
  id: string;
  title: string;
  message: string;
  notification_type: string;
  reference_id?: string;
  is_read: boolean;
  created_at: string;
}

