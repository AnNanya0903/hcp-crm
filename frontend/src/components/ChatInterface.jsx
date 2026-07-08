import React, { useState, useRef, useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { sendMessage } from '../store/chatSlice';

export default function ChatInterface() {
  const dispatch = useDispatch();
  const { messages, preview, toolUsed, status } = useSelector((s) => s.chat);
  const [input, setInput] = useState('');
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    dispatch(sendMessage(input.trim()));
    setInput('');
  };

  return (
    <div className="card">
      <div className="chat-window">
        {messages.length === 0 && (
          <div className="msg agent">
            Hi! Tell me about an HCP interaction — e.g. "Just met Dr. Mehta, discussed
            CardioFlex data, she wants samples and a follow-up next Tuesday."
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role === 'user' ? 'user' : 'agent'}`}>{m.text}</div>
        ))}
        {status === 'loading' && <div className="msg agent">Thinking…</div>}
        <div ref={bottomRef} />
      </div>

      <form className="chat-input-row" onSubmit={handleSend}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your update…"
        />
        <button type="submit" className="btn">Send</button>
      </form>

      {preview && (
        <div className="preview-card">
          <h4>{toolUsed ? `Tool used: ${toolUsed}` : 'Preview'}</h4>
          <pre style={{ whiteSpace: 'pre-wrap', margin: 0, fontSize: 12 }}>
            {JSON.stringify(preview, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
