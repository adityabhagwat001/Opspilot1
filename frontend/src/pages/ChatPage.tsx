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
  Layers,
  Plus,
  MessageSquare,
  Trash2,
  Edit2,
  Check,
  X,
  Search,
  PanelLeftClose,
  PanelLeftOpen,
  Terminal,
  ShieldCheck
} from 'lucide-react';
import { api } from '../services/api';
import { ApprovalCard } from '../components/ApprovalCard';
import { MarkdownMessage } from '../components/MarkdownMessage';
import { ChatMessage, Conversation, User } from '../types';

const INITIAL_WELCOME: ChatMessage = {
  id: 'welcome',
  role: 'assistant',
  content: "Hello, I am **OpsPilot**, your autonomous enterprise operations assistant connected through live FastMCP servers.\n\nI can retrieve authorized data from PostgreSQL, GitHub, email, and calendar, reason across multiple systems, and execute approved actions. Every write strictly requires your approval before touching any system.",
  timestamp: new Date().toISOString()
};

const SUGGESTED_PROMPTS = [
  {
    icon: Database,
    title: 'PostgreSQL Incidents',
    desc: 'Query unresolved database incidents and active tasks',
    prompt: 'Show me all open operational incidents and active tasks from the PostgreSQL database.'
  },
  {
    icon: GitBranch,
    title: 'GitHub Intelligence',
    desc: 'Inspect PRs, open issues, and CI/CD workflow runs',
    prompt: 'Check recent pull requests and workflow runs in my repository, and summarize any failures.'
  },
  {
    icon: Mail,
    title: 'Operational Email',
    desc: 'Draft and review operations alerts before sending',
    prompt: 'Draft an email to engineering-team@enterprise.internal regarding canary deployment status.'
  },
  {
    icon: Calendar,
    title: 'Schedule Operations Standup',
    desc: 'Check team calendar availability and create invite',
    prompt: 'Schedule an operational standup meeting for tomorrow at 3 PM UTC with the DevOps on-call team.'
  }
];

export const ChatPage: React.FC = () => {
  const location = useLocation();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(() => {
    return localStorage.getItem('opspilot_active_chat_id') || null;
  });
  const [messages, setMessages] = useState<ChatMessage[]>([INITIAL_WELCOME]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [isLoadingConvs, setIsLoadingConvs] = useState(false);
  const [activeStep, setActiveStep] = useState<string>('');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [editingConvId, setEditingConvId] = useState<string | null>(null);
  const [editTitleInput, setEditTitleInput] = useState('');
  const [currentUser, setCurrentUser] = useState<User | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const handledPromptRef = useRef<string | null>(null);

  // Load current user profile for sidebar bottom
  useEffect(() => {
    api.getMe()
      .then((u) => setCurrentUser(u))
      .catch(() => setCurrentUser(null));
  }, []);

  // Fetch all conversations from backend
  const loadConversations = useCallback(async (selectId?: string) => {
    setIsLoadingConvs(true);
    try {
      const convs = await api.getConversations();
      setConversations(convs);

      // If a selectId was requested, select it
      if (selectId) {
        setActiveConvId(selectId);
        localStorage.setItem('opspilot_active_chat_id', selectId);
      } else if (convs.length > 0 && !activeConvId && !localStorage.getItem('opspilot_new_chat_requested')) {
        // Auto-select most recent conversation
        const latestId = convs[0].id;
        setActiveConvId(latestId);
        localStorage.setItem('opspilot_active_chat_id', latestId);
      }
    } catch (err) {
      console.error('Failed to load conversations:', err);
    } finally {
      setIsLoadingConvs(false);
    }
  }, [activeConvId]);

  useEffect(() => {
    void loadConversations();
  }, [loadConversations]);

  // Load messages whenever active conversation changes
  useEffect(() => {
    if (!activeConvId) {
      setMessages([INITIAL_WELCOME]);
      return;
    }

    let isCurrent = true;
    setIsLoadingMessages(true);

    api.getMessages(activeConvId)
      .then((msgs) => {
        if (!isCurrent) return;
        if (!msgs || msgs.length === 0) {
          setMessages([INITIAL_WELCOME]);
        } else {
          const mapped: ChatMessage[] = msgs.map((m: any) => ({
            id: m.id || `msg-${Math.random()}`,
            role: m.role,
            content: m.content,
            tool_calls: m.tool_calls,
            tool_results: m.tool_results,
            pending_approval: null,
            timestamp: m.created_at || m.timestamp || new Date().toISOString()
          }));
          setMessages(mapped);
        }
      })
      .catch((err) => {
        if (!isCurrent) return;
        console.error('Failed to load messages for conversation:', err);
        setMessages([
          INITIAL_WELCOME,
          {
            id: 'err-load',
            role: 'assistant',
            content: '**Notice:** Could not load full history for this session. You can continue sending messages or start a New Chat.',
            timestamp: new Date().toISOString()
          }
        ]);
      })
      .finally(() => {
        if (isCurrent) setIsLoadingMessages(false);
      });

    return () => {
      isCurrent = false;
    };
  }, [activeConvId]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, activeStep]);

  // Handle starting a fresh New Chat
  const handleNewChat = useCallback(() => {
    setActiveConvId(null);
    localStorage.removeItem('opspilot_active_chat_id');
    localStorage.setItem('opspilot_new_chat_requested', 'true');
    setMessages([INITIAL_WELCOME]);
    setInput('');
    setTimeout(() => {
      inputRef.current?.focus();
    }, 50);
  }, []);

  // Handle selecting a past conversation from sidebar
  const handleSelectConversation = (convId: string) => {
    if (convId === activeConvId) return;
    localStorage.removeItem('opspilot_new_chat_requested');
    localStorage.setItem('opspilot_active_chat_id', convId);
    setActiveConvId(convId);
  };

  // Handle deleting a conversation
  const handleDeleteConversation = async (e: React.MouseEvent, convId: string) => {
    e.stopPropagation();
    if (!window.confirm('Delete this conversation history? This cannot be undone.')) {
      return;
    }
    try {
      await api.deleteConversation(convId);
      setConversations((prev) => prev.filter((c) => c.id !== convId));
      if (activeConvId === convId) {
        handleNewChat();
      }
    } catch (err: any) {
      alert(`Failed to delete conversation: ${err?.response?.data?.detail || err.message}`);
    }
  };

  // Handle renaming conversation
  const handleStartRename = (e: React.MouseEvent, conv: Conversation) => {
    e.stopPropagation();
    setEditingConvId(conv.id);
    setEditTitleInput(conv.title);
  };

  const handleSaveRename = async (e: React.MouseEvent | React.FormEvent, convId: string) => {
    e.stopPropagation();
    if (!editTitleInput.trim()) {
      setEditingConvId(null);
      return;
    }
    try {
      await api.updateConversationTitle(convId, editTitleInput.trim());
      setConversations((prev) =>
        prev.map((c) => (c.id === convId ? { ...c, title: editTitleInput.trim() } : c))
      );
      setEditingConvId(null);
    } catch (err: any) {
      alert(`Failed to rename conversation: ${err?.response?.data?.detail || err.message}`);
    }
  };

  // Send message
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
    setActiveStep('Analyzing intent & discovering FastMCP tools...');

    try {
      // Send message with current active conversation ID (or undefined for new thread)
      const res = await api.sendMessage(textToSend, activeConvId || undefined);

      // If a new conversation was created on the backend, update state and refresh sidebar
      if (res.conversation_id && res.conversation_id !== activeConvId) {
        setActiveConvId(res.conversation_id);
        localStorage.setItem('opspilot_active_chat_id', res.conversation_id);
        localStorage.removeItem('opspilot_new_chat_requested');
        void loadConversations(res.conversation_id);
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
  }, [input, isLoading, activeConvId, loadConversations]);

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

  const handleInlineApprove = async (approvalId: string) => {
    try {
      const res = await api.approveAction(approvalId);
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

  // Filter conversations based on search
  const filteredConversations = conversations.filter((c) =>
    c.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const activeConv = conversations.find((c) => c.id === activeConvId);

  return (
    <div className="flex h-[calc(100vh-4rem)] bg-[#070b14] overflow-hidden">
      {/* =========================================================================
          LEFT SIDEBAR: ChatGPT-style Past History & New Chat
      ========================================================================= */}
      <aside
        className={`${
          sidebarOpen ? 'w-72 md:w-80' : 'w-0'
        } shrink-0 bg-[#0b1120] border-r border-slate-800/80 flex flex-col transition-all duration-200 ease-in-out overflow-hidden z-20`}
      >
        <div className="p-3.5 flex flex-col h-full">
          {/* Top Header: Branding + New Chat Button */}
          <div className="flex items-center justify-between pb-3 border-b border-slate-800/70">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center shadow-sm shadow-emerald-500/20">
                <Terminal className="w-4 h-4 text-slate-950" />
              </div>
              <span className="font-semibold text-sm text-slate-200 tracking-tight">OpsPilot Chat</span>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 rounded-lg transition-colors md:hidden"
              title="Close sidebar"
            >
              <PanelLeftClose className="w-4 h-4" />
            </button>
          </div>

          {/* New Chat Primary Button */}
          <div className="pt-3 pb-2">
            <button
              id="btn-new-chat"
              onClick={handleNewChat}
              className="w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl bg-slate-900/90 hover:bg-slate-800 border border-slate-700/60 hover:border-emerald-500/50 text-slate-200 hover:text-white transition-all shadow-sm group"
            >
              <div className="flex items-center gap-2.5 text-sm font-medium">
                <div className="w-6 h-6 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center group-hover:bg-emerald-500 group-hover:text-slate-950 transition-colors">
                  <Plus className="w-4 h-4" />
                </div>
                <span>New chat</span>
              </div>
              <span className="text-[11px] font-mono text-slate-500 bg-slate-800/80 px-1.5 py-0.5 rounded border border-slate-700/50 group-hover:text-slate-300">
                + fresh
              </span>
            </button>
          </div>

          {/* Search Conversations Input */}
          <div className="py-1">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search past chats..."
                className="w-full bg-slate-900/60 border border-slate-800/80 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-300 placeholder-slate-500 focus:outline-none focus:border-emerald-500/50 transition-colors"
              />
            </div>
          </div>

          {/* Recents Section Header */}
          <div className="px-1 pt-3 pb-1 flex items-center justify-between text-[11px] font-mono font-medium text-slate-500 uppercase tracking-wider">
            <span>Recent Chats</span>
            <span className="text-[10px] text-slate-500">
              {filteredConversations.length} {filteredConversations.length === 1 ? 'chat' : 'chats'}
            </span>
          </div>

          {/* Conversation History List */}
          <div className="flex-1 overflow-y-auto space-y-1 pr-1 -mr-1 custom-scrollbar">
            {isLoadingConvs && conversations.length === 0 ? (
              <div className="py-8 flex flex-col items-center justify-center text-xs text-slate-500 gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-emerald-400" />
                <span>Loading past history...</span>
              </div>
            ) : filteredConversations.length === 0 ? (
              <div className="py-8 text-center text-xs text-slate-500 px-4">
                {searchQuery ? 'No chats matched your search.' : 'No saved conversations yet. Click "New chat" to begin!'}
              </div>
            ) : (
              filteredConversations.map((conv) => {
                const isActive = conv.id === activeConvId;
                const isEditing = editingConvId === conv.id;

                return (
                  <div
                    key={conv.id}
                    onClick={() => handleSelectConversation(conv.id)}
                    className={`group relative flex items-center justify-between px-3 py-2.5 rounded-xl cursor-pointer text-xs transition-all ${
                      isActive
                        ? 'bg-slate-800/90 text-white font-medium border-l-2 border-emerald-400 shadow-sm'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-850/60 hover:bg-slate-800/40'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 min-w-0 flex-1 mr-2">
                      <MessageSquare className={`w-3.5 h-3.5 shrink-0 ${isActive ? 'text-emerald-400' : 'text-slate-500 group-hover:text-slate-400'}`} />
                      
                      {isEditing ? (
                        <div className="flex items-center gap-1 flex-1" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="text"
                            value={editTitleInput}
                            onChange={(e) => setEditTitleInput(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') void handleSaveRename(e, conv.id);
                              if (e.key === 'Escape') setEditingConvId(null);
                            }}
                            autoFocus
                            className="w-full bg-slate-900 border border-emerald-500/50 rounded px-1.5 py-0.5 text-xs text-white focus:outline-none"
                          />
                          <button
                            onClick={(e) => void handleSaveRename(e, conv.id)}
                            className="p-1 text-emerald-400 hover:text-emerald-300"
                            title="Save"
                          >
                            <Check className="w-3 h-3" />
                          </button>
                          <button
                            onClick={() => setEditingConvId(null)}
                            className="p-1 text-slate-400 hover:text-slate-300"
                            title="Cancel"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </div>
                      ) : (
                        <span className="truncate text-left select-none" title={conv.title}>
                          {conv.title}
                        </span>
                      )}
                    </div>

                    {/* Action buttons (Rename / Delete) visible on hover or active */}
                    {!isEditing && (
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                        <button
                          onClick={(e) => handleStartRename(e, conv)}
                          className="p-1 text-slate-400 hover:text-slate-200 hover:bg-slate-700/60 rounded"
                          title="Rename chat"
                        >
                          <Edit2 className="w-3 h-3" />
                        </button>
                        <button
                          onClick={(e) => void handleDeleteConversation(e, conv.id)}
                          className="p-1 text-slate-400 hover:text-rose-400 hover:bg-slate-700/60 rounded"
                          title="Delete chat"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>

          {/* Bottom Profile Bar */}
          <div className="pt-3 border-t border-slate-800/70 mt-auto">
            <div className="flex items-center justify-between px-2 py-1.5 rounded-xl bg-slate-900/60 border border-slate-800/80">
              <div className="flex items-center gap-2 min-w-0">
                <div className="w-7 h-7 rounded-lg bg-emerald-500/20 border border-emerald-500/30 text-emerald-400 font-bold text-xs flex items-center justify-center shrink-0">
                  {currentUser?.full_name ? currentUser.full_name.slice(0, 2).toUpperCase() : 'OP'}
                </div>
                <div className="min-w-0">
                  <div className="text-xs font-medium text-slate-200 truncate">
                    {currentUser?.full_name || 'Enterprise Admin'}
                  </div>
                  <div className="text-[10px] font-mono text-emerald-400 flex items-center gap-1">
                    <ShieldCheck className="w-2.5 h-2.5" />
                    <span className="uppercase">{currentUser?.role || 'Admin'}</span>
                  </div>
                </div>
              </div>
              <button
                onClick={handleNewChat}
                className="p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-slate-800 rounded-lg transition-colors"
                title="Start a new chat"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </aside>

      {/* =========================================================================
          MAIN CHAT PANEL
      ========================================================================= */}
      <main className="flex-1 flex flex-col h-full overflow-hidden relative">
        {/* Top Header Bar */}
        <div className="h-14 border-b border-slate-800/80 px-4 flex items-center justify-between shrink-0 bg-[#070b14]/90 backdrop-blur-md">
          <div className="flex items-center gap-3 min-w-0">
            <button
              onClick={() => setSidebarOpen((prev) => !prev)}
              className="p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800/70 rounded-xl transition-colors border border-slate-800/80"
              title={sidebarOpen ? 'Collapse sidebar' : 'Open history sidebar'}
            >
              {sidebarOpen ? <PanelLeftClose className="w-4 h-4" /> : <PanelLeftOpen className="w-4 h-4 text-emerald-400" />}
            </button>
            <div className="min-w-0 flex items-center gap-2">
              <span className="text-sm font-semibold text-slate-200 truncate">
                {activeConv ? activeConv.title : 'New Operations Chat'}
              </span>
              {activeConv && (
                <span className="text-[10px] font-mono text-slate-500 bg-slate-900 border border-slate-800 px-2 py-0.5 rounded-full shrink-0">
                  ID: {activeConv.id.slice(0, 8)}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={handleNewChat}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-300 hover:text-white bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 rounded-xl transition-all shadow-sm"
            >
              <Plus className="w-3.5 h-3.5 text-emerald-400" />
              <span>New chat</span>
            </button>
          </div>
        </div>

        {/* Quick Scenario Pills */}
        <div className="px-4 py-2 border-b border-slate-800/50 bg-[#090d18]/60 flex items-center gap-2 overflow-x-auto no-scrollbar shrink-0">
          <span className="text-[11px] font-mono text-slate-400 uppercase tracking-wider shrink-0 flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-emerald-400" /> Scenarios:
          </span>
          <button
            onClick={() => handleSend("Show me all open operational incidents from the database.")}
            className="text-xs bg-slate-900/90 hover:bg-slate-800 text-sky-300 border border-slate-800 rounded-full px-3 py-1 shrink-0 transition-colors flex items-center gap-1.5"
          >
            <Database className="w-3 h-3" /> Incidents (PostgreSQL)
          </button>
          <button
            onClick={() => handleSend("Check the open issues in my repository and identify the highest-priority problems.")}
            className="text-xs bg-slate-900/90 hover:bg-slate-800 text-purple-300 border border-slate-800 rounded-full px-3 py-1 shrink-0 transition-colors flex items-center gap-1.5"
          >
            <GitBranch className="w-3 h-3" /> Open Issues (GitHub)
          </button>
          <button
            onClick={() => handleSend("Create a GitHub issue for fixing the authentication timeout.")}
            className="text-xs bg-slate-900/90 hover:bg-slate-800 text-amber-300 border border-amber-500/30 rounded-full px-3 py-1 shrink-0 transition-colors flex items-center gap-1.5"
          >
            <GitBranch className="w-3 h-3" /> Create Issue (Write Approval)
          </button>
          <button
            onClick={() => handleSend("Find important unread emails related to deployment problems.")}
            className="text-xs bg-slate-900/90 hover:bg-slate-800 text-emerald-300 border border-slate-800 rounded-full px-3 py-1 shrink-0 transition-colors flex items-center gap-1.5"
          >
            <Mail className="w-3 h-3" /> Unread Mail (Email)
          </button>
          <button
            onClick={() => handleSend("Schedule a meeting with the development team tomorrow at 3 PM.")}
            className="text-xs bg-slate-900/90 hover:bg-slate-800 text-teal-300 border border-teal-500/30 rounded-full px-3 py-1 shrink-0 transition-colors flex items-center gap-1.5"
          >
            <Calendar className="w-3 h-3" /> Schedule Meeting (Calendar)
          </button>
        </div>

        {/* Scrollable Messages Thread Area */}
        <div className="flex-1 overflow-y-auto px-4 md:px-8 py-6 space-y-6">
          {isLoadingMessages ? (
            <div className="py-20 flex flex-col items-center justify-center text-slate-400 gap-3">
              <Loader2 className="w-6 h-6 animate-spin text-emerald-400" />
              <span className="text-sm font-mono">Restoring conversation history...</span>
            </div>
          ) : messages.length === 1 && messages[0].id === 'welcome' && !activeConvId ? (
            /* ChatGPT-like Empty State / Starter Hero */
            <div className="max-w-3xl mx-auto py-8 md:py-12 flex flex-col items-center text-center">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/25 mb-4">
                <Bot className="w-8 h-8 text-slate-950" />
              </div>
              <h2 className="text-xl md:text-2xl font-bold text-white mb-2 tracking-tight">
                Where should we begin?
              </h2>
              <p className="text-sm text-slate-400 max-w-lg mb-8 leading-relaxed">
                OpsPilot autonomously queries your PostgreSQL operational database, GitHub repositories, Gmail SMTP, and calendar events through secure FastMCP tools.
              </p>

              {/* 4 Interactive Starter Prompt Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full text-left">
                {SUGGESTED_PROMPTS.map((card, idx) => {
                  const CardIcon = card.icon;
                  return (
                    <button
                      key={idx}
                      onClick={() => handleSend(card.prompt)}
                      className="p-4 rounded-2xl bg-slate-900/70 hover:bg-slate-850 border border-slate-800/80 hover:border-emerald-500/40 transition-all text-left group shadow-sm flex flex-col justify-between"
                    >
                      <div>
                        <div className="flex items-center gap-2 mb-1.5">
                          <CardIcon className="w-4 h-4 text-emerald-400" />
                          <span className="font-semibold text-xs text-slate-200 group-hover:text-emerald-300 transition-colors">
                            {card.title}
                          </span>
                        </div>
                        <p className="text-xs text-slate-400 leading-snug">
                          {card.desc}
                        </p>
                      </div>
                      <span className="text-[11px] font-mono text-emerald-400/70 group-hover:text-emerald-400 mt-3 flex items-center gap-1">
                        Run scenario &rarr;
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          ) : (
            /* Rendered Message List */
            <div className="max-w-4xl mx-auto space-y-6">
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
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* =========================================================================
            BOTTOM INPUT BOX: ChatGPT Style
        ========================================================================= */}
        <div className="p-4 shrink-0 border-t border-slate-800/80 bg-[#070b14]/95 backdrop-blur-md">
          <div className="max-w-4xl mx-auto">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void handleSend();
              }}
              className="relative flex items-center"
            >
              <input
                ref={inputRef}
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
      </main>
    </div>
  );
};
