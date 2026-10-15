import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Activity, 
  ShieldAlert, 
  Blocks, 
  Cpu, 
  ArrowRight, 
  Database, 
  GitBranch, 
  Mail, 
  Calendar,
  AlertOctagon,
  Clock,
  Sparkles
} from 'lucide-react';
import { api } from '../services/api';
import { DashboardStats } from '../types';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await api.getDashboardStats();
        setStats(data);
      } catch (err) {
        console.error('Failed to load dashboard stats:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, []);

  const triggerScenario = (promptText: string) => {
    navigate('/chat', { state: { initialPrompt: promptText } });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-emerald-500/20 border-t-emerald-400 rounded-full animate-spin mx-auto mb-3"></div>
          <p className="text-sm text-slate-400 font-mono">Discovering MCP Mesh & Operational State...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Hero Welcome Banner */}
      <div className="relative overflow-hidden rounded-2xl p-8 bg-gradient-to-r from-slate-900 via-slate-900/90 to-emerald-950/40 border border-slate-800 shadow-xl">
        <div className="relative z-10 max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-xs font-semibold text-emerald-400 mb-4">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Autonomous AI Operations Platform</span>
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight sm:text-4xl">
            Live Enterprise Systems. <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-teal-300">FastMCP Mesh.</span> Mandatory Approval.
          </h1>
          <p className="mt-3 text-sm text-slate-300 leading-relaxed">
            OpsPilot acts directly on your operational database, GitHub repositories, company email, and calendar through custom FastMCP servers. Every read is grounded; every write is gated by human approval.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <button
              id="btn-launch-assistant"
              onClick={() => navigate('/chat')}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-sm bg-emerald-500 text-slate-950 hover:bg-emerald-400 shadow-lg shadow-emerald-500/20 transition-all"
            >
              Launch AI Assistant
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              id="btn-view-approvals"
              onClick={() => navigate('/approvals')}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm bg-slate-800/80 text-slate-200 hover:bg-slate-700/80 border border-slate-700 transition-all"
            >
              Approval Center
              {stats && stats.pending_approvals > 0 && (
                <span className="bg-amber-500 text-slate-950 text-xs font-bold px-1.5 py-0.2 rounded-full">
                  {stats.pending_approvals}
                </span>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1 */}
        <div className="glass-panel p-5 rounded-xl border border-slate-800">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Connected Systems</span>
            <Blocks className="w-5 h-5 text-emerald-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-black text-white">{stats?.connected_systems || 4}</span>
            <span className="text-xs text-emerald-400 font-mono">FastMCP Active</span>
          </div>
          <p className="mt-1 text-xs text-slate-400">Postgres, GitHub, Email, Calendar</p>
        </div>

        {/* Metric 2 */}
        <div className="glass-panel p-5 rounded-xl border border-slate-800">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Discovered MCP Tools</span>
            <Cpu className="w-5 h-5 text-sky-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-black text-white">{stats?.total_mcp_tools || 33}</span>
            <span className="text-xs text-sky-400 font-mono">Tools Ready</span>
          </div>
          <p className="mt-1 text-xs text-slate-400">22 Read Tools • 11 Protected Write Tools</p>
        </div>

        {/* Metric 3 */}
        <div className="glass-panel p-5 rounded-xl border border-slate-800">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Pending Approvals</span>
            <ShieldAlert className="w-5 h-5 text-amber-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-black text-white">{stats?.pending_approvals || 0}</span>
            <span className="text-xs text-amber-400 font-mono">Requires Human Gate</span>
          </div>
          <p className="mt-1 text-xs text-slate-400">Write operations waiting for review</p>
        </div>

        {/* Metric 4 */}
        <div className="glass-panel p-5 rounded-xl border border-slate-800">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Active Incidents</span>
            <AlertOctagon className="w-5 h-5 text-rose-400" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-3xl font-black text-white">{stats?.operations?.open_incidents || 0}</span>
            <span className="text-xs text-rose-400 font-mono">
              {stats?.operations?.critical_incidents || 0} Critical
            </span>
          </div>
          <p className="mt-1 text-xs text-slate-400">{stats?.operations?.active_tasks || 0} active remediation tasks</p>
        </div>
      </div>

      {/* Official Master Scenarios Direct Access */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-bold text-white">Official Scenarios Demonstration</h2>
            <p className="text-xs text-slate-400">Launch any of the 6 end-to-end integration scenarios defined in the Master Specification.</p>
          </div>
          <span className="text-xs font-mono text-emerald-400">Verified Grounding</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {/* Scenario A */}
          <div 
            onClick={() => triggerScenario("Show me all open operational incidents from the database.")}
            className="glass-card p-5 rounded-xl border border-slate-800 hover:border-emerald-500/50 hover:bg-slate-800/40 cursor-pointer transition-all group"
          >
            <div className="flex items-center gap-2 text-xs font-bold text-sky-400 mb-2">
              <Database className="w-4 h-4" />
              <span>SCENARIO A — Database Intelligence</span>
            </div>
            <h3 className="text-sm font-semibold text-white group-hover:text-emerald-300 transition-colors">
              "Show me all open operational incidents from the database."
            </h3>
            <p className="mt-2 text-xs text-slate-400">
              Discovers PostgreSQL FastMCP tools, calls list_incidents, returns live incident records with severity tags.
            </p>
            <div className="mt-4 flex items-center text-xs font-semibold text-emerald-400 group-hover:translate-x-1 transition-transform">
              Run Scenario A <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </div>
          </div>

          {/* Scenario B */}
          <div 
            onClick={() => triggerScenario("Check the open issues in my repository and identify the highest-priority problems.")}
            className="glass-card p-5 rounded-xl border border-slate-800 hover:border-purple-500/50 hover:bg-slate-800/40 cursor-pointer transition-all group"
          >
            <div className="flex items-center gap-2 text-xs font-bold text-purple-400 mb-2">
              <GitBranch className="w-4 h-4" />
              <span>SCENARIO B — GitHub Intelligence</span>
            </div>
            <h3 className="text-sm font-semibold text-white group-hover:text-purple-300 transition-colors">
              "Check the open issues in my repository and identify highest-priority problems."
            </h3>
            <p className="mt-2 text-xs text-slate-400">
              Discovers GitHub FastMCP tools, queries live issues and returns grounded priority summary.
            </p>
            <div className="mt-4 flex items-center text-xs font-semibold text-purple-400 group-hover:translate-x-1 transition-transform">
              Run Scenario B <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </div>
          </div>

          {/* Scenario C */}
          <div 
            onClick={() => triggerScenario("Create a GitHub issue for fixing the authentication timeout.")}
            className="glass-card p-5 rounded-xl border border-amber-500/30 hover:border-amber-400 hover:bg-amber-500/5 cursor-pointer transition-all group"
          >
            <div className="flex items-center gap-2 text-xs font-bold text-amber-400 mb-2">
              <ShieldAlert className="w-4 h-4" />
              <span>SCENARIO C — GitHub Write Approval</span>
            </div>
            <h3 className="text-sm font-semibold text-white group-hover:text-amber-300 transition-colors">
              "Create a GitHub issue for fixing the authentication timeout."
            </h3>
            <p className="mt-2 text-xs text-slate-400">
              Drafts issue, PAUSES at human approval boundary, requires approval, and executes only after signature verification.
            </p>
            <div className="mt-4 flex items-center text-xs font-semibold text-amber-400 group-hover:translate-x-1 transition-transform">
              Run Scenario C <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </div>
          </div>

          {/* Scenario D */}
          <div 
            onClick={() => triggerScenario("Find important unread emails related to deployment problems.")}
            className="glass-card p-5 rounded-xl border border-slate-800 hover:border-emerald-500/50 hover:bg-slate-800/40 cursor-pointer transition-all group"
          >
            <div className="flex items-center gap-2 text-xs font-bold text-emerald-400 mb-2">
              <Mail className="w-4 h-4" />
              <span>SCENARIO D — Email Intelligence</span>
            </div>
            <h3 className="text-sm font-semibold text-white group-hover:text-emerald-300 transition-colors">
              "Find important unread emails related to deployment problems."
            </h3>
            <p className="mt-2 text-xs text-slate-400">
              Discovers Productivity FastMCP server, queries unread inbox messages, returns factual summaries.
            </p>
            <div className="mt-4 flex items-center text-xs font-semibold text-emerald-400 group-hover:translate-x-1 transition-transform">
              Run Scenario D <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </div>
          </div>

          {/* Scenario E */}
          <div 
            onClick={() => triggerScenario("Draft an email to the engineering team about the deployment delay.")}
            className="glass-card p-5 rounded-xl border border-amber-500/30 hover:border-amber-400 hover:bg-amber-500/5 cursor-pointer transition-all group"
          >
            <div className="flex items-center gap-2 text-xs font-bold text-amber-400 mb-2">
              <Mail className="w-4 h-4" />
              <span>SCENARIO E — Email Draft & Send Approval</span>
            </div>
            <h3 className="text-sm font-semibold text-white group-hover:text-amber-300 transition-colors">
              "Draft an email to the engineering team about the deployment delay."
            </h3>
            <p className="mt-2 text-xs text-slate-400">
              Generates draft proposal, pauses for review, and requires explicit authorization before delivery.
            </p>
            <div className="mt-4 flex items-center text-xs font-semibold text-amber-400 group-hover:translate-x-1 transition-transform">
              Run Scenario E <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </div>
          </div>

          {/* Scenario F */}
          <div 
            onClick={() => triggerScenario("Schedule a meeting with the development team tomorrow at 3 PM.")}
            className="glass-card p-5 rounded-xl border border-amber-500/30 hover:border-amber-400 hover:bg-amber-500/5 cursor-pointer transition-all group"
          >
            <div className="flex items-center gap-2 text-xs font-bold text-emerald-400 mb-2">
              <Calendar className="w-4 h-4" />
              <span>SCENARIO F — Calendar Scheduling</span>
            </div>
            <h3 className="text-sm font-semibold text-white group-hover:text-emerald-300 transition-colors">
              "Schedule a meeting with the development team tomorrow at 3 PM."
            </h3>
            <p className="mt-2 text-xs text-slate-400">
              Resolves time slot, checks conflict availability, prepares event, and halts for human approval before booking.
            </p>
            <div className="mt-4 flex items-center text-xs font-semibold text-emerald-400 group-hover:translate-x-1 transition-transform">
              Run Scenario F <ArrowRight className="w-3.5 h-3.5 ml-1" />
            </div>
          </div>
        </div>
      </div>

      {/* Recent Audit Trail Snippet */}
      <div className="glass-panel rounded-2xl border border-slate-800 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-emerald-400" />
            <h3 className="text-sm font-bold text-white">Live Enterprise Audit Log</h3>
          </div>
          <button 
            onClick={() => navigate('/audit')}
            className="text-xs text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
          >
            View Full Audit Trail <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <div className="divide-y divide-slate-800">
          {stats?.recent_activity?.length ? (
            stats.recent_activity.slice(0, 5).map((act) => (
              <div key={act.id} className="py-3 flex items-center justify-between text-xs">
                <div className="flex items-center gap-3">
                  <span className={`px-2 py-0.5 rounded font-mono font-bold text-[10px] uppercase ${
                    act.action_type === 'WRITE_EXECUTED' ? 'bg-emerald-500/20 text-emerald-400' :
                    act.action_type === 'WRITE_PROPOSED' ? 'bg-amber-500/20 text-amber-400' :
                    'bg-slate-800 text-slate-300'
                  }`}>
                    {act.action_type}
                  </span>
                  <span className="font-semibold text-slate-200">{act.tool_name}</span>
                  <span className="text-slate-400 hidden sm:inline">{act.summary}</span>
                </div>
                <div className="flex items-center gap-2 text-slate-500 font-mono">
                  <Clock className="w-3 h-3" />
                  <span>{new Date(act.created_at).toLocaleTimeString()}</span>
                </div>
              </div>
            ))
          ) : (
            <p className="text-xs text-slate-400 py-3">No activity logged yet.</p>
          )}
        </div>
      </div>
    </div>
  );
};
