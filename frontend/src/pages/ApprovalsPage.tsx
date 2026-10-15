import React, { useState, useEffect } from 'react';
import { ShieldCheck, RefreshCw } from 'lucide-react';
import { api } from '../services/api';
import { ApprovalCard } from '../components/ApprovalCard';
import { ApprovalRequest } from '../types';

export const ApprovalsPage: React.FC = () => {
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'pending' | 'all'>('pending');
  const [systemFilter, setSystemFilter] = useState<string>('all');

  const fetchApprovals = async () => {
    try {
      setLoading(true);
      const data = await api.getApprovals();
      setApprovals(data);
    } catch (err) {
      console.error('Failed to fetch approvals:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    const loadData = async () => {
      try {
        const data = await api.getApprovals();
        if (isMounted) setApprovals(data);
      } catch (err) {
        console.error('Failed to fetch approvals:', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    void loadData();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleApprove = async (id: string) => {
    setLoading(true);
    await api.approveAction(id);
    await fetchApprovals();
  };

  const handleReject = async (id: string, reason?: string) => {
    setLoading(true);
    await api.rejectAction(id, reason);
    await fetchApprovals();
  };

  const filteredApprovals = approvals.filter((a) => {
    const matchesTab = activeTab === 'all' || a.approval_status === 'pending';
    const matchesSystem = systemFilter === 'all' || a.target_system.toLowerCase() === systemFilter.toLowerCase();
    return matchesTab && matchesSystem;
  });

  const pendingCount = approvals.filter((a) => a.approval_status === 'pending').length;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Title Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-black text-white">Enterprise Approval Center</h1>
            {pendingCount > 0 && (
              <span className="bg-amber-500 text-slate-950 text-xs font-bold px-2 py-0.5 rounded-full">
                {pendingCount} Pending
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Mandatory security gate for all write actions across PostgreSQL, GitHub, Email, and Calendar.
          </p>
        </div>

        <button
          onClick={fetchApprovals}
          className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:bg-slate-800 transition-colors self-start sm:self-auto"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      {/* Tabs & Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        {/* Tabs */}
        <div className="flex items-center gap-2">
          <button
            id="tab-pending-approvals"
            onClick={() => setActiveTab('pending')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'pending'
                ? 'bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20'
                : 'text-slate-400 hover:text-slate-200 bg-slate-900/50'
            }`}
          >
            Pending Actions ({pendingCount})
          </button>
          <button
            id="tab-all-approvals"
            onClick={() => setActiveTab('all')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'all'
                ? 'bg-slate-800 text-emerald-400 border border-slate-700'
                : 'text-slate-400 hover:text-slate-200 bg-slate-900/50'
            }`}
          >
            All Historic Approvals ({approvals.length})
          </button>
        </div>

        {/* System Filter Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar">
          {['all', 'postgresql', 'github', 'email', 'calendar'].map((sys) => (
            <button
              key={sys}
              onClick={() => setSystemFilter(sys)}
              className={`text-[11px] font-mono uppercase px-2.5 py-1 rounded-lg border transition-all ${
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

      {/* Approvals List */}
      {loading ? (
        <div className="text-center py-12">
          <div className="w-8 h-8 border-4 border-amber-500/20 border-t-amber-400 rounded-full animate-spin mx-auto mb-2"></div>
          <p className="text-xs text-slate-400 font-mono">Loading approval boundary state...</p>
        </div>
      ) : filteredApprovals.length === 0 ? (
        <div className="text-center py-16 glass-panel rounded-2xl border border-slate-800">
          <ShieldCheck className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
          <h3 className="text-base font-bold text-white">All Clear — No Pending Approvals</h3>
          <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
            {activeTab === 'pending'
              ? 'There are currently no proposed actions requiring human approval. You can initiate actions in the AI Assistant.'
              : 'No approvals found matching the selected filter.'}
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredApprovals.map((approval) => (
            <ApprovalCard
              key={approval.id}
              approval={approval}
              onApprove={handleApprove}
              onReject={handleReject}
            />
          ))}
        </div>
      )}
    </div>
  );
};
