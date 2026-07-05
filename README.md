# AI-Powered Leave Management Agent

An intelligent leave management system powered by an AI decision engine that automates employee leave processing. The agent evaluates requests against company policies, checks team availability, and makes instant decisions — or escalates to managers when human judgment is needed.

## Features

- **AI Decision Engine** — Weighted rule evaluation with auto-approve, reject, or escalate
- **Conversational Chatbot** — Apply for leave using natural language
- **Role-Based Dashboards** — Employee, Manager, and Admin views
- **Real-Time Processing** — Leave requests processed in under 2 seconds
- **Team Coverage Analysis** — Ensures minimum team strength is maintained
- **Full Audit Trail** — Every decision logged and traceable
- **Leave Analytics** — Utilization reports and trend analysis

## Quick Start

### Prerequisites

- **Python 3.8+** — [Download](https://python.org)
- **Node.js 18+** — [Download](https://nodejs.org)

### Option 1: One-Click Start (Windows)

Double-click `start.bat` — it installs all dependencies and launches both servers.

### Option 2: Manual Start

**Backend:**
```bash
cd backend
pip install -r requirements.txt
python app.py
```

**Frontend** (in a separate terminal):
```bash
cd frontend
npm install
npm run dev
```

Then open **http://localhost:5173** in your browser.

## Demo Accounts

| Name | Username | Password | Role |
|------|----------|----------|------|
| Priya Sharma | `priya` | `priya123` | Employee |
| Ankit Patel | `ankit` | `ankit123` | Employee |
| Sneha Gupta | `sneha` | `sneha123` | Employee |
| Rahul Verma | `rahul` | `rahul123` | Manager |
| Admin User | `admin` | `admin123` | HR Admin |

## How the AI Agent Works

When a leave request is submitted, the agent runs it through a pipeline of evaluators:

1. **Leave Balance Check** (weight: 0.35) — Verifies sufficient balance
2. **Policy Compliance** (weight: 0.30) — Checks advance notice, max consecutive days, etc.
3. **Team Coverage** (weight: 0.20) — Ensures minimum team strength
4. **Overlap Check** (weight: 0.15) — Prevents duplicate requests

Each evaluator returns PASS, FAIL, or UNCERTAIN. A composite confidence score determines the outcome:
- **Score ≥ 0.7** → Auto-approve
- **Score ≤ 0.3** → Reject
- **Otherwise** → Escalate to manager

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite |
| Backend | Python + Flask |
| Database | SQLite |
| NLP | Pattern-based intent & date extraction |
| Styling | Custom CSS (Dark Glassmorphism) |

## Project Structure

```
├── backend/
│   ├── app.py              # Flask application entry point
│   ├── database.py         # SQLite schema & seed data
│   ├── decision_engine.py  # AI decision engine (core)
│   ├── nlp_parser.py       # Natural language processing
│   ├── routes.py           # REST API endpoints
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── LoginPage.jsx
│   │   │   ├── EmployeeDashboard.jsx
│   │   │   ├── ManagerDashboard.jsx
│   │   │   ├── AdminDashboard.jsx
│   │   │   ├── ChatBot.jsx
│   │   │   └── TeamCalendar.jsx
│   │   ├── api.js          # API client
│   │   ├── App.jsx         # Main application
│   │   └── index.css       # Design system
│   └── package.json
├── start.bat               # One-click startup (Windows)
└── README.md
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Employee login |
| GET | `/api/employees/:id/balances` | Leave balances |
| POST | `/api/leave/apply` | Submit leave request |
| GET | `/api/leave/requests/:id` | Request history |
| POST | `/api/leave/cancel/:id` | Cancel leave |
| GET | `/api/manager/:id/pending` | Escalated requests |
| POST | `/api/leave/review/:id` | Approve/reject |
| GET | `/api/team/:id/calendar` | Team calendar |
| POST | `/api/chat` | Chatbot message |
| GET | `/api/admin/reports` | Leave reports |
| GET | `/api/admin/audit-log` | Audit trail |
