"""
database.py — SQLite database setup, schema creation, and demo data seeding
for the AI-Powered Leave Management Agent.
"""

import sqlite3
import os
import json
from datetime import datetime, date

DB_PATH = os.path.join(os.path.dirname(__file__), 'leave_management.db')


def get_db():
    """Get a database connection with row factory enabled."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables and seed demo data if the database is fresh."""
    conn = get_db()
    cursor = conn.cursor()

    # ── Create Tables ──────────────────────────────────────────────

    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS teams (
            team_id INTEGER PRIMARY KEY AUTOINCREMENT,
            team_name TEXT NOT NULL,
            department TEXT NOT NULL,
            min_coverage_pct REAL DEFAULT 0.5
        );

        CREATE TABLE IF NOT EXISTS employees (
            employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('employee', 'manager', 'admin')),
            department TEXT NOT NULL,
            team_id INTEGER,
            manager_id INTEGER,
            date_of_joining TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (team_id) REFERENCES teams(team_id),
            FOREIGN KEY (manager_id) REFERENCES employees(employee_id)
        );

        CREATE TABLE IF NOT EXISTS leave_policies (
            policy_id INTEGER PRIMARY KEY AUTOINCREMENT,
            leave_type TEXT NOT NULL UNIQUE,
            max_days_per_year INTEGER NOT NULL,
            max_consecutive INTEGER NOT NULL,
            advance_notice_days INTEGER DEFAULT 0,
            requires_document INTEGER DEFAULT 0,
            doc_required_after_days INTEGER DEFAULT 0,
            carry_forward INTEGER DEFAULT 0,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS leave_balances (
            balance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            leave_type TEXT NOT NULL,
            year INTEGER NOT NULL,
            total_allocated INTEGER NOT NULL,
            used INTEGER DEFAULT 0,
            remaining INTEGER NOT NULL,
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
            UNIQUE(employee_id, leave_type, year)
        );

        CREATE TABLE IF NOT EXISTS leave_requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            leave_type TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            num_days INTEGER NOT NULL,
            reason TEXT,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending', 'approved', 'rejected', 'escalated', 'cancelled')),
            submitted_at TEXT NOT NULL,
            decided_at TEXT,
            decided_by TEXT,
            agent_confidence REAL,
            agent_notes TEXT,
            manager_comment TEXT,
            FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
        );

        CREATE TABLE IF NOT EXISTS audit_log (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id INTEGER,
            action TEXT NOT NULL,
            performed_by TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            details TEXT,
            FOREIGN KEY (request_id) REFERENCES leave_requests(request_id)
        );
    ''')

    # ── Seed Demo Data (only if tables are empty) ──────────────────

    count = cursor.execute("SELECT COUNT(*) FROM teams").fetchone()[0]
    if count == 0:
        _seed_demo_data(cursor)

    conn.commit()
    conn.close()


def _seed_demo_data(cursor):
    """Insert sample teams, employees, policies, and balances."""

    current_year = date.today().year

    # Teams
    cursor.executemany(
        "INSERT INTO teams (team_name, department, min_coverage_pct) VALUES (?, ?, ?)",
        [
            ('Platform Squad', 'Engineering', 0.5),
            ('Product Design', 'Design', 0.5),
            ('HR Operations', 'Human Resources', 0.6),
        ]
    )

    # Employees
    # Note: passwords are plain text for demo purposes only
    employees = [
        ('Rahul', 'Verma', 'rahul@company.com', 'rahul', 'rahul123',
         'manager', 'Engineering', 1, None, '2020-03-15'),
        ('Priya', 'Sharma', 'priya@company.com', 'priya', 'priya123',
         'employee', 'Engineering', 1, 1, '2022-06-01'),
        ('Ankit', 'Patel', 'ankit@company.com', 'ankit', 'ankit123',
         'employee', 'Engineering', 1, 1, '2021-09-10'),
        ('Sneha', 'Gupta', 'sneha@company.com', 'sneha', 'sneha123',
         'employee', 'Engineering', 1, 1, '2023-01-20'),
        ('Meera', 'Nair', 'meera@company.com', 'meera', 'meera123',
         'employee', 'Engineering', 1, 1, '2022-11-05'),
        ('Admin', 'User', 'admin@company.com', 'admin', 'admin123',
         'admin', 'Human Resources', 3, None, '2019-01-01'),
    ]
    cursor.executemany(
        """INSERT INTO employees
           (first_name, last_name, email, username, password, role,
            department, team_id, manager_id, date_of_joining)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        employees
    )

    # Leave Policies
    policies = [
        ('Casual Leave', 12, 3, 2, 0, 0, 0,
         'For personal errands, family events, or short breaks. Max 3 consecutive days. Requires 2 days advance notice.'),
        ('Sick Leave', 10, 5, 0, 1, 2, 0,
         'For health-related absences. Medical certificate required if more than 2 consecutive days.'),
        ('Earned Leave', 15, 10, 7, 0, 0, 1,
         'Planned long leaves. Requires 7 days advance notice. Unused days can carry forward up to 5 days.'),
    ]
    cursor.executemany(
        """INSERT INTO leave_policies
           (leave_type, max_days_per_year, max_consecutive, advance_notice_days,
            requires_document, doc_required_after_days, carry_forward, description)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        policies
    )

    # Leave Balances — for each non-admin employee, for current year
    employee_ids = [1, 2, 3, 4, 5]  # Rahul, Priya, Ankit, Sneha, Meera
    leave_types = [
        ('Casual Leave', 12),
        ('Sick Leave', 10),
        ('Earned Leave', 15),
    ]

    balances = []
    for eid in employee_ids:
        for ltype, total in leave_types:
            # Give some employees some used leave for realism
            used = 0
            if eid == 2 and ltype == 'Casual Leave':
                used = 3  # Priya used 3 CL
            elif eid == 3 and ltype == 'Sick Leave':
                used = 2  # Ankit used 2 SL
            elif eid == 4 and ltype == 'Earned Leave':
                used = 5  # Sneha used 5 EL

            balances.append((eid, ltype, current_year, total, used, total - used))

    cursor.executemany(
        """INSERT INTO leave_balances
           (employee_id, leave_type, year, total_allocated, used, remaining)
           VALUES (?, ?, ?, ?, ?, ?)""",
        balances
    )

    # Add a couple of pre-existing leave requests (approved by manager after AI recommendation)
    now = datetime.now().isoformat()
    sample_requests = [
        (2, 'Casual Leave', f'{current_year}-06-10', f'{current_year}-06-12', 3,
         'Family function', 'approved', now, now, 'Rahul Verma', 0.92,
         json.dumps([
             {"name": "Leave Balance", "status": "PASS", "weight": 0.35, "message": "9 days remaining. Requesting 3 day(s)."},
             {"name": "Policy Compliance", "status": "PASS", "weight": 0.30, "message": "All policy checks passed for Casual Leave."},
             {"name": "Team Coverage", "status": "PASS", "weight": 0.20, "message": "4 of 5 members available (80% coverage). Threshold: 50%."},
             {"name": "Overlap Check", "status": "PASS", "weight": 0.15, "message": "No overlapping leave requests found."}
         ]), None),
        (3, 'Sick Leave', f'{current_year}-05-20', f'{current_year}-05-21', 2,
         'Fever and cold', 'approved', now, now, 'Rahul Verma', 0.88,
         json.dumps([
             {"name": "Leave Balance", "status": "PASS", "weight": 0.35, "message": "10 days remaining. Requesting 2 day(s)."},
             {"name": "Policy Compliance", "status": "PASS", "weight": 0.30, "message": "All policy checks passed for Sick Leave."},
             {"name": "Team Coverage", "status": "PASS", "weight": 0.20, "message": "4 of 5 members available (80% coverage). Threshold: 50%."},
             {"name": "Overlap Check", "status": "PASS", "weight": 0.15, "message": "No overlapping leave requests found."}
         ]), None),
        (4, 'Earned Leave', f'{current_year}-04-01', f'{current_year}-04-05', 5,
         'Vacation trip', 'approved', now, now, 'Rahul Verma', 0.55,
         json.dumps([
             {"name": "Leave Balance", "status": "PASS", "weight": 0.35, "message": "15 days remaining. Requesting 5 day(s)."},
             {"name": "Policy Compliance", "status": "PASS", "weight": 0.30, "message": "All policy checks passed for Earned Leave."},
             {"name": "Team Coverage", "status": "UNCERTAIN", "weight": 0.20, "message": "Coverage would be 60%, very close to minimum threshold of 50%. Recommending manager review."},
             {"name": "Overlap Check", "status": "PASS", "weight": 0.15, "message": "No overlapping leave requests found."}
         ]),
         'Approved - team can manage'),
    ]
    cursor.executemany(
        """INSERT INTO leave_requests
           (employee_id, leave_type, start_date, end_date, num_days,
            reason, status, submitted_at, decided_at, decided_by,
            agent_confidence, agent_notes, manager_comment)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        sample_requests
    )

    # Audit log entries for the seeded requests
    audit_entries = [
        (1, 'AI_RECOMMEND_APPROVE', 'AI Agent', now,
         'All checks passed. AI recommends approval. Confidence: 0.92.'),
        (1, 'MANAGER_APPROVED', 'Rahul Verma', now,
         'Manager approved leave request.'),
        (2, 'AI_RECOMMEND_APPROVE', 'AI Agent', now,
         'All checks passed. AI recommends approval. Confidence: 0.88.'),
        (2, 'MANAGER_APPROVED', 'Rahul Verma', now,
         'Manager approved leave request.'),
        (3, 'AI_RECOMMEND_REVIEW', 'AI Agent', now,
         'AI recommends careful review. Team coverage uncertain. Confidence: 0.55.'),
        (3, 'MANAGER_APPROVED', 'Rahul Verma', now,
         'Manager approved with comment: team can manage.'),
    ]
    cursor.executemany(
        """INSERT INTO audit_log (request_id, action, performed_by, timestamp, details)
           VALUES (?, ?, ?, ?, ?)""",
        audit_entries
    )
