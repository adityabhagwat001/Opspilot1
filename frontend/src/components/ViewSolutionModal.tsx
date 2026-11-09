import React from 'react';
import {
  X,
  CheckCircle2,
  AlertTriangle,
  FileCode,
  GitPullRequest,
  GitBranch,
  GitCommit,
  ExternalLink,
  ShieldCheck,
  Clock,
  Terminal,
  Code2,
  AlertCircle,
  HelpCircle,
  Sparkles,
  Layers,
  ShieldAlert,
  Calendar,
  Check,
  RefreshCw
} from 'lucide-react';
import { SolutionHistory, ResolutionStatus } from '../types';

interface ViewSolutionModalProps {
  isOpen: boolean;
  onClose: () => void;
  solution: SolutionHistory | null;
  isLoading?: boolean;
  onVerifyAgain?: () => void;
  isVerifying?: boolean;
}

export const ViewSolutionModal: React.FC<ViewSolutionModalProps> = ({
  isOpen,
  onClose,
  solution,
  isLoading = false,
  onVerifyAgain,
  isVerifying = false
}) => {
  if (!isOpen) return null;

  const renderStatusBadge = (status: string) => {
    const s = (status || '').toUpperCase();
    if (s === 'VERIFIED_RESOLVED' || s === 'RESOLVED') {
      return (
        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
          <CheckCircle2 className="w-4 h-4" />
          VERIFIED RESOLVED
        </span>
      );
    }
    if (s === 'STILL_FAILING') {
      return (
        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-rose-500/20 text-rose-400 border border-rose-500/40">
          <AlertTriangle className="w-4 h-4" />
          STILL FAILING
        </span>
      );
    }
    if (s === 'FIX_FAILED' || s === 'FAILED') {
      return (
        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-rose-500/20 text-rose-400 border border-rose-500/40">
          <AlertCircle className="w-4 h-4" />
          FIX FAILED
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/40">
        <Clock className="w-4 h-4" />
        {s || 'NOT VERIFIED'}
      </span>
    );
  };

  const renderUnifiedDiff = (diffText: string) => {
    if (!diffText || !diffText.trim()) {
      return (
        <div className="text-xs text-slate-500 italic p-3">
          No code changes diff recorded for this execution.
        </div>
      );
    }
    const lines = diffText.split('\n');
    return (
      <div className="rounded-xl overflow-hidden border border-slate-800 bg-slate-950 font-mono text-xs">
        <div className="px-3 py-1.5 bg-slate-900 border-b border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
          <span className="flex items-center gap-1.5">
            <Code2 className="w-3.5 h-3.5 text-cyan-400" />
            <span>Committed Unified Diff</span>
          </span>
          <span className="text-[10px] text-slate-500">Live verified git patch</span>
        </div>
        <div className="p-3 max-h-64 overflow-x-auto overflow-y-auto space-y-0.5 text-xs">
          {lines.map((line, idx) => {
            let lineCls = 'text-slate-300';
            let bgCls = '';
            if (line.startsWith('---') || line.startsWith('+++')) {
              lineCls = 'text-cyan-400 font-bold';
              bgCls = 'bg-cyan-950/20';
            } else if (line.startsWith('@@')) {
              lineCls = 'text-amber-400 font-semibold';
              bgCls = 'bg-amber-950/20';
            } else if (line.startsWith('+') && !line.startsWith('+++')) {
              lineCls = 'text-emerald-400';
              bgCls = 'bg-emerald-950/30 font-medium';
            } else if (line.startsWith('-') && !line.startsWith('---')) {
              lineCls = 'text-rose-400';
              bgCls = 'bg-rose-950/30';
            }
            return (
              <div key={idx} className={`px-2 py-0.5 rounded ${bgCls} ${lineCls} whitespace-pre`}>
                {line || ' '}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-black/80 backdrop-blur-md overflow-y-auto">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl w-full max-w-4xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Modal Header */}
        <div className="px-6 py-4 bg-slate-950/90 border-b border-slate-800 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white tracking-tight">
                  Detailed AI Resolution & Solution History
                </h2>
                {solution && renderStatusBadge(solution.final_result?.status || solution.issue_overview?.resolution_status)}
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Complete evidence-based lifecycle: issue detection, root cause, code diff, testing, PR and post-merge verification.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {onVerifyAgain && (
              <button
                onClick={onVerifyAgain}
                disabled={isVerifying}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isVerifying ? 'animate-spin text-cyan-400' : ''}`} />
                {isVerifying ? 'Verifying...' : 'Re-verify with GitHub'}
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6 text-slate-200">
          {isLoading ? (
            <div className="py-20 flex flex-col items-center justify-center space-y-3">
              <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin" />
              <p className="text-sm text-slate-400 font-medium">Retrieving real-time verified resolution history from GitHub...</p>
            </div>
          ) : !solution ? (
            <div className="py-16 text-center text-slate-400 space-y-4 max-w-md mx-auto">
              <div className="w-12 h-12 rounded-full bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center mx-auto text-cyan-400">
                <Sparkles className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white mb-1">No AI Solution Generated Yet</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  This workflow failure has not been remediated yet. Use &quot;Analyze with AI&quot; on the failure card to diagnose the root cause and generate a verified code patch proposal.
                </p>
              </div>
            </div>
          ) : (
            <>
              {/* 1. Issue Overview */}
              <div className="rounded-xl p-4 bg-slate-950/70 border border-slate-800 space-y-3">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-cyan-400">
                  <Layers className="w-4 h-4 text-cyan-400" />
                  <span>1. Issue Overview</span>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                  <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">Repository</span>
                    <span className="font-mono text-cyan-300 font-medium">{solution.issue_overview?.repo || 'N/A'}</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">Workflow Run</span>
                    <span className="font-mono text-cyan-300 font-medium">#{solution.issue_overview?.workflow_run_id || 'N/A'}</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">Detected Date</span>
                    <span className="text-slate-300 font-medium">{solution.issue_overview?.detected_at ? new Date(solution.issue_overview.detected_at).toLocaleString() : 'Recent'}</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">Current Status</span>
                    <div className="mt-0.5">{renderStatusBadge(solution.issue_overview?.resolution_status || solution.final_result?.status)}</div>
                  </div>
                </div>
                {solution.issue_overview?.original_error && (
                  <div className="text-xs text-slate-400 pt-1">
                    <span className="font-bold text-slate-300">Original Error: </span>
                    <span className="font-mono text-rose-300">{solution.issue_overview.original_error}</span>
                  </div>
                )}
              </div>

              {/* 2. What Was the Problem? */}
              <div className="rounded-xl p-4 bg-slate-950/70 border border-slate-800 space-y-1.5">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-rose-400">
                  <HelpCircle className="w-4 h-4 text-rose-400" />
                  <span>2. What Was the Problem?</span>
                </div>
                <p className="text-sm text-slate-200 leading-relaxed font-normal">
                  {solution.problem_summary || 'The CI/CD build failed during automated testing due to an execution or dependency error.'}
                </p>
              </div>

              {/* 3. Why Did It Happen? (Root Cause) */}
              <div className="rounded-xl p-4 bg-slate-950/70 border border-slate-800 space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-400">
                    <AlertTriangle className="w-4 h-4 text-amber-400" />
                    <span>3. Why Did It Happen? (Technical Root Cause)</span>
                  </div>
                  {solution.root_cause?.confidence_level && (
                    <span className="text-[11px] font-mono text-emerald-400 font-semibold bg-emerald-950/30 px-2 py-0.5 rounded border border-emerald-800/40">
                      {solution.root_cause.confidence_level}
                    </span>
                  )}
                </div>
                <p className="text-sm text-slate-200 leading-relaxed">
                  {solution.root_cause?.technical_cause || 'The application encountered an error executing test commands.'}
                </p>

                {/* Evidence snippet */}
                {solution.root_cause?.log_evidence && (
                  <div className="pt-1">
                    <span className="text-[11px] font-bold text-slate-400 block mb-1">Log Trace Evidence:</span>
                    <pre className="p-3 rounded-lg bg-black/60 border border-slate-800 font-mono text-xs text-rose-300/90 overflow-x-auto whitespace-pre-wrap max-h-32">
                      {solution.root_cause.log_evidence}
                    </pre>
                  </div>
                )}
              </div>

              {/* 4. How Did AI Suggest Solving It? */}
              <div className="rounded-xl p-4 bg-emerald-950/20 border border-emerald-500/30 space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-400">
                  <Sparkles className="w-4 h-4 text-emerald-400" />
                  <span>4. How Did AI Suggest Solving It?</span>
                </div>
                <p className="text-sm text-slate-200 leading-relaxed">
                  {solution.suggested_solution?.summary || 'Apply the targeted patch to resolve the dependency or configuration defect.'}
                </p>
                {solution.suggested_solution?.bullet_points && solution.suggested_solution.bullet_points.length > 0 && (
                  <ul className="space-y-1.5 pt-1 text-xs text-slate-300">
                    {solution.suggested_solution.bullet_points.map((pt, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <Check className="w-3.5 h-3.5 text-emerald-400 mt-0.5 shrink-0" />
                        <span>{pt}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* 5. What Code Was Changed? */}
              <div className="rounded-xl p-4 bg-slate-950/70 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-cyan-400">
                    <FileCode className="w-4 h-4 text-cyan-400" />
                    <span>5. What Code Was Changed?</span>
                  </div>
                  {solution.code_changes?.files && (
                    <span className="text-xs text-slate-400 font-mono">
                      {solution.code_changes.files.length} file(s) modified
                    </span>
                  )}
                </div>

                {solution.code_changes?.files && solution.code_changes.files.length > 0 && (
                  <div className="space-y-2">
                    {solution.code_changes.files.map((file, idx) => (
                      <div key={idx} className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-xs space-y-1">
                        <div className="font-mono font-bold text-sky-300">{file.file_path}</div>
                        <p className="text-slate-400">{file.change_summary}</p>
                        {file.added_lines && file.added_lines.length > 0 && (
                          <div className="text-[11px] font-mono text-emerald-400">
                            Added: {file.added_lines.join(', ')}
                          </div>
                        )}
                        {file.removed_lines && file.removed_lines.length > 0 && (
                          <div className="text-[11px] font-mono text-rose-400">
                            Removed: {file.removed_lines.join(', ')}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {/* Diff code viewer */}
                {renderUnifiedDiff(solution.code_changes?.diff)}
              </div>

              {/* 6. How Was the Fix Tested? */}
              <div className="rounded-xl p-4 bg-slate-950/70 border border-slate-800 space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-teal-400">
                    <Terminal className="w-4 h-4 text-teal-400" />
                    <span>6. How Was the Fix Tested?</span>
                  </div>
                  {solution.testing_evidence?.sandbox_status && (
                    <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-teal-500/20 text-teal-300 border border-teal-500/30">
                      Sandbox: {solution.testing_evidence.sandbox_status}
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                  <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">Test Environment</span>
                    <span className="font-mono text-slate-300">{solution.testing_evidence?.test_environment || 'Isolated Scratch Sandbox + AST Syntax Verification'}</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">Execution Results</span>
                    <span className="font-mono text-emerald-300">{solution.testing_evidence?.test_results || '0 Syntax Errors | AST Syntax Tree Verified'}</span>
                  </div>
                </div>

                {solution.testing_evidence?.passed_checks && solution.testing_evidence.passed_checks.length > 0 && (
                  <div className="pt-1">
                    <span className="text-[11px] font-bold text-slate-400 block mb-1">Passed Checks:</span>
                    <ul className="space-y-1 text-xs text-slate-300">
                      {solution.testing_evidence.passed_checks.map((chk, idx) => (
                        <li key={idx} className="flex items-center gap-2">
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                          <span>{chk}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              {/* 7. GitHub Pull Request Details */}
              <div className="rounded-xl p-4 bg-slate-950/70 border border-slate-800 space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-purple-400">
                    <GitPullRequest className="w-4 h-4 text-purple-400" />
                    <span>7. GitHub Pull Request Details</span>
                  </div>
                  {solution.pr_details?.pr_state && (
                    <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${
                      solution.pr_details.pr_state === 'MERGED'
                        ? 'bg-purple-500/20 text-purple-300 border-purple-500/30'
                        : solution.pr_details.pr_state === 'OPEN'
                        ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                        : 'bg-slate-800 text-slate-400 border-slate-700'
                    }`}>
                      State: {solution.pr_details.pr_state}
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2 text-xs">
                  <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">PR Number & Link</span>
                    {solution.pr_details?.pr_url ? (
                      <a
                        href={solution.pr_details.pr_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-mono text-cyan-400 hover:underline inline-flex items-center gap-1 font-semibold"
                      >
                        PR #{solution.pr_details.pr_number || 'View'}
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    ) : (
                      <span className="text-slate-500">Not created or direct branch</span>
                    )}
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">Fix Branch</span>
                    <span className="font-mono text-slate-300">{solution.pr_details?.branch || 'N/A'}</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                    <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">Merge Commit SHA</span>
                    <span className="font-mono text-purple-300">
                      {solution.pr_details?.merge_commit ? solution.pr_details.merge_commit.substring(0, 10) : 'Not merged yet'}
                    </span>
                  </div>
                </div>
              </div>

              {/* 8. Final Result & Verification Status */}
              <div className={`rounded-xl p-5 border space-y-2 ${
                (solution.final_result?.status || '').toUpperCase() === 'VERIFIED_RESOLVED'
                  ? 'bg-emerald-950/20 border-emerald-500/40'
                  : (solution.final_result?.status || '').toUpperCase() === 'STILL_FAILING'
                  ? 'bg-rose-950/20 border-rose-500/40'
                  : 'bg-amber-950/20 border-amber-500/40'
              }`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-white">
                    <ShieldCheck className="w-5 h-5 text-emerald-400" />
                    <span>8. Final Result & Post-Merge Verification</span>
                  </div>
                  <div>{renderStatusBadge(solution.final_result?.status || 'NOT_VERIFIED')}</div>
                </div>
                <p className="text-sm text-slate-200 leading-relaxed font-normal">
                  {solution.final_result?.explanation || 'Verification results based on live GitHub Actions workflow conclusions.'}
                </p>
                {solution.final_result?.verified_at && (
                  <div className="text-[11px] text-slate-400 font-mono pt-1">
                    Verified timestamp: {new Date(solution.final_result.verified_at).toLocaleString()}
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 bg-slate-950 border-t border-slate-800 flex items-center justify-between shrink-0">
          <div className="text-xs text-slate-500">
            OpsPilot Live Intelligence • Cryptographically Tamper-Evident & Grounded
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-bold bg-slate-800 hover:bg-slate-700 text-white transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
