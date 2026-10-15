import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Blocks, 
  Database, 
  GitBranch, 
  Mail, 
  Calendar,
  ArrowRight
} from 'lucide-react';
import { api } from '../services/api';
import { Integration } from '../types';

const fetchClientTools = async () => {
  try {
    const tools = await fetch('/api/integrations/tools', {
      headers: { Authorization: `Bearer ${localStorage.getItem('opspilot_token') || ''}` }
    }).then(r => r.json());
    return tools.tools || [];
  } catch {
    return [];
  }
};

export const IntegrationsPage: React.FC = () => {
  const navigate = useNavigate();
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [totalTools, setTotalTools] = useState<number>(0);
  const [toolsList, setToolsList] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    const fetchData = async () => {
      try {
        const [integRes, toolsRes] = await Promise.all([
          api.getIntegrations(),
          fetchClientTools()
        ]);
        if (isMounted) {
          setIntegrations(integRes.integrations);
          setTotalTools(integRes.total_tools);
          setToolsList(toolsRes);
        }
      } catch (err) {
        console.error('Failed to load integrations:', err);
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };
    fetchData();
    return () => {
      isMounted = false;
    };
  }, []);

  const getIcon = (provider: string) => {
    switch (provider.toLowerCase()) {
      case 'postgresql': return <Database className="w-6 h-6 text-sky-400" />;
      case 'github': return <GitBranch className="w-6 h-6 text-purple-400" />;
      case 'email': return <Mail className="w-6 h-6 text-amber-400" />;
      case 'calendar': return <Calendar className="w-6 h-6 text-emerald-400" />;
      default: return <Blocks className="w-6 h-6 text-emerald-400" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="w-10 h-10 border-4 border-emerald-500/20 border-t-emerald-400 rounded-full animate-spin mx-auto mb-3"></div>
          <p className="text-sm text-slate-400 font-mono">Discovering MCP Integrations & Tool Registry...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-black text-white">Connected Systems & FastMCP Servers</h1>
        <p className="text-xs text-slate-400 mt-1">
          OpsPilot connects directly to live enterprise systems using custom Model Context Protocol (MCP) servers with dynamic tool discovery.
        </p>
      </div>

      {/* Integration Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {integrations.map((item) => (
          <div key={item.id} className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3.5">
                <div className="p-3 rounded-xl bg-slate-900 border border-slate-800">
                  {getIcon(item.provider)}
                </div>
                <div>
                  <h3 className="text-base font-bold text-white capitalize">{item.name}</h3>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="flex items-center gap-1 text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                      FastMCP Active
                    </span>
                    <span className="text-[11px] font-mono text-slate-400">
                      {item.tool_count} Tools Exposed
                    </span>
                  </div>
                </div>
              </div>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
              {item.notes}
            </p>

            <div>
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Exposed MCP Tools:
              </div>
              <div className="flex flex-wrap gap-1.5">
                {item.tools.map((t) => (
                  <span key={t} className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300">
                    {t}
                  </span>
                ))}
              </div>
            </div>

            {item.provider.toLowerCase() === 'github' && (
              <div className="pt-2 border-t border-slate-800/80">
                <button
                  id="btn-manage-github-intelligence"
                  onClick={() => navigate('/github')}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-purple-500/10 text-purple-300 border border-purple-500/30 hover:bg-purple-500/20 transition-all shadow-sm"
                >
                  <GitBranch className="w-4 h-4 text-purple-400" />
                  <span>Launch GitHub Intelligence & CI/CD DevOps</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Complete FastMCP Tool Mesh */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-white">Full FastMCP Tool Registry ({totalTools || toolsList.length || 33} Tools)</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Categorized into safe read operations and protected write operations.
            </p>
          </div>
          <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2.5 py-1 rounded-lg border border-emerald-500/20">
            Model Context Protocol v1.0
          </span>
        </div>

        <div className="divide-y divide-slate-800 max-h-96 overflow-y-auto pr-2">
          {toolsList.map((tool, idx) => (
            <div key={idx} className="py-3 flex items-start justify-between gap-4 text-xs">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono font-bold text-white text-sm">{tool.name}</span>
                  <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded font-bold ${
                    tool.is_write 
                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30' 
                      : 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                  }`}>
                    {tool.is_write ? 'PROTECTED WRITE' : 'READ-ONLY'}
                  </span>
                  <span className="text-[10px] font-mono text-slate-400 uppercase bg-slate-900 px-1.5 py-0.5 rounded">
                    {tool.system}
                  </span>
                </div>
                <p className="text-slate-400 mt-1">{tool.description}</p>
              </div>

              {tool.requires_approval && (
                <span className="shrink-0 text-[10px] font-bold text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-1 rounded">
                  Approval Required
                </span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
