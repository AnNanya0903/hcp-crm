import React, { useEffect } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { loadInteractions } from '../store/interactionsSlice';

export default function InteractionsList() {
  const dispatch = useDispatch();
  const interactions = useSelector((s) => s.interactions.interactions);
  const hcps = useSelector((s) => s.interactions.hcps);
  const lastSubmission = useSelector((s) => s.interactions.lastSubmission);

  useEffect(() => {
    dispatch(loadInteractions());
  }, [dispatch, lastSubmission]);

  const hcpName = (id) => hcps.find((h) => h.id === id)?.name || id;

  return (
    <div className="card">
      <h4 style={{ marginTop: 0 }}>Recent Interactions</h4>
      {interactions.length === 0 && <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>No interactions logged yet.</div>}
      {interactions.map((i) => (
        <div className="list-row" key={i.id}>
          <div>
            <strong>{hcpName(i.hcp_id)}</strong> — {i.interaction_type}
            <div style={{ color: 'var(--text-muted)' }}>{i.summary || i.topics.join(', ')}</div>
          </div>
          <span className={`badge ${i.sentiment}`}>{i.sentiment}</span>
        </div>
      ))}
    </div>
  );
}
