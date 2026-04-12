import React, { useState, useEffect, useRef } from 'react';
import { Upload, Search, Trash2, FileText, X, Check } from 'lucide-react';
import { getDocuments, uploadPDF, deleteDocument, searchDocs } from '../utils/api';
import { Card, Button, Input, SectionHeader, EmptyState, Tag, Spinner } from '../components/UI';

function UploadZone({ onUpload }) {
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState(null);
  const [docId, setDocId] = useState('');
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const inputRef = useRef();

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f?.type === 'application/pdf') setFile(f);
  };

  const doUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError('');
    setResult(null);
    try {
      const { data } = await uploadPDF(file, docId || undefined);
      setResult(data);
      setFile(null);
      setDocId('');
      onUpload?.();
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed');
    }
    setUploading(false);
  };

  return (
    <div style={{ marginBottom: 24 }}>
      {/* Drop zone */}
      <div
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        onClick={() => !file && inputRef.current?.click()}
        style={{
          border: `2px dashed ${dragging ? 'var(--accent-core)' : file ? 'var(--green)' : 'var(--border-mid)'}`,
          borderRadius: 14,
          padding: '32px 24px',
          textAlign: 'center',
          cursor: file ? 'default' : 'pointer',
          background: dragging
            ? 'var(--accent-muted)'
            : file
              ? 'rgba(16,185,129,0.05)'
              : 'var(--bg-elevated)',
          transition: 'all var(--t-smooth)',
          marginBottom: 12,
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          style={{ display: 'none' }}
          onChange={e => setFile(e.target.files[0])}
        />

        {file ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
            <FileText size={20} color="var(--green)" />
            <div>
              <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>
                {file.name}
              </p>
              <p style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                {(file.size / 1024).toFixed(1)} KB
              </p>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); setFile(null); }}
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                color: 'var(--text-dim)', display: 'flex', marginLeft: 8,
              }}
            >
              <X size={14} />
            </button>
          </div>
        ) : (
          <>
            <Upload size={24} color="var(--text-dim)" style={{ margin: '0 auto 10px' }} />
            <p style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 4 }}>
              Drop a PDF here or click to browse
            </p>
            <p style={{ fontSize: 11, color: 'var(--text-dim)' }}>
              PDF files only — will be chunked and embedded for RAG
            </p>
          </>
        )}
      </div>

      {file && (
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <Input
            value={docId}
            onChange={e => setDocId(e.target.value)}
            placeholder="Document ID (optional — leave empty for auto)"
            style={{ flex: 1 }}
          />
          <Button
            variant="primary"
            icon={Upload}
            loading={uploading}
            onClick={doUpload}
          >
            Ingest PDF
          </Button>
        </div>
      )}

      {result && (
        <div style={{
          marginTop: 10, padding: '10px 14px',
          background: result.status === 'success'
            ? 'rgba(16,185,129,0.08)'
            : 'rgba(245,158,11,0.08)',
          border: `1px solid ${result.status === 'success' ? 'rgba(16,185,129,0.25)' : 'rgba(245,158,11,0.25)'}`,
          borderRadius: 9,
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <Check size={14} color={result.status === 'success' ? 'var(--green)' : 'var(--yellow)'} />
          <p style={{ fontSize: 12, color: result.status === 'success' ? 'var(--green)' : 'var(--yellow)' }}>
            {result.status === 'success'
              ? `✓ Ingested ${result.chunks_stored} chunks from "${result.filename}"`
              : `Document "${result.doc_id}" already exists`
            }
          </p>
        </div>
      )}

      {error && (
        <p style={{ fontSize: 12, color: 'var(--red)', marginTop: 8 }}>{error}</p>
      )}
    </div>
  );
}

function SearchPanel() {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState('hybrid');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  const doSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const { data } = await searchDocs(query, 8, mode);
      setResults(data.results || []);
      setSearched(true);
    } catch {}
    setLoading(false);
  };

  const modeColors = {
    hybrid: 'var(--accent-core)',
    vector: 'var(--cyan-core)',
    keyword: 'var(--agent-coder)',
  };

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <div style={{ flex: 1 }}>
          <Input
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && doSearch()}
            placeholder="Search your knowledge base..."
            prefix={<Search size={13} />}
          />
        </div>
        {/* Mode selector */}
        <div style={{
          display: 'flex', gap: 2,
          background: 'var(--bg-base)',
          border: '1px solid var(--border-dim)',
          borderRadius: 9, padding: 3,
        }}>
          {['hybrid', 'vector', 'keyword'].map(m => (
            <button
              key={m}
              onClick={() => setMode(m)}
              style={{
                padding: '5px 10px', borderRadius: 7,
                border: 'none', cursor: 'pointer',
                fontSize: 11, fontFamily: 'var(--font-mono)',
                background: mode === m ? modeColors[m] + '22' : 'transparent',
                color: mode === m ? modeColors[m] : 'var(--text-tertiary)',
                border: mode === m ? `1px solid ${modeColors[m]}44` : '1px solid transparent',
                transition: 'all var(--t-fast)',
              }}
            >
              {m}
            </button>
          ))}
        </div>
        <Button variant="primary" icon={Search} onClick={doSearch} loading={loading}>
          Search
        </Button>
      </div>

      {loading && (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 32 }}>
          <Spinner />
        </div>
      )}

      {!loading && searched && results.length === 0 && (
        <EmptyState icon="🔍" title="No results"
          description="Try a different query or upload more documents" />
      )}

      {!loading && results.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <p style={{
            fontSize: 11, color: 'var(--text-dim)',
            fontFamily: 'var(--font-mono)', marginBottom: 4,
          }}>
            {results.length} results · mode: {mode}
          </p>
          {results.map((r, i) => {
            const score = r.rrf_score ?? r.similarity ?? r.keyword_score ?? 0;
            return (
              <div key={i} style={{
                padding: '12px 14px',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border-dim)',
                borderRadius: 10,
                animation: `slide-up ${0.05 + i * 0.04}s both`,
              }}>
                <div style={{
                  display: 'flex', gap: 8, marginBottom: 6,
                  alignItems: 'center',
                }}>
                  <FileText size={12} color="var(--text-dim)" />
                  <span style={{
                    fontSize: 11, color: 'var(--text-tertiary)',
                    fontFamily: 'var(--font-mono)',
                  }}>
                    {r.filename} · chunk {r.chunk_index}
                  </span>
                  <span style={{
                    marginLeft: 'auto', fontSize: 10,
                    fontFamily: 'var(--font-mono)',
                    color: score > 0.7 ? 'var(--green)' : score > 0.4 ? 'var(--yellow)' : 'var(--text-dim)',
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border-dim)',
                    padding: '1px 7px', borderRadius: 4,
                  }}>
                    {(score * 100).toFixed(0)}%
                  </span>
                </div>
                <p style={{
                  fontSize: 12, color: 'var(--text-secondary)',
                  lineHeight: 1.6, fontFamily: 'var(--font-body)',
                }}>
                  {r.text}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function DocumentsPage() {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('upload');

  const loadDocs = async () => {
    setLoading(true);
    try {
      const { data } = await getDocuments();
      setDocs(data.documents || []);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { loadDocs(); }, []);

  const del = async (docId) => {
    await deleteDocument(docId);
    setDocs(d => d.filter(doc => doc.doc_id !== docId));
  };

  const TABS = [
    { id: 'upload', label: 'Upload', icon: '📤' },
    { id: 'search', label: 'Search', icon: '🔍' },
    { id: 'library', label: 'Library', icon: '📚' },
  ];

  return (
    <div style={{ padding: 24, overflowY: 'auto', height: '100%' }}>
      <SectionHeader
        title="Knowledge Base"
        subtitle="Upload PDFs and search with hybrid vector + keyword retrieval"
        action={
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <Tag color="var(--accent-core)">{docs.length} documents</Tag>
          </div>
        }
      />

      {/* Tab bar */}
      <div style={{
        display: 'flex', gap: 2,
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-dim)',
        borderRadius: 10, padding: 4, marginBottom: 24,
      }}>
        {TABS.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              flex: 1, padding: '7px 12px', borderRadius: 7,
              border: activeTab === tab.id ? '1px solid var(--border-mid)' : '1px solid transparent',
              cursor: 'pointer', fontSize: 12,
              fontFamily: 'var(--font-body)', fontWeight: 500,
              background: activeTab === tab.id ? 'var(--bg-card)' : 'transparent',
              color: activeTab === tab.id ? 'var(--text-primary)' : 'var(--text-tertiary)',
              transition: 'all var(--t-fast)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 5,
            }}
          >
            <span>{tab.icon}</span> {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'upload' && (
        <div style={{ animation: 'fade-in 0.3s both' }}>
          <UploadZone onUpload={loadDocs} />
        </div>
      )}

      {activeTab === 'search' && (
        <div style={{ animation: 'fade-in 0.3s both' }}>
          <SearchPanel />
        </div>
      )}

      {activeTab === 'library' && (
        <div style={{ animation: 'fade-in 0.3s both' }}>
          {loading ? (
            <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
              <Spinner />
            </div>
          ) : docs.length === 0 ? (
            <EmptyState icon="📚" title="No documents"
              description="Upload a PDF to add it to your knowledge base" />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {docs.map((doc, i) => (
                <Card key={doc.doc_id} style={{ padding: '14px 16px', animation: `slide-up ${i * 0.06}s both` }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div style={{
                      width: 40, height: 40, borderRadius: 9,
                      background: 'rgba(29,111,255,0.1)',
                      border: '1px solid var(--accent-rim)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}>
                      <FileText size={18} color="var(--accent-core)" />
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{
                        fontSize: 13, fontWeight: 600, color: 'var(--text-primary)',
                        marginBottom: 3,
                      }} className="truncate">
                        {doc.filename}
                      </p>
                      <div style={{ display: 'flex', gap: 8 }}>
                        <span style={{
                          fontSize: 10, color: 'var(--text-dim)',
                          fontFamily: 'var(--font-mono)',
                        }}>
                          ID: {doc.doc_id}
                        </span>
                        <Tag color="var(--cyan-core)">{doc.chunk_count} chunks</Tag>
                        <span style={{ fontSize: 10, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
                          {doc.ingested_at?.substring(0, 10)}
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={() => del(doc.doc_id)}
                      style={{
                        background: 'none', border: 'none', cursor: 'pointer',
                        color: 'var(--text-dim)', padding: 6,
                        borderRadius: 6, display: 'flex',
                        transition: 'color var(--t-fast)',
                      }}
                      onMouseEnter={e => e.currentTarget.style.color = 'var(--red)'}
                      onMouseLeave={e => e.currentTarget.style.color = 'var(--text-dim)'}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
