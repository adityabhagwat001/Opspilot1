import React, { useState } from 'react';
import { 
  ShieldAlert, 
  CheckCircle2, 
  XCircle, 
  Hash, 
  AlertTriangle,
  Database,
  GitBranch,
  Mail,
  Calendar,
  ChevronDown,
  ChevronUp,
  Loader2,
  Trash2,
  Clock
} from 'lucide-react';
import { ApprovalRequest } from '../types';

interface ApprovalCardProps {
  approval: ApprovalRequest;
  onApprove: (id: string) => Promise<void>;
  onReject: (id: string, reason?: string) => Promise<void>;
  onDelete?: (id: string) => Promise<void>;
  compact?: boolean;
}

export const ApprovalCard: React.FC<ApprovalCardProps> = ({
  approval,
  onApprove,
  onReject,
  onDelete,
  compact = false
}) => {
  const [isApproving, setIsApproving] = useState(false);
  const [isRejecting, setIsRejecting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [expanded, setExpanded] = useState(!compact);
  const [rejectReason, setRejectReason] = useState('');
  const [showRejectInput, setShowRejectInput] = useState(false);

  const getSystemIcon = (system: string) => {
    switch (system.toLowerCase()) {
      case 'postgresql': return <Database className="w-4 h-4 text-sky-400" />;
      case 'github': return <GitBranch className="w-4 h-4 text-purple-400" />;
      case 'email': return <Mail className="w-4 h-4 text-amber-400" />;
      case 'calendar': return <Calendar className="w-4 h-4 text-emerald-400" />;
      default: return <ShieldAlert className="w-4 h-4 text-slate-400" />;
    }
  };

  const handleApprove = async () => {
    try {
      setIsApproving(true);
      await onApprove(approval.id);
    } finally {
      setIsApproving(false);
    }
  };

  const handleReject = async () => {
    try {
      setIsRejecting(true);
      await onReject(approval.id, rejectReason);
      setShowRejectInput(false);
    } finally {
      setIsRejecting(false);
    }
  };

  const handleDelete = async () => {
    if (!onDelete) return;
    try {
      setIsDeleting(true);
      await onDelete(approval.id);
    } finally {
      setIsDeleting(false);
    }
  };

  const status = (approval.approval_status || 'pending').toLowerCase();
  const isPending = status === 'pending';
  const isApproved = status === 'approved' || status === 'succeeded';
  const isRejected = status === 'rejected';
  const isExpired = status === 'expired';
  const isFailed = status === 'failed';

  return (
    <div className={`rounded-xl border transition-all ${
      isPending 
        ? 'border-amber-500/40 bg-gradient-to-b from-amber-500/10 to-slate-900/90 shadow-lg shadow-amber-500/5' 
        : isApproved
        ? 'border-emerald-500/30 bg-slate-900/60'
        : isRejected || isFailed
        ? 'border-rose-500/30 bg-slate-900/60'
        : isExpired
        ? 'border-slate-700 bg-slate-900/40 opacity-75'
        : 'border-slate-800 bg-slate-900/60'
    } p-5`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <div className="p-2.5 rounded-lg bg-slate-800/80 border border-slate-700/50 mt-0.5">
            {getSystemIcon(approval.target_system)}
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-mono font-semibold uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                {approval.target_system}
              </span>
              <span className="text-sm font-bold text-white font-mono">
                {approval.tool_name}
              </span>
              <span className={`text-[11px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                isPending ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                isApproved ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                isExpired ? 'bg-slate-700 text-slate-300 border border-slate-600' :
                'bg-rose-500/20 text-rose-400 border border-rose-500/30'
              }`}>
                {approval.approval_status}
              </span>
            </div>
            <h4 className="text-sm font-semibold text-slate-100 mt-1.5">
              {approval.action_summary}
            </h4>
          </div>
        </div>

        <div className="flex items-center gap-1.5">
          {onDelete && !isPending && (
            <button
              onClick={handleDelete}
              disabled={isDeleting}
              title="Remove approval record"
              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
            >
              {isDeleting ? <Loader2 className="w-4 h-4 animate-spin text-rose-400" /> : <Trash2 className="w-4 h-4" />}
            </button>
          )}
          <button 
            onClick={() => setExpanded(!expanded)}
            className="text-slate-400 hover:text-slate-200 p-1.5 rounded-md hover:bg-slate-800"
          >
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Body */}
      {expanded && (
        <div className="mt-4 pt-4 border-t border-slate-800/80 space-y-3">
          {/* Canonical parameters view */}
          <div>
            <div className="flex items-center justify-between text-xs text-slate-400 mb-1.5">
              <span className="font-semibold text-slate-300">Exact Action Parameters (Canonical JSON):</span>
              {approval.action_hash && (
                <span className="flex items-center gap-1 font-mono text-[10px] text-slate-400">
                  <Hash className="w-3 h-3 text-emerald-400" />
                  SHA256: {approval.action_hash.slice(0, 12)}...
                </span>
              )}
            </div>
            <pre className="p-3 rounded-lg bg-slate-950/80 border border-slate-800/80 text-xs font-mono text-emerald-300 overflow-x-auto max-h-48">
              {JSON.stringify(approval.arguments, null, 2)}
            </pre>
          </div>

          {/* Execution Result (if completed) */}
          {approval.execution_result && (
            <div>
              <div className="text-xs font-semibold text-slate-300 mb-1">Execution Outcome:</div>
              <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300 overflow-x-auto max-h-36">
                {JSON.stringify(approval.execution_result, null, 2)}
              </pre>
            </div>
          )}

          {/* Expired notice */}
          {isExpired && (
            <div className="flex items-center gap-2 p-3 rounded-lg bg-slate-800/60 border border-slate-700/60 text-xs text-slate-300">
              <Clock className="w-4 h-4 text-slate-400 shrink-0" />
              <span>This proposed action exceeded its 15-minute validity window without authorization and has expired safely.</span>
            </div>
          )}

          {/* Security Notice for Pending Actions */}
          {isPending && (
            <div className="flex items-start gap-2.5 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs text-amber-300">
              <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold">Security Boundary:</span> This write operation modifies external state. No change is made until you authorize it.
              </div>
            </div>
          )}

          {/* Action Buttons */}
          {isPending && (
            <div className="flex items-center justify-end gap-3 pt-2">
              {!showRejectInput ? (
                <>
                  <button
                    id={`btn-reject-${approval.id}`}
                    onClick={() => setShowRejectInput(true)}
                    disabled={isApproving || isRejecting}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold text-rose-300 hover:text-rose-200 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 transition-all disabled:opacity-50"
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    Reject Action
                  </button>

                  <button
                    id={`btn-approve-${approval.id}`}
                    onClick={handleApprove}
                    disabled={isApproving || isRejecting}
                    className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-bold text-slate-950 bg-emerald-400 hover:bg-emerald-300 shadow-md shadow-emerald-500/20 transition-all disabled:opacity-50"
                  >
                    {isApproving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
                    Approve & Execute
                  </button>
                </>
              ) : (
                <div className="flex items-center gap-2 w-full">
                  <input
                    type="text"
                    placeholder="Enter reason for rejection (optional)..."
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    className="flex-1 bg-slate-950 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-rose-500"
                  />
                  <button
                    onClick={() => setShowRejectInput(false)}
                    className="text-xs text-slate-400 hover:text-slate-200 px-2"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleReject}
                    disabled={isRejecting}
                    className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-bold bg-rose-600 text-white hover:bg-rose-500"
                  >
                    {isRejecting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : 'Confirm Rejection'}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
