export interface User {
  id: string;
  email: string;
  full_name: string;
  role: 'admin' | 'operator' | 'viewer';
  account_type?: 'individual' | 'company' | 'company_employee';
  company_name?: string;
  workspace_id?: string;
  is_verified?: boolean;
  permissions?: string[];
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
  requesting_user_id?: string;
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
  proposal_id?: string;
  failure_id?: string;
  repo_full_name?: string;
  has_solution?: boolean;
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

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
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
  missing_scopes?: string[];
  target_repo?: string;
  can_push?: boolean;
  can_pull?: boolean;
  is_admin?: boolean;
  permission_level?: 'read_write' | 'read_only' | 'none' | 'disconnected';
  permission_label?: string;
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
  can_push?: boolean;
  can_pull?: boolean;
  is_admin?: boolean;
  permission_level?: string;
  permission_label?: string;
}

export interface RepositoryOverview {
  owner: string;
  repo: string;
  full_name: string;
  description: string;
  html_url: string;
  default_branch: string;
  private: boolean;
  stars: number;
  forks: number;
  permissions: {
    can_push: boolean;
    can_pull: boolean;
    is_admin: boolean;
    permission_level: string;
    permission_label: string;
  };
  latest_commit?: {
    sha: string;
    full_sha: string;
    message: string;
    author: string;
    date: string;
    html_url: string;
  } | null;
  open_pull_requests_count: number;
  open_pull_requests: Array<{
    number: number;
    title: string;
    user: string;
    html_url: string;
    created_at: string;
    draft: boolean;
  }>;
  prs_message?: string | null;
  open_issues_count: number;
  open_issues: Array<{
    number: number;
    title: string;
    user: string;
    labels: string[];
    comments: number;
    html_url: string;
    created_at: string;
  }>;
  issues_message?: string | null;
  recent_workflow_runs_count: number;
  recent_workflow_runs: Array<{
    id: number;
    name: string;
    status: string;
    conclusion: string;
    event: string;
    head_branch: string;
    head_sha: string;
    html_url: string;
    created_at: string;
  }>;
  runs_message?: string | null;
}

export interface GitHubEventItem {
  id: string;
  delivery_id: string;
  repo_name?: string;
  repo_full_name?: string;
  event_type: string;
  action: string;
  actor?: string;
  sender?: string;
  summary: string;
  created_at: string;
  payload?: any;
}

export type ResolutionStatus = 'NOT_VERIFIED' | 'VERIFYING' | 'VERIFIED_RESOLVED' | 'STILL_FAILING' | 'VERIFICATION_FAILED';
export type AIAnalysisStatus = 'NOT_ANALYZED' | 'ANALYZING' | 'ANALYZED' | 'ANALYSIS_FAILED';

export interface FileChangeItem {
  file_name: string;
  file_path: string;
  reason: string;
  proposed_changes: string;
}

export interface StructuredAnalysis {
  problem_summary: string;
  root_cause: string;
  error_type?: string;
  failed_step?: string;
  log_evidence?: string;
  affected_file?: string;
  dependency_or_config?: string;
  confidence_level?: string;
  recommended_solution: string;
  files_requiring_changes: FileChangeItem[];
  code_changes_diff: string;
  risk_assessment: string;
  expected_result: string;
  is_groq_powered?: boolean;
}

export interface SolutionHistory {
  issue_overview: {
    title: string;
    repo: string;
    workflow_run_id: number;
    detected_at?: string;
    original_error?: string;
    resolution_status: ResolutionStatus | string;
  };
  problem_summary: string;
  root_cause: {
    technical_cause: string;
    error_type?: string;
    failed_step?: string;
    log_evidence?: string;
    affected_file?: string;
    confidence_level?: string;
  };
  suggested_solution: {
    summary: string;
    bullet_points: string[];
  };
  code_changes: {
    diff: string;
    files: Array<{
      file_path: string;
      change_summary: string;
      added_lines?: string[];
      removed_lines?: string[];
    }>;
  };
  testing_evidence: {
    test_commands: string[];
    test_environment: string;
    test_results: string;
    passed_checks: string[];
    failed_checks: string[];
    sandbox_status?: string;
    actions_url?: string;
  };
  pr_details: {
    pr_number?: number;
    pr_url?: string;
    branch?: string;
    pr_state?: string;
    merge_commit?: string;
    merged_at?: string;
  };
  final_result: {
    status: ResolutionStatus | string;
    explanation: string;
    verified_at?: string;
  };
}

export interface WorkflowFailureItem {
  id: string;
  repo_name?: string;
  repo_full_name?: string;
  workflow_name: string;
  run_id: number;
  commit_sha?: string;
  commit_message?: string;
  branch: string;
  sender: string;
  html_url?: string;
  failing_step?: string;
  error_snippet?: string;
  error_log_snippet?: string;
  analysis_summary?: string;
  root_cause?: string;
  suggested_fix?: string;
  analysis_status?: AIAnalysisStatus | string;
  structured_analysis?: StructuredAnalysis | null;
  resolution_status?: ResolutionStatus | string;
  status: 'detected' | 'analyzed' | 'fix_proposed' | 'fix_applied' | 'resolved';
  detected_at: string;
  analysis?: any;
  proposal?: any;
  fix_proposal?: {
    id: string;
    title: string;
    status: string;
    branch_name: string;
    pr_url?: string | null;
    approval_id?: string;
    pr_status?: string;
    resolution_status?: ResolutionStatus | string;
  } | null;
}

export interface FixProposalItem {
  id: string;
  failure_id: string;
  repo_name: string;
  repo_full_name?: string;
  branch_name: string;
  title: string;
  description: string;
  diff_content: string;
  status: 'proposed' | 'pending' | 'approved' | 'applied' | 'rejected' | 'failed';
  approval_id?: string;
  pr_url?: string | null;
  pr_number?: number | null;
  pr_status?: 'OPEN' | 'MERGED' | 'CLOSED' | 'NOT_CREATED' | 'ERROR' | 'UNKNOWN';
  resolution_status?: ResolutionStatus | string;
  merge_commit_sha?: string | null;
  merged_at?: string | null;
  verified_at?: string | null;
  verification_details?: any;
  test_results?: any;
  workflow_run_id?: number;
  commit_sha?: string;
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

export interface CompanyDetails {
  id: string;
  name: string;
  slug: string;
  company_email?: string;
  website?: string;
  industry?: string;
  status: string;
  member_count: number;
  pending_invites_count: number;
  created_at?: string;
}

export interface CompanyMember {
  member_id: string;
  user_id: string;
  full_name: string;
  email: string;
  role: 'admin' | 'operator' | 'viewer';
  account_type?: string;
  account_status?: string;
  is_verified?: boolean;
  last_login_at?: string | null;
}

export interface WorkspaceInvitationItem {
  id: string;
  email: string;
  role: string;
  status: string;
  created_at: string;
  expires_at: string;
}

export interface UserWorkspace {
  id: string;
  name: string;
  slug: string;
  company_email?: string;
  website?: string;
  industry?: string;
  role: string;
  status: string;
}

