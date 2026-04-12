import React, { useState, useRef, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import { Send, Zap, Bot, User, RotateCcw, Shield, ChevronDown, ChevronUp } from 'lucide-react';
import { sendChat, sendMultiAgent, getPendingHITL, approveHITL, rejectHITL } from '../utils/api';
import { AgentPill, ScoreBadge, Button, Spinner, Card, Tag } from '../components/UI';

const AGENT_ORDER = ['planner', 'researcher', 'coder', 'critic', 'responder'];

function PipelineTrace({ agentsUsed = [], critiqeScore = 0, hadRevision, plan = {} }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div style={{
      marginTop: 12,
      padding: '10px 14px',
      background: 'var(--bg-surface)',
      border: '1px solid var(--border-dim)',
      borderRadius: 10,
    }}>
      {/* Agent flow */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap',
      }}>
        {agentsUsed.map((agent, i) => (
          <React.Fragment key={agent}>
            <AgentPill agent={agent} done />
            {i < agentsUsed.length - 1 && (
              <span style={{ color: 'var(--text-dim)', fontSize: 10 }}>→</span>
            )}
          </React.Fragment>
        ))}
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6, alignItems: 'center' }}>
          {critiqeScore > 0 && <ScoreBadge score={critiqeScore} />}
          {hadRevision && (
            <Tag color="var(--yellow)">revised</Tag>
          )}
          <button
            onClick={() => setExpanded(v => !v)}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--text-tertiary)', display: 'flex', alignItems: 'center',
              padding: '0 4px',
            }}
          >
            {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </button>
        </div>
      </div>

      {/* Expanded plan details */}
      {expanded && plan && Object.keys(plan).length > 0 && (
        <div style={{
          marginTop: 12,
          paddingTop: 12,
          borderTop: '1px solid var(--border-dim)',
          display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8,
        }}>
          {[
            ['Task Type', plan.task_type],
            ['Complexity', plan.complexity],
            ['Confidence', plan.confidence ? `${Math.round(plan.confidence * 100)}%` : null],
            ['Estimated Steps', plan.estimated_steps],
          ].filter(([, v]) => v).map(([k, v]) => (
            <div key={k}>
              <p style={{ fontSize: 10, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', marginBottom: 2 }}>
                {k.toUpperCase()}
              </p>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
                {String(v)}
              </p>
            </div>
          ))}
          {plan.search_queries?.length > 0 && (
            <div style={{ gridColumn: '1/-1' }}>
              <p style={{ fontSize: 10, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', marginBottom: 4 }}>
                SEARCH QUERIES
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {plan.search_queries.map((q, i) => (
                  <Tag key={i} color="var(--cyan-core)">{q}</Tag>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function HITLPanel({ onDecision }) {
  const [pending, setPending] = useState([]);
  const [feedbacks, setFeedbacks] = useState({});

  useEffect(() => {
    const poll = async () => {
      try {
        const { data } = await getPendingHITL();
        setPending(data.requests || []);
      } catch {}
    };
    poll();
    const id = setInterval(poll, 2000);
    return () => clearInterval(id);
  }, []);

  if (pending.length === 0) return null;

  const decide = async (reqId, approved) => {
    const feedback = feedbacks[reqId] || '';
    if (approved) await approveHITL(reqId, feedback);
    else await rejectHITL(reqId, feedback);
    setPending(p => p.filter(r => r.request_id !== reqId));
    onDecision?.();
  };

  return (
    <div style={{
      margin: '0 0 16px 0',
      padding: 16,
      background: 'rgba(245,158,11,0.06)',
      border: '1px solid rgba(245,158,11,0.25)',
      borderRadius: 12,
      animation: 'slide-up 0.3s both',
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12,
      }}>
        <Shield size={14} color="var(--yellow)" />
        <span style={{
          fontFamily: 'var(--font-display)',
          fontSize: 13, fontWeight: 700, color: 'var(--yellow)',
        }}>
          Awaiting Approval
        </span>
        <span style={{
          marginLeft: 'auto',
          padding: '1px 8px',
          background: 'rgba(245,158,11,0.2)',
          borderRadius: 10,
          fontSize: 11,
          fontFamily: 'var(--font-mono)',
          color: 'var(--yellow)',
        }}>
          {pending.length} pending
        </span>
      </div>

      {pending.map(req => (
        <div key={req.request_id} style={{
          padding: 12,
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border-mid)',
          borderRadius: 9,
          marginBottom: 8,
        }}>
          <div style={{ marginBottom: 8 }}>
            <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 3 }}>
              {req.action}
            </p>
            <p style={{ fontSize: 11, color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>
              {req.details?.user_message?.substring(0, 100)}...
            </p>
          </div>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <input
              placeholder="Optional feedback..."
              value={feedbacks[req.request_id] || ''}
              onChange={e => setFeedbacks(f => ({ ...f, [req.request_id]: e.target.value }))}
              style={{
                flex: 1, background: 'var(--bg-surface)',
                border: '1px solid var(--border-mid)', borderRadius: 7,
                padding: '6px 10px', color: 'var(--text-primary)',
                fontSize: 12, fontFamily: 'var(--font-body)', outline: 'none',
              }}
            />
            <Button variant="success" size="sm" onClick={() => decide(req.request_id, true)}>
              Approve
            </Button>
            <Button variant="danger" size="sm" onClick={() => decide(req.request_id, false)}>
              Reject
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}

function Message({ msg }) {
  const isUser = msg.role === 'user';
  return (
    <div style={{
      display: 'flex',
      flexDirection: isUser ? 'row-reverse' : 'row',
      gap: 12, marginBottom: 20,
      animation: 'slide-up 0.3s both',
    }}>
      {/* Avatar */}
      <div style={{
        width: 32, height: 32, borderRadius: '50%', flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: isUser
          ? 'linear-gradient(135deg, var(--accent-core), var(--accent-glow))'
          : 'linear-gradient(135deg, var(--bg-elevated), var(--bg-card))',
        border: isUser ? 'none' : '1px solid var(--border-mid)',
        boxShadow: isUser ? '0 0 16px rgba(29,111,255,0.3)' : 'none',
      }}>
        {isUser
          ? <User size={14} color="#fff" />
          : <Bot size={14} color="var(--accent-soft)" />
        }
      </div>

      {/* Content */}
      <div style={{ maxWidth: '78%', minWidth: 0 }}>
        <div style={{
          padding: '12px 16px',
          borderRadius: isUser ? '16px 4px 16px 16px' : '4px 16px 16px 16px',
          background: isUser
            ? 'linear-gradient(135deg, var(--accent-core), #1558cc)'
            : 'var(--bg-card)',
          border: isUser ? 'none' : '1px solid var(--border-mid)',
          color: 'var(--text-primary)',
          fontSize: 13, lineHeight: 1.65,
          boxShadow: isUser ? '0 4px 20px rgba(29,111,255,0.2)' : 'var(--shadow-card)',
        }}>
          {isUser ? (
            <p style={{ margin: 0 }}>{msg.content}</p>
          ) : (
            <div className="markdown-body">
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Pipeline trace for assistant */}
        {!isUser && msg.metadata?.agents_used?.length > 0 && (
          <PipelineTrace
            agentsUsed={msg.metadata.agents_used}
            critiqeScore={msg.metadata.critique_score}
            hadRevision={msg.metadata.had_revision}
            plan={msg.metadata.plan}
          />
        )}

        {/* Timestamp */}
        <p style={{
          fontSize: 10, color: 'var(--text-dim)',
          marginTop: 4,
          textAlign: isUser ? 'right' : 'left',
          fontFamily: 'var(--font-mono)',
        }}>
          {msg.time}
        </p>
      </div>
    </div>
  );
}

export default function ChatPage({ sessionId, userId }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState('multi');
  const [hitlEnabled, setHitlEnabled] = useState(false);
  const bottomRef = useRef();
  const inputRef = useRef();

  const scrollToBottom = useCallback(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => { scrollToBottom(); }, [messages, scrollToBottom]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const text = input.trim();
    setInput('');

    const userMsg = {
      role: 'user', content: text,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);

    try {
      let data;
      if (mode === 'multi') {
        const res = await sendMultiAgent(text, sessionId, userId, hitlEnabled);
        data = res.data;
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.response,
          metadata: data,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        }]);
      } else {
        const res = await sendChat(text, sessionId);
        data = res.data;
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.response,
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        }]);
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `**Error:** ${err.response?.data?.detail?.substring(0, 200) || err.message}`,
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  const clearChat = () => setMessages([]);

  const SUGGESTIONS = [
    'Search for the latest developments in LangGraph',
    'Write Python code to find prime numbers up to 100',
    'What is RAG and how does it work?',
    'Calculate the compound interest on $10,000 at 5% for 10 years',
  ];

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100%', overflow: 'hidden',
    }}>
      {/* Top bar */}
      <div style={{
        padding: '12px 24px',
        borderBottom: '1px solid var(--border-dim)',
        display: 'flex', alignItems: 'center', gap: 12,
        background: 'var(--bg-surface)',
        flexShrink: 0,
      }}>
        {/* Mode selector */}
        <div style={{
          display: 'flex', gap: 2,
          background: 'var(--bg-base)',
          border: '1px solid var(--border-dim)',
          borderRadius: 9, padding: 3,
        }}>
          {[
            { id: 'multi', label: '5-Agent Pipeline', icon: '⚡' },
            { id: 'single', label: 'Single Agent', icon: '🤖' },
          ].map(m => (
            <button
              key={m.id}
              onClick={() => setMode(m.id)}
              style={{
                padding: '5px 12px', borderRadius: 7,
                border: 'none', cursor: 'pointer',
                fontSize: 12, fontFamily: 'var(--font-body)', fontWeight: 500,
                background: mode === m.id ? 'var(--accent-core)' : 'transparent',
                color: mode === m.id ? '#fff' : 'var(--text-tertiary)',
                transition: 'all var(--t-fast)',
                display: 'flex', alignItems: 'center', gap: 5,
              }}
            >
              <span>{m.icon}</span> {m.label}
            </button>
          ))}
        </div>

        {/* HITL toggle */}
        {mode === 'multi' && (
          <label style={{
            display: 'flex', alignItems: 'center', gap: 8,
            cursor: 'pointer', userSelect: 'none',
          }}>
            <div
              onClick={() => setHitlEnabled(v => !v)}
              style={{
                width: 36, height: 20, borderRadius: 10,
                background: hitlEnabled ? 'var(--yellow)' : 'var(--bg-elevated)',
                border: `1px solid ${hitlEnabled ? 'var(--yellow)' : 'var(--border-mid)'}`,
                position: 'relative', transition: 'all var(--t-smooth)',
                cursor: 'pointer',
              }}
            >
              <div style={{
                width: 14, height: 14, borderRadius: '50%',
                background: '#fff',
                position: 'absolute', top: 2,
                left: hitlEnabled ? 18 : 2,
                transition: 'left var(--t-smooth)',
                boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
              }} />
            </div>
            <span style={{
              fontSize: 12, color: hitlEnabled ? 'var(--yellow)' : 'var(--text-tertiary)',
              fontFamily: 'var(--font-mono)', fontWeight: 500,
              display: 'flex', alignItems: 'center', gap: 4,
            }}>
              <Shield size={11} />
              HITL
            </span>
          </label>
        )}

        <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
          <Button variant="ghost" size="sm" icon={RotateCcw} onClick={clearChat}>
            Clear
          </Button>
        </div>
      </div>

      {/* Messages area */}
      <div style={{
        flex: 1, overflowY: 'auto', padding: '24px',
        display: 'flex', flexDirection: 'column',
      }}>
        {/* HITL approvals */}
        {hitlEnabled && <HITLPanel onDecision={() => {}} />}

        {/* Empty state */}
        {messages.length === 0 && (
          <div style={{
            flex: 1, display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
            gap: 32, paddingBottom: 40,
          }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{
                width: 64, height: 64, borderRadius: '50%',
                background: 'linear-gradient(135deg, var(--accent-muted), var(--bg-elevated))',
                border: '1px solid var(--accent-rim)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                margin: '0 auto 16px',
                boxShadow: 'var(--shadow-glow)',
              }}>
                <Zap size={24} color="var(--accent-core)" />
              </div>
              <h2 style={{
                fontFamily: 'var(--font-display)',
                fontSize: 22, fontWeight: 700,
                color: 'var(--text-primary)',
                letterSpacing: '-0.02em', marginBottom: 8,
              }}>
                NEXUS is ready
              </h2>
              <p style={{ fontSize: 13, color: 'var(--text-tertiary)', maxWidth: 340 }}>
                {mode === 'multi'
                  ? '5 specialized agents — Planner, Researcher, Coder, Critic, Responder — will collaborate on your task.'
                  : 'Single agent mode — direct, fast responses.'
                }
              </p>
            </div>

            {/* Suggestion chips */}
            <div style={{
              display: 'flex', flexWrap: 'wrap', gap: 8,
              justifyContent: 'center', maxWidth: 560,
            }}>
              {SUGGESTIONS.map((s, i) => (
                <button
                  key={i}
                  onClick={() => { setInput(s); inputRef.current?.focus(); }}
                  style={{
                    padding: '8px 14px',
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border-mid)',
                    borderRadius: 20, cursor: 'pointer',
                    fontSize: 12, color: 'var(--text-secondary)',
                    fontFamily: 'var(--font-body)',
                    transition: 'all var(--t-fast)',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.borderColor = 'var(--accent-core)';
                    e.currentTarget.style.color = 'var(--accent-soft)';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.borderColor = 'var(--border-mid)';
                    e.currentTarget.style.color = 'var(--text-secondary)';
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Message list */}
        {messages.map((msg, i) => (
          <Message key={i} msg={msg} />
        ))}

        {/* Typing indicator */}
        {loading && (
          <div style={{
            display: 'flex', gap: 12, marginBottom: 20,
            animation: 'slide-up 0.3s both',
          }}>
            <div style={{
              width: 32, height: 32, borderRadius: '50%',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border-mid)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0,
            }}>
              <Bot size={14} color="var(--accent-soft)" />
            </div>
            <div style={{
              padding: '14px 18px',
              background: 'var(--bg-card)',
              border: '1px solid var(--border-mid)',
              borderRadius: '4px 16px 16px 16px',
              display: 'flex', alignItems: 'center', gap: 12,
            }}>
              {mode === 'multi' ? (
                <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                  {AGENT_ORDER.map(agent => (
                    <AgentPill key={agent} agent={agent} active />
                  ))}
                  <span style={{
                    fontSize: 11, color: 'var(--text-dim)',
                    fontFamily: 'var(--font-mono)',
                    animation: 'pulse-glow 1.5s ease-in-out infinite',
                  }}>
                    running...
                  </span>
                </div>
              ) : (
                <div style={{ display: 'flex', gap: 4 }}>
                  {[0, 1, 2].map(i => (
                    <span key={i} style={{
                      width: 6, height: 6, borderRadius: '50%',
                      background: 'var(--accent-core)',
                      animation: `pulse-glow 1.2s ease-in-out infinite`,
                      animationDelay: `${i * 0.2}s`,
                    }} />
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div style={{
        padding: '16px 24px',
        borderTop: '1px solid var(--border-dim)',
        background: 'var(--bg-surface)',
        flexShrink: 0,
      }}>
        <div style={{
          display: 'flex', gap: 10,
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border-mid)',
          borderRadius: 14, padding: '8px 8px 8px 16px',
          transition: 'border-color var(--t-fast)',
        }}
          onFocusCapture={e => e.currentTarget.style.borderColor = 'var(--accent-core)'}
          onBlurCapture={e => e.currentTarget.style.borderColor = 'var(--border-mid)'}
        >
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            placeholder={
              mode === 'multi'
                ? 'Ask anything — agents will collaborate...'
                : 'Send a message...'
            }
            rows={1}
            style={{
              flex: 1, background: 'none', border: 'none', outline: 'none',
              color: 'var(--text-primary)', fontFamily: 'var(--font-body)',
              fontSize: 14, lineHeight: 1.5, resize: 'none',
              maxHeight: 120, overflowY: 'auto',
            }}
          />
          <button
            onClick={send}
            disabled={!input.trim() || loading}
            style={{
              width: 40, height: 40, borderRadius: 10,
              background: input.trim() && !loading
                ? 'var(--accent-core)'
                : 'var(--bg-card)',
              border: `1px solid ${input.trim() && !loading ? 'var(--accent-glow)' : 'var(--border-dim)'}`,
              cursor: input.trim() && !loading ? 'pointer' : 'not-allowed',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'all var(--t-fast)',
              flexShrink: 0,
              boxShadow: input.trim() && !loading ? '0 0 16px rgba(29,111,255,0.3)' : 'none',
            }}
          >
            {loading
              ? <Spinner size={16} color="var(--accent-soft)" />
              : <Send size={15} color={input.trim() ? '#fff' : 'var(--text-dim)'} />
            }
          </button>
        </div>
        <p style={{
          textAlign: 'center', marginTop: 8,
          fontSize: 10, color: 'var(--text-dim)',
          fontFamily: 'var(--font-mono)',
        }}>
          Enter to send · Shift+Enter for newline
          {hitlEnabled && ' · HITL active — agent will pause for approval'}
        </p>
      </div>
    </div>
  );
}
