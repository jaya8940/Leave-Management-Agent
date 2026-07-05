import { useState, useEffect } from 'react';
import { getReports, getAuditLog, getPolicies } from '../api';

export default function AdminDashboard({ showToast }) {
  const [activeTab, setActiveTab] = useState('reports');
  const [reports, setReports] = useState(null);
  const [auditLog, setAuditLog] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [rep, log, pol] = await Promise.all([
        getReports(),
        getAuditLog(),
        getPolicies(),
      ]);
      setReports(rep);
      setAuditLog(log);
      setPolicies(pol);
    } catch (err) {
      showToast('Failed to load admin data: ' + err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (isoStr) => {
    if (!isoStr) return '—';
    const d = new Date(isoStr);
    return d.toLocaleDateString('en-IN', {
      day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit'
    });
  };

  const getAuditDotClass = (action) => {
    if (action.includes('APPROVED')) return 'approve';
    if (action.includes('REJECTED')) return 'reject';
    if (action.includes('RECOMMEND_REVIEW')) return 'escalate';
    if (action.includes('RECOMMEND')) return 'approve';
    if (action.includes('CANCELLED')) return 'cancel';
    return 'approve';
  };

  if (loading) {
    return (
      <div className="loading-screen">
        <span className="spinner"></span> Loading admin dashboard...
      </div>
    );
  }

  const maxDays = reports?.by_type
    ? Math.max(...reports.by_type.map((t) => t.days_used || 0), 1)
    : 1;

  return (
    <div>
      <div className="page-header">
        <h1>Admin Dashboard 📊</h1>
        <p>Organization-wide leave analytics and system audit</p>
      </div>

      <div className="tabs">
        <button className={`tab ${activeTab === 'reports' ? 'active' : ''}`} onClick={() => setActiveTab('reports')}>
          Reports
        </button>
        <button className={`tab ${activeTab === 'audit' ? 'active' : ''}`} onClick={() => setActiveTab('audit')}>
          Audit Log
        </button>
        <button className={`tab ${activeTab === 'policies' ? 'active' : ''}`} onClick={() => setActiveTab('policies')}>
          Leave Policies
        </button>
      </div>

      {activeTab === 'reports' && reports && (
        <div className="fade-in-up">
          {/* Summary Stats */}
          <div className="grid-4" style={{ marginBottom: '2rem' }}>
            <div className="glass-card stat-card fade-in-up">
              <div className="stat-value">{reports.total_requests}</div>
              <div className="stat-label">Total Requests</div>
            </div>
            <div className="glass-card stat-card fade-in-up">
              <div className="stat-value">{reports.total_ai_recommend_approve}</div>
              <div className="stat-label">AI Recommend-Approve</div>
            </div>
            <div className="glass-card stat-card fade-in-up">
              <div className="stat-value" style={{ backgroundImage: 'linear-gradient(135deg, #10b981, #06b6d4)' }}>
                {reports.ai_recommend_approve_rate}%
              </div>
              <div className="stat-label">AI Recommend-Approve Rate</div>
            </div>
            <div className="glass-card stat-card fade-in-up">
              <div className="stat-value" style={{ backgroundImage: 'linear-gradient(135deg, #f59e0b, #ef4444)' }}>
                {reports.by_type?.reduce((sum, t) => sum + (t.days_used || 0), 0) || 0}
              </div>
              <div className="stat-label">Total Days Used</div>
            </div>
          </div>

          {/* Leave Usage by Type */}
          <div className="grid-2" style={{ marginBottom: '2rem' }}>
            <div className="glass-card">
              <h3 style={{ marginBottom: '1.25rem' }}>Leave Usage by Type</h3>
              {reports.by_type?.map((type, i) => {
                const gradients = [
                  'linear-gradient(90deg, #6366f1, #8b5cf6)',
                  'linear-gradient(90deg, #ef4444, #f97316)',
                  'linear-gradient(90deg, #10b981, #06b6d4)',
                ];
                const pct = maxDays > 0 ? ((type.days_used || 0) / maxDays) * 100 : 0;
                return (
                  <div key={type.leave_type} className="report-bar">
                    <span className="report-bar-label">{type.leave_type}</span>
                    <div className="report-bar-track">
                      <div
                        className="report-bar-fill"
                        style={{
                          width: `${Math.max(pct, 8)}%`,
                          background: gradients[i % gradients.length],
                        }}
                      >
                        {type.days_used || 0} days
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="glass-card">
              <h3 style={{ marginBottom: '1.25rem' }}>Request Outcomes</h3>
              {reports.by_type?.map((type) => (
                <div key={type.leave_type} style={{ marginBottom: '1rem' }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.5rem' }}>
                    {type.leave_type}
                  </div>
                  <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.8rem' }}>
                    <span style={{ color: 'var(--status-approved)' }}>
                      ✅ {type.approved || 0} approved
                    </span>
                    <span style={{ color: 'var(--status-rejected)' }}>
                      ❌ {type.rejected || 0} rejected
                    </span>
                    <span style={{ color: 'var(--status-escalated)' }}>
                      ⏳ {type.escalated || 0} escalated
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Employee Usage */}
          <div className="glass-card">
            <h3 style={{ marginBottom: '1.25rem' }}>Employee Leave Usage</h3>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Department</th>
                  <th>Total Days Used</th>
                </tr>
              </thead>
              <tbody>
                {reports.employee_usage?.map((emp, i) => (
                  <tr key={i}>
                    <td>{emp.name}</td>
                    <td style={{ color: 'var(--text-muted)' }}>{emp.department}</td>
                    <td>
                      <strong>{emp.total_days || 0}</strong> days
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'audit' && (
        <div className="glass-card fade-in-up">
          <h3 style={{ marginBottom: '1.25rem' }}>System Audit Trail</h3>
          {auditLog.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📜</div>
              <h3>No audit entries</h3>
            </div>
          ) : (
            auditLog.map((entry) => (
              <div key={entry.log_id} className="audit-entry">
                <div className={`audit-dot ${getAuditDotClass(entry.action)}`} />
                <div className="audit-content">
                  <div className="audit-action">
                    {entry.action.replace(/_/g, ' ')}
                    {entry.employee_name && (
                      <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>
                        {' '}— {entry.employee_name}
                      </span>
                    )}
                  </div>
                  <div className="audit-details">
                    {entry.leave_type && `${entry.leave_type} • `}
                    {entry.start_date && entry.end_date && `${entry.start_date} to ${entry.end_date} • `}
                    By {entry.performed_by}
                  </div>
                  {entry.details && (
                    <div className="audit-details" style={{ marginTop: '0.2rem', fontStyle: 'italic' }}>
                      {entry.details}
                    </div>
                  )}
                </div>
                <div className="audit-time">{formatTime(entry.timestamp)}</div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'policies' && (
        <div className="fade-in-up">
          <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Leave Type</th>
                  <th>Max Days/Year</th>
                  <th>Max Consecutive</th>
                  <th>Advance Notice</th>
                  <th>Document Required</th>
                  <th>Carry Forward</th>
                </tr>
              </thead>
              <tbody>
                {policies.map((p) => (
                  <tr key={p.policy_id}>
                    <td>{p.leave_type}</td>
                    <td>{p.max_days_per_year} days</td>
                    <td>{p.max_consecutive} days</td>
                    <td>{p.advance_notice_days > 0 ? `${p.advance_notice_days} days` : 'None'}</td>
                    <td>
                      {p.requires_document
                        ? <span style={{ color: 'var(--accent-amber)' }}>Yes (after {p.doc_required_after_days} days)</span>
                        : <span style={{ color: 'var(--text-muted)' }}>No</span>
                      }
                    </td>
                    <td>
                      {p.carry_forward
                        ? <span style={{ color: 'var(--accent-emerald)' }}>Yes</span>
                        : <span style={{ color: 'var(--text-muted)' }}>No</span>
                      }
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ marginTop: '1.5rem' }}>
            {policies.map((p) => (
              <div key={p.policy_id} className="glass-card" style={{ marginBottom: '1rem' }}>
                <h3 style={{ marginBottom: '0.5rem' }}>{p.leave_type}</h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>{p.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
