import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { DashboardPage } from './pages/DashboardPage';
import { ChatPage } from './pages/ChatPage';
import { ApprovalsPage } from './pages/ApprovalsPage';
import { IntegrationsPage } from './pages/IntegrationsPage';
import { GitHubDevOpsPage } from './pages/GitHubDevOpsPage';
import { AuditPage } from './pages/AuditPage';
import { LoginPage } from './pages/LoginPage';
import { api } from './services/api';
import { User } from './types';

export const App: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [pendingApprovalsCount, setPendingApprovalsCount] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;
    const initSession = async () => {
      const token = localStorage.getItem('opspilot_token');
      if (!token) {
        if (isMounted) {
          setUser(null);
          setLoading(false);
        }
        return;
      }

      try {
        const u = await api.getMe();
        if (isMounted) setUser(u);
      } catch {
        localStorage.removeItem('opspilot_token');
        if (isMounted) setUser(null);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    void initSession();
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (!user) return;
    let isMounted = true;
    const pollPending = async () => {
      if (!localStorage.getItem('opspilot_token')) {
        if (isMounted) setPendingApprovalsCount(0);
        return;
      }
      try {
        const apps = await api.getApprovals('pending');
        if (isMounted) setPendingApprovalsCount(apps.length);
      } catch {
        // ignore
      }
    };

    void pollPending();
    const interval = setInterval(() => {
      void pollPending();
    }, 10000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [user]);

  const handleLogout = () => {
    localStorage.removeItem('opspilot_token');
    setUser(null);
    setPendingApprovalsCount(0);
  };

  const handleLoginSuccess = (loggedInUser: User) => {
    setUser(loggedInUser);
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
        {user && (
          <Navbar
            user={user}
            pendingApprovalsCount={pendingApprovalsCount}
            onLogout={handleLogout}
          />
        )}

        <main className="flex-1">
          <Routes>
            <Route
              path="/login"
              element={
                user ? <Navigate to="/" replace /> : <LoginPage onLoginSuccess={handleLoginSuccess} />
              }
            />
            {user ? (
              <>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/chat" element={<ChatPage />} />
                <Route path="/approvals" element={<ApprovalsPage />} />
                <Route path="/github" element={<GitHubDevOpsPage />} />
                <Route path="/integrations" element={<IntegrationsPage />} />
                <Route path="/audit" element={<AuditPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </>
            ) : (
              <Route path="*" element={<Navigate to="/login" replace />} />
            )}
          </Routes>
        </main>
      </div>
    </Router>
  );
};

export default App;
