import React, { useEffect, useState } from 'react';
import { useDispatch } from 'react-redux';
import { loadHcps } from '../store/interactionsSlice';
import StructuredForm from './StructuredForm';
import ChatInterface from './ChatInterface';
import InteractionsList from './InteractionsList';

export default function LogInteractionScreen() {
  const dispatch = useDispatch();
  const [tab, setTab] = useState('form');

  useEffect(() => {
    dispatch(loadHcps());
  }, [dispatch]);

  return (
    <div className="app-shell">
      <div className="app-header">
        <h1>Log Interaction</h1>
        <p>Capture an HCP interaction via the structured form or by chatting naturally with the AI agent.</p>
      </div>

      <div className="tabs">
        <button className={`tab-btn ${tab === 'form' ? 'active' : ''}`} onClick={() => setTab('form')}>
          Structured Form
        </button>
        <button className={`tab-btn ${tab === 'chat' ? 'active' : ''}`} onClick={() => setTab('chat')}>
          Conversational
        </button>
      </div>

      {tab === 'form' ? <StructuredForm /> : <ChatInterface />}

      <InteractionsList />
    </div>
  );
}
