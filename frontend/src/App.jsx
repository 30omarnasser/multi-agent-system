import React, { useState, useEffect, useMemo } from 'react';
import { LayoutDashboard, MessageSquare, Brain, FileText, Settings, Zap, Activity } from 'lucide-react';
import DashboardPage from './pages/DashboardPage';
import ChatPage from './pages/ChatPage';
import MemoryPage from './pages/MemoryPage';
import DocumentsPage from './pages/DocumentsPage';
import { getHealth } from './utils/api';
import './index.css';

// Markdown styles
const markdownStyles = `
  .markdown-body { color: var(--text-primary); line-height: 1.65; }
  .markdown-body p { margin: 0 0 10px; }
  .markdown-body p:last-child { margin-bottom: 0; }
  .markdown-body h1,.markdown-body h2,.markdown-body h3 {
    font-family: var(--font-display);
    font-weight: 700; margin: 16px 0 8px;
    color: var(--text-primary);
  }
  .markdown-body h1 { font-size: 18px; }
  .markdown-body h2 { font-size: 15px; }
  .markdown-body h3 { font-size: 13px; }
  .markdown-body code {
    background: var(--bg-surface);
    border: 1px solid var(--border-dim);
    border-radius: 4px; padding: 1px 6px;
    font-family: var(--font-mono); font-size: 12px;
    color: var(--cyan-core);
  }
  .markdown-body pre {
    background: var(--bg-base);
    border: 1px solid var(--border-dim);
    border-radius: 9px; padding: 14px;
    overflow-x: auto; margin: 10px 0;
  }
  .markdown-body pre code {
    background: none; border: none;
    padding: 0; color: var(--text-secondary);
    font-size: 12px; line-height: 1.6;
  }
  .markdown-body ul, .markdown-body ol {
    padding-left: 20px; margin: 8px 0;
  }
  .markdown-body li { margin: 4px 0; font-size: 13px; }
  .markdown-body strong { color: var(--text-primary); font-weight: 600; }
  .markdown-body em { color: var(--accent-soft); }
  .markdown-body blockquote {
    border-left: 2px solid var(--accent-core);
    padding-left: 12px; margin: 8px 0;
    color: var(--text-tertiary); font-style: italic;
  }
  .markdown-body table {
    width: 100%; border-collapse: collapse; margin: 10px 0;
  }
  .markdown-body th, .markdown-body td {
    padding: 7px 12px; text-align: left; font-size: 12px;
    border: 1px solid var(--border-dim);
  }
  .markdown-body th {
    background: var(--bg-elevated);
    font-family: var(--font-mono); font-weight: 600;
    color: var(--text-secondary);
  }
  .markdown-body a { color: var(--accent-soft); }
  .markdown-body hr {
    border: none; border-top: 1px solid var(--border-dim);
    margin: 14px 0;
  }
`;

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Overview',  icon: LayoutDashboard },
  { id: 'chat',      label: 'Chat',      icon: MessageSquare },
  { id: 'memory',    label: 'Memory',    icon: Brain },
  { id: 'documents', label: 'Documents', icon: FileText },
];

function NavItem({ item, active, onClick }) {
  const Icon = item.icon;
  return (
    <button
      onClick={onClick}
      title={item.label}
      style={{
        width: '100%', padding: '10px 14px',
        display: 'flex', alignItems: 'center', gap: 10,
        background: active ? 'var(--accent-muted)' : 'transparent',
        border: `1px solid ${active ? 'var(--accent-rim)' : 'transparent'}`,
        borderRadius: 9, cursor: 'pointer',
        color: active ? 'var(--accent-soft)' : 'var(--text-tertiary)',
        fontFamily: 'var(--font-body)', fontWeight: 500, fontSize: 13,
        transition: 'all var(--t-fast)',
        textAlign: 'left',
      }}
      onMouseEnter={e => {
        if (!active) {
          e.currentTarget.style.background = 'var(--bg-elevated)';
          e.currentTarget.style.color = 'var(--text-secondary)';
        }
      }}
      onMouseLeave={e => {
        if (!active) {
          e.currentTarget.style.background = 'transparent';
          e.currentTarget.style.color = 'var(--text-tertiary)';
        }
      }}
    >
      <Icon size={15} />
      {item.label}
      {active && (
        <div style={{
          marginLeft: 'auto',
          width: 4, height: 4, borderRadius: '50%',
          background: 'var(--accent-core)',
          boxShadow: '0 0 8px var(--accent-core)',
        }} />
      )}
    </button>
  );
}

function Sidebar({ activeRoute, onNavigate, health }) {
  const allOk = health && ['api', 'redis', 'postgres', 'ollama'].every(s => health[s] === 'ok');

  return (
    <div style={{
      width: 220, flexShrink: 0,
      background: 'var(--bg-surface)',
      borderRight: '1px solid var(--border-dim)',
      display: 'flex', flexDirection: 'column',
      height: '100vh',
    }}>
      {/* Logo */}
      <div style={{
        padding: '20px 16px 16px',
        borderBottom: '1px solid var(--border-dim)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 34, height: 34, borderRadius: 10,
            background: 'linear-gradient(135deg, var(--accent-core), #0a3d99)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 20px rgba(29,111,255,0.4)',
          }}>
            <Zap size={17} color="#fff" />
          </div>
          <div>
            <p style={{
              fontFamily: 'var(--font-display)',
              fontSize: 17, fontWeight: 800,
              color: 'var(--text-primary)',
              letterSpacing: '-0.03em', lineHeight: 1,
            }}>
              NEXUS
            </p>
            <p style={{
              fontSize: 9, color: 'var(--text-dim)',
              fontFamily: 'var(--font-mono)',
              letterSpacing: '0.1em',
            }}>
              MULTI-AGENT AI
            </p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav style={{ padding: '12px 10px', flex: 1 }}>
        <p style={{
          fontSize: 9, color: 'var(--text-dim)',
          fontFamily: 'var(--font-mono)', fontWeight: 500,
          letterSpacing: '0.1em', textTransform: 'uppercase',
          padding: '0 4px', marginBottom: 6,
        }}>
          Navigation
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {NAV_ITEMS.map(item => (
            <NavItem
              key={item.id}
              item={item}
              active={activeRoute === item.id}
              onClick={() => onNavigate(item.id)}
            />
          ))}
        </div>
      </nav>

      {/* Status footer */}
      <div style={{
        padding: '12px 16px',
        borderTop: '1px solid var(--border-dim)',
      }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8,
        }}>
          <Activity size={12} color={allOk ? 'var(--green)' : 'var(--yellow)'} />
          <span style={{
            fontSize: 11, fontFamily: 'var(--font-mono)',
            color: allOk ? 'var(--green)' : 'var(--yellow)',
            fontWeight: 500,
          }}>
            {allOk ? 'All systems go' : 'Checking...'}
          </span>
        </div>
        {health && (
          <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
            {['api', 'redis', 'postgres', 'ollama'].map(svc => (
              <div key={svc} style={{
                width: 6, height: 6, borderRadius: '50%',
                background: health[svc] === 'ok' ? 'var(--green)' : 'var(--red)',
                boxShadow: health[svc] === 'ok'
                  ? '0 0 4px var(--green)'
                  : '0 0 4px var(--red)',
                title: svc,
              }} title={`${svc}: ${health[svc]}`} />
            ))}
          </div>
        )}
        <p style={{
          fontSize: 9, color: 'var(--text-dim)',
          fontFamily: 'var(--font-mono)', marginTop: 6,
        }}>
          v1.0.0 · localhost:8000
        </p>
      </div>
    </div>
  );
}

function Header({ route }) {
  const titles = {
    dashboard: { label: 'System Overview', sub: 'Monitor all services and agents' },
    chat:      { label: 'Agent Chat',      sub: 'Talk to the multi-agent pipeline' },
    memory:    { label: 'Memory Explorer', sub: 'Browse facts, episodes, and profiles' },
    documents: { label: 'Knowledge Base', sub: 'Upload PDFs and search documents' },
  };
  const current = titles[route] || titles.dashboard;

  return (
    <div style={{
      height: 54, flexShrink: 0,
      borderBottom: '1px solid var(--border-dim)',
      display: 'flex', alignItems: 'center',
      padding: '0 24px',
      background: 'var(--bg-base)',
    }}>
      <div>
        <h1 style={{
          fontFamily: 'var(--font-display)',
          fontSize: 15, fontWeight: 700,
          color: 'var(--text-primary)',
          letterSpacing: '-0.02em', lineHeight: 1,
        }}>
          {current.label}
        </h1>
        <p style={{
          fontSize: 11, color: 'var(--text-dim)', marginTop: 2,
          fontFamily: 'var(--font-mono)',
        }}>
          {current.sub}
        </p>
      </div>

      {/* Grid texture */}
      <div style={{
        position: 'absolute', right: 0, top: 0,
        width: 200, height: 54,
        backgroundImage: 'linear-gradient(var(--border-dim) 1px, transparent 1px), linear-gradient(90deg, var(--border-dim) 1px, transparent 1px)',
        backgroundSize: '20px 20px',
        opacity: 0.3,
        pointerEvents: 'none',
      }} />
    </div>
  );
}

// Session state
const SESSION_ID = `session_${Math.random().toString(36).slice(2, 10)}`;
const USER_ID = `user_${Math.random().toString(36).slice(2, 10)}`;

export default function App() {
  const [route, setRoute] = useState('dashboard');
  const [health, setHealth] = useState(null);

  useEffect(() => {
    const check = async () => {
      try {
        const { data } = await getHealth();
        setHealth(data);
      } catch {}
    };
    check();
    const id = setInterval(check, 30000);
    return () => clearInterval(id);
  }, []);

  const page = useMemo(() => {
    switch (route) {
      case 'chat':      return <ChatPage sessionId={SESSION_ID} userId={USER_ID} />;
      case 'memory':    return <MemoryPage />;
      case 'documents': return <DocumentsPage />;
      default:          return <DashboardPage />;
    }
  }, [route]);

  return (
    <>
      <style>{markdownStyles}</style>
      <div style={{
        display: 'flex', height: '100vh',
        background: 'var(--bg-void)',
        overflow: 'hidden',
      }}>
        <Sidebar activeRoute={route} onNavigate={setRoute} health={health} />
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          <Header route={route} />
          <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
            {page}
          </div>
        </div>
      </div>
    </>
  );
}
