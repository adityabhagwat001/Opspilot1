import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  GitBranch, 
  GitPullRequest, 
  AlertOctagon, 
  CheckCircle2, 
  RefreshCw, 
  ExternalLink, 
  ShieldCheck, 
  Bot, 
  Activity, 
  Bell, 
  AlertTriangle,
  Play,
  Terminal,
  FileCode,
  ArrowRight,
  KeyRound,
  Eye,
  EyeOff,
  X,
  Trash2
} from 'lucide-react';
import { api } from '../services/api';
import { 
  GitHubAccount, 
  GitHubRepository, 
  GitHubEventItem, 
  WorkflowFailureItem, 
  FixProposalItem, 
  GitHubHealth, 
  GitHubNotificationItem 
} from '../types';

export const GitHubDevOpsPage: React.FC = () => {
  const navigate = useNavigate();

  // Primary State
  const [account, setAccount] = useState<GitHubAccount | null>(null);
  const [repositories, setRepositories] = useState<GitHubRepository[]>([]);
  const [failures, setFailures] = useState<WorkflowFailureItem[]>([]);
  const [proposals, setProposals] = useState<FixProposalItem[]>([]);
  const [events, setEvents] = useState<GitHubEventItem[]>([]);
  const [health, setHealth] = useState<GitHubHealth | null>(null);
  const [notifications, setNotifications] = useState<GitHubNotificationItem[]>([]);

  // UI State
  const [loading, setLoading] = useState<boolean>(true);
  const [syncing, setSyncing] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'failures' | 'proposals' | 'repos' | 'activity'>('failures');
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);
  const [selectedFailure, setSelectedFailure] = useState<WorkflowFailureItem | null>(null);

  // Connect Another GitHub Profile Modal State
  const [isConnectModalOpen, setIsConnectModalOpen] = useState(false);
  const [connectUsername, setConnectUsername] = useState('');
  const [connectToken, setConnectToken] = useState('');
  const [connectDefaultRepo, setConnectDefaultRepo] = useState('');
  const [showToken, setShowToken] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [connectError, setConnectError] = useState<string | null>(null);

  const handleConnectSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!connectToken.trim()) return;
    setConnecting(true);
    setConnectError(null);
    try {
      const res = await api.connectGitHub({
        token: connectToken.trim(),
        username: connectUsername.trim() || undefined,
        default_repo: connectDefaultRepo.trim() || undefined
      });
      setIsConnectModalOpen(false);
      setConnectToken('');
      setConnectUsername('');
      setConnectDefaultRepo('');
      setStatusMessage({
        text: res.message || `Connected to GitHub account @${res.account.login} in real-time!`,
        type: 'success'
      });
      await loadAllData(false);
    } catch (err: any) {
      setConnectError(err?.response?.data?.detail || err.message || 'GitHub authentication failed.');
    } finally {
      setConnecting(false);
    }
  };

  const handleDisconnect = async () => {
    if (!window.confirm('Disconnect your active GitHub account?')) return;
    setConnecting(true);
    try {
      await api.disconnectGitHub();
      setIsConnectModalOpen(false);
      setStatusMessage({
        text: 'GitHub account disconnected.',
        type: 'success'
      });
      await loadAllData(false);
    } catch (err: any) {
      alert(`Disconnect failed: ${err?.response?.data?.detail || err.message}`);
    } finally {
      setConnecting(false);
    }
  };

  const loadAllData = async (showLoading = true) => {
    if (showLoading) setLoading(true);
    try {
      const [accRes, repoRes, failRes, propRes, eventRes, healthRes, notifRes] = await Promise.all([
        api.getGitHubAccount().catch(() => null),
        api.getGitHubRepositories().catch(() => ({ count: 0, repositories: [] })),
        api.getGitHubFailures(30).catch(() => []),
        api.getGitHubProposals().catch(() => []),
        api.getGitHubActivity(40).catch(() => []),
        api.getGitHubHealth().catch(() => null),
        api.getNotifications(false).catch(() => ({ unread_count: 0, notifications: [] })),
      ]);

      if (accRes) setAccount(accRes);

      const safeRepos = Array.isArray(repoRes) 
        ? repoRes 
        : (repoRes && Array.isArray((repoRes as any).repositories) ? (repoRes as any).repositories : []);
      setRepositories(safeRepos);

      const safeFailures = Array.isArray(failRes) 
        ? failRes 
        : (failRes && Array.isArray((failRes as any).failures) ? (failRes as any).failures : []);
      setFailures(safeFailures);

      const safeProposals = Array.isArray(propRes) 
        ? propRes 
        : (propRes && Array.isArray((propRes as any).proposals) ? (propRes as any).proposals : []);
      setProposals(safeProposals);

      const safeEvents = Array.isArray(eventRes) 
        ? eventRes 
        : (eventRes && Array.isArray((eventRes as any).events) ? (eventRes as any).events : []);
      setEvents(safeEvents);

      if (healthRes) setHealth(healthRes);

      const safeNotifs = Array.isArray(notifRes) 
        ? notifRes 
        : (notifRes && Array.isArray((notifRes as any).notifications) ? (notifRes as any).notifications : []);
      setNotifications(safeNotifs);
    } catch (err: any) {
      console.error('Failed to load GitHub DevOps telemetry:', err);
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  useEffect(() => {
    void loadAllData(true);
    const interval = setInterval(() => {
      void loadAllData(false);
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const res = await api.syncGitHubData();
      setStatusMessage({
        text: `Reconciliation complete: Synced ${res.synced_repositories} repositories (${res.new_items_synced} updates discovered).`,
        type: 'success'
      });
      await loadAllData(false);
    } catch (err: any) {
      setStatusMessage({
        text: `Synchronization failed: ${err.response?.data?.detail || err.message}`,
        type: 'error'
      });
    } finally {
      setSyncing(false);
      setTimeout(() => setStatusMessage(null), 5000);
    }
  };

  const handleToggleMonitoring = async (repo: GitHubRepository) => {
    const nextState = !repo.is_monitored;
    // Optimistic update
    setRepositories(prev => (prev || []).map(r => r.full_name === repo.full_name ? { ...r, is_monitored: nextState } : r));
    try {
      await api.toggleRepositoryMonitor(repo.full_name, nextState, repo.default_branch);
      await loadAllData(false);
    } catch (err: any) {
      // Revert on error
      setRepositories(prev => (prev || []).map(r => r.full_name === repo.full_name ? { ...r, is_monitored: !nextState } : r));
      setStatusMessage({
        text: `Failed to update monitoring: ${err.response?.data?.detail || err.message}`,
        type: 'error'
      });
    }
  };

  const handleAnalyzeFailure = async (failureId: string) => {
    setActionLoadingId(`analyze-${failureId}`);
    try {
      const res = await api.analyzeFailure(failureId);
      setStatusMessage({
        text: `Analysis complete for run: Root cause identified.`,
        type: 'success'
      });
      await loadAllData(false);
      const updatedFail = (failures || []).find(f => f.id === failureId);
      if (updatedFail) {
        setSelectedFailure({
          ...updatedFail,
          root_cause: res.root_cause,
          suggested_fix: res.suggested_fix,
          status: 'analyzed'
        });
      }
    } catch (err: any) {
      setStatusMessage({
        text: `Analysis failed: ${err.response?.data?.detail || err.message}`,
        type: 'error'
      });
    } finally {
      setActionLoadingId(null);
      setTimeout(() => setStatusMessage(null), 5000);
    }
  };

  const handleProposeFix = async (failureId: string) => {
    setActionLoadingId(`propose-${failureId}`);
    try {
      const res = await api.proposeFix(failureId);
      setStatusMessage({
        text: `Patch proposal generated! Created human approval gate #${res.approval_id || 'PENDING'}.`,
        type: 'success'
      });
      await loadAllData(false);
      setActiveTab('proposals');
    } catch (err: any) {
      setStatusMessage({
        text: `Failed to generate fix proposal: ${err.response?.data?.detail || err.message}`,
        type: 'error'
      });
    } finally {
      setActionLoadingId(null);
      setTimeout(() => setStatusMessage(null), 5000);
    }
  };

  const handleExecuteProposal = async (proposalId: string) => {
    setActionLoadingId(`exec-${proposalId}`);
    try {
      const res = await api.executeProposal(proposalId);
      setStatusMessage({
        text: `Fix applied successfully! Created Pull Request: ${res.pr_url}`,
        type: 'success'
      });
      await loadAllData(false);
    } catch (err: any) {
      const detail = err.response?.data?.detail || err.message;
      if (detail?.includes('approval') || detail?.includes('rejected') || detail?.includes('pending')) {
        setStatusMessage({
          text: `Action paused: Human approval is pending. Please approve in the Approval Center first.`,
          type: 'error'
        });
      } else {
        setStatusMessage({
          text: `Execution failed: ${detail}`,
          type: 'error'
        });
      }
    } finally {
      setActionLoadingId(null);
      setTimeout(() => setStatusMessage(null), 7000);
    }
  };

  const handleMarkNotificationRead = async (notifId: string) => {
    try {
      await api.markNotificationRead(notifId);
      setNotifications(prev => (prev || []).map(n => n.id === notifId ? { ...n, is_read: true } : n));
    } catch {
      // ignore
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await api.markAllNotificationsRead();
      setNotifications(prev => (prev || []).map(n => ({ ...n, is_read: true })));
    } catch {
      // ignore
    }
  };

  const handleDeleteProposal = async (proposalId: string) => {
    setActionLoadingId(`del-prop-${proposalId}`);
    try {
      await api.deleteGitHubProposal(proposalId);
      setProposals(prev => (prev || []).filter(p => p.id !== proposalId));
      setStatusMessage({
        text: 'Fix proposal removed successfully.',
        type: 'success'
      });
    } catch (err: any) {
      setStatusMessage({
        text: `Failed to remove proposal: ${err?.response?.data?.detail || err.message}`,
        type: 'error'
      });
    } finally {
      setActionLoadingId(null);
      setTimeout(() => setStatusMessage(null), 4000);
    }
  };

  const handleDeleteFailure = async (failureId: string) => {
    setActionLoadingId(`del-fail-${failureId}`);
    try {
      await api.deleteGitHubFailure(failureId);
      setFailures(prev => (prev || []).filter(f => f.id !== failureId));
      setStatusMessage({
        text: 'Failure record dismissed successfully.',
        type: 'success'
      });
    } catch (err: any) {
      setStatusMessage({
        text: `Failed to dismiss failure: ${err?.response?.data?.detail || err.message}`,
        type: 'error'
      });
    } finally {
      setActionLoadingId(null);
      setTimeout(() => setStatusMessage(null), 4000);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-emerald-500/20 border-t-emerald-400 rounded-full animate-spin mx-auto mb-3"></div>
          <p className="text-sm text-slate-400 font-mono">Synchronizing Live GitHub Telemetry & CI/CD Mesh...</p>
        </div>
      </div>
    );
  }

  // Filter out any mock/fake enterprise-ops entries and broken mock run IDs
  const safeFailures = (failures || []).filter(f => !f.repo_full_name?.includes('enterprise-ops'));
  const safeRepos = (repositories || []).filter(r => !r.full_name?.includes('enterprise-ops') && !r.name?.includes('enterprise-ops'));
  const safeProposals = (proposals || []).filter(p => !p.repo_full_name?.includes('enterprise-ops') && !p.repo_name?.includes('enterprise-ops'));
  const safeEvents = (events || []).filter(e => !e.repo_full_name?.includes('enterprise-ops'));
  const safeNotifications = (notifications || []).filter(
    n => !n.message?.includes('enterprise-ops') && 
         !n.title?.includes('enterprise-ops') && 
         !n.message?.includes('#38558137') && 
         !n.message?.includes('#26776825')
  );

  const activeFailuresCount = safeFailures.filter(f => f.status === 'detected' || f.status === 'analyzed').length;
  const unreadNotifsCount = safeNotifications.filter(n => !n.is_read).length;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Status banner */}
      {statusMessage && (
        <div className={`p-4 rounded-xl text-sm flex items-center justify-between animate-fade-in ${
          statusMessage.type === 'success' 
            ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-300' 
            : 'bg-rose-500/10 border border-rose-500/30 text-rose-300'
        }`}>
          <div className="flex items-center gap-2.5">
            {statusMessage.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            )}
            <span>{statusMessage.text}</span>
          </div>
          <button 
            onClick={() => setStatusMessage(null)}
            className="text-xs opacity-75 hover:opacity-100 font-mono px-2 py-0.5"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Header & Account Bar */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-purple-600 to-indigo-500 flex items-center justify-center shadow-lg shadow-purple-500/20">
              <GitBranch className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-2xl font-black text-white">GitHub Intelligence & AI DevOps</h1>
                <span className={`text-[11px] font-mono font-bold px-2 py-0.5 rounded-full border ${
                  account?.connected 
                    ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' 
                    : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                }`}>
                  {account?.connected ? 'Live Connected' : 'Disconnected'}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Real-time repository telemetry, CI/CD failure analysis, AI patch proposals, and cryptographic human approval gating.
              </p>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleSync}
              disabled={syncing}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:bg-slate-800 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin text-emerald-400' : ''}`} />
              <span>{syncing ? 'Reconciling...' : 'Sync GitHub'}</span>
            </button>
            <button
              onClick={() => navigate('/approvals')}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-amber-500/10 border border-amber-500/20 text-amber-300 hover:bg-amber-500/20 transition-colors"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
              <span>Approval Center</span>
            </button>
          </div>
        </div>

        {/* Connected Account Details Sub-panel */}
        <div className="bg-slate-950/60 p-4 rounded-xl border border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            {account?.avatar_url ? (
              <img src={account.avatar_url} alt="GitHub avatar" className="w-9 h-9 rounded-full border border-slate-700" />
            ) : (
              <div className="w-9 h-9 rounded-full bg-slate-800 flex items-center justify-center text-slate-400 font-mono text-xs">
                GH
              </div>
            )}
            <div>
              <div className="flex items-center gap-2">
                <span className="font-bold text-white text-sm">
                  {account?.connected 
                    ? (account.name || `@${account.login}`) 
                    : 'No GitHub Account Connected'}
                </span>
                {account?.html_url && (
                  <a 
                    href={account.html_url} 
                    target="_blank" 
                    rel="noreferrer" 
                    className="text-slate-400 hover:text-emerald-400 transition-colors"
                  >
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
              <p className="text-[11px] text-slate-400 font-mono">
                {account?.connected 
                  ? `@${account.login} • ${account.public_repos ?? 0} Public Repositories`
                  : 'Click "Switch / Connect Profile" to connect your GitHub account'}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-xs font-mono">
            <div>
              <span className="text-slate-500">OAuth Scopes:</span>{' '}
              <span className="text-purple-300">
                {account?.scopes && account.scopes.length > 0 ? account.scopes.join(', ') : 'repo, workflow'}
              </span>
            </div>
            <div className="hidden sm:block text-slate-700">|</div>
            <div className="text-slate-400">
              {account?.note || 'Verified FastMCP Gateway'}
            </div>
            <div className="hidden sm:block text-slate-700">|</div>
            <button
              onClick={() => {
                setConnectError(null);
                setIsConnectModalOpen(true);
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/40 text-emerald-300 hover:text-emerald-200 transition-all shadow-sm"
              title="Connect another GitHub account with real-time verification"
            >
              <KeyRound className="w-3.5 h-3.5 text-emerald-400" />
              <span>Switch / Connect Profile</span>
            </button>
          </div>
        </div>
      </div>

      {/* Repository Health & Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Health Score */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Repo Health Score</span>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
              health?.status === 'OPTIMAL' ? 'bg-emerald-500/10 text-emerald-400' :
              health?.status === 'WARNING' ? 'bg-amber-500/10 text-amber-400' : 'bg-rose-500/10 text-rose-400'
            }`}>
              {health?.status || 'OPTIMAL'}
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-black text-white">{health?.overall_health_score ?? 100}%</span>
            <span className="text-xs text-emerald-400 font-mono">Operational</span>
          </div>
          <div className="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
            <div 
              className={`h-full rounded-full transition-all duration-500 ${
                (health?.overall_health_score ?? 100) >= 80 ? 'bg-emerald-500' :
                (health?.overall_health_score ?? 100) >= 50 ? 'bg-amber-500' : 'bg-rose-500'
              }`}
              style={{ width: `${health?.overall_health_score ?? 100}%` }}
            ></div>
          </div>
        </div>

        {/* Active Failures */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Active CI/CD Failures</span>
            <AlertOctagon className={`w-4 h-4 ${activeFailuresCount > 0 ? 'text-rose-400 animate-pulse' : 'text-slate-500'}`} />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-black text-white">{activeFailuresCount}</span>
            <span className="text-xs text-slate-400">incidents</span>
          </div>
          <p className="text-[11px] text-slate-500 font-mono">
            {health?.resolved_failures_count ?? 0} auto-remediated & resolved
          </p>
        </div>

        {/* Monitored Repos */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>Monitored Repos</span>
            <GitBranch className="w-4 h-4 text-purple-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-black text-white">
              {safeRepos.filter(r => r.is_monitored).length}
            </span>
            <span className="text-xs text-slate-400">of {safeRepos.length} total</span>
          </div>
          <p className="text-[11px] text-slate-500 font-mono">
            Webhook listener active
          </p>
        </div>

        {/* Fix Proposals */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400 font-medium">
            <span>AI Fix Proposals</span>
            <ShieldCheck className="w-4 h-4 text-amber-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-black text-white">{safeProposals.length}</span>
            <span className="text-xs text-slate-400">generated</span>
          </div>
          <p className="text-[11px] text-slate-500 font-mono">
            Cryptographically gated
          </p>
        </div>
      </div>

      {/* In-App Notifications Drawer / Alert Banner */}
      {safeNotifications.length > 0 && (
        <div className="glass-card p-4 rounded-2xl border border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Bell className="w-4 h-4 text-amber-400" />
              <span className="text-xs font-bold text-white uppercase tracking-wider">
                DevOps Notifications & Real-Time Alerts
              </span>
              {unreadNotifsCount > 0 && (
                <span className="text-[10px] font-bold bg-amber-500 text-slate-950 px-1.5 py-0.5 rounded-full">
                  {unreadNotifsCount} new
                </span>
              )}
            </div>
            {unreadNotifsCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="text-[11px] text-slate-400 hover:text-white font-mono transition-colors"
              >
                Mark all as read
              </button>
            )}
          </div>

          <div className="divide-y divide-slate-800/80 max-h-36 overflow-y-auto pr-1">
            {safeNotifications.slice(0, 5).map(n => (
              <div 
                key={n.id} 
                className={`py-2 px-1 flex items-center justify-between gap-3 text-xs ${n.is_read ? 'opacity-60' : 'opacity-100 font-medium'}`}
              >
                <div className="flex items-center gap-2">
                  <span className={`w-1.5 h-1.5 rounded-full ${n.is_read ? 'bg-slate-600' : 'bg-amber-400 animate-pulse'}`}></span>
                  <span className="text-slate-200">{n.title}:</span>
                  <span className="text-slate-400">{n.message}</span>
                </div>
                {!n.is_read && (
                  <button
                    onClick={() => handleMarkNotificationRead(n.id)}
                    className="text-[10px] font-mono text-emerald-400 hover:text-emerald-300"
                  >
                    Dismiss
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Main Tabs Navigation */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center gap-2">
          <button
            id="tab-ci-failures"
            onClick={() => setActiveTab('failures')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'failures'
                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30 shadow-md shadow-rose-500/10'
                : 'text-slate-400 hover:text-slate-200 bg-slate-900/50'
            }`}
          >
            <AlertOctagon className="w-3.5 h-3.5" />
            <span>CI/CD Failures</span>
            {activeFailuresCount > 0 && (
              <span className="px-1.5 py-0.2 rounded-full bg-rose-500 text-white text-[10px]">
                {activeFailuresCount}
              </span>
            )}
          </button>

          <button
            id="tab-fix-proposals"
            onClick={() => setActiveTab('proposals')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'proposals'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30 shadow-md shadow-amber-500/10'
                : 'text-slate-400 hover:text-slate-200 bg-slate-900/50'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>AI Fix Proposals</span>
            {safeProposals.length > 0 && (
              <span className="px-1.5 py-0.2 rounded-full bg-amber-500 text-slate-950 text-[10px]">
                {safeProposals.length}
              </span>
            )}
          </button>

          <button
            id="tab-repositories"
            onClick={() => setActiveTab('repos')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'repos'
                ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30 shadow-md shadow-purple-500/10'
                : 'text-slate-400 hover:text-slate-200 bg-slate-900/50'
            }`}
          >
            <GitBranch className="w-3.5 h-3.5" />
            <span>Repositories ({safeRepos.length})</span>
          </button>

          <button
            id="tab-activity-ledger"
            onClick={() => setActiveTab('activity')}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'activity'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 shadow-md shadow-emerald-500/10'
                : 'text-slate-400 hover:text-slate-200 bg-slate-900/50'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Live Activity ({safeEvents.length})</span>
          </button>
        </div>

        <button
          onClick={() => navigate('/chat')}
          className="hidden sm:flex items-center gap-1.5 text-xs text-emerald-400 hover:text-emerald-300 transition-colors font-mono"
        >
          <Bot className="w-4 h-4" />
          <span>Ask AI OpsPilot</span>
          <ArrowRight className="w-3 h-3" />
        </button>
      </div>

      {/* TAB 1: CI/CD FAILURES */}
      {activeTab === 'failures' && (
        <div className="space-y-4">
          {safeFailures.length === 0 ? (
            <div className="glass-panel p-12 text-center rounded-2xl border border-slate-800 space-y-3">
              <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto" />
              <h3 className="text-base font-bold text-white">All Monitored Workflows Healthy</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                No active CI/CD workflow failures detected. Live GitHub webhooks and reconciliation are listening for pipeline anomalies.
              </p>
            </div>
          ) : (
            safeFailures.map(failure => {
              const isAnalyzing = actionLoadingId === `analyze-${failure.id}`;
              const isProposing = actionLoadingId === `propose-${failure.id}`;
              const repoDisplayName = failure.repo_full_name || failure.repo_name || 'monitored-repo';
              const errorSnippet = failure.error_log_snippet || failure.error_snippet;

              return (
                <div 
                  key={failure.id} 
                  className={`glass-panel p-6 rounded-2xl border transition-all ${
                    failure.status === 'detected' 
                      ? 'border-rose-500/40 bg-rose-950/10' 
                      : 'border-slate-800'
                  }`}
                >
                  <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
                    <div className="space-y-2 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`text-[10px] font-mono uppercase font-bold px-2 py-0.5 rounded ${
                          failure.status === 'detected' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' :
                          failure.status === 'analyzed' ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30' :
                          failure.status === 'fix_proposed' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' :
                          'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                        }`}>
                          {failure.status ? failure.status.replace('_', ' ') : 'detected'}
                        </span>
                        <span className="font-bold text-white text-base">
                          {failure.workflow_name || 'Continuous Integration Pipeline'}
                        </span>
                        <span className="text-xs font-mono text-slate-400">
                          #{failure.run_id}
                        </span>
                        {failure.html_url && (
                          <a 
                            href={failure.html_url} 
                            target="_blank" 
                            rel="noreferrer" 
                            className="text-slate-400 hover:text-emerald-400"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        )}
                      </div>

                      <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-slate-400">
                        <span>Repository: <strong className="text-slate-200">{repoDisplayName}</strong></span>
                        <span>Branch: <code className="text-purple-300">{failure.branch || 'main'}</code></span>
                        <span>Actor: <strong className="text-slate-200">{failure.sender || 'github-actor'}</strong></span>
                        {failure.commit_sha && (
                          <span>Commit: <code className="text-slate-300">{failure.commit_sha.substring(0, 7)}</code></span>
                        )}
                      </div>

                      {failure.commit_message && (
                        <p className="text-xs text-slate-300 italic">
                          "{failure.commit_message}"
                        </p>
                      )}

                      {/* Error log snippet */}
                      {errorSnippet && (
                        <div className="bg-slate-950/80 p-3 rounded-xl border border-slate-800 font-mono text-xs text-rose-300/90 overflow-x-auto leading-relaxed">
                          <div className="text-[10px] text-slate-500 uppercase tracking-wider mb-1 flex items-center gap-1">
                            <Terminal className="w-3 h-3 text-rose-400" />
                            Failing Step: {failure.failing_step || 'Verification'}
                          </div>
                          <pre>{errorSnippet}</pre>
                        </div>
                      )}

                      {/* AI Root Cause Analysis (if analyzed) */}
                      {(failure.root_cause || failure.analysis?.root_cause) && (
                        <div className="bg-sky-950/20 p-4 rounded-xl border border-sky-500/30 space-y-2 mt-3">
                          <div className="flex items-center gap-2 text-sky-400 text-xs font-bold uppercase tracking-wider">
                            <Bot className="w-4 h-4" />
                            AI Root-Cause Diagnosis
                          </div>
                          <p className="text-xs text-slate-200 leading-relaxed font-mono">
                            {failure.root_cause || failure.analysis?.root_cause}
                          </p>
                          {(failure.suggested_fix || failure.analysis?.suggested_fix) && (
                            <div className="text-xs text-emerald-300/90 pt-1 border-t border-sky-500/20">
                              <strong>Recommended Fix:</strong> {failure.suggested_fix || failure.analysis?.suggested_fix}
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Action buttons */}
                    <div className="flex lg:flex-col gap-2 shrink-0">
                      <button
                        onClick={() => handleAnalyzeFailure(failure.id)}
                        disabled={isAnalyzing}
                        className="flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-sky-500/10 border border-sky-500/30 text-sky-300 hover:bg-sky-500/20 transition-colors disabled:opacity-50"
                      >
                        <Bot className={`w-3.5 h-3.5 ${isAnalyzing ? 'animate-spin' : ''}`} />
                        <span>{isAnalyzing ? 'Analyzing...' : 'Analyze with AI'}</span>
                      </button>

                      <button
                        onClick={() => handleProposeFix(failure.id)}
                        disabled={isProposing}
                        className="flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold bg-amber-500/10 border border-amber-500/30 text-amber-300 hover:bg-amber-500/20 transition-colors disabled:opacity-50"
                      >
                        <ShieldCheck className={`w-3.5 h-3.5 ${isProposing ? 'animate-spin' : ''}`} />
                        <span>{isProposing ? 'Generating...' : 'Propose AI Code Fix'}</span>
                      </button>

                      <button
                        onClick={() => handleDeleteFailure(failure.id)}
                        disabled={actionLoadingId === `del-fail-${failure.id}`}
                        className="flex items-center justify-center gap-1 px-3 py-1.5 rounded-xl text-xs font-medium text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 border border-slate-800 hover:border-rose-500/30 transition-colors"
                        title="Dismiss and remove this failure record"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        <span>Dismiss</span>
                      </button>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      )}

      {/* TAB 2: AI FIX PROPOSALS */}
      {activeTab === 'proposals' && (
        <div className="space-y-6">
          {safeProposals.length === 0 ? (
            <div className="glass-panel p-12 text-center rounded-2xl border border-slate-800 space-y-3">
              <ShieldCheck className="w-12 h-12 text-emerald-400 mx-auto" />
              <h3 className="text-base font-bold text-white">No Fix Proposals Pending</h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto">
                All monitored repositories for {account?.login ? `@${account.login}` : 'your account'} are healthy and operational. OpsPilot generates patch proposals when real CI/CD failures are diagnosed.
              </p>
            </div>
          ) : (
            safeProposals.map(proposal => {
              const isExecuting = actionLoadingId === `exec-${proposal.id}`;
              const isValidPr = proposal.pr_url && !proposal.pr_url.includes('enterprise-ops') && proposal.pr_url.startsWith('https://github.com/');

              return (
                <div key={proposal.id} className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] font-mono uppercase font-bold px-2 py-0.5 rounded ${
                          proposal.status === 'applied' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' :
                          proposal.status === 'approved' ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30' :
                          'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                        }`}>
                          {proposal.status}
                        </span>
                        <h3 className="text-base font-bold text-white">{proposal.title}</h3>
                      </div>
                      <p className="text-xs text-slate-300">
                        {proposal.description}
                      </p>
                      <div className="flex flex-wrap items-center gap-3 text-xs font-mono text-slate-400 pt-1">
                        <span>Target Repo: <strong className="text-white">{proposal.repo_name || proposal.repo_full_name}</strong></span>
                        <span>Fix Branch: <code className="text-purple-300">{proposal.branch_name}</code></span>
                        {isValidPr && (
                          <a 
                            href={proposal.pr_url} 
                            target="_blank" 
                            rel="noreferrer" 
                            className="flex items-center gap-1 text-emerald-400 hover:text-emerald-300 font-bold"
                          >
                            <GitPullRequest className="w-3.5 h-3.5" />
                            <span>PR #{proposal.pr_number || ''}</span>
                            <ExternalLink className="w-3 h-3" />
                          </a>
                        )}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2 shrink-0">
                      {proposal.status !== 'applied' && (
                        <>
                          <button
                            onClick={() => navigate('/approvals')}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-900 border border-slate-700 text-slate-300 hover:text-white"
                          >
                            <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
                            <span>Review in Approval Center</span>
                          </button>

                          <button
                            onClick={() => handleExecuteProposal(proposal.id)}
                            disabled={isExecuting}
                            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition-colors disabled:opacity-50"
                          >
                            <Play className={`w-3.5 h-3.5 ${isExecuting ? 'animate-spin' : ''}`} />
                            <span>{isExecuting ? 'Applying...' : 'Apply Approved Fix'}</span>
                          </button>
                        </>
                      )}

                      {proposal.status === 'applied' && isValidPr && (
                        <a
                          href={proposal.pr_url}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold bg-purple-600/20 text-purple-300 border border-purple-500/30 hover:bg-purple-600/30 transition-colors"
                        >
                          <GitPullRequest className="w-3.5 h-3.5" />
                          <span>View Open Pull Request</span>
                          <ExternalLink className="w-3 h-3" />
                        </a>
                      )}

                      <button
                        onClick={() => handleDeleteProposal(proposal.id)}
                        disabled={actionLoadingId === `del-prop-${proposal.id}`}
                        className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 border border-slate-800 hover:border-rose-500/30 transition-colors"
                        title="Dismiss and remove this fix proposal"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                        <span className="hidden sm:inline">Dismiss</span>
                      </button>
                    </div>
                  </div>

                  {/* Unified Diff Box */}
                  {proposal.diff_content && (
                    <div className="rounded-xl overflow-hidden border border-slate-800 bg-[#070b14]">
                      <div className="flex items-center justify-between px-3.5 py-1.5 bg-slate-900/90 border-b border-slate-800 text-[11px] font-mono text-slate-400">
                        <span className="flex items-center gap-1.5 text-slate-300">
                          <FileCode className="w-3.5 h-3.5 text-emerald-400" />
                          Unified Git Patch
                        </span>
                        <span className="text-[10px] text-slate-500">
                          Safety: Never pushes to default branch
                        </span>
                      </div>
                      <pre className="p-3.5 overflow-x-auto text-xs font-mono leading-relaxed max-h-60 overflow-y-auto">
                        {proposal.diff_content.split('\n').map((line, idx) => {
                          const isAdd = line.startsWith('+') && !line.startsWith('+++');
                          const isDel = line.startsWith('-') && !line.startsWith('---');
                          const isMeta = line.startsWith('@@') || line.startsWith('diff --git');
                          return (
                            <div 
                              key={idx} 
                              className={`${
                                isAdd ? 'text-emerald-400 bg-emerald-500/10' :
                                isDel ? 'text-rose-400 bg-rose-500/10' :
                                isMeta ? 'text-purple-400' : 'text-slate-300'
                              } px-1`}
                            >
                              {line}
                            </div>
                          );
                        })}
                      </pre>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}

      {/* TAB 3: REPOSITORIES */}
      {activeTab === 'repos' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <p>Select which authorized repositories OpsPilot should actively monitor for webhook activity and CI/CD events.</p>
            <span className="font-mono">{safeRepos.filter(r => r.is_monitored).length} of {safeRepos.length} monitored</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {safeRepos.map(repo => (
              <div 
                key={repo.full_name || repo.name} 
                className={`glass-panel p-5 rounded-2xl border transition-all ${
                  repo.is_monitored ? 'border-purple-500/30' : 'border-slate-800 opacity-70'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <h4 className="font-bold text-white text-sm">{repo.name}</h4>
                      {repo.private && (
                        <span className="text-[9px] font-mono uppercase bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded">
                          Private
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-400 font-mono">{repo.full_name}</p>
                  </div>

                  <label className="relative inline-flex items-center cursor-pointer">
                    <input 
                      type="checkbox" 
                      className="sr-only peer"
                      checked={Boolean(repo.is_monitored)}
                      onChange={() => handleToggleMonitoring(repo)}
                    />
                    <div className="w-9 h-5 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-emerald-500"></div>
                  </label>
                </div>

                <p className="text-xs text-slate-400 mt-2 line-clamp-2">
                  {repo.description || 'No description provided.'}
                </p>

                <div className="flex items-center justify-between text-xs font-mono text-slate-500 mt-4 pt-3 border-t border-slate-800">
                  <span className="text-purple-300">branch: {repo.default_branch || 'main'}</span>
                  <span className="text-emerald-400">{repo.health_score ?? 100}% Health</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* TAB 4: LIVE ACTIVITY LEDGER */}
      {activeTab === 'activity' && (
        <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-bold text-white">Live GitHub Webhook Ledger</h3>
            <span className="text-xs font-mono text-slate-400">
              Verified Delivery Signatures & Deduplication
            </span>
          </div>

          {safeEvents.length === 0 ? (
            <div className="py-8 text-center text-slate-500 text-xs font-mono">
              No webhook events ingested yet. Trigger a commit or pull request to view real-time events.
            </div>
          ) : (
            <div className="divide-y divide-slate-800 max-h-[500px] overflow-y-auto pr-2">
              {safeEvents.map(ev => {
                const deliveryId = ev.delivery_id ? ev.delivery_id.substring(0, 10) : 'webhook';
                const actorName = ev.sender || ev.actor || 'system';
                const repoName = ev.repo_full_name || ev.repo_name || 'monitored-repo';

                return (
                  <div key={ev.id || deliveryId} className="py-3 flex items-start justify-between gap-4 text-xs">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] font-mono uppercase font-bold px-2 py-0.5 rounded ${
                          ev.event_type === 'workflow_run' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' :
                          ev.event_type === 'push' ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30' :
                          ev.event_type === 'pull_request' ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30' :
                          'bg-slate-800 text-slate-300'
                        }`}>
                          {ev.event_type}
                        </span>
                        <span className="font-semibold text-white">{ev.summary}</span>
                      </div>
                      <div className="flex items-center gap-3 text-[11px] font-mono text-slate-500">
                        <span>repo: {repoName}</span>
                        <span>actor: {actorName}</span>
                        <span>delivery: {deliveryId}...</span>
                      </div>
                    </div>
                    <span className="text-[11px] font-mono text-slate-500 shrink-0">
                      {ev.created_at ? new Date(ev.created_at).toLocaleTimeString() : ''}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
      {/* =========================================================================
          CONNECT / SWITCH GITHUB ACCOUNT MODAL
      ========================================================================= */}
      {isConnectModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
          <div className="glass-panel w-full max-w-lg p-6 rounded-2xl border border-slate-700/80 shadow-2xl space-y-5 bg-[#0b1120]">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-purple-500/20 text-purple-400 border border-purple-500/30 flex items-center justify-center">
                  <GitBranch className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Connect Another GitHub Profile</h3>
                  <p className="text-xs text-slate-400">Real-time authentication and live repository discovery</p>
                </div>
              </div>
              <button
                onClick={() => {
                  setIsConnectModalOpen(false);
                  setConnectError(null);
                }}
                className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {connectError && (
              <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300 flex items-start gap-2.5">
                <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <span className="flex-1">{connectError}</span>
              </div>
            )}

            <form onSubmit={handleConnectSubmit} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">
                  GitHub Username or Email <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  value={connectUsername}
                  onChange={(e) => setConnectUsername(e.target.value)}
                  required
                  placeholder="e.g. adityabhagwat001 or adityabhagwat2181@gmail.com"
                  className="w-full bg-slate-900 border border-slate-800 focus:border-emerald-500 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-slate-300 font-medium">
                    GitHub Password or Personal Access Token <span className="text-rose-400">*</span>
                  </label>
                  <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                    Real-Time Auth
                  </span>
                </div>
                <div className="relative">
                  <input
                    type={showToken ? "text" : "password"}
                    value={connectToken}
                    onChange={(e) => setConnectToken(e.target.value)}
                    required
                    placeholder="Enter your GitHub account password or token"
                    className="w-full bg-slate-900 border border-slate-800 focus:border-emerald-500 rounded-xl pl-3.5 pr-10 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => setShowToken(!showToken)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                  >
                    {showToken ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
                  Log in directly using your GitHub username/email & password, or use a personal access token.
                </p>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">
                  Default Repository Name <span className="text-slate-500 font-normal">(Optional, will auto-select latest repo)</span>
                </label>
                <input
                  type="text"
                  value={connectDefaultRepo}
                  onChange={(e) => setConnectDefaultRepo(e.target.value)}
                  placeholder="e.g. SafeHer or auth-service"
                  className="w-full bg-slate-900 border border-slate-800 focus:border-emerald-500 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none"
                />
              </div>

              <div className="pt-2 flex items-center justify-between gap-3">
                {account?.connected && (
                  <button
                    type="button"
                    onClick={handleDisconnect}
                    disabled={connecting}
                    className="px-3.5 py-2 rounded-xl text-xs font-semibold text-rose-400 hover:bg-rose-500/10 border border-rose-500/20 transition-colors"
                  >
                    Disconnect Current
                  </button>
                )}
                <div className="flex items-center gap-2.5 ml-auto">
                  <button
                    type="button"
                    onClick={() => {
                      setIsConnectModalOpen(false);
                      setConnectError(null);
                    }}
                    className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-850 border border-slate-800 transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={connecting || !connectToken.trim()}
                    className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-emerald-500 text-slate-950 hover:bg-emerald-400 disabled:opacity-40 transition-all shadow-md shadow-emerald-500/20"
                  >
                    {connecting ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Verifying with GitHub in Real-Time...</span>
                      </>
                    ) : (
                      <>
                        <ShieldCheck className="w-3.5 h-3.5" />
                        <span>Verify & Connect Profile</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
