import { useCallback, useEffect, useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import { getDashboard, getReminders } from '../api.js';
import { asList, fmtDate, fmtDateTime } from '../format.js';
import { Card, Empty, ErrorBox, Loading, StatusBadge } from '../components/ui.jsx';

export default function Dashboard() {
  const { recipientId } = useOutletContext();
  const [dash, setDash] = useState(null);
  const [reminders, setReminders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [d, r] = await Promise.all([getDashboard(recipientId), getReminders(recipientId)]);
      setDash(d || {});
      setReminders(asList(r, 'items'));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [recipientId]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <Loading text="Loading dashboard…" />;
  if (error) return <ErrorBox message={error} onRetry={load} />;

  const nextAppts = asList(dash.next_appointments, 'items').slice(0, 3);
  const refills = asList(dash.refills_due, 'items');
  const overdue = asList(dash.overdue_tasks, 'items');
  const pending = dash.pending_count ?? 0;
  const recent = asList(dash.recent_activity, 'items').slice(0, 5);
  const byAssignee = Array.isArray(dash.open_tasks_by_assignee)
    ? dash.open_tasks_by_assignee.map((o) => ({ name: o.assignee_name ?? o.name ?? 'Unassigned', count: o.count ?? o.open ?? 0 }))
    : Object.entries(dash.open_tasks_by_assignee || {}).map(([name, count]) => ({ name, count }));

  return (
    <div className="stack">
      <div className="grid-2">
        <Card title="Pending tasks">
          <p style={{ fontSize: '2rem', margin: 0 }}>{pending}</p>
          <Link to={`/r/${recipientId}/tasks`}>View tasks</Link>
        </Card>

        <Card title="Next 3 appointments">
          {nextAppts.length === 0 ? (
            <Empty>No upcoming appointments.</Empty>
          ) : (
            <ul className="list">
              {nextAppts.map((a) => (
                <li key={a.id} className="list-item">
                  <div>
                    <strong>{a.title}</strong>
                    <div className="muted small">{fmtDateTime(a.scheduled_at)}</div>
                  </div>
                  <StatusBadge value={a.status} />
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Refills due within 14 days">
          {refills.length === 0 ? (
            <Empty>No refills due soon.</Empty>
          ) : (
            <ul className="list">
              {refills.map((p, i) => (
                <li key={p.id ?? i} className="list-item">
                  <div>
                    <strong>{p.medication ?? p.name ?? 'Prescription'}</strong>
                    <div className="muted small">Refills remaining: {p.refills_remaining ?? '—'}</div>
                  </div>
                  <span className="badge badge-warn">{fmtDate(p.refill_due_at ?? p.due_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Overdue tasks">
          {overdue.length === 0 ? (
            <Empty>Nothing overdue.</Empty>
          ) : (
            <ul className="list">
              {overdue.map((t) => (
                <li key={t.id} className="list-item">
                  <div>
                    <strong>{t.title}</strong>
                    <div className="muted small">Due {fmtDateTime(t.due_at)}</div>
                  </div>
                  <span className="badge badge-danger">overdue</span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Open tasks per assignee">
          {byAssignee.length === 0 ? (
            <Empty>No open tasks.</Empty>
          ) : (
            <ul className="list">
              {byAssignee.map((o) => (
                <li key={o.name} className="list-item">
                  <span>{o.name}</span>
                  <span className="badge">{o.count}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Recent activity">
          {recent.length === 0 ? (
            <Empty>No activity yet.</Empty>
          ) : (
            <ul className="list">
              {recent.map((a, i) => (
                <li key={a.id ?? i} className="small">
                  <strong>{a.actor_name ?? 'Someone'}</strong> {a.summary ?? a.action}{' '}
                  <span className="muted">· {fmtDateTime(a.created_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <Card title="Reminders (next 48 hours)">
        {reminders.length === 0 ? (
          <Empty>No reminders in the next 48 hours.</Empty>
        ) : (
          <ul className="list">
            {reminders.map((r, i) => (
              <li key={r.id ?? i} className="list-item">
                <div>
                  <strong>{r.title ?? r.message ?? 'Reminder'}</strong>
                  <div className="muted small">{fmtDateTime(r.due_at ?? r.scheduled_at ?? r.reminder_at)}</div>
                </div>
                {r.kind && <span className="badge">{r.kind}</span>}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
