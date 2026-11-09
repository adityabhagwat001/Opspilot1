import React, { useState, useEffect } from 'react';
import { 
  Building2, 
  Users, 
  UserPlus, 
  Mail, 
  ShieldAlert, 
  ShieldCheck, 
  Trash2, 
  Clock, 
  CheckCircle2, 
  AlertCircle, 
  Copy, 
  Check, 
  Globe, 
  Briefcase, 
  RefreshCw,
  ArrowRightLeft
} from 'lucide-react';
import { api } from '../services/api';
import { User, CompanyDetails, CompanyMember, WorkspaceInvitationItem, UserWorkspace } from '../types';

interface CompanyManagementPageProps {
  currentUser: User;
}

export const CompanyManagementPage: React.FC<CompanyManagementPageProps> = ({ currentUser }) => {
  const [company, setCompany] = useState<CompanyDetails | null>(null);
  const [members, setMembers] = useState<CompanyMember[]>([]);
  const [invitations, setInvitations] = useState<WorkspaceInvitationItem[]>([]);
  const [workspaces, setWorkspaces] = useState<UserWorkspace[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  
  // Invite form state
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState<'operator' | 'admin'>('operator');
  const [inviteSuccessMsg, setInviteSuccessMsg] = useState<string | null>(null);
  const [generatedInviteUrl, setGeneratedInviteUrl] = useState<string | null>(null);
  const [copiedUrl, setCopiedUrl] = useState(false);

  // Status/Feedback messages
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const [compRes, memsRes, invsRes, wsRes] = await Promise.all([
        api.getCompanyDetails(),
        api.getCompanyMembers(),
        api.getCompanyInvitations(),
        api.getUserWorkspaces()
      ]);
      setCompany(compRes);
      setMembers(memsRes);
      setInvitations(invsRes);
      setWorkspaces(wsRes);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to load organization data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchData();
  }, []);

  const handleSendInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail.trim()) return;

    setActionLoading(true);
    setInviteSuccessMsg(null);
    setGeneratedInviteUrl(null);
    setErrorMsg(null);

    try {
      const res = await api.inviteEmployee(inviteEmail.trim(), inviteRole);
      setInviteSuccessMsg(`Invitation dispatched to ${inviteEmail.trim()}`);
      if (res.invite_url) {
        setGeneratedInviteUrl(res.invite_url);
      }
      setInviteEmail('');
      // Refresh members & invites
      const [memsRes, invsRes, compRes] = await Promise.all([
        api.getCompanyMembers(),
        api.getCompanyInvitations(),
        api.getCompanyDetails()
      ]);
      setMembers(memsRes);
      setInvitations(invsRes);
      setCompany(compRes);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to send invitation.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRoleChange = async (memberId: string, newRole: string) => {
    setActionLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      await api.updateMemberRole(memberId, newRole);
      setSuccessMsg('Employee role updated successfully.');
      const mems = await api.getCompanyMembers();
      setMembers(mems);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to update employee role.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRemoveMember = async (memberId: string, memberName: string) => {
    if (!window.confirm(`Are you sure you want to remove ${memberName} from this organization?`)) {
      return;
    }

    setActionLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      await api.removeMember(memberId);
      setSuccessMsg(`Employee ${memberName} has been removed.`);
      const [memsRes, compRes] = await Promise.all([
        api.getCompanyMembers(),
        api.getCompanyDetails()
      ]);
      setMembers(memsRes);
      setCompany(compRes);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to remove employee.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRevokeInvitation = async (invitationId: string) => {
    setActionLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      await api.revokeInvitation(invitationId);
      setSuccessMsg('Invitation revoked successfully.');
      const [invsRes, compRes] = await Promise.all([
        api.getCompanyInvitations(),
        api.getCompanyDetails()
      ]);
      setInvitations(invsRes);
      setCompany(compRes);
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to revoke invitation.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleSwitchWorkspace = async (workspaceId: string) => {
    setActionLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.switchWorkspace(workspaceId);
      if (res.access_token) {
        localStorage.setItem('opspilot_token', res.access_token);
        window.location.reload();
      }
    } catch (err: any) {
      setErrorMsg(err.response?.data?.detail || err.message || 'Failed to switch workspace context.');
      setActionLoading(false);
    }
  };

  const handleCopyInviteUrl = () => {
    if (!generatedInviteUrl) return;
    navigator.clipboard.writeText(generatedInviteUrl);
    setCopiedUrl(true);
    setTimeout(() => setCopiedUrl(false), 3000);
  };

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 flex justify-center items-center">
        <div className="w-8 h-8 border-4 border-emerald-500/20 border-t-emerald-400 rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
              <Building2 className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                {company?.name || 'Company Management'}
                <span className="text-xs font-mono uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                  {company?.status || 'Active'}
                </span>
              </h1>
              <p className="text-sm text-slate-400">
                Manage organization employees, invitations, role assignments, and workspace security boundaries.
              </p>
            </div>
          </div>
        </div>

        <button
          onClick={fetchData}
          disabled={loading || actionLoading}
          className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-900 border border-slate-800 text-xs font-medium text-slate-300 hover:bg-slate-800 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${actionLoading ? 'animate-spin' : ''}`} />
          Refresh Data
        </button>
      </div>

      {/* Global Alerts */}
      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-start gap-3 text-rose-300 text-sm">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div className="flex-1">{errorMsg}</div>
          <button onClick={() => setErrorMsg(null)} className="text-rose-400 hover:text-rose-200">×</button>
        </div>
      )}

      {successMsg && (
        <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-start gap-3 text-emerald-300 text-sm">
          <CheckCircle2 className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div className="flex-1">{successMsg}</div>
          <button onClick={() => setSuccessMsg(null)} className="text-emerald-400 hover:text-emerald-200">×</button>
        </div>
      )}

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-[#0b1120] border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs uppercase font-medium tracking-wider">Total Members</span>
            <Users className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold text-white">{company?.member_count || members.length}</p>
          <p className="text-xs text-slate-500 mt-1">Active team operators & admins</p>
        </div>

        <div className="bg-[#0b1120] border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs uppercase font-medium tracking-wider">Pending Invites</span>
            <Mail className="w-4 h-4 text-amber-400" />
          </div>
          <p className="text-2xl font-bold text-white">{company?.pending_invites_count ?? invitations.length}</p>
          <p className="text-xs text-slate-500 mt-1">Awaiting employee activation</p>
        </div>

        <div className="bg-[#0b1120] border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs uppercase font-medium tracking-wider">Industry Domain</span>
            <Briefcase className="w-4 h-4 text-sky-400" />
          </div>
          <p className="text-base font-semibold text-white truncate">{company?.industry || 'Technology & Cloud'}</p>
          <p className="text-xs text-slate-500 mt-1">Workspace classification</p>
        </div>

        <div className="bg-[#0b1120] border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs uppercase font-medium tracking-wider">Website</span>
            <Globe className="w-4 h-4 text-indigo-400" />
          </div>
          <p className="text-base font-semibold text-white truncate">{company?.website || 'internal.company.corp'}</p>
          <p className="text-xs text-slate-500 mt-1">Verified company portal</p>
        </div>
      </div>

      {/* Multi-Tenant Switcher (if user belongs to multiple organizations) */}
      {workspaces.length > 1 && (
        <div className="bg-[#0b1120] border border-slate-800 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <ArrowRightLeft className="w-4 h-4 text-sky-400" />
            <h3 className="text-sm font-semibold text-slate-200">Switch Organization Workspace</h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {workspaces.map((ws) => (
              <div 
                key={ws.id}
                className={`p-3 rounded-lg border flex items-center justify-between transition-all ${
                  ws.id === company?.id 
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-white' 
                    : 'bg-slate-900/60 border-slate-800 hover:border-slate-700 text-slate-300'
                }`}
              >
                <div>
                  <p className="text-sm font-medium">{ws.name}</p>
                  <p className="text-xs text-slate-400 capitalize">Role: {ws.role}</p>
                </div>
                {ws.id !== company?.id && (
                  <button
                    onClick={() => handleSwitchWorkspace(ws.id)}
                    disabled={actionLoading}
                    className="px-2.5 py-1 text-xs font-semibold rounded bg-sky-500/20 text-sky-300 border border-sky-500/30 hover:bg-sky-500/30 transition-colors"
                  >
                    Switch
                  </button>
                )}
                {ws.id === company?.id && (
                  <span className="text-xs font-mono font-semibold text-emerald-400">Current</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Invite Employee Section */}
      <div className="bg-[#0b1120] border border-slate-800 rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <UserPlus className="w-5 h-5 text-emerald-400" />
          <h2 className="text-lg font-bold text-white">Invite New Team Member</h2>
        </div>
        <p className="text-xs text-slate-400 mb-6">
          Send an invitation link to onboard an engineer or administrator into this organization workspace.
        </p>

        <form onSubmit={handleSendInvite} className="grid grid-cols-1 md:grid-cols-12 gap-4">
          <div className="md:col-span-6">
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Employee Email Address
            </label>
            <input
              type="email"
              required
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="engineer@company.com"
              className="w-full px-3.5 py-2.5 bg-slate-900 border border-slate-800 rounded-lg text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />
          </div>

          <div className="md:col-span-4">
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              Assigned Role
            </label>
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value as 'operator' | 'admin')}
              className="w-full px-3.5 py-2.5 bg-slate-900 border border-slate-800 rounded-lg text-sm text-slate-100 focus:outline-none focus:border-emerald-500"
            >
              <option value="operator">DevOps Operator (Propose, Investigate, Chat)</option>
              <option value="admin">Enterprise Administrator (Manage, Approve, Audit)</option>
            </select>
          </div>

          <div className="md:col-span-2 flex items-end">
            <button
              type="submit"
              disabled={actionLoading || !inviteEmail.trim()}
              className="w-full py-2.5 px-4 bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-slate-950 font-semibold rounded-lg text-sm transition-colors flex items-center justify-center gap-2"
            >
              <UserPlus className="w-4 h-4" />
              <span>Send Invite</span>
            </button>
          </div>
        </form>

        {inviteSuccessMsg && (
          <div className="mt-4 p-3.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-xs">
            <p className="font-semibold">{inviteSuccessMsg}</p>
            {generatedInviteUrl && (
              <div className="mt-2 flex items-center gap-2 bg-slate-950 p-2 rounded border border-slate-800 font-mono text-[11px] text-slate-300">
                <span className="truncate flex-1">{generatedInviteUrl}</span>
                <button
                  onClick={handleCopyInviteUrl}
                  className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 flex items-center gap-1 flex-shrink-0"
                >
                  {copiedUrl ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  <span>{copiedUrl ? 'Copied' : 'Copy Link'}</span>
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Enrolled Team Members Table */}
      <div className="bg-[#0b1120] border border-slate-800 rounded-xl overflow-hidden">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users className="w-5 h-5 text-emerald-400" />
            <h2 className="text-base font-bold text-white">Active Team Members</h2>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            {members.length} {members.length === 1 ? 'member' : 'members'} enrolled
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-900/60 text-xs uppercase text-slate-400 font-mono">
              <tr>
                <th className="py-3 px-4">Employee</th>
                <th className="py-3 px-4">Role</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Account Type</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {members.map((mem) => {
                const isCurrentUser = mem.user_id === currentUser.id;
                return (
                  <tr key={mem.member_id} className="hover:bg-slate-800/20 transition-colors">
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center font-bold text-xs text-emerald-400">
                          {mem.full_name ? mem.full_name.charAt(0).toUpperCase() : 'U'}
                        </div>
                        <div>
                          <p className="font-medium text-slate-200 flex items-center gap-1.5">
                            {mem.full_name}
                            {isCurrentUser && (
                              <span className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.2 rounded font-mono">You</span>
                            )}
                          </p>
                          <p className="text-xs text-slate-400 font-mono">{mem.email}</p>
                        </div>
                      </div>
                    </td>

                    <td className="py-3.5 px-4">
                      <select
                        value={mem.role}
                        onChange={(e) => handleRoleChange(mem.member_id, e.target.value)}
                        disabled={actionLoading}
                        className={`text-xs font-bold uppercase rounded px-2.5 py-1 font-mono focus:outline-none border ${
                          mem.role === 'admin'
                            ? 'bg-amber-500/10 text-amber-300 border-amber-500/30'
                            : 'bg-sky-500/10 text-sky-300 border-sky-500/30'
                        }`}
                      >
                        <option value="operator" className="bg-slate-900 text-slate-200">DevOps Operator</option>
                        <option value="admin" className="bg-slate-900 text-slate-200">Enterprise Admin</option>
                      </select>
                    </td>

                    <td className="py-3.5 px-4">
                      <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-400">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
                        Active
                      </span>
                    </td>

                    <td className="py-3.5 px-4 text-xs font-mono text-slate-400 capitalize">
                      {mem.account_type?.replace('_', ' ') || 'Company'}
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => handleRemoveMember(mem.member_id, mem.full_name)}
                        disabled={actionLoading}
                        title="Remove member"
                        className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pending Invitations Table */}
      {invitations.length > 0 && (
        <div className="bg-[#0b1120] border border-slate-800 rounded-xl overflow-hidden">
          <div className="p-5 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-amber-400" />
              <h2 className="text-base font-bold text-white">Pending Invitations</h2>
            </div>
            <span className="text-xs text-slate-400 font-mono">
              {invitations.length} awaiting response
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-900/60 text-xs uppercase text-slate-400 font-mono">
                <tr>
                  <th className="py-3 px-4">Invited Email</th>
                  <th className="py-3 px-4">Assigned Role</th>
                  <th className="py-3 px-4">Date Sent</th>
                  <th className="py-3 px-4">Expires</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {invitations.map((inv) => (
                  <tr key={inv.id} className="hover:bg-slate-800/20 transition-colors">
                    <td className="py-3.5 px-4 font-mono text-xs text-slate-200">
                      {inv.email}
                    </td>
                    <td className="py-3.5 px-4">
                      <span className={`text-[10px] font-bold uppercase rounded px-2 py-0.5 font-mono ${
                        inv.role === 'admin'
                          ? 'bg-amber-500/10 text-amber-300 border border-amber-500/30'
                          : 'bg-sky-500/10 text-sky-300 border border-sky-500/30'
                      }`}>
                        {inv.role}
                      </span>
                    </td>
                    <td className="py-3.5 px-4 text-xs text-slate-400">
                      {new Date(inv.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3.5 px-4 text-xs text-slate-400">
                      {new Date(inv.expires_at).toLocaleDateString()}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <button
                        onClick={() => handleRevokeInvitation(inv.id)}
                        disabled={actionLoading}
                        className="text-xs font-semibold text-rose-400 hover:text-rose-300 px-2.5 py-1 rounded bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 transition-colors"
                      >
                        Revoke
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

