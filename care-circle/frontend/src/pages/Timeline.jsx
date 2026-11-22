import { useCallback, useEffect, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { getTimeline } from '../api.js';
import { asList, fmtDateTime } from '../format.js';
import { Card, Empty, ErrorBox, Loading } from '../components/ui.jsx';

export default function Timeline() {
  const { recipientId } = useOutletContext();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getTimeline(recipientId);
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
    <Card title="Timeline">
      {loading && <Loading />}
      {!loading && error && <ErrorBox message={error} onRetry={load} />}
      {!loading && !error && items.length === 0 && <Empty>Nothing on the timeline yet.</Empty>}
      {!loading &&
        !error &&
        items.map((item, i) => (
          <div key={item.id ?? i} className="timeline-item">
            <span className="timeline-time">{fmtDateTime(item.occurred_at ?? item.at ?? item.created_at)}</span>
            <span className={`badge ${item.type === 'report' ? 'badge-ok' : ''}`}>{item.type ?? 'item'}</span>
            <div>
              <strong>{item.title ?? item.summary ?? item.description ?? 'Entry'}</strong>
              {item.detail && <div className="muted small">{item.detail}</div>}
            </div>
          </div>
        ))}
    </Card>
  );
}
