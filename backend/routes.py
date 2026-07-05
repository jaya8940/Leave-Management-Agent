"""
routes.py — REST API endpoints for the Leave Management Agent.

Handles all HTTP requests from the frontend, including:
- Authentication (login)
- Employee profile and balance queries
- Leave request submission, cancellation, and manager review
- Chatbot message processing
- Team calendar and reports
- Audit log access
"""

from flask import Blueprint, request, jsonify
from datetime import datetime, date
from database import get_db
from decision_engine import process_leave_request, RECOMMEND_APPROVE, RECOMMEND_REJECT, RECOMMEND_REVIEW
from nlp_parser import generate_chat_response
import json

api = Blueprint('api', __name__)


# ── Authentication ─────────────────────────────────────────────────

@api.route('/auth/login', methods=['POST'])
def login():
    """Simple login with username/password. Returns employee profile."""
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'error': 'Username and password are required.'}), 400

    conn = get_db()
    employee = conn.execute(
        """SELECT employee_id, first_name, last_name, email, username,
                  role, department, team_id, manager_id, date_of_joining
           FROM employees WHERE username = ? AND password = ? AND is_active = 1""",
        (username, password)
    ).fetchone()
    conn.close()

    if employee is None:
        return jsonify({'error': 'Invalid username or password.'}), 401

    return jsonify({
        'employee_id': employee['employee_id'],
        'first_name': employee['first_name'],
        'last_name': employee['last_name'],
        'email': employee['email'],
        'username': employee['username'],
        'role': employee['role'],
        'department': employee['department'],
        'team_id': employee['team_id'],
        'manager_id': employee['manager_id'],
        'date_of_joining': employee['date_of_joining'],
    })


# ── Employee Profile & Balances ───────────────────────────────────

@api.route('/employees/<int:employee_id>', methods=['GET'])
def get_employee(employee_id):
    """Get employee profile."""
    conn = get_db()
    emp = conn.execute(
        """SELECT employee_id, first_name, last_name, email, role,
                  department, team_id, manager_id, date_of_joining
           FROM employees WHERE employee_id = ?""",
        (employee_id,)
    ).fetchone()
    conn.close()

    if emp is None:
        return jsonify({'error': 'Employee not found.'}), 404

    return jsonify(dict(emp))


@api.route('/employees/<int:employee_id>/balances', methods=['GET'])
def get_balances(employee_id):
    """Get leave balances for an employee for the current year."""
    year = date.today().year
    conn = get_db()
    balances = conn.execute(
        """SELECT lb.leave_type, lb.total_allocated, lb.used, lb.remaining,
                  lp.max_days_per_year, lp.max_consecutive, lp.description
           FROM leave_balances lb
           JOIN leave_policies lp ON lb.leave_type = lp.leave_type
           WHERE lb.employee_id = ? AND lb.year = ?""",
        (employee_id, year)
    ).fetchall()
    conn.close()

    return jsonify([dict(b) for b in balances])


# ── Leave Requests ─────────────────────────────────────────────────

@api.route('/leave/apply', methods=['POST'])
def apply_leave():
    """
    Submit a new leave request. The AI decision engine evaluates it
    and returns a recommendation. The request is always saved as 'pending'
    for manager approval.
    """
    data = request.get_json()

    required = ['employee_id', 'leave_type', 'start_date', 'end_date', 'num_days']
    for field in required:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    employee_id = data['employee_id']
    leave_type = data['leave_type']
    start_date = data['start_date']
    end_date = data['end_date']
    num_days = data['num_days']
    reason = data.get('reason', '')

    # Validate dates
    try:
        s = datetime.strptime(start_date, '%Y-%m-%d').date()
        e = datetime.strptime(end_date, '%Y-%m-%d').date()
        if e < s:
            return jsonify({'error': 'End date cannot be before start date.'}), 400
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD.'}), 400

    # Process through the decision engine
    result, request_id = process_leave_request(
        employee_id, leave_type, start_date, end_date, num_days, reason
    )

    return jsonify({
        'request_id': request_id,
        **result.to_dict()
    })


@api.route('/leave/requests/<int:employee_id>', methods=['GET'])
def get_requests(employee_id):
    """Get all leave requests for an employee, ordered by most recent."""
    conn = get_db()
    requests = conn.execute(
        """SELECT * FROM leave_requests
           WHERE employee_id = ?
           ORDER BY submitted_at DESC""",
        (employee_id,)
    ).fetchall()
    conn.close()

    result = []
    for r in requests:
        row = dict(r)
        # Parse agent_notes from JSON string
        if row.get('agent_notes'):
            try:
                row['agent_notes'] = json.loads(row['agent_notes'])
            except (json.JSONDecodeError, TypeError):
                pass
        result.append(row)

    return jsonify(result)


@api.route('/leave/cancel/<int:request_id>', methods=['POST'])
def cancel_leave(request_id):
    """Cancel an approved leave request (only if start date is in the future)."""
    conn = get_db()
    req = conn.execute(
        "SELECT * FROM leave_requests WHERE request_id = ?",
        (request_id,)
    ).fetchone()

    if req is None:
        conn.close()
        return jsonify({'error': 'Request not found.'}), 404

    if req['status'] not in ('approved', 'escalated', 'pending'):
        conn.close()
        return jsonify({'error': f'Cannot cancel a request with status: {req["status"]}.'}), 400

    start = datetime.strptime(req['start_date'], '%Y-%m-%d').date()
    if start <= date.today():
        conn.close()
        return jsonify({'error': 'Cannot cancel leave that has already started.'}), 400

    now = datetime.now().isoformat()

    # Update request status
    conn.execute(
        """UPDATE leave_requests SET status = 'cancelled', decided_at = ?, decided_by = 'Employee'
           WHERE request_id = ?""",
        (now, request_id)
    )

    # Restore balance if it was approved
    if req['status'] == 'approved':
        year = datetime.strptime(req['start_date'], '%Y-%m-%d').year
        conn.execute(
            """UPDATE leave_balances
               SET used = used - ?, remaining = remaining + ?
               WHERE employee_id = ? AND leave_type = ? AND year = ?""",
            (req['num_days'], req['num_days'], req['employee_id'],
             req['leave_type'], year)
        )

    # Audit log
    conn.execute(
        """INSERT INTO audit_log (request_id, action, performed_by, timestamp, details)
           VALUES (?, 'CANCELLED', 'Employee', ?, 'Leave request cancelled by employee.')""",
        (request_id, now)
    )

    conn.commit()
    conn.close()

    return jsonify({'message': 'Leave request cancelled successfully.', 'request_id': request_id})


# ── Manager Actions ────────────────────────────────────────────────

@api.route('/manager/<int:manager_id>/pending', methods=['GET'])
def get_pending_requests(manager_id):
    """Get all pending requests for teams managed by this manager."""
    conn = get_db()
    requests = conn.execute(
        """SELECT lr.*, e.first_name, e.last_name, e.department
           FROM leave_requests lr
           JOIN employees e ON lr.employee_id = e.employee_id
           WHERE e.manager_id = ? AND lr.status = 'pending'
           ORDER BY lr.submitted_at DESC""",
        (manager_id,)
    ).fetchall()
    conn.close()

    result = []
    for r in requests:
        row = dict(r)
        if row.get('agent_notes'):
            try:
                row['agent_notes'] = json.loads(row['agent_notes'])
            except (json.JSONDecodeError, TypeError):
                pass
        result.append(row)

    return jsonify(result)


@api.route('/leave/review/<int:request_id>', methods=['POST'])
def review_request(request_id):
    """Manager approves or rejects a pending leave request."""
    data = request.get_json()
    action = data.get('action')  # 'approve' or 'reject'
    comment = data.get('comment', '')
    manager_id = data.get('manager_id')

    if action not in ('approve', 'reject'):
        return jsonify({'error': 'Action must be "approve" or "reject".'}), 400

    conn = get_db()
    req = conn.execute(
        "SELECT * FROM leave_requests WHERE request_id = ?",
        (request_id,)
    ).fetchone()

    if req is None:
        conn.close()
        return jsonify({'error': 'Request not found.'}), 404

    if req['status'] != 'pending':
        conn.close()
        return jsonify({'error': 'Only pending requests can be reviewed.'}), 400

    # Get manager name
    manager = conn.execute(
        "SELECT first_name, last_name FROM employees WHERE employee_id = ?",
        (manager_id,)
    ).fetchone()
    manager_name = f"{manager['first_name']} {manager['last_name']}" if manager else 'Manager'

    now = datetime.now().isoformat()
    new_status = 'approved' if action == 'approve' else 'rejected'

    conn.execute(
        """UPDATE leave_requests
           SET status = ?, decided_at = ?, decided_by = ?, manager_comment = ?
           WHERE request_id = ?""",
        (new_status, now, manager_name, comment, request_id)
    )

    # Update balance if approved
    if action == 'approve':
        year = datetime.strptime(req['start_date'], '%Y-%m-%d').year
        conn.execute(
            """UPDATE leave_balances
               SET used = used + ?, remaining = remaining - ?
               WHERE employee_id = ? AND leave_type = ? AND year = ?""",
            (req['num_days'], req['num_days'], req['employee_id'],
             req['leave_type'], year)
        )

    # Audit log
    audit_action = 'MANAGER_APPROVED' if action == 'approve' else 'MANAGER_REJECTED'
    conn.execute(
        """INSERT INTO audit_log (request_id, action, performed_by, timestamp, details)
           VALUES (?, ?, ?, ?, ?)""",
        (request_id, audit_action, manager_name, now,
         f'{audit_action} with comment: {comment}' if comment else audit_action)
    )

    conn.commit()
    conn.close()

    return jsonify({
        'message': f'Request {new_status} by {manager_name}.',
        'request_id': request_id,
        'status': new_status
    })


# ── Team Calendar ──────────────────────────────────────────────────

@api.route('/team/<int:team_id>/calendar', methods=['GET'])
def get_team_calendar(team_id):
    """Get all approved leaves for team members (current + upcoming)."""
    conn = get_db()

    # Get team info
    team = conn.execute("SELECT * FROM teams WHERE team_id = ?", (team_id,)).fetchone()
    if team is None:
        conn.close()
        return jsonify({'error': 'Team not found.'}), 404

    # Get team members
    members = conn.execute(
        """SELECT employee_id, first_name, last_name, role
           FROM employees WHERE team_id = ? AND is_active = 1""",
        (team_id,)
    ).fetchall()

    # Get approved/escalated leaves for the team
    today_str = date.today().strftime('%Y-%m-%d')
    leaves = conn.execute(
        """SELECT lr.*, e.first_name, e.last_name
           FROM leave_requests lr
           JOIN employees e ON lr.employee_id = e.employee_id
           WHERE e.team_id = ?
           AND lr.status IN ('approved', 'escalated')
           AND lr.end_date >= ?
           ORDER BY lr.start_date""",
        (team_id, today_str)
    ).fetchall()
    conn.close()

    return jsonify({
        'team': dict(team),
        'members': [dict(m) for m in members],
        'leaves': [dict(l) for l in leaves]
    })


# ── Chatbot ────────────────────────────────────────────────────────

@api.route('/chat', methods=['POST'])
def chat():
    """
    Process a chatbot message and return the agent's response.
    Handles intent classification, data retrieval, and leave processing.
    """
    data = request.get_json()
    message = data.get('message', '').strip()
    employee_id = data.get('employee_id')

    if not message:
        return jsonify({'response': 'Please type a message!', 'action': None})

    # Process through NLP
    chat_result = generate_chat_response(message, employee_id)

    # Handle actions that need database interaction
    if chat_result.get('action') == 'fetch_balance':
        conn = get_db()
        year = date.today().year
        balances = conn.execute(
            """SELECT leave_type, total_allocated, used, remaining
               FROM leave_balances WHERE employee_id = ? AND year = ?""",
            (employee_id, year)
        ).fetchall()
        conn.close()

        if balances:
            lines = ["Here's your leave balance for this year:\n"]
            for b in balances:
                bar_filled = int((b['used'] / b['total_allocated']) * 10) if b['total_allocated'] > 0 else 0
                bar = '█' * bar_filled + '░' * (10 - bar_filled)
                lines.append(
                    f"**{b['leave_type']}**: {b['remaining']} remaining "
                    f"/ {b['total_allocated']} total ({b['used']} used)\n"
                    f"`{bar}`"
                )
            chat_result['response'] = '\n\n'.join(lines)
        else:
            chat_result['response'] = "I couldn't find your leave balance records. Please contact HR."

    elif chat_result.get('action') == 'fetch_status':
        conn = get_db()
        requests_list = conn.execute(
            """SELECT leave_type, start_date, end_date, num_days, status, submitted_at
               FROM leave_requests WHERE employee_id = ?
               ORDER BY submitted_at DESC LIMIT 5""",
            (employee_id,)
        ).fetchall()
        conn.close()

        if requests_list:
            lines = ["Here are your recent leave requests:\n"]
            status_emoji = {
                'approved': '✅', 'rejected': '❌', 'escalated': '⏳',
                'pending': '🔄', 'cancelled': '🚫'
            }
            for r in requests_list:
                emoji = status_emoji.get(r['status'], '❓')
                lines.append(
                    f"{emoji} **{r['leave_type']}** — {r['start_date']} to {r['end_date']} "
                    f"({r['num_days']} day{'s' if r['num_days'] > 1 else ''}) — "
                    f"**{r['status'].upper()}**"
                )
            chat_result['response'] = '\n\n'.join(lines)
        else:
            chat_result['response'] = "You don't have any leave requests yet."

    elif chat_result.get('action') == 'apply_leave':
        parsed = chat_result.get('parsed', {})

        # Check what's missing
        missing = []
        if not parsed.get('leave_type'):
            missing.append('leave type')
        if not parsed.get('start_date'):
            missing.append('dates')

        if missing:
            chat_result['response'] = (
                f"I'd like to help you apply for leave, but I need a few more details:\n\n"
                f"**Missing:** {', '.join(missing)}\n\n"
                f"Could you try again? For example:\n"
                f"\"I need **casual leave** on **July 15 and 16**\""
            )
            chat_result['action'] = None
        else:
            # We have enough info — return parsed data for the frontend to confirm
            chat_result['response'] = (
                f"I've parsed your request:\n\n"
                f"📋 **Leave Type:** {parsed['leave_type']}\n"
                f"📅 **From:** {parsed['start_date']}\n"
                f"📅 **To:** {parsed['end_date']}\n"
                f"⏱️ **Duration:** {parsed['num_days']} day(s)\n"
                f"📝 **Reason:** {parsed.get('reason') or 'Not specified'}\n\n"
                f"Would you like me to submit this request?"
            )
            chat_result['needs_confirmation'] = True

    return jsonify(chat_result)


@api.route('/chat/confirm', methods=['POST'])
def chat_confirm():
    """Process a confirmed leave request from the chatbot."""
    data = request.get_json()
    employee_id = data.get('employee_id')
    leave_type = data.get('leave_type')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    num_days = data.get('num_days')
    reason = data.get('reason', '')

    result, request_id = process_leave_request(
        employee_id, leave_type, start_date, end_date, num_days, reason
    )

    # Build a conversational response
    rules_display = []
    for rule in result.rule_results:
        if rule.status == 'PASS':
            rules_display.append(f"✅ **{rule.name}:** {rule.message}")
        elif rule.status == 'FAIL':
            rules_display.append(f"❌ **{rule.name}:** {rule.message}")
        else:
            rules_display.append(f"⚠️ **{rule.name}:** {rule.message}")

    rules_text = '\n'.join(rules_display)

    rec_label = {
        'recommend_approve': '✅ Approve',
        'recommend_reject': '❌ Reject',
        'recommend_review': '⚠️ Needs Review'
    }.get(result.recommendation, 'Review')

    response = (
        f"I've evaluated your request:\n\n"
        f"{rules_text}\n\n"
        f"**AI Recommendation:** {rec_label}\n"
        f"**Confidence Score:** {(result.confidence * 100):.0f}%\n\n"
        f"📋 Your request has been submitted and is **awaiting manager approval**.\n"
        f"You'll be notified once your manager responds."
    )

    return jsonify({
        'response': response,
        'request_id': request_id,
        'recommendation': result.to_dict()
    })


# ── Admin: Reports ─────────────────────────────────────────────────

@api.route('/admin/reports', methods=['GET'])
def get_reports():
    """Generate leave utilization reports."""
    conn = get_db()
    year = date.today().year

    # Leave utilization by type
    by_type = conn.execute(
        """SELECT leave_type,
                  COUNT(*) as total_requests,
                  SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
                  SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected,
                  SUM(CASE WHEN status = 'escalated' THEN 1 ELSE 0 END) as escalated,
                  SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled,
                  SUM(CASE WHEN status = 'approved' THEN num_days ELSE 0 END) as days_used
           FROM leave_requests
           GROUP BY leave_type"""
    ).fetchall()

    # Leave utilization by department
    by_dept = conn.execute(
        """SELECT e.department,
                  COUNT(*) as total_requests,
                  SUM(CASE WHEN lr.status = 'approved' THEN lr.num_days ELSE 0 END) as days_used
           FROM leave_requests lr
           JOIN employees e ON lr.employee_id = e.employee_id
           GROUP BY e.department"""
    ).fetchall()

    # AI recommendation rate (how often AI recommended approval)
    total = conn.execute("SELECT COUNT(*) as cnt FROM leave_requests").fetchone()['cnt']
    ai_recommend_approve = conn.execute(
        "SELECT COUNT(*) as cnt FROM audit_log WHERE action = 'AI_RECOMMEND_APPROVE'"
    ).fetchone()['cnt']

    # Employee utilization
    emp_usage = conn.execute(
        """SELECT e.first_name || ' ' || e.last_name as name,
                  e.department,
                  SUM(CASE WHEN lr.status = 'approved' THEN lr.num_days ELSE 0 END) as total_days
           FROM employees e
           LEFT JOIN leave_requests lr ON e.employee_id = lr.employee_id
           WHERE e.role != 'admin'
           GROUP BY e.employee_id
           ORDER BY total_days DESC"""
    ).fetchall()

    conn.close()

    return jsonify({
        'by_type': [dict(r) for r in by_type],
        'by_department': [dict(r) for r in by_dept],
        'employee_usage': [dict(r) for r in emp_usage],
        'ai_recommend_approve_rate': round((ai_recommend_approve / total * 100), 1) if total > 0 else 0,
        'total_requests': total,
        'total_ai_recommend_approve': ai_recommend_approve,
    })


@api.route('/admin/audit-log', methods=['GET'])
def get_audit_log():
    """Get the full audit trail."""
    conn = get_db()
    logs = conn.execute(
        """SELECT al.*, lr.leave_type, lr.start_date, lr.end_date,
                  e.first_name || ' ' || e.last_name as employee_name
           FROM audit_log al
           LEFT JOIN leave_requests lr ON al.request_id = lr.request_id
           LEFT JOIN employees e ON lr.employee_id = e.employee_id
           ORDER BY al.timestamp DESC
           LIMIT 100"""
    ).fetchall()
    conn.close()

    return jsonify([dict(l) for l in logs])


# ── Leave Policies ─────────────────────────────────────────────────

@api.route('/policies', methods=['GET'])
def get_policies():
    """Get all leave policies."""
    conn = get_db()
    policies = conn.execute("SELECT * FROM leave_policies").fetchall()
    conn.close()
    return jsonify([dict(p) for p in policies])
