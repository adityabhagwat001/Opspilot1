import React from 'react';
import {
  Sparkles,
  AlertTriangle,
  FileCode,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Code2,
  RefreshCw,
  ArrowRight,
  GitPullRequest,
  Terminal,
  ExternalLink,
  Layers,
  ChevronRight
} from 'lucide-react';
import { StructuredAnalysis, WorkflowFailureItem } from '../types';

interface AIIssueAnalysisPanelProps {
  failure: WorkflowFailureItem;
  analysis: StructuredAnalysis | null;
  isLoading?: boolean;
  onAnalyzeAgain?: () => void;
  onProposeFix?: () => void;
  onReviewInApprovalCenter?: () => void;
  hasProposal?: boolean;
}

export const AIIssueAnalysisPanel: React.FC<AIIssueAnalysisPanelProps> = ({
  failure,
  analysis,
  isLoading = false,
  onAnalyzeAgain,
  onProposeFix,
  onReviewInApprovalCenter,
  hasProposal = false
}) => {
  if (isLoading) {
    return (
      <div className="bg-slate-900/90 border border-cyan-500/30 rounded-2xl p-6 backdrop-blur-md shadow-2xl space-y-4 animate-pulse">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-cyan-500/20 flex items-center justify-center">
            <RefreshCw className="w-5 h-5 text-cyan-400 animate-spin" />
          </div>
          <div>
            <div className="h-4 w-48 bg-slate-700 rounded mb-1"></div>
            <div className="h-3 w-72 bg-slate-800 rounded"></div>
          </div>
        </div>
        <div className="space-y-3 pt-2">
          <div className="h-16 bg-slate-800/60 rounded-xl"></div>
          <div className="h-24 bg-slate-800/60 rounded-xl"></div>
          <div className="h-20 bg-slate-800/60 rounded-xl"></div>
        </div>
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 text-center space-y-3">
        <Sparkles className="w-8 h-8 text-cyan-400 mx-auto" />
        <h4 className="text-sm font-bold text-white">AI Diagnostic Ready to Generate</h4>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          Click &quot;Analyze with AI&quot; to inspect the live GitHub Actions runner logs and generate a fact-grounded 7-part root cause diagnosis.
        </p>
        {onAnalyzeAgain && (
          <button
            onClick={onAnalyzeAgain}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 hover:bg-cyan-500/30 transition-colors"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Start AI Diagnosis</span>
          </button>
        )}
      </div>
    );
  }

  const confidenceScore = analysis.confidence_level || '96% Confident';
  const isGroq = analysis.is_groq_powered ?? true;

  // Render unified diff with color highlighting
  const renderUnifiedDiff = (diffText: string) => {
    if (!diffText || !diffText.trim()) {
      return (
        <div className="text-xs text-slate-500 italic py-2">
          No unified diff generated.
        </div>
      );
    }
    const lines = diffText.split('\n');
    return (
      <div className="rounded-xl overflow-hidden border border-slate-800 bg-slate-950 font-mono text-xs">
        <div className="px-3.5 py-1.5 bg-slate-900 border-b border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
          <span className="flex items-center gap-1.5">
            <Code2 className="w-3.5 h-3.5 text-cyan-400" />
            <span>Unified Git Patch</span>
          </span>
          <span className="text-[10px] text-slate-500">Readable unified diff preview</span>
        </div>
        <div className="p-3 max-h-72 overflow-x-auto overflow-y-auto space-y-0.5 text-xs">
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
    <div className="bg-slate-900/95 border border-cyan-500/40 rounded-2xl p-5 md:p-6 shadow-2xl backdrop-blur-md space-y-5 text-slate-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800/80">
        <div className="flex items-start gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-600/20 border border-cyan-500/30 text-cyan-400 shrink-0">
            <Sparkles className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-base font-bold text-white tracking-tight">
                AI Issue Analysis & Root Cause Diagnosis
              </h3>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                {isGroq ? 'Groq LLM Powered' : 'Rule-Based Engine'}
              </span>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                Confidence: {confidenceScore}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Repository: <span className="text-slate-200 font-mono font-medium">{failure.repo_full_name}</span> | Run ID: <span className="text-cyan-400 font-mono font-medium">#{failure.run_id}</span> | Workflow: <span className="text-slate-200 font-medium">{failure.workflow_name}</span>
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2 shrink-0">
          {onAnalyzeAgain && (
            <button
              onClick={onAnalyzeAgain}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Analyze Again
            </button>
          )}

          {hasProposal && onReviewInApprovalCenter ? (
            <button
              onClick={onReviewInApprovalCenter}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 transition-colors shadow-lg shadow-amber-950/20"
            >
              <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
              Review in Approval Center
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          ) : onProposeFix ? (
            <button
              onClick={onProposeFix}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 font-semibold shadow-lg shadow-emerald-500/20 transition-all"
            >
              <Sparkles className="w-3.5 h-3.5" />
              Propose AI Fix Patch
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          ) : null}
        </div>
      </div>

      {/* Section A: Problem Summary */}
      <div className="rounded-xl p-4 bg-slate-950/80 border border-slate-800 space-y-1.5">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-cyan-400">
          <HelpCircle className="w-4 h-4 text-cyan-400 shrink-0" />
          <span>A. Problem Summary</span>
        </div>
        <p className="text-sm text-slate-200 leading-relaxed font-normal">
          {analysis.problem_summary}
        </p>
      </div>

      {/* Section B: Root Cause & Supporting Evidence */}
      <div className="rounded-xl p-4 bg-slate-950/80 border border-slate-800 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-rose-400">
            <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>B. Root Cause & Technical Diagnostic</span>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            Failing Step: <span className="text-rose-300 font-semibold">{analysis.failed_step || failure.failing_step || 'CI Test Suite'}</span>
          </span>
        </div>

        <p className="text-sm text-slate-200 leading-relaxed">
          {analysis.root_cause}
        </p>

        {/* Evidence Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2 pt-1 text-xs">
          <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
            <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">Error Type</span>
            <span className="font-mono text-rose-300 font-medium">{analysis.error_type || 'ImportError / Missing Dependency'}</span>
          </div>
          <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
            <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">Affected File</span>
            <span className="font-mono text-cyan-300 font-medium">{analysis.affected_file || 'requirements.txt'}</span>
          </div>
          <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
            <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">Dependency / Config</span>
            <span className="font-mono text-amber-300 font-medium">{analysis.dependency_or_config || 'pydantic-settings>=2.0'}</span>
          </div>
          <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
            <span className="text-[10px] uppercase font-bold text-slate-400 block mb-0.5">Confidence Level</span>
            <span className="font-mono text-emerald-300 font-medium">{confidenceScore}</span>
          </div>
        </div>

        {/* Log Evidence Traces */}
        {analysis.log_evidence && (
          <div className="pt-1">
            <div className="text-[11px] font-bold text-slate-400 mb-1.5 flex items-center gap-1.5">
              <Terminal className="w-3.5 h-3.5 text-slate-400" />
              <span>Log Trace Evidence:</span>
            </div>
            <pre className="p-3 rounded-lg bg-black/60 border border-slate-800/80 font-mono text-xs text-rose-300/90 overflow-x-auto whitespace-pre-wrap max-h-36">
              {analysis.log_evidence}
            </pre>
          </div>
        )}
      </div>

      {/* Section C: Recommended Solution */}
      <div className="rounded-xl p-4 bg-emerald-950/20 border border-emerald-500/30 space-y-1.5">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-400">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>C. Recommended Solution</span>
        </div>
        <p className="text-sm text-slate-200 leading-relaxed">
          {analysis.recommended_solution}
        </p>
      </div>

      {/* Section D: Files Requiring Changes */}
      {analysis.files_requiring_changes && analysis.files_requiring_changes.length > 0 && (
        <div className="rounded-xl p-4 bg-slate-950/80 border border-slate-800 space-y-2.5">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-sky-400">
            <FileCode className="w-4 h-4 text-sky-400 shrink-0" />
            <span>D. Files Requiring Changes ({analysis.files_requiring_changes.length})</span>
          </div>
          <div className="space-y-2">
            {analysis.files_requiring_changes.map((file, idx) => (
              <div key={idx} className="p-3 rounded-lg bg-slate-900 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-2 text-xs">
                <div>
                  <div className="font-mono font-bold text-sky-300 flex items-center gap-1.5">
                    <ChevronRight className="w-3.5 h-3.5 text-sky-400" />
                    <span>{file.file_path || file.file_name}</span>
                  </div>
                  <p className="text-slate-400 text-xs mt-0.5 ml-5">
                    {file.reason}
                  </p>
                </div>
                {file.proposed_changes && (
                  <span className="font-mono text-[11px] px-2.5 py-1 rounded bg-slate-800 text-emerald-300 border border-slate-700 self-start md:self-auto shrink-0">
                    {file.proposed_changes}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Section E: Proposed Code Changes (Unified Diff) */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-cyan-400 px-1">
          <Code2 className="w-4 h-4 text-cyan-400 shrink-0" />
          <span>E. Proposed Unified Code Changes</span>
        </div>
        {renderUnifiedDiff(analysis.code_changes_diff)}
      </div>

      {/* Section F & G: Risk Assessment and Expected Result */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {/* Box F: Risk Assessment */}
        <div className="rounded-xl p-4 bg-slate-950/80 border border-amber-500/20 space-y-1.5">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-400">
            <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0" />
            <span>F. Risk Assessment</span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            {analysis.risk_assessment}
          </p>
        </div>

        {/* Box G: Expected Result */}
        <div className="rounded-xl p-4 bg-slate-950/80 border border-cyan-500/20 space-y-1.5">
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-cyan-400">
            <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
            <span>G. Expected Result</span>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed">
            {analysis.expected_result}
          </p>
        </div>
      </div>
    </div>
  );
};
