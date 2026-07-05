import { useState, useEffect } from 'react';
import LoginPage from './components/LoginPage';
import EmployeeDashboard from './components/EmployeeDashboard';
import ManagerDashboard from './components/ManagerDashboard';
import AdminDashboard from './components/AdminDashboard';
import ChatBot from './components/ChatBot';
import './index.css';

function Toast({ message, type, onClose }) {
  useEffect(() => {
    const timer = setTimeout(onClose, 4000);
    return () => clearTimeout(timer);
  }, [onClose]);

  return (
    <div className={`toast toast-${type}`}>
      {message}
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(null);
  const [toast, setToast] = useState(null);

  // Persist login in session
  useEffect(() => {
    const saved = sessionStorage.getItem('lma_user');
    if (saved) {
      try {
        setUser(JSON.parse(saved));
      } catch {
        sessionStorage.removeItem('lma_user');
      }
    }
  }, []);

  const handleLogin = (userData) => {
    setUser(userData);
    sessionStorage.setItem('lma_user', JSON.stringify(userData));
  };

  const handleLogout = () => {
    setUser(null);
    sessionStorage.removeItem('lma_user');
  };

  const showToast = (message, type = 'info') => {
    setToast({ message, type, key: Date.now() });
  };

  if (!user) {
    return (
      <>
        <LoginPage onLogin={handleLogin} />
        {toast && (
          <Toast
            key={toast.key}
            message={toast.message}
            type={toast.type}
            onClose={() => setToast(null)}
          />
        )}
      </>
    );
  }

  const renderDashboard = () => {
    switch (user.role) {
      case 'manager':
        return <ManagerDashboard user={user} showToast={showToast} />;
      case 'admin':
        return <AdminDashboard showToast={showToast} />;
      default:
        return <EmployeeDashboard user={user} showToast={showToast} />;
    }
  };

  return (
    <div className="app-container">
      {/* Navigation */}
      <nav className="navbar">
        <div className="navbar-brand">
          <div className="navbar-logo">🤖</div>
          <span className="navbar-title">Leave Management Agent</span>
        </div>
        <div className="navbar-user">
          <span className="navbar-role">{user.role}</span>
          <span className="navbar-name">
            {user.first_name} {user.last_name}
          </span>
          <button className="navbar-logout" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </nav>

      {/* Main Content */}
      <main className="main-content">
        {renderDashboard()}
      </main>

      {/* Chatbot (available for all logged-in users) */}
      <ChatBot user={user} />

      {/* Toast Notification */}
      {toast && (
        <Toast
          key={toast.key}
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
}
