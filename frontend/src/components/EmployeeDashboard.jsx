import { useState, useEffect } from 'react';
import { getBalances, getRequests, applyLeave, cancelLeave } from '../api';

const BALANCE_STYLES = [
  { gradient: 'linear-gradient(135deg, #6366f1, #8b5cf6)', bg: 'rgba(99,102,241,0.12)', icon: '🏖️' },
  { gradient: 'linear-gradient(135deg, #ef4444, #f97316)', bg: 'rgba(239,68,68,0.12)', icon: '🏥' },
  { gradient: 'linear-gradient(135deg, #10b981, #06b6d4)', bg: 'rgba(16,185,129,0.12)', icon: '⭐' },
];

export default function EmployeeDashboard({ user, showToast }) {
  const [balances, setBalances] = useState([]);
  const [requests, setRequests] = useState([]);
  const [activeTab, setActiveTab] = useState('overview');
  const [formData, setFormData] = useState({
    leave_type: 'Casual Leave',
    start_date: '',
    end_date: '',
    reason: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [lastResult, setLastResult] = useState(null);

  useEffect(() => {
    loadData();
  }, [user.employee_id]);

  const loadData = async () => {
    try {
      const [bal, req] = await Promise.all([
        getBalances(user.employee_id),
        getRequests(user.employee_id),
      ]);
      setBalances(bal);
      setRequests(req);
    } catch (err) {
      showToast('Failed to load data: ' + err.message, 'error');
    }
  };

  const handleApply = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setLastResult(null);

    try {
      const startDate = new Date(formData.start_date + 'T00:00:00');
      const endDate = new Date(formData.end_date + 'T00:00:00');
      const numDays = Math.round((endDate - startDate) / (1000 * 60 * 60 * 24)) + 1;

      if (numDays < 1) {
        showToast('End date must be on or after start date.', 'error');
        setSubmitting(false);
        return;
      }

      const result = await applyLeave({
        employee_id: user.employee_id,
        leave_type: formData.leave_type,
        start_date: formData.start_date,
        end_date: formData.end_date,
        num_days: numDays,
        reason: formData.reason,
      });

      setLastResult(result);

      if (result.recommendation === 'recommend_approve') {
        showToast('📋 Request submitted! AI recommends approval. Awaiting manager.', 'success');
      } else if (result.recommendation === 'recommend_reject') {
        showToast('📋 Request submitted. AI flagged issues. Awaiting manager review.', 'info');
      } else {
        showToast('📋 Request submitted. Awaiting manager review.', 'info');
      }

      setFormData({ leave_type: 'Casual Leave', start_date: '', end_date: '', reason: '' });
      loadData();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = async (requestId) => {
    try {
      await cancelLeave(requestId);
      showToast('Leave request cancelled.', 'success');
      loadData();
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-IN', {
      day: 'numeric', month: 'short', year: 'numeric'
    });
  };

  return (
    <div>
      <div className="page-header">
        <h1>Welcome back, {user.first_name} 👋</h1>
        <p>Manage your leaves and check your balances</p>
      </div>

      {/* Tabs */}
      <div className="tabs">
        <button className={`tab ${activeTab === 'overview' ? 'active' : ''}`} onClick={() => setActiveTab('overview')}>
          Overview
        </button>
        <button className={`tab ${activeTab === 'apply' ? 'active' : ''}`} onClick={() => setActiveTab('apply')}>
          Apply Leave
        </button>
        <button className={`tab ${activeTab === 'history' ? 'active' : ''}`} onClick={() => setActiveTab('history')}>
          Request History
        </button>
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="fade-in-up">
          <div className="section-header">
            <h2>Leave Balances</h2>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              Year {new Date().getFullYear()}
            </span>
          </div>
          <div className="grid-3">
            {balances.map((bal, i) => {
              const style = BALANCE_STYLES[i % BALANCE_STYLES.length];
              const usedPct = bal.total_allocated > 0 ? (bal.used / bal.total_allocated) * 100 : 0;
              return (
                <div key={bal.leave_type} className="glass-card balance-card fade-in-up">
                  <div className="balance-card-header">
                    <div className="balance-card-icon" style={{ background: style.bg }}>
                      {style.icon}
                    </div>
                    <span className="balance-card-type">{bal.leave_type}</span>
                  </div>
                  <div className="balance-card-number" style={{ backgroundImage: style.gradient, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                    {bal.remaining}
                  </div>
                  <div className="balance-card-label">days remaining</div>
                  <div className="balance-progress">
                    <div
                      className="balance-progress-bar"
                      style={{ width: `${usedPct}%`, background: style.gradient }}
                    />
                  </div>
                  <div className="balance-card-detail">
                    <span>Used: {bal.used}</span>
                    <span>Total: {bal.total_allocated}</span>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Recent Requests */}
          <div style={{ marginTop: '2rem' }}>
            <div className="section-header">
              <h2>Recent Requests</h2>
              <button className="btn btn-ghost btn-sm" onClick={() => setActiveTab('history')}>
                View All →
              </button>
            </div>
            {requests.length === 0 ? (
              <div className="glass-card empty-state">
                <div className="empty-state-icon">📋</div>
                <h3>No leave requests yet</h3>
                <p>Apply for leave to get started</p>
              </div>
            ) : (
              <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Type</th>
                      <th>Dates</th>
                      <th>Days</th>
                      <th>Status</th>
                      <th>Decided By</th>
                    </tr>
                  </thead>
                  <tbody>
                    {requests.slice(0, 5).map((req) => (
                      <tr key={req.request_id}>
                        <td>{req.leave_type}</td>
                        <td>{formatDate(req.start_date)} — {formatDate(req.end_date)}</td>
                        <td>{req.num_days}</td>
                        <td>
                          <span className={`badge badge-${req.status}`}>
                            {req.status}
                          </span>
                        </td>
                        <td>{req.decided_by || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Apply Tab */}
      {activeTab === 'apply' && (
        <div className="fade-in-up">
          <div className="glass-card">
            <h2 style={{ marginBottom: '1.25rem' }}>Apply for Leave</h2>
            <form className="request-form" onSubmit={handleApply}>
              <div className="form-group">
                <label className="form-label">Leave Type</label>
                <select
                  className="form-select"
                  value={formData.leave_type}
                  onChange={(e) => setFormData({ ...formData, leave_type: e.target.value })}
                >
                  <option value="Casual Leave">Casual Leave</option>
                  <option value="Sick Leave">Sick Leave</option>
                  <option value="Earned Leave">Earned Leave</option>
                </select>
              </div>



              <div className="form-group">
                <label className="form-label">Start Date</label>
                <input
                  className="form-input"
                  type="date"
                  value={formData.start_date}
                  onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">End Date</label>
                <input
                  className="form-input"
                  type="date"
                  value={formData.end_date}
                  onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                  required
                />
              </div>

              <div className="form-group full-width">
                <label className="form-label">Reason (optional)</label>
                <textarea
                  className="form-textarea"
                  placeholder="Briefly describe the reason for your leave..."
                  value={formData.reason}
                  onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
                />
              </div>

              <button className="btn btn-primary" type="submit" disabled={submitting}>
                {submitting ? <><span className="spinner"></span> Processing...</> : '🚀 Submit Request'}
              </button>
            </form>
          </div>

          {/* AI Recommendation Result */}
          {lastResult && (
            <div className="glass-card fade-in-up" style={{ marginTop: '1.5rem' }}>
              <h3 style={{ marginBottom: '1rem' }}>
                🤖 AI Recommendation:
                {lastResult.recommendation === 'recommend_approve' && ' ✅ Approve'}
                {lastResult.recommendation === 'recommend_reject' && ' ❌ Reject'}
                {lastResult.recommendation === 'recommend_review' && ' ⚠️ Needs Review'}
              </h3>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem', fontSize: '0.9rem' }}>
                {lastResult.summary}
              </p>
              <div style={{ marginBottom: '0.75rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                Confidence Score: <strong style={{ color: 'var(--text-primary)' }}>{(lastResult.confidence * 100).toFixed(0)}%</strong>
              </div>
              {lastResult.rules && lastResult.rules.map((rule, i) => (
                <div key={i} className="rule-item">
                  <span className="rule-icon">
                    {rule.status === 'PASS' ? '✓' : rule.status === 'FAIL' ? '✗' : '⚠'}
                  </span>
                  <strong>{rule.name}:</strong>&nbsp;{rule.message}
                </div>
              ))}
              <div style={{ marginTop: '1rem', padding: '0.75rem', background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.15)', borderRadius: 'var(--radius-md)', fontSize: '0.85rem', color: 'var(--status-pending)' }}>
                📋 Status: <strong>Pending Manager Approval</strong>
              </div>
            </div>
          )}
        </div>
      )}

      {/* History Tab */}
      {activeTab === 'history' && (
        <div className="fade-in-up">
          <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
            {requests.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">📋</div>
                <h3>No leave requests</h3>
                <p>Your request history will appear here</p>
              </div>
            ) : (
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>From</th>
                    <th>To</th>
                    <th>Days</th>
                    <th>Reason</th>
                    <th>Status</th>
                    <th>Decided By</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {requests.map((req) => {
                    const canCancel =
                      ['approved', 'escalated', 'pending'].includes(req.status) &&
                      new Date(req.start_date + 'T00:00:00') > new Date();
                    return (
                      <tr key={req.request_id}>
                        <td>{req.leave_type}</td>
                        <td>{formatDate(req.start_date)}</td>
                        <td>{formatDate(req.end_date)}</td>
                        <td>{req.num_days}</td>
                        <td style={{ maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {req.reason || '—'}
                        </td>
                        <td><span className={`badge badge-${req.status}`}>{req.status}</span></td>
                        <td>{req.decided_by || '—'}</td>
                        <td>
                          {canCancel && (
                            <button
                              className="btn btn-ghost btn-sm"
                              onClick={() => handleCancel(req.request_id)}
                            >
                              Cancel
                            </button>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
