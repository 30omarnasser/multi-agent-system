import React from 'react';

// ─── Status Badge ─────────────────────────────────────────────

export function StatusBadge({ status, label }) {
  const isOk = status === 'ok';
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      padding: '3px 10px', borderRadius: 20,
      fontSize: 11, fontFamily: 'var(--font-mono)',
      fontWeight: 500, letterSpacing: '0.05em',
      background: isOk ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
      border: `1px solid ${isOk ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'}`,
      color: isOk ? 'var(--green)' : 'var(--red)',
    }}>
      <span style={{
        width: 5, height: 5, borderRadius: '50%',
        background: isOk ? 'var(--green)' : 'var(--red)',
        boxShadow: isOk ? '0 0 6px var(--green)' : '0 0 6px var(--red)',
        animation: isOk ? 'pulse-glow 2s ease-in-out infinite' : 'none',
      }} />
      {label || status}
    </span>
  );
}

// ─── Card ─────────────────────────────────────────────────────

export function Card({ children, style, className, onClick, glow }) {
  return (
    <div
      onClick={onClick}
      className={className}
      style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border-mid)',
        borderRadius: 12,
        padding: 20,
        boxShadow: glow ? 'var(--shadow-glow)' : 'var(--shadow-card)',
        transition: 'all var(--t-smooth)',
        cursor: onClick ? 'pointer' : 'default',
        ...style,
      }}
    >
      {children}
    </div>
  );
}

// ─── Button ───────────────────────────────────────────────────

export function Button({ children, onClick, variant = 'primary', size = 'md',
  disabled, loading, style, icon: Icon }) {
  const variants = {
    primary: {
      background: 'var(--accent-core)',
      color: '#fff',
      border: '1px solid var(--accent-glow)',
      boxShadow: '0 0 20px rgba(29,111,255,0.3)',
    },
    secondary: {
      background: 'var(--bg-elevated)',
      color: 'var(--text-primary)',
      border: '1px solid var(--border-mid)',
    },
    ghost: {
      background: 'transparent',
      color: 'var(--text-secondary)',
      border: '1px solid transparent',
    },
    danger: {
      background: 'rgba(239,68,68,0.1)',
      color: 'var(--red)',
      border: '1px solid rgba(239,68,68,0.3)',
    },
    success: {
      background: 'rgba(16,185,129,0.1)',
      color: 'var(--green)',
      border: '1px solid rgba(16,185,129,0.3)',
    },
    cyan: {
      background: 'rgba(0,200,255,0.1)',
      color: 'var(--cyan-core)',
      border: '1px solid rgba(0,200,255,0.3)',
      boxShadow: '0 0 16px rgba(0,200,255,0.1)',
    },
  };

  const sizes = {
    sm: { padding: '5px 12px', fontSize: 12, borderRadius: 7 },
    md: { padding: '8px 16px', fontSize: 13, borderRadius: 9 },
    lg: { padding: '11px 22px', fontSize: 14, borderRadius: 10 },
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        fontFamily: 'var(--font-body)', fontWeight: 500,
        cursor: disabled || loading ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        transition: 'all var(--t-fast)',
        whiteSpace: 'nowrap',
        ...variants[variant],
        ...sizes[size],
        ...style,
      }}
    >
      {loading ? (
        <span style={{
          width: 12, height: 12, border: '2px solid currentColor',
          borderTopColor: 'transparent', borderRadius: '50%',
          animation: 'spin 0.8s linear infinite',
        }} />
      ) : Icon ? <Icon size={13} /> : null}
      {children}
    </button>
  );
}

// ─── Input ────────────────────────────────────────────────────

export function Input({ value, onChange, placeholder, onKeyDown, style,
  prefix, suffix, type = 'text' }) {
  return (
    <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
      {prefix && (
        <span style={{
          position: 'absolute', left: 12,
          color: 'var(--text-tertiary)', pointerEvents: 'none',
          display: 'flex', alignItems: 'center',
        }}>
          {prefix}
        </span>
      )}
      <input
        type={type}
        value={value}
        onChange={onChange}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        style={{
          width: '100%',
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-mid)',
          borderRadius: 9,
          padding: `9px ${suffix ? 40 : 14}px 9px ${prefix ? 38 : 14}px`,
          color: 'var(--text-primary)',
          fontFamily: 'var(--font-body)',
          fontSize: 13,
          outline: 'none',
          transition: 'border-color var(--t-fast)',
          '::placeholder': { color: 'var(--text-tertiary)' },
          ...style,
        }}
        onFocus={e => e.target.style.borderColor = 'var(--accent-core)'}
        onBlur={e => e.target.style.borderColor = 'var(--border-mid)'}
      />
      {suffix && (
        <span style={{
          position: 'absolute', right: 12,
          color: 'var(--text-tertiary)',
          display: 'flex', alignItems: 'center',
        }}>
          {suffix}
        </span>
      )}
    </div>
  );
}

// ─── Agent Pill ───────────────────────────────────────────────

const AGENT_META = {
  planner:    { color: '#3b82f6', icon: '🗺️', label: 'Planner' },
  researcher: { color: '#06b6d4', icon: '🔍', label: 'Researcher' },
  coder:      { color: '#f59e0b', icon: '💻', label: 'Coder' },
  critic:     { color: '#ef4444', icon: '⚖️', label: 'Critic' },
  responder:  { color: '#8b5cf6', icon: '✍️', label: 'Responder' },
};

export function AgentPill({ agent, active, done }) {
  const meta = AGENT_META[agent] || { color: '#6b7280', icon: '🤖', label: agent };
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 6,
      padding: '4px 10px',
      borderRadius: 20,
      fontSize: 11,
      fontFamily: 'var(--font-mono)',
      fontWeight: 500,
      background: active
        ? `${meta.color}22`
        : done ? `${meta.color}11` : 'var(--bg-elevated)',
      border: `1px solid ${active ? meta.color : done ? `${meta.color}44` : 'var(--border-dim)'}`,
      color: active || done ? meta.color : 'var(--text-dim)',
      boxShadow: active ? `0 0 12px ${meta.color}33` : 'none',
      transition: 'all var(--t-smooth)',
    }}>
      <span style={{ fontSize: 10 }}>{meta.icon}</span>
      {meta.label}
      {active && (
        <span style={{
          width: 5, height: 5, borderRadius: '50%',
          background: meta.color,
          animation: 'pulse-glow 1s ease-in-out infinite',
        }} />
      )}
      {done && <span style={{ fontSize: 9 }}>✓</span>}
    </div>
  );
}

// ─── Score Badge ──────────────────────────────────────────────

export function ScoreBadge({ score }) {
  const color = score >= 8 ? 'var(--green)' : score >= 6 ? 'var(--yellow)' : 'var(--red)';
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 3,
      padding: '2px 8px',
      borderRadius: 6,
      fontSize: 11,
      fontFamily: 'var(--font-mono)',
      fontWeight: 600,
      background: `${color}18`,
      border: `1px solid ${color}44`,
      color,
    }}>
      {score}/10
    </span>
  );
}

// ─── Loading Spinner ──────────────────────────────────────────

export function Spinner({ size = 20, color = 'var(--accent-core)' }) {
  return (
    <span style={{
      display: 'inline-block',
      width: size, height: size,
      border: `2px solid ${color}33`,
      borderTopColor: color,
      borderRadius: '50%',
      animation: 'spin 0.8s linear infinite',
    }} />
  );
}

// ─── Section Header ───────────────────────────────────────────

export function SectionHeader({ title, subtitle, action }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start',
      justifyContent: 'space-between', marginBottom: 20,
    }}>
      <div>
        <h2 style={{
          fontFamily: 'var(--font-display)',
          fontSize: 18, fontWeight: 700,
          color: 'var(--text-primary)',
          letterSpacing: '-0.02em',
        }}>
          {title}
        </h2>
        {subtitle && (
          <p style={{ fontSize: 12, color: 'var(--text-tertiary)', marginTop: 3 }}>
            {subtitle}
          </p>
        )}
      </div>
      {action}
    </div>
  );
}

// ─── Empty State ──────────────────────────────────────────────

export function EmptyState({ icon, title, description }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      padding: '48px 24px', textAlign: 'center',
      gap: 12,
    }}>
      <span style={{ fontSize: 32, opacity: 0.4 }}>{icon}</span>
      <p style={{
        fontFamily: 'var(--font-display)',
        fontSize: 14, fontWeight: 600,
        color: 'var(--text-tertiary)',
      }}>
        {title}
      </p>
      {description && (
        <p style={{ fontSize: 12, color: 'var(--text-dim)', maxWidth: 260 }}>
          {description}
        </p>
      )}
    </div>
  );
}

// ─── Tag ──────────────────────────────────────────────────────

export function Tag({ children, color = 'var(--accent-core)' }) {
  return (
    <span style={{
      display: 'inline-block',
      padding: '2px 8px',
      borderRadius: 4,
      fontSize: 10,
      fontFamily: 'var(--font-mono)',
      fontWeight: 500,
      background: `${color}15`,
      border: `1px solid ${color}33`,
      color,
      letterSpacing: '0.04em',
    }}>
      {children}
    </span>
  );
}

// ─── Metric Card ──────────────────────────────────────────────

export function MetricCard({ label, value, sub, color = 'var(--accent-core)', icon: Icon }) {
  return (
    <Card style={{ padding: '16px 20px' }}>
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
      }}>
        <div>
          <p style={{
            fontSize: 11, color: 'var(--text-tertiary)',
            fontFamily: 'var(--font-mono)', fontWeight: 500,
            letterSpacing: '0.08em', textTransform: 'uppercase',
            marginBottom: 6,
          }}>
            {label}
          </p>
          <p style={{
            fontFamily: 'var(--font-display)',
            fontSize: 26, fontWeight: 700,
            color, lineHeight: 1,
          }}>
            {value}
          </p>
          {sub && (
            <p style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 5 }}>
              {sub}
            </p>
          )}
        </div>
        {Icon && (
          <div style={{
            width: 36, height: 36,
            background: `${color}15`,
            border: `1px solid ${color}33`,
            borderRadius: 9,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Icon size={16} color={color} />
          </div>
        )}
      </div>
    </Card>
  );
}

export { AGENT_META };
