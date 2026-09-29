import { useState } from 'react';
import { createComplaint } from '../api/client';
import type { Complaint, ComplaintCreate } from '../api/types';

export function SubmitPage() {
  const [form, setForm] = useState<ComplaintCreate>({
    text: '',
    location: '',
    reporter_contact: '',
  });
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<Complaint | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  const validate = (): boolean => {
    const errs: Record<string, string> = {};
    if (form.text.length < 10) errs.text = 'Must be at least 10 characters';
    if (form.text.length > 2000) errs.text = 'Must be at most 2000 characters';
    if (form.location.length < 3) errs.location = 'Must be at least 3 characters';
    if (form.location.length > 200) errs.location = 'Must be at most 200 characters';
    setFieldErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setResult(null);

    if (!validate()) return;

    setLoading(true);
    try {
      const complaint = await createComplaint({
        text: form.text,
        location: form.location,
        reporter_contact: form.reporter_contact || null,
      });
      setResult(complaint);
      setForm({ text: '', location: '', reporter_contact: '' });
      setFieldErrors({});
    } catch (err: any) {
      if (err.status === 429) {
        setError(`Rate limit exceeded. Please try again in ${err.body?.retry_after || 60} seconds.`);
      } else if (err.status === 400 && err.body?.errors) {
        const errs: Record<string, string> = {};
        for (const e of err.body.errors) {
          errs[e.field] = e.message;
        }
        setFieldErrors(errs);
      } else {
        setError(err.message || 'Something went wrong');
      }
    } finally {
      setLoading(false);
    }
  };

  const priorityClass = (p: string) => {
    if (p === 'high') return 'badge badge-high';
    if (p === 'low') return 'badge badge-low';
    return 'badge badge-normal';
  };

  return (
    <div className="page submit-page">
      <div className="page-header">
        <h1>Submit a Complaint</h1>
        <p className="page-subtitle">Report a municipal issue in your area</p>
      </div>

      <div className="submit-layout">
        <form className="card submit-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="complaint-text">Complaint Details *</label>
            <textarea
              id="complaint-text"
              placeholder="Describe the issue in detail (10–2000 characters)"
              value={form.text}
              onChange={(e) => setForm({ ...form, text: e.target.value })}
              rows={5}
              maxLength={2000}
              disabled={loading}
            />
            <div className="field-info">
              <span className={`char-count ${form.text.length < 10 ? 'warn' : ''}`}>
                {form.text.length}/2000
              </span>
              {fieldErrors.text && <span className="field-error">{fieldErrors.text}</span>}
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="complaint-location">Location *</label>
            <input
              id="complaint-location"
              type="text"
              placeholder="Street, area, city (3–200 characters)"
              value={form.location}
              onChange={(e) => setForm({ ...form, location: e.target.value })}
              maxLength={200}
              disabled={loading}
            />
            {fieldErrors.location && <span className="field-error">{fieldErrors.location}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="complaint-contact">Contact (optional)</label>
            <input
              id="complaint-contact"
              type="text"
              placeholder="Phone or email"
              value={form.reporter_contact || ''}
              onChange={(e) => setForm({ ...form, reporter_contact: e.target.value })}
              maxLength={200}
              disabled={loading}
            />
          </div>

          {error && <div className="alert alert-error">{error}</div>}

          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? (
              <span className="loading-state">
                <span className="spinner" />
                Analyzing with AI…
              </span>
            ) : (
              'Submit Complaint'
            )}
          </button>
        </form>

        {result && (
          <div className="card result-card fade-in">
            <h2>Complaint Submitted</h2>
            <div className="result-badges">
              <span className={`badge badge-category-${result.category}`}>
                {result.category}
              </span>
              <span className={priorityClass(result.priority)}>
                {result.priority}
              </span>
              <span className="badge badge-provider" title="Triage provider">
                {result.triaged_by}
              </span>
            </div>
            {result.ai_summary && (
              <div className="result-summary">
                <strong>AI Summary:</strong> {result.ai_summary}
              </div>
            )}
            <div className="result-meta">
              <span>ID: {result.id.slice(0, 8)}…</span>
              <span>Latency: {result.triage_latency_ms}ms</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
