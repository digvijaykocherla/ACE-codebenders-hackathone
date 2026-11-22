import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { createRecipient, listRecipients } from '../api.js';
import { roleOf } from '../format.js';
import { Card, Empty, ErrorBox, Loading } from '../components/ui.jsx';

const EMPTY_FORM = { full_name: '', city: '', notes: '' };

export default function Recipients() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await listRecipients();
      setItems(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  async function handleCreate(e) {
    e.preventDefault();
    setFormError('');
    if (!form.full_name.trim()) {
      setFormError('Full name is required.');
      return;
    }
    setSaving(true);
    try {
      await createRecipient({
        full_name: form.full_name.trim(),
        city: form.city.trim() || null,
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

  let listBody;
  if (loading) listBody = <Loading />;
  else if (error) listBody = <ErrorBox message={error} onRetry={load} />;
  else if (items.length === 0) listBody = <Empty>No care recipients yet. Create one below.</Empty>;
  else
    listBody = (
      <ul className="list">
        {items.map((r) => (
          <li key={r.id} className="list-item">
            <div>
              <strong>{r.full_name}</strong>{' '}
              <span className="muted small">{r.city}</span>
            </div>
            <div className="row-gap">
              {roleOf(r) && <span className="badge">{roleOf(r)}</span>}
              <Link className="btn btn-small" to={`/r/${r.id}/dashboard`}>Open</Link>
            </div>
          </li>
        ))}
      </ul>
    );

  return (
    <div className="stack">
      <Card title="Care recipients">{listBody}</Card>

      <Card title="Add a care recipient">
        {formError && <div className="alert error">{formError}</div>}
        <form className="form" onSubmit={handleCreate}>
          <label className="field">
            <span>Full name</span>
            <input value={form.full_name} onChange={set('full_name')} required />
          </label>
          <label className="field">
            <span>City</span>
            <input value={form.city} onChange={set('city')} />
          </label>
          <label className="field wide">
            <span>Notes</span>
            <textarea value={form.notes} onChange={set('notes')} />
          </label>
          <div>
            <button className="btn" type="submit" disabled={saving}>
              {saving ? 'Saving…' : 'Create recipient'}
            </button>
          </div>
        </form>
      </Card>
    </div>
  );
}
