import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useLocation } from 'react-router-dom';
import { 
  Send, 
  Bot, 
  User as UserIcon, 
  Sparkles, 
  Loader2, 
  Database, 
  GitBranch, 
  Mail, 
  Calendar, 
  Layers 
} from 'lucide-react';
import { api } from '../services/api';
import { ApprovalCard } from '../components/ApprovalCard';
import { MarkdownMessage } from '../components/MarkdownMessage';
import { ChatMessage } from '../types';

const INITIAL_WELCOME: ChatMessage = {
  id: 'welcome',
  role: 'assistant',
  content: "Hello, I am **OpsPilot**, your autonomous enterprise operations assistant connected through live FastMCP servers.\n\nI can retrieve authorized data from PostgreSQL, GitHub, email, and calendar, reason across multiple systems, and execute approved actions. Every write strictly requires your approval before touching any system.",
  timestamp: new Date().toISOString()
};

export const ChatPage: React.FC = () => {
  const location = useLocation();
  const [messages, setMessages] = useState<ChatMessage[]>([INITIAL_WELCOME]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [activeStep, setActiveStep] = useState<string>('');
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const handledPromptRef = useRef<string | null>(null);

  const handleSend = useCallback(async (customText?: string) => {
    const textToSend = customText || input;
    if (!textToSend.trim() || isLoading) return;

    setInput('');
    const userMsg: ChatMessage = {
      id: `usr-${Date.now()}`,
      role: 'user',
      content: textToSend,
      timestamp: new Date().toISOString()
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);
    setActiveStep('Analyzing intent & discovering MCP tools...');

    try {
      const res = await api.sendMessage(textToSend, conversationId);
      if (res.conversation_id && !conversationId) {
        setConversationId(res.conversation_id);
      }

      const asstMsg: ChatMessage = {
        id: `asst-${Date.now()}`,
        role: 'assistant',
        content: res.response || 'Operation completed.',
        tool_calls: res.planned_actions,
        tool_results: res.tool_results,
        pending_approval: res.pending_approval,
        timestamp: new Date().toISOString()
      };
      setMessages((prev) => [...prev, asstMsg]);
    } catch (err: any) {
      console.error('Chat error:', err);
      const errMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        role: 'assistant',
        content: `**Error:** ${err?.response?.data?.detail || err.message || 'Failed to communicate with agent service.'}`,
        timestamp: new Date().toISOString()
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setIsLoading(false);
      setActiveStep('');
    }
  }, [input, isLoading, conversationId]);

  // Auto-fill prompt if navigated from Dashboard
  useEffect(() => {
    const prompt = (location.state as any)?.initialPrompt;
    if (prompt && handledPromptRef.current !== prompt) {
      handledPromptRef.current = prompt;
      setInput(prompt);
      const timer = setTimeout(() => {
        void handleSend(prompt);
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [location.state, handleSend]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, activeStep]);


  const handleInlineApprove = async (approvalId: string) => {
    try {
      const res = await api.approveAction(approvalId);
      // Update message state
      setMessages((prev) =>
        prev.map((m) => {
          if (m.pending_approval && m.pending_approval.id === approvalId) {
            return {
              ...m,
              pending_approval: {
                ...m.pending_approval,
                approval_status: 'approved',
                execution_result: res.execution_result
              }
            };
          }
          return m;
        })
      );
    } catch (err: any) {
      alert(`Approval execution failed: ${err?.response?.data?.detail || err.message}`);
    }
  };

  const handleInlineReject = async (approvalId: string, reason?: string) => {
    try {
      await api.rejectAction(approvalId, reason);
      setMessages((prev) =>
        prev.map((m) => {
          if (m.pending_approval && m.pending_approval.id === approvalId) {
            return {
              ...m,
              pending_approval: {
                ...m.pending_approval,
                approval_status: 'rejected',
                execution_result: { rejected: true, reason }
              }
            };
          }
          return m;
        })
      );
    } catch (err: any) {
      alert(`Rejection failed: ${err?.response?.data?.detail || err.message}`);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 flex flex-col h-[calc(100vh-4.5rem)]">
      {/* Quick Scenario Pills */}
      <div className="flex items-center gap-2 overflow-x-auto pb-3 mb-3 shrink-0 no-scrollbar">
        <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider shrink-0 flex items-center gap-1">
          <Sparkles className="w-3 h-3 text-emerald-400" /> Scenarios:
        </span>
        <button
          onClick={() => handleSend("Show me all open operational incidents from the database.")}
          className="text-xs bg-slate-900 hover:bg-slate-800 text-sky-300 border border-slate-800 rounded-full px-3 py-1 shrink-0 transition-colors flex items-center gap-1.5"
        >
          <Database className="w-3 h-3" /> Incidents (PostgreSQL)
        </button>
        <button
          onClick={() => handleSend("Check the open issues in my repository and identify the highest-priority problems.")}
          className="text-xs bg-slate-900 hover:bg-slate-800 text-purple-300 border border-slate-800 rounded-full px-3 py-1 shrink-0 transition-colors flex items-center gap-1.5"
        >
          <GitBranch className="w-3 h-3" /> Open Issues (GitHub)
        </button>
        <button
          onClick={() => handleSend("Create a GitHub issue for fixing the authentication timeout.")}
          className="text-xs bg-slate-900 hover:bg-slate-800 text-amber-300 border border-amber-500/30 rounded-full px-3 py-1 shrink-0 transition-colors flex items-center gap-1.5"
        >
          <GitBranch className="w-3 h-3" /> Create Issue (Write Approval)
        </button>
        <button
          onClick={() => handleSend("Find important unread emails related to deployment problems.")}
          className="text-xs bg-slate-900 hover:bg-slate-800 text-emerald-300 border border-slate-800 rounded-full px-3 py-1 shrink-0 transition-colors flex items-center gap-1.5"
        >
          <Mail className="w-3 h-3" /> Unread Mail (Email)
        </button>
        <button
          onClick={() => handleSend("Schedule a meeting with the development team tomorrow at 3 PM.")}
          className="text-xs bg-slate-900 hover:bg-slate-800 text-teal-300 border border-teal-500/30 rounded-full px-3 py-1 shrink-0 transition-colors flex items-center gap-1.5"
        >
          <Calendar className="w-3 h-3" /> Schedule Meeting (Calendar)
        </button>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto space-y-6 pr-2">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`flex items-start gap-3.5 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {m.role === 'assistant' && (
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-500 flex items-center justify-center shrink-0 shadow-md shadow-emerald-500/20">
                <Bot className="w-5 h-5 text-white" />
              </div>
            )}

            <div className={`max-w-3xl space-y-3 ${
              m.role === 'user'
                ? 'bg-emerald-500 text-slate-950 px-4 py-3 rounded-2xl rounded-tr-none font-medium text-sm shadow-md'
                : 'glass-panel p-5 rounded-2xl rounded-tl-none border border-slate-800 text-sm text-slate-200'
            }`}>
              {/* Message Content */}
              {m.role === 'user' ? (
                <div className="whitespace-pre-wrap leading-relaxed">
                  {m.content}
                </div>
              ) : (
                <MarkdownMessage content={m.content} />
              )}

              {/* Collapsible Tool Invocations Badge */}
              {m.tool_calls && m.tool_calls.length > 0 && (
                <div className="mt-3 pt-3 border-t border-slate-800/80">
                  <div className="text-[11px] font-mono text-slate-400 mb-1 flex items-center gap-1.5">
                    <Layers className="w-3.5 h-3.5 text-sky-400" />
                    <span>MCP Tools Discovered & Executed ({m.tool_calls.length}):</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {m.tool_calls.map((tc, idx) => (
                      <span key={idx} className="text-[11px] font-mono bg-slate-900 border border-slate-800 px-2 py-0.5 rounded text-sky-300">
                        {tc.tool}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Inline Approval Gate Card */}
              {m.pending_approval && (
                <div className="mt-4">
                  <ApprovalCard
                    approval={m.pending_approval}
                    onApprove={handleInlineApprove}
                    onReject={handleInlineReject}
                  />
                </div>
              )}
            </div>

            {m.role === 'user' && (
              <div className="w-9 h-9 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0">
                <UserIcon className="w-5 h-5 text-slate-300" />
              </div>
            )}
          </div>
        ))}

        {/* Streaming / Loading Indicator */}
        {isLoading && (
          <div className="flex items-start gap-3.5">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-500 flex items-center justify-center shrink-0 animate-pulse">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div className="glass-panel p-4 rounded-2xl rounded-tl-none border border-slate-800 text-xs text-slate-300 flex items-center gap-3">
              <Loader2 className="w-4 h-4 text-emerald-400 animate-spin" />
              <span className="font-mono">{activeStep || 'Reasoning over live FastMCP tools...'}</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Box */}
      <div className="pt-4 shrink-0">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="relative flex items-center"
        >
          <input
            id="input-chat-message"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
            placeholder="Ask about incidents, check GitHub issues, schedule meetings, or request actions..."
            className="w-full bg-slate-900/90 border border-slate-800 focus:border-emerald-500 rounded-2xl pl-5 pr-28 py-3.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 transition-all shadow-inner"
          />
          <button
            id="btn-send-message"
            type="submit"
            disabled={isLoading || !input.trim()}
            className="absolute right-2 flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold bg-emerald-500 text-slate-950 hover:bg-emerald-400 disabled:opacity-40 disabled:hover:bg-emerald-500 transition-all shadow-md shadow-emerald-500/20"
          >
            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            <span>Execute</span>
          </button>
        </form>
        <p className="text-[11px] text-slate-500 text-center mt-2 font-mono">
          Strict Policy: Read tools execute immediately. Write tools require explicit human approval before touching external systems.
        </p>
      </div>
    </div>
  );
};
