import { useState, useEffect } from 'react';
import { getTeamCalendar } from '../api';

export default function TeamCalendar({ teamId, showToast }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!teamId) return;
    loadCalendar();
  }, [teamId]);

  const loadCalendar = async () => {
    setLoading(true);
    try {
      const result = await getTeamCalendar(teamId);
      setData(result);
    } catch (err) {
      showToast('Failed to load team calendar: ' + err.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    return new Date(dateStr + 'T00:00:00').toLocaleDateString('en-IN', {
      day: 'numeric', month: 'short'
    });
  };

  if (!teamId) {
    return (
      <div className="glass-card empty-state">
        <div className="empty-state-icon">👥</div>
        <h3>No team assigned</h3>
        <p>You are not assigned to a team</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="loading-screen">
        <span className="spinner"></span> Loading team calendar...
      </div>
    );
  }

  if (!data) return null;

  // Build a lookup: employee_id → array of leaves
  const leaveLookup = {};
  data.leaves.forEach((leave) => {
    if (!leaveLookup[leave.employee_id]) {
      leaveLookup[leave.employee_id] = [];
    }
    leaveLookup[leave.employee_id].push(leave);
  });

  return (
    <div>
      <div className="glass-card">
        <div className="section-header">
          <div>
            <h3>{data.team.team_name}</h3>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
              {data.team.department} • Min coverage: {(data.team.min_coverage_pct * 100).toFixed(0)}%
            </p>
          </div>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            {data.members.length} members
          </span>
        </div>

        {data.members.map((member) => {
          const memberLeaves = leaveLookup[member.employee_id] || [];
          const isOnLeave = memberLeaves.some((l) => {
            const today = new Date().toISOString().split('T')[0];
            return l.start_date <= today && l.end_date >= today;
          });

          return (
            <div key={member.employee_id} className="calendar-member">
              <div className="calendar-member-avatar">
                {member.first_name[0]}{member.last_name[0]}
              </div>
              <div className="calendar-member-info">
                <div className="calendar-member-name">
                  {member.first_name} {member.last_name}
                  {member.role === 'manager' && (
                    <span style={{ fontSize: '0.7rem', color: 'var(--accent-indigo)', marginLeft: '0.5rem' }}>
                      MANAGER
                    </span>
                  )}
                </div>
                {memberLeaves.length > 0 ? (
                  <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginTop: '0.3rem' }}>
                    {memberLeaves.map((l, i) => (
                      <span key={i} className="calendar-leave-tag">
                        {l.leave_type}: {formatDate(l.start_date)} — {formatDate(l.end_date)}
                      </span>
                    ))}
                  </div>
                ) : null}
              </div>
              {isOnLeave ? (
                <span className="calendar-leave-tag">On Leave</span>
              ) : (
                <span className="calendar-available-tag">Available</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
