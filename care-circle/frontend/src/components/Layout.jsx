import { Link, NavLink, Outlet, useNavigate, useParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useAuth } from '../auth.jsx';
import { listRecipients } from '../api.js';
import { canWrite, roleOf } from '../format.js';

const SECTIONS = [
  ['dashboard', 'Dashboard'],
  ['timeline', 'Timeline'],
  ['appointments', 'Appointments'],
  ['prescriptions', 'Prescriptions'],
  ['reports', 'Reports'],
  ['tasks', 'Tasks'],
  ['team', 'Team'],
  ['activity', 'Activity'],
];

export default function Layout() {
  const { recipientId } = useParams();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [state, setState] = useState({ loading: Boolean(recipientId), error: '', recipient: null, role: null });

  useEffect(() => {
    if (!recipientId) return undefined;
    let active = true;
    setState({ loading: true, error: '', recipient: null, role: null });
    listRecipients()
      .then((list) => {
        if (!active) return;
        const found = (Array.isArray(list) ? list : []).find((r) => String(r.id) === String(recipientId));
        if (!found) {
          setState({ loading: false, error: 'Care recipient not found or you do not have access.', recipient: null, role: null });
        } else {
          setState({ loading: false, error: '', recipient: found, role: roleOf(found) });
        }
      })
      .catch((err) => {
        if (active) setState({ loading: false, error: err.message, recipient: null, role: null });
      });
    return () => {
      active = false;
    };
  }, [recipientId]);

  const ctx = {
    recipientId,
    recipient: state.recipient,
    role: state.role,
    canWrite: canWrite(state.role),
  };

  function handleLogout() {
    logout();
    navigate('/login', { replace: true });
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <Link to="/" className="brand">Care Circle</Link>
        <div className="topbar-right">
          <span>{user?.full_name}</span>
          <button className="btn btn-ghost btn-small" onClick={handleLogout}>Log out</button>
        </div>
      </header>
      <div className="demo-banner">
        Demo data in this app is SYNTHETIC. Care Circle organises care logistics only and gives no medical advice.
      </div>
      <div className="body-row">
        {recipientId && (
          <nav className="sidenav">
            <Link to="/">← All recipients</Link>
            {SECTIONS.map(([path, label]) => (
              <NavLink
                key={path}
                to={`/r/${recipientId}/${path}`}
                className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
              >
                {label}
              </NavLink>
            ))}
          </nav>
        )}
        <main className="content">
          {recipientId && state.loading && <p className="muted">Loading care recipient…</p>}
          {recipientId && state.error && <div className="alert error">{state.error}</div>}
          {recipientId && state.recipient && (
            <div className="recipient-heading">
              <h1>{state.recipient.full_name}</h1>
              <span className="badge">Your role: {state.role ?? 'unknown'}</span>
              {!ctx.canWrite && <span className="badge badge-muted">Read only</span>}
            </div>
          )}
          {(!recipientId || state.recipient) && <Outlet context={ctx} />}
        </main>
      </div>
    </div>
  );
}
