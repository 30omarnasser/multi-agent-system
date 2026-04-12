import React, { useState, useEffect } from 'react';
import { Activity, Zap, Brain, FileText, RefreshCw, TrendingUp, Clock } from 'lucide-react';
import { getHealth, getMemoryStats, getEvalSummary } from '../utils/api';
import { Card, MetricCard, StatusBadge, SectionHeader, Tag, Button, Spinner } from '../components/UI';
import { AGENT_META } from '../components/UI';

const AGENT_DESCRIPTIONS = {
  planner:    'Task decomposition · confidence scoring · routing',
  researcher: 'Web search · RAG retrieval · synthesis',
  coder:      'Python execution · sandboxed · 10s timeout',
  critic:     'Quality scoring 0-10 · revision loops',
  responder:  'Final synthesis · personalization · context',
};

function AgentCard({ agent, delay = 0 }) {
  const meta = AGENT_META[agent];
  return (
    <div style={{
      padding: '14px 16px',
      background: 'var(--bg-elevated)',
      border: `1px solid ${meta.color}22`,
      borderRadius: 12,
      display: 'flex', gap: 12, alignItems: 'flex-start',
      transition: 'all var(--t-smooth)',
      animation: `slide-up ${0.3 + delay}s both`,
    }}
      onMouseEnter={e => {
        e.currentTarget.style.borderColor = `${meta.color}55`;
        e.currentTarget.style.background = `${meta.color}0a`;
      }}
      onMouseLeave={e => {
        e.currentTarget.style.borderColor = `${meta.color}22`;
        e.currentTarget.style.background = 'var(--bg-elevated)';
      }}
    >
      <div style={{
        width: 36, height: 36, borderRadius: 9, flexShrink: 0,
        background: `${meta.color}15`,
        border: `1px solid ${meta.color}33`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 16,
      }}>
        {meta.icon}
      </div>
      <div>
        <p style={{
          fontSize: 13, fontWeight: 700, color: meta.color,
          fontFamily: 'var(--font-display)', marginBottom: 3,
        }}>
          {meta.label}
        </p>
        <p style={{ fontSize: 11, color: 'var(--text-dim)', lineHeight: 1.4 }}>
          {AGENT_DESCRIPTIONS[agent]}
        </p>
      </div>
    </div>
  );
}

function HealthPanel({ health }) {
  const services = ['api', 'redis', 'postgres', 'ollama'];
  return (
    <Card style={{ padding: '16px 20px' }}>
      <p style={{
        fontSize: 11, fontFamily: 'var(--font-mono)',
        fontWeight: 500, color: 'var(--text-tertiary)',
        letterSpacing: '0.08em', textTransform: 'uppercase',
        marginBottom: 12,
      }}>
        Service Health
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {services.map(svc => (
          <div key={svc} style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          }}>
            <span style={{
              fontSize: 12, color: 'var(--text-secondary)',
              fontFamily: 'var(--font-mono)',
            }}>
              {svc.toUpperCase()}
            </span>
            <StatusBadge status={health?.[svc] || 'unknown'} label={health?.[svc] || '...'} />
          </div>
        ))}
      </div>
    </Card>
  );
}

function PipelineFlowDiagram() {
  const agents = ['planner', 'researcher', 'coder', 'critic', 'responder'];
  return (
    <Card style={{ padding: '20px' }}>
      <p style={{
        fontSize: 11, fontFamily: 'var(--font-mono)',
        color: 'var(--text-tertiary)', letterSpacing: '0.08em',
        textTransform: 'uppercase', marginBottom: 16,
      }}>
        Agent Pipeline Flow
      </p>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 4,
        overflowX: 'auto', paddingBottom: 4,
      }}>
        {agents.map((agent, i) => {
          const meta = AGENT_META[agent];
          return (
            <React.Fragment key={agent}>
              <div style={{
                flexShrink: 0,
                padding: '6px 12px',
                borderRadius: 20,
                background: `${meta.color}15`,
                border: `1px solid ${meta.color}44`,
                display: 'flex', alignItems: 'center', gap: 6,
                animation: `slide-up ${0.1 + i * 0.1}s both`,
              }}>
                <span style={{ fontSize: 12 }}>{meta.icon}</span>
                <span style={{
                  fontSize: 11, color: meta.color,
                  fontFamily: 'var(--font-mono)', fontWeight: 500,
                }}>
                  {meta.label}
                </span>
              </div>
              {i < agents.length - 1 && (
                <span style={{
                  color: 'var(--text-dim)', fontSize: 14, flexShrink: 0,
                }}>→</span>
              )}
            </React.Fragment>
          );
        })}
      </div>
      <div style={{
        marginTop: 12, padding: '8px 12px',
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-dim)',
        borderRadius: 8,
        fontSize: 11, color: 'var(--text-dim)',
        fontFamily: 'var(--font-mono)',
        lineHeight: 1.6,
      }}>
        Planner routes → Researcher searches web+RAG → Coder executes Python →
        Critic scores (0-10) → loops if rejected → Responder synthesizes final answer
      </div>
    </Card>
  );
}

export default function DashboardPage() {
  const [health, setHealth] = useState(null);
  const [stats, setStats] = useState(null);
  const [evalStats, setEvalStats] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [h, s] = await Promise.allSettled([getHealth(), getMemoryStats()]);
      if (h.status === 'fulfilled') setHealth(h.value.data);
      if (s.status === 'fulfilled') setStats(s.value.data);
      try {
        const e = await getEvalSummary();
        setEvalStats(e.data);
      } catch {}
    } catch {}
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const allHealthy = health &&
    ['api', 'redis', 'postgres', 'ollama'].every(s => health[s] === 'ok');

  return (
    <div style={{ padding: 24, overflowY: 'auto', height: '100%' }}>
      <SectionHeader
        title="System Overview"
        subtitle="Real-time status of your multi-agent AI system"
        action={
          <Button variant="secondary" size="sm" icon={RefreshCw} onClick={load}>
            Refresh
          </Button>
        }
      />

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
          <Spinner size={32} />
        </div>
      ) : (
        <>
          {/* Status banner */}
          <div style={{
            padding: '12px 16px',
            background: allHealthy ? 'rgba(16,185,129,0.06)' : 'rgba(239,68,68,0.06)',
            border: `1px solid ${allHealthy ? 'rgba(16,185,129,0.2)' : 'rgba(239,68,68,0.2)'}`,
            borderRadius: 10,
            display: 'flex', alignItems: 'center', gap: 10,
            marginBottom: 24,
            animation: 'slide-up 0.3s both',
          }}>
            <div style={{
              width: 8, height: 8, borderRadius: '50%',
              background: allHealthy ? 'var(--green)' : 'var(--red)',
              boxShadow: `0 0 8px ${allHealthy ? 'var(--green)' : 'var(--red)'}`,
              animation: 'pulse-glow 2s ease-in-out infinite',
            }} />
            <span style={{
              fontSize: 13, fontWeight: 600,
              color: allHealthy ? 'var(--green)' : 'var(--red)',
              fontFamily: 'var(--font-display)',
            }}>
              {allHealthy ? 'All systems operational' : 'Some services degraded'}
            </span>
            <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
              {new Date().toLocaleTimeString()}
            </span>
          </div>

          {/* Metrics grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
            gap: 12, marginBottom: 24,
          }}>
            <MetricCard
              label="Facts Stored"
              value={stats?.facts?.total || 0}
              color="var(--accent-core)"
              icon={Brain}
            />
            <MetricCard
              label="Episodes"
              value={stats?.episodes?.total || 0}
              color="var(--cyan-core)"
              icon={Clock}
            />
            <MetricCard
              label="Documents"
              value={stats?.documents?.total_docs || 0}
              color="var(--agent-coder)"
              icon={FileText}
            />
            <MetricCard
              label="Avg Score"
              value={evalStats?.avg_score ? `${evalStats.avg_score}/10` : '—'}
              color="var(--green)"
              icon={TrendingUp}
              sub={evalStats ? `${evalStats.total_runs} runs` : 'No runs yet'}
            />
          </div>

          <div style={{
            display: 'grid', gridTemplateColumns: '1fr 300px',
            gap: 16, marginBottom: 24,
          }}>
            {/* Pipeline diagram */}
            <div>
              <PipelineFlowDiagram />
            </div>
            {/* Health panel */}
            <HealthPanel health={health} />
          </div>

          {/* Agent cards */}
          <p style={{
            fontSize: 11, fontFamily: 'var(--font-mono)',
            color: 'var(--text-tertiary)', letterSpacing: '0.08em',
            textTransform: 'uppercase', marginBottom: 12,
          }}>
            Specialized Agents
          </p>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: 12, marginBottom: 24,
          }}>
            {Object.keys(AGENT_META).map((agent, i) => (
              <AgentCard key={agent} agent={agent} delay={i * 0.05} />
            ))}
          </div>

          {/* Memory layer summary */}
          <p style={{
            fontSize: 11, fontFamily: 'var(--font-mono)',
            color: 'var(--text-tertiary)', letterSpacing: '0.08em',
            textTransform: 'uppercase', marginBottom: 12,
          }}>
            Memory Architecture
          </p>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: 10,
          }}>
            {[
              { name: 'Redis', desc: 'Short-term session memory', ttl: '1hr TTL', color: '#ef4444', icon: '⚡' },
              { name: 'PostgreSQL Facts', desc: 'Long-term semantic facts', ttl: 'pgvector', color: '#3b82f6', icon: '🧠' },
              { name: 'Episodic', desc: 'Past session summaries', ttl: 'Cross-session', color: '#06b6d4', icon: '📖' },
              { name: 'Documents', desc: 'PDF knowledge base', ttl: 'Hybrid search', color: '#f59e0b', icon: '📄' },
              { name: 'User Profiles', desc: 'Auto-learned preferences', ttl: 'Persistent', color: '#8b5cf6', icon: '👤' },
            ].map((layer, i) => (
              <div key={layer.name} style={{
                padding: '12px 14px',
                background: 'var(--bg-elevated)',
                border: `1px solid ${layer.color}22`,
                borderRadius: 10,
                animation: `slide-up ${0.4 + i * 0.05}s both`,
              }}>
                <div style={{ display: 'flex', gap: 8, marginBottom: 6 }}>
                  <span style={{ fontSize: 16 }}>{layer.icon}</span>
                  <div>
                    <p style={{
                      fontSize: 12, fontWeight: 700, color: layer.color,
                      fontFamily: 'var(--font-display)',
                    }}>
                      {layer.name}
                    </p>
                    <p style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 2 }}>
                      {layer.desc}
                    </p>
                  </div>
                </div>
                <Tag color={layer.color}>{layer.ttl}</Tag>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
