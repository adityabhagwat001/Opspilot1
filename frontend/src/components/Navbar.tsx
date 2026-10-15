import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { 
  Bot, 
  LayoutDashboard, 
  ShieldCheck, 
  Blocks, 
  ScrollText, 
  LogOut, 
  Terminal,
  GitBranch
} from 'lucide-react';
import { User } from '../types';

interface NavbarProps {
  user: User | null;
  pendingApprovalsCount: number;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ user, pendingApprovalsCount, onLogout }) => {
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-50 border-b border-slate-800/80 bg-[#070b14]/90 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand Logo */}
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => navigate('/')}>
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <Terminal className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-xl tracking-tight text-white">OPS<span className="text-emerald-400">PILOT</span></span>
                <span className="text-[10px] font-semibold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-1.5 py-0.5 rounded-full">
                  FastMCP
                </span>
              </div>
              <p className="text-[11px] text-slate-400 -mt-1 font-mono">Enterprise AI Operations</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1">
            <NavLink
              to="/"
              id="nav-dashboard"
              className={({ isActive }) =>
                `flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-slate-800/80 text-emerald-400 shadow-sm border border-slate-700/60'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                }`
              }
            >
              <LayoutDashboard className="w-4 h-4" />
              <span>Dashboard</span>
            </NavLink>

            <NavLink
              to="/chat"
              id="nav-assistant"
              className={({ isActive }) =>
                `flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-slate-800/80 text-emerald-400 shadow-sm border border-slate-700/60'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                }`
              }
            >
              <Bot className="w-4 h-4" />
              <span>AI Assistant</span>
            </NavLink>

            <NavLink
              to="/approvals"
              id="nav-approvals"
              className={({ isActive }) =>
                `flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium relative transition-all ${
                  isActive
                    ? 'bg-slate-800/80 text-amber-400 shadow-sm border border-slate-700/60'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                }`
              }
            >
              <ShieldCheck className="w-4 h-4" />
              <span>Approval Center</span>
              {pendingApprovalsCount > 0 && (
                <span className="flex items-center justify-center text-[10px] font-bold bg-amber-500 text-slate-950 px-1.5 py-0.5 rounded-full animate-pulse">
                  {pendingApprovalsCount}
                </span>
              )}
            </NavLink>

            <NavLink
              to="/github"
              id="nav-github"
              className={({ isActive }) =>
                `flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-slate-800/80 text-emerald-400 shadow-sm border border-slate-700/60'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                }`
              }
            >
              <GitBranch className="w-4 h-4" />
              <span>GitHub DevOps</span>
            </NavLink>

            <NavLink
              to="/integrations"
              id="nav-integrations"
              className={({ isActive }) =>
                `flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-slate-800/80 text-emerald-400 shadow-sm border border-slate-700/60'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                }`
              }
            >
              <Blocks className="w-4 h-4" />
              <span>Integrations</span>
            </NavLink>

            <NavLink
              to="/audit"
              id="nav-audit"
              className={({ isActive }) =>
                `flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-slate-800/80 text-emerald-400 shadow-sm border border-slate-700/60'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40'
                }`
              }
            >
              <ScrollText className="w-4 h-4" />
              <span>Audit Log</span>
            </NavLink>
          </nav>

          {/* User profile & controls */}
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-300">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              <span className="font-mono text-emerald-400">Live MCP Mesh</span>
            </div>

            {user ? (
              <div className="flex items-center gap-2">
                <div className="text-right hidden sm:block">
                  <p className="text-xs font-semibold text-slate-200">{user.full_name}</p>
                  <p className="text-[10px] uppercase tracking-wider text-slate-400 font-mono">{user.role}</p>
                </div>
                <button
                  id="btn-logout"
                  onClick={onLogout}
                  title="Logout"
                  className="p-2 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            ) : (
              <NavLink
                to="/login"
                id="btn-nav-login"
                className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition-colors"
              >
                Sign In
              </NavLink>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
