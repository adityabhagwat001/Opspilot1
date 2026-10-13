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
