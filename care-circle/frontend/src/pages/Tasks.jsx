import { useCallback, useEffect, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { completeTask, createTask, listMembers, listTasks, updateTask } from '../api.js';
import { asList, fmtDateTime, isDone, isOverdue, toIso } from '../format.js';
import { Card, Empty, ErrorBox, Loading } from '../components/ui.jsx';

const PRIORITIES = ['low', 'normal', 'high'];
const EMPTY_FORM = { title: '', assignee_id: '', due_at: '', reminder_at: '', priority: 'normal' };

export default function Tasks() {
  const { recipientId, canWrite } = useOutletContext();
  const [items, setItems] = useState([]);
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState('open');
  const [overdueOnly, setOverdueOnly] = useState(false);
  const [actionError, setActionError] = useState('');
  const [form, setForm] = useState(EMPTY_FORM);
  const [formError, setFormError] = useState('');
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [t, m] = await Promise.all([listTasks(recipientId), listMembers(recipientId)]);
      setItems(asList(t, 'items'));
      setMembers(asList(m, 'items'));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [recipientId]);

  useEffect(() => {
    load();
  }, [load]);

  const visible = items.filter((t) => {
    if (statusFilter === 'open' && isDone(t)) return false;
    if (statusFilter === 'done' && !isDone(t)) return false;
    if (overdueOnly && !isOverdue(t)) return false;
    return true;
  });

  const memberId = (m) => m.user_id ?? m.id;
  const memberName = (m) => m.full_name ?? m.user?.full_name ?? m.email ?? 'Member';
  const nameOf = (id) => {
    const m = members.find((x) => String(memberId(x)) === String(id));
    return m ? memberName(m) : 'Unassigned';
  };

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  async function handleComplete(task) {
    setActionError('');
    try {
      await completeTask(recipientId, task.id);
      await load();
    } catch (err) {
      setActionError(err.message);
    }
  }

  async function handleReopen(task) {
    setActionError('');
    try {
      await updateTask(recipientId, task.id, { status: 'open' });
      await load();
    } catch (err) {
      setActionError(err.message);
    }
  }

  async function handleCreate(e) {
    e.preventDefault();
    setFormError('');
    if (!form.title.trim()) {
      setFormError('Title is required.');
      return;
    }
    setSaving(true);
    try {
      await createTask(recipientId, {
        title: form.title.trim(),
        assignee_id: form.assignee_id ? Number(form.assignee_id) : null,
        due_at: toIso(form.due_at),
        reminder_at: toIso(form.reminder_at),
        priority: form.priority,
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
      <Card
        title="Tasks"
        action={
          <div className="row-gap">
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="open">Open</option>
              <option value="done">Done</option>
              <option value="all">All</option>
            </select>
            <label className="field checkbox">
              <input type="checkbox" checked={overdueOnly} onChange={(e) => setOverdueOnly(e.target.checked)} />
              <span>Overdue only</span>
            </label>
          </div>
        }
      >
        {actionError && <ErrorBox message={actionError} />}
        {loading && <Loading />}
        {!loading && error && <ErrorBox message={error} onRetry={load} />}
        {!loading && !error && visible.length === 0 && <Empty>No tasks match these filters.</Empty>}
        {!loading && !error && visible.length > 0 && (
          <ul className="list">
            {visible.map((t) => (
              <li key={t.id} className="list-item">
                <div>
                  <strong>{t.title}</strong>{' '}
                  <span className="badge">{t.priority ?? 'normal'}</span>
                  <div className="muted small">
                    Assignee: {nameOf(t.assignee_id)}
                    {t.due_at ? ` · Due ${fmtDateTime(t.due_at)}` : ''}
                    {t.reminder_at ? ` · Reminder ${fmtDateTime(t.reminder_at)}` : ''}
                  </div>
                </div>
                <div className="row-gap">
                  {isOverdue(t) && <span className="badge badge-danger">overdue</span>}
                  {isDone(t) && <span className="badge badge-ok">done</span>}
                  {canWrite && !isDone(t) && (
                    <button className="btn btn-small" onClick={() => handleComplete(t)}>Complete</button>
                  )}
                  {canWrite && isDone(t) && (
                    <button className="btn btn-outline btn-small" onClick={() => handleReopen(t)}>Reopen</button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {canWrite && (
        <Card title="Add a task">
          {formError && <div className="alert error">{formError}</div>}
          <form className="form" onSubmit={handleCreate}>
            <label className="field wide">
              <span>Title</span>
              <input value={form.title} onChange={set('title')} required />
            </label>
            <label className="field">
              <span>Assignee</span>
              <select value={form.assignee_id} onChange={set('assignee_id')}>
                <option value="">Unassigned</option>
                {members.map((m) => (
                  <option key={memberId(m)} value={memberId(m)}>{memberName(m)}</option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Priority</span>
              <select value={form.priority} onChange={set('priority')}>
                {PRIORITIES.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>Due</span>
              <input type="datetime-local" value={form.due_at} onChange={set('due_at')} />
            </label>
            <label className="field">
              <span>Reminder</span>
              <input type="datetime-local" value={form.reminder_at} onChange={set('reminder_at')} />
            </label>
            <div>
              <button className="btn" type="submit" disabled={saving}>
                {saving ? 'Saving…' : 'Add task'}
              </button>
            </div>
          </form>
        </Card>
      )}
    </div>
  );
}
