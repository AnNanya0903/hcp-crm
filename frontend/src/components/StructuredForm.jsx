import React, { useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { submitInteraction, clearLastSubmission } from '../store/interactionsSlice';

const PRODUCTS = ['CardioFlex', 'Nexivar', 'GlucoBalance', 'PulmoCare', 'OncoShield'];

const emptyForm = {
  hcp_id: '',
  interaction_type: 'visit',
  products_discussed: [],
  topics: '',
  sentiment: 'neutral',
  samples_distributed: false,
  sample_qty: 0,
  follow_up_required: false,
  follow_up_date: '',
  summary: '',
};

export default function StructuredForm() {
  const dispatch = useDispatch();
  const hcps = useSelector((s) => s.interactions.hcps);
  const lastSubmission = useSelector((s) => s.interactions.lastSubmission);
  const [form, setForm] = useState(emptyForm);

  const handleChange = (field, value) => setForm((f) => ({ ...f, [field]: value }));

  const toggleProduct = (product) => {
    setForm((f) => ({
      ...f,
      products_discussed: f.products_discussed.includes(product)
        ? f.products_discussed.filter((p) => p !== product)
        : [...f.products_discussed, product],
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    dispatch(
      submitInteraction({
        ...form,
        topics: form.topics ? form.topics.split(',').map((t) => t.trim()) : [],
        follow_up_date: form.follow_up_date || null,
      })
    );
    setForm(emptyForm);
  };

  return (
    <div className="card">
      <form onSubmit={handleSubmit}>
        <div className="form-grid">
          <div className="field">
            <label>HCP</label>
            <select value={form.hcp_id} onChange={(e) => handleChange('hcp_id', e.target.value)} required>
              <option value="">Select HCP…</option>
              {hcps.map((h) => (
                <option key={h.id} value={h.id}>{h.name} — {h.specialty}</option>
              ))}
            </select>
          </div>

          <div className="field">
            <label>Interaction Type</label>
            <select value={form.interaction_type} onChange={(e) => handleChange('interaction_type', e.target.value)}>
              <option value="visit">Visit</option>
              <option value="call">Call</option>
              <option value="email">Email</option>
              <option value="conference">Conference</option>
            </select>
          </div>

          <div className="field full">
            <label>Products Discussed</label>
            <div>
              {PRODUCTS.map((p) => (
                <label key={p} className="chip" style={{ cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={form.products_discussed.includes(p)}
                    onChange={() => toggleProduct(p)}
                    style={{ marginRight: 6 }}
                  />
                  {p}
                </label>
              ))}
            </div>
          </div>

          <div className="field full">
            <label>Topics (comma-separated)</label>
            <input value={form.topics} onChange={(e) => handleChange('topics', e.target.value)} placeholder="e.g. new trial data, dosing questions" />
          </div>

          <div className="field">
            <label>Sentiment</label>
            <select value={form.sentiment} onChange={(e) => handleChange('sentiment', e.target.value)}>
              <option value="positive">Positive</option>
              <option value="neutral">Neutral</option>
              <option value="negative">Negative</option>
            </select>
          </div>

          <div className="field">
            <label>Samples Distributed</label>
            <div className="checkbox-row">
              <input
                type="checkbox"
                checked={form.samples_distributed}
                onChange={(e) => handleChange('samples_distributed', e.target.checked)}
              />
              <input
                type="number"
                min="0"
                style={{ width: 80 }}
                value={form.sample_qty}
                onChange={(e) => handleChange('sample_qty', Number(e.target.value))}
                disabled={!form.samples_distributed}
              />
            </div>
          </div>

          <div className="field">
            <label>Follow-up Required</label>
            <div className="checkbox-row">
              <input
                type="checkbox"
                checked={form.follow_up_required}
                onChange={(e) => handleChange('follow_up_required', e.target.checked)}
              />
              <input
                type="date"
                value={form.follow_up_date}
                onChange={(e) => handleChange('follow_up_date', e.target.value)}
                disabled={!form.follow_up_required}
              />
            </div>
          </div>

          <div className="field full">
            <label>Notes / Summary</label>
            <textarea value={form.summary} onChange={(e) => handleChange('summary', e.target.value)} placeholder="Free-text notes about the interaction…" />
          </div>
        </div>

        <div style={{ marginTop: 16 }}>
          <button type="submit" className="btn">Log Interaction</button>
        </div>
      </form>

      {lastSubmission?.status === 'success' && (
        <div className="preview-card">
          <h4>✓ Logged</h4>
          <div>{lastSubmission.message}</div>
          <button className="btn secondary" style={{ marginTop: 10 }} onClick={() => dispatch(clearLastSubmission())}>
            Dismiss
          </button>
        </div>
      )}
    </div>
  );
}
