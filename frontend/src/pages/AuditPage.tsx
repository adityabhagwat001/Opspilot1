import React, { useState, useEffect } from 'react';
import { 
  Search, 
  ChevronDown, 
  ChevronUp, 
  RefreshCw 
} from 'lucide-react';
import { api } from '../services/api';
import { AuditLog } from '../types';

export const AuditPage: React.FC = () => {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [systemFilter, setSystemFilter] = useState('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const data = await api.getAuditLogs(systemFilter === 'all' ? undefined : systemFilter);
      setLogs(data);
    } catch (err) {
      console.error('Failed to load audit logs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    const loadLogs = async () => {
      try {
        const data = await api.getAuditLogs(systemFilter === 'all' ? undefined : systemFilter);
        if (isMounted) setLogs(data);
      } catch (err) {
        console.error('Failed to load audit logs:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    void loadLogs();
    return () => {
      isMounted = false;
    };
  }, [systemFilter]);

  const filteredLogs = logs.filter((l) => {
    const q = search.toLowerCase();
    return (
      l.tool_name.toLowerCase().includes(q) ||
      l.result_summary.toLowerCase().includes(q) ||
      l.action_type.toLowerCase().includes(q)
    );
  });

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-white">Enterprise Audit Trail</h1>
          <p className="text-xs text-slate-400 mt-1">
            Tamper-evident log of all tool invocations, proposed actions, approvals, and execution outcomes.
          </p>
        </div>

        <button
          onClick={fetchLogs}
          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-slate-900 border border-slate-800 text-slate-300 hover:text-white transition-colors self-start sm:self-auto"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by tool name, summary, or action type..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-slate-900 border border-slate-800 focus:border-emerald-500 rounded-xl pl-10 pr-4 py-2 text-xs text-white placeholder-slate-500 focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-1.5 w-full sm:w-auto overflow-x-auto no-scrollbar">
          {['all', 'postgresql', 'github', 'email', 'calendar'].map((sys) => (
            <button
              key={sys}
              onClick={() => setSystemFilter(sys)}
              className={`text-[11px] font-mono uppercase px-2.5 py-1.5 rounded-lg border transition-all ${
                systemFilter === sys
                  ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300'
                  : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-300'
              }`}
            >
              {sys}
            </button>
          ))}
        </div>
      </div>

      {/* Logs Table / Cards */}
      <div className="glass-panel rounded-2xl border border-slate-800 overflow-hidden">
        {loading ? (
          <div className="text-center py-12">
            <div className="w-8 h-8 border-4 border-emerald-500/20 border-t-emerald-400 rounded-full animate-spin mx-auto mb-2"></div>
            <p className="text-xs text-slate-400 font-mono">Fetching audit records...</p>
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="text-center py-12 text-slate-400 text-xs font-mono">
            No audit records found matching criteria.
          </div>
        ) : (
          <div className="divide-y divide-slate-800">
            {filteredLogs.map((log) => {
              const isExpanded = expandedId === log.id;
              return (
                <div key={log.id} className="p-4 hover:bg-slate-800/30 transition-colors">
                  <div 
                    className="flex items-start justify-between gap-4 cursor-pointer"
                    onClick={() => setExpandedId(isExpanded ? null : log.id)}
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase ${
                          log.action_type === 'WRITE_EXECUTED' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                          log.action_type === 'WRITE_PROPOSED' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                          log.action_type === 'APPROVAL_REJECTED' ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30' :
                          'bg-slate-800 text-slate-300'
                        }`}>
                          {log.action_type}
                        </span>
                        <span className="text-xs font-mono font-bold text-white">
                          {log.tool_name}
                        </span>
                        <span className="text-[10px] font-mono uppercase bg-slate-900 px-1.5 py-0.5 rounded text-slate-400">
                          {log.target_system}
                        </span>
                      </div>
                      <p className="text-xs text-slate-300">{log.result_summary}</p>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      <div className="text-right text-[11px] text-slate-500 font-mono">
                        <div>{new Date(log.created_at).toLocaleDateString()}</div>
                        <div>{new Date(log.created_at).toLocaleTimeString()}</div>
                      </div>
                      {isExpanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="mt-3 pt-3 border-t border-slate-800/80 space-y-2">
                      <div className="text-[11px] font-mono text-slate-400">
                        Audit ID: <span className="text-slate-200">{log.id}</span>
                        {log.approval_id && (
                          <span className="ml-3">Approval ID: <span className="text-amber-400">{log.approval_id}</span></span>
                        )}
                      </div>
                      <div>
                        <div className="text-[11px] font-semibold text-slate-400 mb-1">Invocated Parameters:</div>
                        <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-[11px] font-mono text-emerald-300 overflow-x-auto">
                          {JSON.stringify(log.parameters, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
