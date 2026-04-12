import React, { useState, useEffect } from 'react';
import { RefreshCw, Search, Trash2, Brain, Clock, User, FileText, Wrench } from 'lucide-react';
import {
  getMemoryStats, getFacts, searchFacts, getRecentEpisodes,
  searchEpisodes, deleteEpisode, getProfiles, runMaintenance,
  deduplicateFacts, summarizeFacts,
} from '../utils/api';
import { Card, Button, Input, SectionHeader, EmptyState, MetricCard, Tag, Spinner } from '../components/UI';

function FactsList({ sessionId }) {
  const [facts, setFacts] = useState([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      if (query) {
        const { data } = await searchFacts(query, 20);
        setFacts(data.results || []);
      } else {
        const { data } = await getFacts(sessionId);
        setFacts(data.facts || []);
      }
    } catch {}
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const catColors = {
    personal: '#3b82f6', project: '#06b6d4', technical: '#f59e0b',
    preference: '#8b5cf6', general: '#6b7280',
  };

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <div style={{ flex: 1 }}>
          <Input
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && load()}
            placeholder="Semantic search facts..."
            prefix={<Search size={13} />}
          />
        </div>
        <Button variant="secondary" size="md" icon={Search} onClick={load}>
          Search
        </Button>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
          <Spinner />
        </div>
      ) : facts.length === 0 ? (
        <EmptyState icon="💡" title="No facts yet"
          description="Facts are automatically extracted from conversations" />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {facts.map((fact, i) => (
            <div key={i} style={{
              padding: '10px 14px',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-dim)',
              borderRadius: 9,
              display: 'flex', alignItems: 'flex-start', gap: 10,
              animation: `slide-up ${0.1 + i * 0.03}s both`,
            }}>
              <Tag color={catColors[fact.category] || '#6b7280'}>
                {fact.category || 'general'}
              </Tag>
              <p style={{ flex: 1, fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                {fact.fact}
              </p>
              {fact.similarity && (
                <span style={{
                  fontSize: 10, color: 'var(--text-dim)',
                  fontFamily: 'var(--font-mono)', flexShrink: 0,
                }}>
                  {(fact.similarity * 100).toFixed(0)}%
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function EpisodesList() {
  const [episodes, setEpisodes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await getRecentEpisodes(20);
      setEpisodes(data.episodes || []);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const del = async (id) => {
    await deleteEpisode(id);
    setEpisodes(e => e.filter(ep => ep.id !== id));
  };

  if (loading) return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
      <Spinner />
    </div>
  );

  if (episodes.length === 0) return (
    <EmptyState icon="📖" title="No episodes yet"
      description="Episodes are saved after each conversation session" />
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {episodes.map((ep, i) => (
        <div key={ep.id} style={{
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border-dim)',
          borderRadius: 10,
          overflow: 'hidden',
          animation: `slide-up ${0.1 + i * 0.04}s both`,
        }}>
          <div
            onClick={() => setExpanded(expanded === ep.id ? null : ep.id)}
            style={{
              padding: '12px 14px', cursor: 'pointer',
              display: 'flex', alignItems: 'flex-start', gap: 10,
            }}
          >
            <Clock size={13} color="var(--text-dim)" style={{ marginTop: 2, flexShrink: 0 }} />
            <div style={{ flex: 1, minWidth: 0 }}>
              <p style={{
                fontSize: 12, fontWeight: 500, color: 'var(--text-primary)',
                marginBottom: 3, lineHeight: 1.4,
              }}>
                {ep.summary?.substring(0, 120)}{ep.summary?.length > 120 ? '...' : ''}
              </p>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                <span style={{
                  fontSize: 10, color: 'var(--text-dim)',
                  fontFamily: 'var(--font-mono)',
                }}>
                  {ep.session_id}
                </span>
                {(ep.key_topics || []).slice(0, 3).map(t => (
                  <Tag key={t} color="var(--cyan-core)">{t}</Tag>
                ))}
              </div>
            </div>
            <button
              onClick={e => { e.stopPropagation(); del(ep.id); }}
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                color: 'var(--text-dim)', padding: 4,
                display: 'flex', alignItems: 'center',
              }}
            >
              <Trash2 size={12} />
            </button>
          </div>

          {expanded === ep.id && (
            <div style={{
              padding: '0 14px 14px',
              borderTop: '1px solid var(--border-dim)',
              paddingTop: 12,
              marginTop: -1,
            }}>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 8 }}>
                {ep.summary}
              </p>
              {ep.outcome && (
                <p style={{ fontSize: 11, color: 'var(--text-tertiary)' }}>
                  <strong>Outcome:</strong> {ep.outcome}
                </p>
              )}
              <p style={{
                fontSize: 10, color: 'var(--text-dim)', marginTop: 6,
                fontFamily: 'var(--font-mono)',
              }}>
                {ep.message_count} messages · {ep.created_at?.substring(0, 10)}
              </p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function ProfilesList() {
  const [profiles, setProfiles] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await getProfiles();
      setProfiles(data.profiles || []);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const expertiseColor = {
    expert: '#10b981', advanced: '#3b82f6',
    intermediate: '#f59e0b', beginner: '#ef4444',
  };

  if (loading) return (
    <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
      <Spinner />
    </div>
  );

  if (profiles.length === 0) return (
    <EmptyState icon="👤" title="No profiles yet"
      description="Profiles are automatically learned from conversations" />
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {profiles.map((p, i) => (
        <Card key={p.user_id} style={{ padding: '14px 16px', animation: `slide-up ${0.1 + i * 0.05}s both` }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
            <div style={{
              width: 36, height: 36, borderRadius: '50%',
              background: 'linear-gradient(135deg, var(--accent-core), var(--accent-glow))',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 14, fontWeight: 700, color: '#fff',
              fontFamily: 'var(--font-display)',
            }}>
              {(p.name || p.user_id)[0].toUpperCase()}
            </div>
            <div>
              <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                {p.name || p.user_id}
              </p>
              <p style={{ fontSize: 10, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                {p.interaction_count} interactions
              </p>
            </div>
            {p.expertise_level && p.expertise_level !== 'unknown' && (
              <Tag color={expertiseColor[p.expertise_level] || '#6b7280'} style={{ marginLeft: 'auto' }}>
                {p.expertise_level}
              </Tag>
            )}
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
            {(p.interests || []).slice(0, 5).map(interest => (
              <Tag key={interest} color="var(--accent-soft)">{interest}</Tag>
            ))}
            {p.communication_style && p.communication_style !== 'neutral' && (
              <Tag color="var(--text-secondary)">{p.communication_style}</Tag>
            )}
          </div>
        </Card>
      ))}
    </div>
  );
}

export default function MemoryPage() {
  const [stats, setStats] = useState(null);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [maintenanceLoading, setMaintenanceLoading] = useState(false);
  const [maintenanceResult, setMaintenanceResult] = useState(null);

  const loadStats = async () => {
    try {
      const { data } = await getMemoryStats();
      setStats(data);
    } catch {}
  };

  useEffect(() => { loadStats(); }, []);

  const doMaintenance = async () => {
    setMaintenanceLoading(true);
    try {
      const { data } = await runMaintenance({ deduplicate: true });
      setMaintenanceResult(data);
      loadStats();
    } catch {}
    setMaintenanceLoading(false);
  };

  const TABS = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'facts', label: 'Facts', icon: '💡' },
    { id: 'episodes', label: 'Episodes', icon: '📖' },
    { id: 'profiles', label: 'Profiles', icon: '👤' },
  ];

  return (
    <div style={{ padding: '24px', overflowY: 'auto', height: '100%' }}>
      <SectionHeader
        title="Memory Explorer"
        subtitle="Explore all 5 memory layers of the system"
        action={
          <Button variant="secondary" size="sm" icon={RefreshCw} onClick={loadStats}>
            Refresh
          </Button>
        }
      />

      {/* Tab bar */}
      <div style={{
        display: 'flex', gap: 2,
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-dim)',
        borderRadius: 10, padding: 4,
        marginBottom: 24,
      }}>
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              flex: 1, padding: '7px 12px', borderRadius: 7,
              border: 'none', cursor: 'pointer',
              fontSize: 12, fontFamily: 'var(--font-body)', fontWeight: 500,
              background: activeTab === tab.id ? 'var(--bg-card)' : 'transparent',
              color: activeTab === tab.id ? 'var(--text-primary)' : 'var(--text-tertiary)',
              border: activeTab === tab.id ? '1px solid var(--border-mid)' : '1px solid transparent',
              transition: 'all var(--t-fast)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5,
            }}
          >
            <span>{tab.icon}</span> {tab.label}
          </button>
        ))}
      </div>

      {/* Dashboard tab */}
      {activeTab === 'dashboard' && (
        <div style={{ animation: 'fade-in 0.3s both' }}>
          {stats && (
            <>
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                gap: 12, marginBottom: 24,
              }}>
                <MetricCard
                  label="Total Facts"
                  value={stats.facts?.total || 0}
                  color="var(--accent-core)"
                  icon={Brain}
                />
                <MetricCard
                  label="Episodes"
                  value={stats.episodes?.total || 0}
                  color="var(--cyan-core)"
                  icon={Clock}
                />
                <MetricCard
                  label="Doc Chunks"
                  value={stats.documents?.total_chunks || 0}
                  color="var(--agent-coder)"
                  icon={FileText}
                />
                <MetricCard
                  label="Profiles"
                  value={stats.profiles?.total || 0}
                  color="var(--agent-responder)"
                  icon={User}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
                <Card>
                  <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12 }}>
                    Facts by Category
                  </p>
                  {Object.entries(stats.facts?.by_category || {}).map(([cat, count]) => (
                    <div key={cat} style={{
                      display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8,
                    }}>
                      <span style={{ fontSize: 11, color: 'var(--text-tertiary)', width: 80, fontFamily: 'var(--font-mono)' }}>
                        {cat}
                      </span>
                      <div style={{
                        flex: 1, height: 6, background: 'var(--bg-elevated)',
                        borderRadius: 3, overflow: 'hidden',
                      }}>
                        <div style={{
                          height: '100%',
                          width: `${Math.min(100, (count / (stats.facts?.total || 1)) * 100)}%`,
                          background: 'var(--accent-core)',
                          borderRadius: 3,
                        }} />
                      </div>
                      <span style={{ fontSize: 11, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', width: 20 }}>
                        {count}
                      </span>
                    </div>
                  ))}
                </Card>

                <Card>
                  <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12 }}>
                    Recommendations
                  </p>
                  {(stats.recommendations || []).map((rec, i) => (
                    <div key={i} style={{
                      display: 'flex', gap: 8, marginBottom: 8,
                    }}>
                      <span style={{ color: 'var(--accent-core)', fontSize: 12 }}>→</span>
                      <p style={{ fontSize: 12, color: 'var(--text-tertiary)', lineHeight: 1.4 }}>{rec}</p>
                    </div>
                  ))}
                </Card>
              </div>

              {/* Maintenance */}
              <Card>
                <p style={{
                  fontSize: 13, fontWeight: 600,
                  fontFamily: 'var(--font-display)',
                  color: 'var(--text-primary)', marginBottom: 14,
                }}>
                  Memory Maintenance
                </p>
                <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                  <Button
                    variant="secondary"
                    icon={Wrench}
                    loading={maintenanceLoading}
                    onClick={doMaintenance}
                  >
                    Run Full Maintenance
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={async () => { await deduplicateFacts(); loadStats(); }}
                  >
                    Deduplicate Facts
                  </Button>
                </div>
                {maintenanceResult && (
                  <div style={{
                    marginTop: 12, padding: '10px 12px',
                    background: 'rgba(16,185,129,0.06)',
                    border: '1px solid rgba(16,185,129,0.2)',
                    borderRadius: 8,
                    fontSize: 12, fontFamily: 'var(--font-mono)',
                    color: 'var(--green)',
                  }}>
                    ✓ Facts pruned: {maintenanceResult.facts_pruned} ·
                    Episodes pruned: {maintenanceResult.episodes_pruned} ·
                    Deduped: {maintenanceResult.facts_deduplicated}
                  </div>
                )}
              </Card>
            </>
          )}
        </div>
      )}

      {activeTab === 'facts' && (
        <div style={{ animation: 'fade-in 0.3s both' }}>
          <FactsList />
        </div>
      )}

      {activeTab === 'episodes' && (
        <div style={{ animation: 'fade-in 0.3s both' }}>
          <EpisodesList />
        </div>
      )}

      {activeTab === 'profiles' && (
        <div style={{ animation: 'fade-in 0.3s both' }}>
          <ProfilesList />
        </div>
      )}
    </div>
  );
}
