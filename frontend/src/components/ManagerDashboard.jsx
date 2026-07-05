import { useState, useEffect } from 'react';
import { getPendingRequests, reviewRequest, getTeamCalendar } from '../api';
import TeamCalendar from './TeamCalendar';

export default function ManagerDashboard({ user, showToast }) {
  const [pending, setPending] = useState([]);
  const [activeTab, setActiveTab] = useState('pending');
  const [comments, setComments] = useState({});
  const [processing, setProcessing] = useState(null);

  useEffect(() => {
    loadPending();
  }, [user.employee_id]);

  const loadPending = async () => {
    try {
      const data = await getPendingRequests(user.employee_id);
      setPending(data);
    } catch (err) {
      showToast('Failed to load pending requests: ' + err.message, 'error');
    }
  };

  const handleReview = async (requestId, action) => {
    setProcessing(requestId);
    try {
      await reviewRequest(requestId, action, comments[requestId] || '', user.employee_id);
      showToast(
        action === 'approve'
          ? '✅ Request approved successfully.'
          : '❌ Request rejected.',
        action === 'approve' ? 'success' : 'info'
      );
      loadPending();
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setProcessing(null);
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
        <h1>Manager Dashboard 🎯</h1>
        <p>Review pending requests and manage your team</p>
      </div>

      <div className="tabs">
        <button className={`tab ${activeTab === 'pending' ? 'active' : ''}`} onClick={() => setActiveTab('pending')}>
          Pending Reviews ({pending.length})
        </button>
        <button className={`tab ${activeTab === 'team' ? 'active' : ''}`} onClick={() => setActiveTab('team')}>
          Team Calendar
        </button>
      </div>

      {activeTab === 'pending' && (
        <div>
          {pending.length === 0 ? (
            <div className="glass-card empty-state fade-in-up">
              <div className="empty-state-icon">🎉</div>
              <h3>All caught up!</h3>
              <p>No pending requests need your review</p>
            </div>
          ) : (
            pending.map((req) => (
              <div key={req.request_id} className="glass-card pending-card fade-in-up">
                <div className="pending-card-header">
                  <div className="pending-card-employee">
                    <div className="pending-card-avatar">
                      {req.first_name?.[0]}{req.last_name?.[0]}
                    </div>
                    <div>
                      <div className="pending-card-name">{req.first_name} {req.last_name}</div>
                      <div className="pending-card-dept">{req.department}</div>
                    </div>
                  </div>
                  <span className="badge badge-pending">Pending</span>
                </div>

                <div className="pending-card-details">
                  <div>
                    <div className="pending-card-detail-label">Leave Type</div>
                    <div className="pending-card-detail-value">{req.leave_type}</div>
                  </div>
                  <div>
                    <div className="pending-card-detail-label">Dates</div>
                    <div className="pending-card-detail-value">
                      {formatDate(req.start_date)} — {formatDate(req.end_date)}
                    </div>
                  </div>
                  <div>
                    <div className="pending-card-detail-label">Duration</div>
                    <div className="pending-card-detail-value">{req.num_days} day{req.num_days > 1 ? 's' : ''}</div>
                  </div>
                </div>

                {req.reason && (
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                    <strong>Reason:</strong> {req.reason}
                  </p>
                )}

                {/* Agent Analysis */}
                {req.agent_notes && (
                  <div className="pending-card-analysis">
                    <h4>🤖 AI Recommendation: {
                      req.agent_confidence >= 0.7 ? '✅ Approve' :
                      req.agent_confidence <= 0.3 ? '❌ Reject' : '⚠️ Needs Review'
                    } (Confidence: {(req.agent_confidence * 100).toFixed(0)}%)</h4>
                    {(Array.isArray(req.agent_notes) ? req.agent_notes : []).map((rule, i) => (
                      <div key={i} className="rule-item">
                        <span className="rule-icon">
                          {rule.status === 'PASS' ? '✓' : rule.status === 'FAIL' ? '✗' : '⚠'}
                        </span>
                        <strong>{rule.name}:</strong>&nbsp;
                        <span>{rule.message}</span>
                      </div>
                    ))}
                  </div>
                )}

                <div className="comment-input">
                  <input
                    className="form-input"
                    type="text"
                    placeholder="Add a comment (optional)..."
                    value={comments[req.request_id] || ''}
                    onChange={(e) => setComments({ ...comments, [req.request_id]: e.target.value })}
                    style={{ width: '100%' }}
                  />
                </div>

                <div className="pending-card-actions">
                  <button
                    className="btn btn-success"
                    onClick={() => handleReview(req.request_id, 'approve')}
                    disabled={processing === req.request_id}
                  >
                    {processing === req.request_id ? <span className="spinner"></span> : '✓'} Approve
                  </button>
                  <button
                    className="btn btn-danger"
                    onClick={() => handleReview(req.request_id, 'reject')}
                    disabled={processing === req.request_id}
                  >
                    ✕ Reject
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {activeTab === 'team' && (
        <div className="fade-in-up">
          <TeamCalendar teamId={user.team_id} showToast={showToast} />
        </div>
      )}
    </div>
  );
}
