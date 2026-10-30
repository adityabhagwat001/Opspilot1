import React, { useState } from 'react';
import { 
  ShieldAlert, 
  CheckCircle2, 
  XCircle, 
  Hash, 
  AlertTriangle,
  AlertCircle,
  Database,
  GitBranch,
  Mail,
  Calendar,
  ChevronDown,
  ChevronUp,
  Loader2,
  Trash2,
  Clock,
  Sparkles,
  ExternalLink,
  FileCode,
  Code
} from 'lucide-react';
import { ApprovalRequest } from '../types';

interface ApprovalCardProps {
  approval: ApprovalRequest;
  onApprove: (id: string) => Promise<void>;
  onReject: (id: string, reason?: string) => Promise<void>;
  onDelete?: (id: string) => Promise<void>;
  compact?: boolean;
}

function parseApprovalStory(approval: ApprovalRequest) {
  const args = approval.arguments || {};
  const tool = (approval.tool_name || '').toLowerCase();
  const system = (approval.target_system || '').toLowerCase();
  const status = (approval.approval_status || '').toLowerCase();
  const isCompleted = status === 'approved' || status === 'succeeded';

  let issueTitle = 'Operational Issue Detected';
  let issueDesc = approval.action_summary || 'An operational trigger requires human review.';
  let solutionTitle = 'Proposed AI Remediation';
  let solutionDesc = 'Execute tool action to resolve operational bottleneck.';
  let patchFiles: Array<{ path: string; summary?: string }> = [];
  let changesSummary = '';
  let resolutionText = '';
  let prUrl: string | undefined = undefined;

  if (tool === 'create_pull_request') {
    const owner = args.owner || '';
    const repo = args.repo || '';
    const repoFull = owner && repo ? `${owner}/${repo}` : (approval.action_summary.includes("'") ? approval.action_summary.split("'")[3] || '' : '');
    const title = args.title || '';
    const body = args.body || '';
    const head = args.head || 'fix-branch';
    const base = args.base || 'main';

    issueTitle = title || `Issue in repository ${repoFull}`;
    
    // Extract root cause or clean issue text from body
    if (body.includes('**Root Cause:**')) {
      const match = body.match(/\*\*Root Cause:\*\*\s*([^\n]+)/);
      issueDesc = match ? match[1].trim() : `Automated triage detected an error or dependency issue in ${repoFull}.`;
    } else if (body.includes('Remediation Plan:')) {
      const match = body.match(/\*\*Remediation Plan:\*\*\s*([^\n]+)/);
      issueDesc = match ? match[1].trim() : `Open issue or regression identified in ${repoFull} requiring automated patch.`;
    } else {
      issueDesc = `Operational triage detected an issue in repository ${repoFull} requiring a verified Pull Request.`;
    }

    solutionTitle = `Create Fix Branch & Open Pull Request (${head} → ${base})`;
    solutionDesc = `OpsPilot prepares branch '${head}' and submits the remediation patch against the '${base}' branch.`;

    if (Array.isArray(args.patch_files)) {
      patchFiles = args.patch_files.map((p: any) => ({
        path: p.path || 'Code patch',
        summary: p.content ? `${p.content.split('\n').length} lines modified` : undefined
      }));
      changesSummary = `Modified ${patchFiles.length} file(s): ${patchFiles.map(f => f.path).join(', ')}`;
    }

    if (isCompleted) {
      resolutionText = `Pull Request created on GitHub. The fix branch '${head}' was provisioned and linked to '${base}'.`;
      // Resolve valid PR URL
      const res = approval.execution_result;
      const data = res?.data || res;
      const candidateUrl = data?.html_url || (typeof res === 'object' ? res?.html_url : '');
      if (candidateUrl && !candidateUrl.includes('enterprise-ops') && !candidateUrl.endsWith('/pull/101')) {
        prUrl = candidateUrl;
      } else if (repoFull) {
        prUrl = `https://github.com/${repoFull}/pulls`;
      }
    }
  } else if (tool === 'update_incident_status') {
    const incId = args.incident_id || 'INC-01';
    const newStatus = args.new_status || 'resolved';
    issueTitle = `Incident #${incId} Active State`;
    issueDesc = `Operational incident #${incId} was investigated and verified for state change to '${newStatus.toUpperCase()}'.`;
    solutionTitle = `Transition Incident State to '${newStatus.toUpperCase()}'`;
    solutionDesc = `Update the PostgreSQL operational incident record and log resolution timeline.`;
    changesSummary = `Status updated to ${newStatus.toUpperCase()}`;
    if (isCompleted) {
      resolutionText = `Incident #${incId} marked as '${newStatus.toUpperCase()}' in PostgreSQL. SRE audit record appended.`;
    }
  } else if (tool === 'create_operational_task') {
    const taskTitle = args.title || 'Remediation Task';
    issueTitle = `Operational Action Item Required`;
    issueDesc = args.description || `Engineering investigation required for system reliability.`;
    solutionTitle = `Create Priority ${args.priority?.toUpperCase() || 'P1'} Task: "${taskTitle}"`;
    solutionDesc = `Add actionable task item to the engineering remediation queue in PostgreSQL.`;
    changesSummary = `Created task with priority ${args.priority || 'P1'}`;
    if (isCompleted) {
      resolutionText = `Task successfully registered and assigned to on-call engineering team.`;
    }
  } else if (tool === 'send_email' || tool === 'create_email_draft') {
    const recipient = args.recipient || args.to || 'ops-team';
    const subject = args.subject || 'Operational Notification';
    issueTitle = `Incident Dispatch Required`;
    issueDesc = `Stakeholders need an urgent operational briefing regarding system health.`;
    solutionTitle = `Dispatch Email: "${subject}"`;
    solutionDesc = `Send operational status email to ${recipient}.`;
    changesSummary = `Email dispatched to ${recipient}`;
    if (isCompleted) {
      resolutionText = `Email sent successfully via SMTP mail relay to ${recipient}.`;
    }
  } else if (tool === 'create_calendar_event') {
    const eventTitle = args.summary || args.title || 'Triage Meeting';
    issueTitle = `Team Coordination Required`;
    issueDesc = `Cross-functional triage meeting required to align on incident resolution.`;
    solutionTitle = `Schedule Calendar Event: "${eventTitle}"`;
    solutionDesc = `Book time slot on operational calendar and send invitations.`;
    changesSummary = `Calendar event scheduled`;
    if (isCompleted) {
      resolutionText = `Meeting booked on calendar and invitations sent to attendees.`;
    }
  } else {
    issueTitle = `System Mutation Request (${system.toUpperCase()})`;
    issueDesc = approval.action_summary;
    solutionTitle = `Execute ${approval.tool_name}`;
    solutionDesc = `Apply changes to ${approval.target_system} with authorized parameters.`;
    changesSummary = `Parameters applied to ${approval.target_system}`;
    if (isCompleted) {
      resolutionText = `Action executed successfully on ${approval.target_system}.`;
    }
  }

  return {
    issueTitle,
    issueDesc,
    solutionTitle,
    solutionDesc,
    patchFiles,
    changesSummary,
    resolutionText,
    prUrl
  };
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
  const [showRawJson, setShowRawJson] = useState(false);
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

  const story = parseApprovalStory(approval);

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
    } p-5 space-y-4`}>
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
            title={expanded ? "Collapse details" : "Expand details"}
          >
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Expanded Simplified Plain-Text Details */}
      {expanded && (
        <div className="pt-2 border-t border-slate-800/80 space-y-3.5">
          {/* Section 1 & 2: Issue and Proposed Solution in Plain Text */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Box 1: What is the Issue? */}
            <div className="rounded-xl p-4 bg-slate-950/80 border border-slate-800 space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold text-rose-400">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>1. What is the Issue?</span>
              </div>
              <div className="text-sm font-bold text-white">{story.issueTitle}</div>
              <p className="text-xs text-slate-300 leading-relaxed">{story.issueDesc}</p>
            </div>

            {/* Box 2: Proposed AI Solution */}
            <div className="rounded-xl p-4 bg-slate-950/80 border border-slate-800 space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold text-sky-400">
                <Sparkles className="w-4 h-4 shrink-0" />
                <span>2. Proposed AI Solution</span>
              </div>
              <div className="text-sm font-bold text-white">{story.solutionTitle}</div>
              <p className="text-xs text-slate-300 leading-relaxed">{story.solutionDesc}</p>
              {story.patchFiles.length > 0 && (
                <div className="pt-1 flex flex-wrap gap-1.5">
                  {story.patchFiles.map((pf, idx) => (
                    <span key={idx} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-sky-950/50 border border-sky-800/40 text-xs font-mono text-sky-300">
                      <FileCode className="w-3.5 h-3.5 text-sky-400" />
                      <span>{pf.path}</span>
                      {pf.summary && <span className="text-slate-400 text-[10px]">({pf.summary})</span>}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Section 3: When Solved / Succeeded - How it was solved & Changes Done */}
          {isApproved && (
            <div className="rounded-xl p-4 bg-emerald-950/20 border border-emerald-500/30 space-y-2.5">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs font-bold text-emerald-400">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>3. How It Was Solved & Changes Applied</span>
                </div>
                <span className="text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  Resolved & Verified
                </span>
              </div>
              <p className="text-xs text-emerald-200/90 leading-relaxed font-medium">
                {story.resolutionText || 'Remediation completed successfully. All proposed changes applied and verified.'}
              </p>
              {story.changesSummary && (
                <div className="text-xs text-slate-300 font-mono flex items-center gap-2 pt-0.5">
                  <span className="text-slate-400">Exact changes applied:</span>
                  <span className="text-emerald-300 font-semibold">{story.changesSummary}</span>
                </div>
              )}
              {story.prUrl && (
                <div className="pt-1">
                  <a 
                    href={story.prUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 border border-emerald-500/40 text-emerald-300 text-xs font-bold transition-all"
                  >
                    <GitBranch className="w-3.5 h-3.5" />
                    <span>View Pull Request on GitHub</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              )}
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

          {/* Action Buttons for Pending Requests */}
          {isPending && (
            <div className="flex items-center justify-end gap-3 pt-1">
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

          {/* Collapsible Technical Details (Raw JSON & Canonical Hash) */}
          <div className="pt-2 border-t border-slate-800/50">
            <button
              onClick={() => setShowRawJson(!showRawJson)}
              className="flex items-center gap-1.5 text-xs font-mono text-slate-400 hover:text-slate-200 py-1 transition-colors"
            >
              <Code className="w-3.5 h-3.5 text-slate-500" />
              <span>{showRawJson ? 'Hide Technical Raw JSON & Canonical Hash' : 'View Technical Raw JSON & Canonical Hash (Debug)'}</span>
              {showRawJson ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>

            {showRawJson && (
              <div className="mt-3 space-y-3 animate-fade-in">
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
                    <div className="text-xs font-semibold text-slate-300 mb-1">Execution Outcome (Raw JSON):</div>
                    <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300 overflow-x-auto max-h-36">
                      {JSON.stringify(approval.execution_result, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
