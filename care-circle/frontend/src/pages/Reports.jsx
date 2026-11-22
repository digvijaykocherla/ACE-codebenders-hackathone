import { useCallback, useEffect, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { createReport, listReports } from '../api.js';
import { asList, fmtDate } from '../format.js';
import { Card, Empty, ErrorBox, Loading } from '../components/ui.jsx';

const EMPTY_FORM = { title: '', report_date: '', provider: '', summary: '' };

export default function Reports() {
  const { recipientId, canWrite } = useOutletContext();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [form, setForm] = useState(EMPTY_FORM);
  const [formError, setFormError] = useState('');
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await listReports(recipientId);
      setItems(asList(data, 'items'));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [recipientId]);

  useEffect(() => {
    load();
  }, [load]);

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  async function handleCreate(e) {
    e.preventDefault();
    setFormError('');
    if (!form.title.trim()) {
      setFormError('Title is required.');
      return;
    }
    setSaving(true);
    try {
      await createReport(recipientId, {
        title: form.title.trim(),
        report_date: form.report_date || null,
        provider: form.provider.trim() || null,
        summary: form.summary.trim() || null,
      });
      setForm(EMPTY_FORM);
      await load();
    } catch (err) {
      setFormError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="stack">
      <Card title="Medical reports">
        <p className="muted small" style={{ margin: 0 }}>
          Store a factual summary of each document for coordination. Care Circle does not interpret reports.
        </p>
        {loading && <Loading />}
        {!loading && error && <ErrorBox message={error} onRetry={load} />}
        {!loading && !error && items.length === 0 && <Empty>No reports recorded.</Empty>}
        {!loading && !error && items.length > 0 && (
          <ul className="list">
            {items.map((r) => (
              <li key={r.id} className="list-item">
                <div>
                  <strong>{r.title}</strong>
                  <div className="muted small">
                    {fmtDate(r.report_date)}
                    {r.provider ? ` · ${r.provider}` : ''}
                  </div>
                  {r.summary && <div className="small">{r.summary}</div>}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {canWrite && (
        <Card title="Add a report">
          {formError && <div className="alert error">{formError}</div>}
          <form className="form" onSubmit={handleCreate}>
            <label className="field">
              <span>Title</span>
              <input value={form.title} onChange={set('title')} required />
            </label>
            <label className="field">
              <span>Report date</span>
              <input type="date" value={form.report_date} onChange={set('report_date')} />
            </label>
            <label className="field">
              <span>Provider</span>
              <input value={form.provider} onChange={set('provider')} />
            </label>
            <label className="field wide">
              <span>Summary</span>
              <textarea value={form.summary} onChange={set('summary')} />
            </label>
            <div>
              <button className="btn" type="submit" disabled={saving}>
                {saving ? 'Saving…' : 'Add report'}
              </button>
            </div>
          </form>
        </Card>
      )}
    </div>
  );
}
