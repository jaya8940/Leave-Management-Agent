"""
app.py — Flask application entry point for the Leave Management Agent.
Initializes the database, registers routes, and starts the server.
"""

from flask import Flask
from flask_cors import CORS
from database import init_db
from routes import api

app = Flask(__name__)
CORS(app)

# Register the API blueprint with /api prefix
app.register_blueprint(api, url_prefix='/api')


@app.route('/')
def index():
    return {
        'name': 'AI-Powered Leave Management Agent',
        'version': '1.0.0',
        'status': 'running',
        'endpoints': {
            'login': '/api/auth/login',
            'balances': '/api/employees/<id>/balances',
            'apply_leave': '/api/leave/apply',
            'requests': '/api/leave/requests/<employee_id>',
            'chat': '/api/chat',
            'team_calendar': '/api/team/<team_id>/calendar',
            'reports': '/api/admin/reports',
            'audit_log': '/api/admin/audit-log',
        }
    }


if __name__ == '__main__':
    print("\n[*] Initializing AI-Powered Leave Management Agent...")
    print("[*] Setting up database and seeding demo data...")
    init_db()
    print("[OK] Database ready!")
    print("[*] Starting Flask server on http://localhost:5000")
    print("-" * 50)
    app.run(debug=True, port=5000)
