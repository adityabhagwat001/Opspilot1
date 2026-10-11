import React, { useState, useEffect } from 'react';
import { 
  Activity, 
  Server, 
  Cpu, 
  HardDrive, 
  Clock, 
  RefreshCw, 
  ExternalLink, 
  Terminal,
  Zap
} from 'lucide-react';

interface SystemMetrics {
  cpu_percent: number;
  memory_used_mb: number;
  memory_total_mb: number;
  memory_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  disk_percent: number;
  platform: string;
}

interface HealthData {
  status: string;
  version: string;
  service: string;
  environment: string;
  timestamp: string;
  uptime_seconds: number;
  dependencies: {
    database: string;
    cache: string;
    telemetry_bus: string;
  };
  system_metrics?: SystemMetrics;
}

interface LogEntry {
  id: string;
  timestamp: string;
  level: 'info' | 'success' | 'warn';
  message: string;
}

export const App: React.FC = () => {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [backendOnline, setBackendOnline] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [currentTime, setCurrentTime] = useState<string>(new Date().toISOString().slice(11, 19) + ' UTC');

  // Clock ticker
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date().toISOString().slice(11, 19) + ' UTC');
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const addLog = (level: 'info' | 'success' | 'warn', message: string) => {
    const newEntry: LogEntry = {
      id: Math.random().toString(36).substring(7),
      timestamp: new Date().toISOString().slice(11, 19),
      level,
      message,
    };
    setLogs((prev) => [newEntry, ...prev.slice(0, 40)]);
  };

  const fetchHealth = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/v1/health');
      if (res.ok) {
        const data: HealthData = await res.json();
        setHealth(data);
        setBackendOnline(true);
        addLog('success', `Healthcheck probe acknowledged: 200 OK (${data.service} v${data.version})`);
      } else {
        throw new Error(`Server returned ${res.status}`);
      }
    } catch (err: any) {
      setBackendOnline(false);
      // Fallback baseline for local demonstration when backend server is starting
      setHealth({
        status: 'standby',
        version: '0.1.0-alpha',
        service: 'OpsPilot Core (Local Mock)',
        environment: 'development',
        timestamp: new Date().toISOString(),
        uptime_seconds: 342.1,
        dependencies: {
          database: 'ready',
          cache: 'ready',
          telemetry_bus: 'active',
        },
        system_metrics: {
          cpu_percent: 18.4,
          memory_used_mb: 4820,
          memory_total_mb: 16384,
          memory_percent: 29.4,
          disk_used_gb: 124.5,
          disk_total_gb: 512.0,
          disk_percent: 24.3,
          platform: 'Local Machine Host Node',
        },
      });
      addLog('warn', `Direct backend fetch failed (${err.message || 'offline'}). Using standby telemetry buffer.`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    addLog('info', 'OpsPilot Console initialized. Mounting SRE observability engine.');
    fetchHealth();
    const interval = setInterval(fetchHealth, 8000);
    return () => clearInterval(interval);
  }, []);

  const metrics = health?.system_metrics;

  return (
    <div className="app-container">
      {/* Top Bar Navigation */}
      <header className="topbar">
        <div className="brand">
          <div className="brand-icon">
            <Activity size={20} color="#ffffff" />
          </div>
          <span className="brand-title">OpsPilot</span>
          <span className="brand-tag">Sprint 1</span>
        </div>

        <div className="topbar-meta">
          <div className="status-indicator">
            <span className="pulse-dot"></span>
            <span>{backendOnline ? 'ALL SYSTEMS OPERATIONAL' : 'LOCAL DEV STANDBY'}</span>
          </div>

          <div className="meta-pill">
            <Clock size={12} style={{ display: 'inline', marginRight: '4px' }} />
            {currentTime}
          </div>

          <div className="meta-pill" style={{ color: backendOnline ? '#34d399' : '#f59e0b' }}>
            API: {backendOnline ? 'CONNECTED' : 'DISCONNECTED'}
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="main-content">
        {/* Sprint 1 Banner */}
        <section className="sprint-banner">
          <div>
            <div className="sprint-badge">Milestone v0.1.0-alpha.1 • 3-Month Plan (Sprint 1 of 15)</div>
            <h1 className="sprint-banner-title">Architecture Foundation & Diagnostics Console</h1>
            <p className="sprint-banner-desc">
              Establishing polyglot architecture, clean FastAPI async backend, automated CI/CD pipeline,
              and live telemetry health probe ingestion for continuous GitHub evaluation.
            </p>
          </div>

          <div className="sprint-actions">
            <button className="btn-secondary" onClick={fetchHealth} disabled={loading}>
              <RefreshCw size={15} className={loading ? 'spin' : ''} />
              {loading ? 'Probing...' : 'Refresh Probe'}
            </button>
            <a 
              href="http://localhost:8000/api/v1/docs" 
              target="_blank" 
              rel="noreferrer" 
              className="btn-primary"
            >
              <ExternalLink size={15} />
              OpenAPI Swagger
            </a>
          </div>
        </section>

        {/* Metrics Grid */}
        <section className="stat-grid">
          <div className="stat-card">
            <div className="stat-header">
              <span>CPU Utilization</span>
              <Cpu size={18} color="#38bdf8" />
            </div>
            <div className="stat-value">{metrics ? `${metrics.cpu_percent}%` : '--'}</div>
            <div className="stat-sub">
              <span>Normal operational baseline</span>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-header">
              <span>Memory Usage</span>
              <Activity size={18} color="#10b981" />
            </div>
            <div className="stat-value">{metrics ? `${metrics.memory_percent}%` : '--'}</div>
            <div className="stat-sub">
              <span>{metrics ? `${(metrics.memory_used_mb / 1024).toFixed(1)} GB / ${(metrics.memory_total_mb / 1024).toFixed(1)} GB` : '--'}</span>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-header">
              <span>Disk Volume</span>
              <HardDrive size={18} color="#a855f7" />
            </div>
            <div className="stat-value">{metrics ? `${metrics.disk_percent}%` : '--'}</div>
            <div className="stat-sub">
              <span>{metrics ? `${metrics.disk_used_gb} GB used of ${metrics.disk_total_gb} GB` : '--'}</span>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-header">
              <span>Core Uptime</span>
              <Server size={18} color="#f59e0b" />
            </div>
            <div className="stat-value">{health ? `${Math.floor(health.uptime_seconds)}s` : '--'}</div>
            <div className="stat-sub">
              <span>Service: {health?.service || 'OpsPilot'}</span>
            </div>
          </div>
        </section>

        {/* Details Two-Column Grid */}
        <section className="details-grid">
          {/* Live Telemetry Resource Allocation */}
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">
                <Zap size={18} color="#38bdf8" />
                Live Node Telemetry Probes
              </div>
              <span className="meta-pill">Node: {metrics?.platform || 'Host Host'}</span>
            </div>

            <div className="panel-body">
              {/* CPU Meter */}
              <div className="metric-row">
                <div className="metric-meta">
                  <span className="metric-label">Processor Load</span>
                  <span className="metric-val">{metrics?.cpu_percent ?? 0}%</span>
                </div>
                <div className="progress-track">
                  <div 
                    className="progress-fill fill-cyan" 
                    style={{ width: `${Math.min(metrics?.cpu_percent ?? 0, 100)}%` }}
                  ></div>
                </div>
              </div>

              {/* Memory Meter */}
              <div className="metric-row">
                <div className="metric-meta">
                  <span className="metric-label">Virtual Memory Allocation</span>
                  <span className="metric-val">{metrics?.memory_percent ?? 0}%</span>
                </div>
                <div className="progress-track">
                  <div 
                    className="progress-fill fill-emerald" 
                    style={{ width: `${Math.min(metrics?.memory_percent ?? 0, 100)}%` }}
                  ></div>
                </div>
              </div>

              {/* Disk Meter */}
              <div className="metric-row">
                <div className="metric-meta">
                  <span className="metric-label">Root Partition Footprint</span>
                  <span className="metric-val">{metrics?.disk_percent ?? 0}%</span>
                </div>
                <div className="progress-track">
                  <div 
                    className="progress-fill fill-violet" 
                    style={{ width: `${Math.min(metrics?.disk_percent ?? 0, 100)}%` }}
                  ></div>
                </div>
              </div>

              {/* Micro-table of subsystem dependencies */}
              <div style={{ marginTop: '1rem', borderTop: '1px solid var(--border-subtle)', paddingTop: '1rem' }}>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.5rem', fontWeight: 600 }}>
                  Subsystem Bus Status
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem' }}>
                  <div className="stat-card" style={{ padding: '0.75rem' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Database Layer</span>
                    <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#34d399' }}>{health?.dependencies.database.toUpperCase()}</span>
                  </div>
                  <div className="stat-card" style={{ padding: '0.75rem' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Redis Cache</span>
                    <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#34d399' }}>{health?.dependencies.cache.toUpperCase()}</span>
                  </div>
                  <div className="stat-card" style={{ padding: '0.75rem' }}>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Telemetry Bus</span>
                    <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#38bdf8' }}>{health?.dependencies.telemetry_bus.toUpperCase()}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* SRE Event Stream & Probe Log */}
          <div className="panel">
            <div className="panel-header">
              <div className="panel-title">
                <Terminal size={18} color="#a855f7" />
                SRE Stream Log
              </div>
              <span className="meta-pill">{logs.length} Events</span>
            </div>

            <div className="panel-body" style={{ padding: '1rem' }}>
              <div className="terminal-window">
                {logs.length === 0 ? (
                  <div style={{ color: 'var(--text-dim)' }}>Awaiting telemetry events...</div>
                ) : (
                  logs.map((log) => (
                    <div key={log.id} className="log-line">
                      <span className="log-ts">[{log.timestamp}]</span>
                      <span className={`log-level-${log.level}`}>{log.level.toUpperCase()}</span>
                      <span className="log-msg">{log.message}</span>
                    </div>
                  ))
                )}
              </div>

              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                <button 
                  className="btn-secondary" 
                  style={{ width: '100%', fontSize: '0.75rem', padding: '0.4rem' }}
                  onClick={() => addLog('info', `Manual heartbeat ping triggered by operator at ${new Date().toLocaleTimeString()}`)}
                >
                  Append Audit Trace
                </button>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="footer">
        <div>
          OpsPilot Platform &copy; 2026 • 6-Month Industry-Level Capstone Engineering Project
        </div>
        <div>
          Evaluation Sprint 1 of 15 • Tag: <span style={{ fontFamily: 'var(--font-mono)', color: '#38bdf8' }}>v0.1.0-alpha.1</span>
        </div>
      </footer>
    </div>
  );
};

export default App;
