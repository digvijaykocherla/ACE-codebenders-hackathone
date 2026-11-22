import { useCallback, useEffect, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { createAppointment, listAppointments, updateAppointment } from '../api.js';
import { fmtDateTime, toIso } from '../format.js';
import { Card, Empty, ErrorBox, Loading, StatusBadge } from '../components/ui.jsx';

const STATUSES = ['scheduled', 'completed', 'cancelled'];
const EMPTY_FORM = { title: '', scheduled_at: '', location: '', notes: '' };

export default function Appointments() {
  const { recipientId, canWrite } = useOutletContext();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [form, setForm] = useState(EMPTY_FORM);
  const [formError, setFormError] = useState('');
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await listAppointments(recipientId);
      setItems(Array.isArray(data) ? data : []);
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
    if (!form.title.trim() || !form.scheduled_at) {
      setFormError('Title and date/time are required.');
      return;
    }
    setSaving(true);
    try {
      await createAppointment(recipientId, {
        title: form.title.trim(),
        scheduled_at: toIso(form.scheduled_at),
        location: form.location.trim() || null,
        notes: form.notes.trim() || null,
      });
      setForm(EMPTY_FORM);
      await load();
    } catch (err) {
      setFormError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleStatus(item, status) {
    setActionError('');
    try {
      await updateAppointment(recipientId, item.id, { status });
      await load();
    } catch (err) {
      setActionError(err.message);
    }
  }

  return (
    <div className="stack">
      <Card title="Appointments">
        {actionError && <ErrorBox message={actionError} />}
        {loading && <Loading />}
        {!loading && error && <ErrorBox message={error} onRetry={load} />}
        {!loading && !error && items.length === 0 && <Empty>No appointments yet.</Empty>}
        {!loading && !error && items.length > 0 && (
          <ul className="list">
            {items.map((a) => (
              <li key={a.id} className="list-item">
                <div>
                  <strong>{a.title}</strong>
                  <div className="muted small">
                    {fmtDateTime(a.scheduled_at)}
                    {a.location ? ` · ${a.location}` : ''}
                  </div>
                </div>
                <div className="row-gap">
                  {canWrite ? (
                    <select value={a.status} onChange={(e) => handleStatus(a, e.target.value)}>
                      {STATUSES.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  ) : (
                    <StatusBadge value={a.status} />
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {canWrite && (
        <Card title="Add an appointment">
          {formError && <div className="alert error">{formError}</div>}
          <form className="form" onSubmit={handleCreate}>
            <label className="field">
              <span>Title</span>
              <input value={form.title} onChange={set('title')} required />
            </label>
            <label className="field">
              <span>Date and time</span>
              <input type="datetime-local" value={form.scheduled_at} onChange={set('scheduled_at')} required />
            </label>
            <label className="field">
              <span>Location</span>
              <input value={form.location} onChange={set('location')} />
            </label>
            <label className="field wide">
              <span>Notes</span>
              <textarea value={form.notes} onChange={set('notes')} />
            </label>
            <div>
              <button className="btn" type="submit" disabled={saving}>
                {saving ? 'Saving…' : 'Add appointment'}
              </button>
            </div>
          </form>
        </Card>
      )}
    </div>
  );
}
