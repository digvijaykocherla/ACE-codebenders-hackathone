import { useCallback, useEffect, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { getActivity } from '../api.js';
import { asList, fmtDateTime } from '../format.js';
import { Card, Empty, ErrorBox, Loading } from '../components/ui.jsx';

export default function Activity() {
  const { recipientId } = useOutletContext();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getActivity(recipientId, 50);
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

  return (
    <Card title="Who did what">
      {loading && <Loading />}
      {!loading && error && <ErrorBox message={error} onRetry={load} />}
      {!loading && !error && items.length === 0 && <Empty>No activity recorded yet.</Empty>}
      {!loading && !error && items.length > 0 && (
        <ul className="list">
          {items.map((a, i) => (
            <li key={a.id ?? i} className="timeline-item">
              <span className="timeline-time">{fmtDateTime(a.created_at ?? a.at)}</span>
              <div>
                <strong>{a.actor_name ?? a.user?.full_name ?? 'Someone'}</strong>{' '}
                {a.summary ?? a.action}
                {a.entity_type && <span className="badge">{a.entity_type}</span>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
