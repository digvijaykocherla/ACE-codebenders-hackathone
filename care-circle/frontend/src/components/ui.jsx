export function Card({ title, action, children }) {
  return (
    <section className="card">
      <header className="card-head">
        <h2>{title}</h2>
        {action}
      </header>
      {children}
    </section>
  );
}

export function Empty({ children }) {
  return <p className="empty">{children}</p>;
}

export function Loading({ text = 'Loading…' }) {
  return <p className="muted">{text}</p>;
}

export function ErrorBox({ message, onRetry }) {
  return (
    <div className="alert error">
      <span>{message}</span>
      {onRetry && (
        <button className="btn btn-outline btn-small" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  );
}

export function StatusBadge({ value }) {
  const cls =
    value === 'done' || value === 'completed' || value === 'scheduled'
      ? 'badge badge-ok'
      : value === 'cancelled'
        ? 'badge badge-muted'
        : 'badge';
  return <span className={cls}>{value ?? 'unknown'}</span>;
}
