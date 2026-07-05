import { useState } from 'react';
import { login } from '../api';

const DEMO_ACCOUNTS = [
  { name: 'Priya Sharma', username: 'priya', password: 'priya123', role: 'Employee' },
  { name: 'Ankit Patel', username: 'ankit', password: 'ankit123', role: 'Employee' },
  { name: 'Rahul Verma', username: 'rahul', password: 'rahul123', role: 'Manager' },
  { name: 'Admin User', username: 'admin', password: 'admin123', role: 'Admin' },
  // { name: 'Karthi', username: 'karthi', password: 'karthi123', role: 'Employee' },
];

export default function LoginPage({ onLogin }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const user = await login(username, password);
      onLogin(user);
    } catch (err) {
      setError(err.message || 'Login failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = async (account) => {
    setUsername(account.username);
    setPassword(account.password);
    setError('');
    setLoading(true);

    try {
      const user = await login(account.username, account.password);
      onLogin(user);
    } catch (err) {
      setError(err.message || 'Login failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-container">
        <div className="login-header">
          <div className="login-icon">🤖</div>
          <h1>Leave Management Agent</h1>
          <p>AI-powered intelligent leave processing system</p>
        </div>

        <div className="glass-card login-card">
          <form className="login-form" onSubmit={handleSubmit}>
            {error && <div className="login-error">{error}</div>}

            <div className="form-group">
              <label className="form-label" htmlFor="username">Username</label>
              <input
                id="username"
                className="form-input"
                type="text"
                placeholder="Enter your username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="password">Password</label>
              <input
                id="password"
                className="form-input"
                type="password"
                placeholder="Enter your password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            <button className="btn btn-primary btn-lg" type="submit" disabled={loading}>
              {loading ? <><span className="spinner"></span> Signing in...</> : 'Sign In'}
            </button>
          </form>

          <div className="login-divider">Demo Accounts</div>

          <div className="demo-accounts">
            {DEMO_ACCOUNTS.map((account) => (
              <button
                key={account.username}
                className="demo-account-btn"
                onClick={() => handleDemoLogin(account)}
                disabled={loading}
              >
                <span>{account.name} ({account.username})</span>
                <span className="demo-role">{account.role}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
