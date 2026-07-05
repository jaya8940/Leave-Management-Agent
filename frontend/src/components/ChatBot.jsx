import { useState, useRef, useEffect } from 'react';
import { sendChatMessage, confirmChatLeave } from '../api';

export default function ChatBot({ user }) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([
    {
      type: 'agent',
      text: "Hello! 👋 I'm your Leave Management Agent. I can help you apply for leave, check your balance, or view request status. Just type naturally!",
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [pendingConfirm, setPendingConfirm] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const addMessage = (type, text) => {
    setMessages((prev) => [...prev, { type, text }]);
  };

  const handleSend = async () => {
    const msg = input.trim();
    if (!msg || loading) return;

    addMessage('user', msg);
    setInput('');
    setLoading(true);

    try {
      const result = await sendChatMessage(msg, user.employee_id);

      if (result.needs_confirmation && result.action === 'apply_leave') {
        setPendingConfirm(result.parsed);
        addMessage('agent', result.response);
      } else if (result.response) {
        addMessage('agent', result.response);
      }
    } catch (err) {
      addMessage('agent', '❌ Sorry, something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async (confirmed) => {
    if (!confirmed) {
      setPendingConfirm(null);
      addMessage('agent', 'No worries! Request cancelled. Let me know if you need anything else.');
      return;
    }

    setLoading(true);
    addMessage('user', 'Yes, submit it!');

    try {
      const result = await confirmChatLeave({
        employee_id: user.employee_id,
        ...pendingConfirm,
      });
      addMessage('agent', result.response);
    } catch (err) {
      addMessage('agent', '❌ Failed to process request. Please try using the dashboard form.');
    } finally {
      setPendingConfirm(null);
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Render markdown-like formatting in chat messages
  const renderText = (text) => {
    if (!text) return '';
    // Bold
    let html = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    // Line breaks
    html = html.replace(/\n/g, '<br/>');
    return <span dangerouslySetInnerHTML={{ __html: html }} />;
  };

  return (
    <>
      {/* Toggle Button */}
      <button
        className={`chatbot-toggle ${isOpen ? 'active' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        title="Chat with AI Agent"
      >
        {isOpen ? '✕' : '💬'}
      </button>

      {/* Chat Window */}
      {isOpen && (
        <div className="chatbot-window">
          <div className="chatbot-header">
            <div className="chatbot-header-icon">🤖</div>
            <div className="chatbot-header-info">
              <h3>Leave Agent</h3>
              <p>● Online</p>
            </div>
          </div>

          <div className="chatbot-messages">
            {messages.map((msg, i) => (
              <div key={i} className={`chat-message ${msg.type}`}>
                {renderText(msg.text)}
              </div>
            ))}

            {/* Confirmation Buttons */}
            {pendingConfirm && !loading && (
              <div className="chat-confirm-buttons" style={{ alignSelf: 'flex-start' }}>
                <button className="btn btn-success btn-sm" onClick={() => handleConfirm(true)}>
                  ✓ Yes, submit
                </button>
                <button className="btn btn-ghost btn-sm" onClick={() => handleConfirm(false)}>
                  ✕ Cancel
                </button>
              </div>
            )}

            {/* Typing Indicator */}
            {loading && (
              <div className="chat-typing">
                <span></span>
                <span></span>
                <span></span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          <div className="chatbot-input">
            <input
              type="text"
              placeholder="Type your message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={loading}
            />
            <button
              className="chatbot-send"
              onClick={handleSend}
              disabled={loading || !input.trim()}
            >
              ➤
            </button>
          </div>
        </div>
      )}
    </>
  );
}
