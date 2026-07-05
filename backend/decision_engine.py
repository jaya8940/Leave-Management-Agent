"""
decision_engine.py — The core AI agent that evaluates leave requests
using a weighted rule-based decision system.

Implements the LeaveDecisionEngine algorithm from the project report:
- PolicyEvaluator: checks request against company leave policies
- BalanceChecker: verifies sufficient leave balance
- TeamCoverageAnalyzer: ensures minimum team strength is maintained
- ConfidenceAssessor: computes composite score for final decision
"""

from datetime import datetime, date, timedelta
from database import get_db
import json


# ── Result Constants ───────────────────────────────────────────────

PASS = 'PASS'
FAIL = 'FAIL'
UNCERTAIN = 'UNCERTAIN'

RECOMMEND_APPROVE = 'recommend_approve'
RECOMMEND_REJECT = 'recommend_reject'
RECOMMEND_REVIEW = 'recommend_review'


class RuleResult:
    """Holds the result of evaluating a single rule."""
    def __init__(self, name, status, weight, message):
        self.name = name
        self.status = status      # PASS, FAIL, or UNCERTAIN
        self.weight = weight
        self.message = message

    def to_dict(self):
        return {
            'name': self.name,
            'status': self.status,
            'weight': self.weight,
            'message': self.message
        }


class DecisionResult:
    """Holds the AI recommendation (not a final decision)."""
    def __init__(self, recommendation, confidence, rule_results, summary):
        self.recommendation = recommendation  # recommend_approve, recommend_reject, recommend_review
        self.confidence = confidence           # 0.0 to 1.0
        self.rule_results = rule_results
        self.summary = summary

    def to_dict(self):
        return {
            'recommendation': self.recommendation,
            'confidence': round(self.confidence, 2),
            'summary': self.summary,
            'rules': [r.to_dict() for r in self.rule_results]
        }


# ── Individual Evaluators ──────────────────────────────────────────

def check_leave_balance(employee_id, leave_type, num_days, year):
    """
    Verify the employee has enough remaining leave of the requested type.
    Weight: 0.35 (critical — no balance means no leave)
    """
    conn = get_db()
    balance = conn.execute(
        """SELECT remaining FROM leave_balances
           WHERE employee_id = ? AND leave_type = ? AND year = ?""",
        (employee_id, leave_type, year)
    ).fetchone()
    conn.close()

    if balance is None:
        return RuleResult(
            'Leave Balance',
            FAIL, 0.35,
            f'No {leave_type} balance found for this year.'
        )

    remaining = balance['remaining']
    if remaining >= num_days:
        return RuleResult(
            'Leave Balance',
            PASS, 0.35,
            f'{remaining} days remaining. Requesting {num_days} day(s).'
        )
    elif remaining > 0:
        return RuleResult(
            'Leave Balance',
            FAIL, 0.35,
            f'Insufficient balance. Only {remaining} day(s) remaining, but {num_days} requested.'
        )
    else:
        return RuleResult(
            'Leave Balance',
            FAIL, 0.35,
            f'No {leave_type} balance remaining for this year.'
        )


def check_policy_rules(leave_type, num_days, start_date, reason):
    """
    Evaluate the request against the organization's leave policy.
    Checks: advance notice, max consecutive days, document requirement.
    Weight: 0.30
    """
    conn = get_db()
    policy = conn.execute(
        "SELECT * FROM leave_policies WHERE leave_type = ?",
        (leave_type,)
    ).fetchone()
    conn.close()

    if policy is None:
        return RuleResult(
            'Policy Compliance',
            FAIL, 0.30,
            f'Unknown leave type: {leave_type}.'
        )

    # Parse the start date
    if isinstance(start_date, str):
        leave_start = datetime.strptime(start_date, '%Y-%m-%d').date()
    else:
        leave_start = start_date

    today = date.today()
    days_notice = (leave_start - today).days

    issues = []
    status = PASS

    # Check advance notice requirement
    if policy['advance_notice_days'] > 0 and days_notice < policy['advance_notice_days']:
        # For sick leave, be lenient — mark as uncertain rather than fail
        if leave_type == 'Sick Leave':
            status = UNCERTAIN if status != FAIL else FAIL
            issues.append(
                f'Short notice ({days_notice} day(s)), but sick leave can be urgent.'
            )
        else:
            status = FAIL
            issues.append(
                f'Requires {policy["advance_notice_days"]} days advance notice, '
                f'but only {days_notice} day(s) given.'
            )

    # Check max consecutive days
    if num_days > policy['max_consecutive']:
        status = FAIL
        issues.append(
            f'Exceeds maximum consecutive days ({policy["max_consecutive"]}) '
            f'for {leave_type}.'
        )

    # Check document requirement
    if policy['requires_document'] and num_days > policy['doc_required_after_days']:
        if not reason or len(reason.strip()) < 5:
            status = UNCERTAIN if status != FAIL else FAIL
            issues.append(
                f'{leave_type} longer than {policy["doc_required_after_days"]} day(s) '
                f'may require supporting documentation.'
            )

    # Check if leave is in the past
    if leave_start < today:
        status = FAIL
        issues.append('Cannot apply for leave on past dates.')

    message = '; '.join(issues) if issues else f'All policy checks passed for {leave_type}.'
    return RuleResult('Policy Compliance', status, 0.30, message)


def check_team_coverage(employee_id, start_date, end_date):
    """
    Check if approving this request would bring team strength below
    the configured minimum coverage percentage.
    Weight: 0.20
    """
    conn = get_db()

    # Get employee's team info
    employee = conn.execute(
        """SELECT e.team_id, t.team_name, t.min_coverage_pct
           FROM employees e JOIN teams t ON e.team_id = t.team_id
           WHERE e.employee_id = ?""",
        (employee_id,)
    ).fetchone()

    if employee is None or employee['team_id'] is None:
        conn.close()
        return RuleResult(
            'Team Coverage',
            UNCERTAIN, 0.20,
            'Employee is not assigned to a team. Cannot verify coverage.'
        )

    team_id = employee['team_id']
    min_coverage = employee['min_coverage_pct']

    # Count total active team members
    total_members = conn.execute(
        "SELECT COUNT(*) as cnt FROM employees WHERE team_id = ? AND is_active = 1",
        (team_id,)
    ).fetchone()['cnt']

    if total_members <= 1:
        conn.close()
        return RuleResult(
            'Team Coverage',
            UNCERTAIN, 0.20,
            'Only one member in the team. Escalating for manager review.'
        )

    # Count team members already on approved/escalated leave during the requested period
    on_leave = conn.execute(
        """SELECT COUNT(DISTINCT employee_id) as cnt FROM leave_requests
           WHERE employee_id IN (SELECT employee_id FROM employees WHERE team_id = ?)
           AND employee_id != ?
           AND status IN ('approved', 'escalated')
           AND start_date <= ? AND end_date >= ?""",
        (team_id, employee_id, end_date, start_date)
    ).fetchone()['cnt']
    conn.close()

    # Calculate coverage if this request is approved
    available_after = total_members - on_leave - 1  # -1 for the requesting employee
    coverage_after = available_after / total_members

    if coverage_after >= min_coverage:
        return RuleResult(
            'Team Coverage',
            PASS, 0.20,
            f'{available_after} of {total_members} members available '
            f'({coverage_after:.0%} coverage). Threshold: {min_coverage:.0%}.'
        )
    elif coverage_after >= (min_coverage - 0.1):
        return RuleResult(
            'Team Coverage',
            UNCERTAIN, 0.20,
            f'Coverage would be {coverage_after:.0%}, very close to '
            f'minimum threshold of {min_coverage:.0%}. Recommending manager review.'
        )
    else:
        return RuleResult(
            'Team Coverage',
            FAIL, 0.20,
            f'Coverage would drop to {coverage_after:.0%}, below the '
            f'minimum threshold of {min_coverage:.0%}.'
        )


def check_overlap(employee_id, start_date, end_date):
    """
    Check if the employee already has an active leave request
    overlapping with the requested dates.
    Weight: 0.15
    """
    conn = get_db()
    overlap = conn.execute(
        """SELECT request_id, start_date, end_date, status FROM leave_requests
           WHERE employee_id = ?
           AND status IN ('approved', 'pending', 'escalated')
           AND start_date <= ? AND end_date >= ?""",
        (employee_id, end_date, start_date)
    ).fetchone()
    conn.close()

    if overlap:
        return RuleResult(
            'Overlap Check',
            FAIL, 0.15,
            f'Overlapping leave already exists '
            f'({overlap["start_date"]} to {overlap["end_date"]}, '
            f'status: {overlap["status"]}).'
        )
    else:
        return RuleResult(
            'Overlap Check',
            PASS, 0.15,
            'No overlapping leave requests found.'
        )


# ── Main Decision Engine ──────────────────────────────────────────

def evaluate_leave_request(employee_id, leave_type, start_date, end_date, num_days, reason=None):
    """
    Run the full decision engine pipeline on a leave request.

    Algorithm:
        1. Initialize score = 1.0
        2. For each rule: evaluate and adjust score based on weight
        3. If score <= 0.3: Recommend Reject
        4. If score >= 0.7 and no uncertainties: Recommend Approve
        5. Otherwise: Recommend Review

    The AI only produces a recommendation — the final decision
    is always made by the manager.

    Returns a DecisionResult with the recommendation, confidence, and rule details.
    """
    year = datetime.now().year

    # Run all evaluators
    rule_results = [
        check_leave_balance(employee_id, leave_type, num_days, year),
        check_policy_rules(leave_type, num_days, start_date, reason),
        check_team_coverage(employee_id, start_date, end_date),
        check_overlap(employee_id, start_date, end_date),
    ]

    # Calculate composite confidence score
    score = 1.0
    fail_reasons = []
    uncertain_flags = []

    for rule in rule_results:
        if rule.status == FAIL:
            score -= rule.weight
            fail_reasons.append(rule.message)
        elif rule.status == UNCERTAIN:
            score -= (rule.weight * 0.5)
            uncertain_flags.append(rule.message)

    # Clamp score to [0, 1]
    score = max(0.0, min(1.0, score))

    # Recommendation thresholds (AI recommends, manager decides)
    if score <= 0.3:
        recommendation = RECOMMEND_REJECT
        summary = 'AI recommends rejection. ' + ' | '.join(fail_reasons)
    elif score >= 0.7 and len(uncertain_flags) == 0:
        recommendation = RECOMMEND_APPROVE
        summary = 'All checks passed. AI recommends approval.'
    else:
        recommendation = RECOMMEND_REVIEW
        reasons = fail_reasons + uncertain_flags
        summary = 'AI recommends careful review. ' + ' | '.join(reasons)

    return DecisionResult(recommendation, score, rule_results, summary)


def process_leave_request(employee_id, leave_type, start_date, end_date, num_days, reason=None):
    """
    Full processing pipeline: evaluate with AI, persist as pending, log audit.
    The AI only recommends — all requests are saved as 'pending' for manager approval.
    Leave balances are NOT deducted here; only when the manager approves.
    Returns the recommendation result and the created request ID.
    """
    # Run the decision engine (produces a recommendation, not a final decision)
    result = evaluate_leave_request(
        employee_id, leave_type, start_date, end_date, num_days, reason
    )

    conn = get_db()
    try:
        now = datetime.now().isoformat()

        # Insert the leave request — always as 'pending'
        cursor = conn.execute(
            """INSERT INTO leave_requests
               (employee_id, leave_type, start_date, end_date, num_days,
                reason, status, submitted_at, decided_at, decided_by,
                agent_confidence, agent_notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                employee_id, leave_type, start_date, end_date, num_days,
                reason, 'pending', now,
                None,   # decided_at — pending manager action
                None,   # decided_by — pending manager action
                result.confidence,
                json.dumps(result.to_dict()['rules'])
            )
        )
        request_id = cursor.lastrowid

        # Do NOT update leave balance here — only when manager approves

        # Audit log — record the AI recommendation
        recommendation_label = {
            RECOMMEND_APPROVE: 'AI_RECOMMEND_APPROVE',
            RECOMMEND_REJECT: 'AI_RECOMMEND_REJECT',
            RECOMMEND_REVIEW: 'AI_RECOMMEND_REVIEW'
        }
        conn.execute(
            """INSERT INTO audit_log (request_id, action, performed_by, timestamp, details)
               VALUES (?, ?, ?, ?, ?)""",
            (request_id, recommendation_label[result.recommendation], 'AI Agent', now, result.summary)
        )

        conn.commit()
    finally:
        conn.close()

    return result, request_id
