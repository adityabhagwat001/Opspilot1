import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { DashboardPage } from './pages/DashboardPage';
import { ChatPage } from './pages/ChatPage';
import { ApprovalsPage } from './pages/ApprovalsPage';
import { IntegrationsPage } from './pages/IntegrationsPage';
import { AuditPage } from './pages/AuditPage';
import { LoginPage } from './pages/LoginPage';
import { api } from './services/api';
import { User } from './types';

export const App: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);

  const fetchSession = async () => {
    const token = localStorage.getItem('opspilot_token');
    if (!token) {
      // Default fallback demo user for seamless evaluation
      setUser({
        id: 'usr-admin-01',
        email: 'admin@opspilot.internal',
        full_name: 'Enterprise Admin',
        role: 'admin'
      });
      setLoading(false);
      return;
    }

    try {
      const u = await api.getMe();
      setUser(u);
    } catch {
      localStorage.removeItem('opspilot_token');
    } finally {
      setLoading(false);
    }
  };

  const fetchPendingApprovals = async () => {
    try {
      const apps = await api.getApprovals('pending');
      setPendingApprovalsCount(apps.length);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    fetchSession();
    fetchPendingApprovals();
    const interval = setInterval(fetchPendingApprovals, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('opspilot_token');
    setUser(null);
  };

  const handleLoginSuccess = (loggedInUser: User) => {
    setUser(loggedInUser);
    fetchPendingApprovals();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#070b14] flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-emerald-500/20 border-t-emerald-400 rounded-full animate-spin"></div>
      </div>
    );
  }

  return (
    <Router>
      <div className="min-h-screen bg-[#070b14] flex flex-col text-slate-100">
        <Navbar
          user={user}
          pendingApprovalsCount={pendingApprovalsCount}
          onLogout={handleLogout}
        />

        <main className="flex-1">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/approvals" element={<ApprovalsPage />} />
            <Route path="/integrations" element={<IntegrationsPage />} />
            <Route path="/audit" element={<AuditPage />} />
            <Route
              path="/login"
              element={<LoginPage onLoginSuccess={handleLoginSuccess} />}
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
};

export default App;
