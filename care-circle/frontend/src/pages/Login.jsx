import { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth.jsx';

export default function Login() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mode, setMode] = useState('login');
  const [form, setForm] = useState({ full_name: '', email: '', password: '', city: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      if (mode === 'login') {
        await login(form.email.trim(), form.password);
      } else {
        if (!form.full_name.trim()) throw new Error('Full name is required.');
        await register(form.full_name.trim(), form.email.trim(), form.password, form.city.trim());
      }
      navigate(location.state?.from || '/', { replace: true });
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="card auth-card">
        <h1>Care Circle</h1>
        <p className="muted">Coordinate care for an elderly family member across siblings and cities.</p>

        <div className="hint-box">
          <strong>Demo accounts (synthetic data)</strong>
          <ul>
            <li><code>priya@demo-family.com</code></li>
            <li><code>arjun@demo-family.com</code></li>
            <li><code>meera@demo-family.com</code></li>
          </ul>
          Password: <code>Demo@1234</code>
        </div>

        {error && <div className="alert error">{error}</div>}

        <form onSubmit={handleSubmit}>
          {mode === 'register' && (
            <>
              <label className="field">
                <span>Full name</span>
                <input value={form.full_name} onChange={set('full_name')} required />
              </label>
              <label className="field">
                <span>City</span>
                <input value={form.city} onChange={set('city')} />
              </label>
            </>
          )}
          <label className="field">
            <span>Email</span>
            <input type="email" value={form.email} onChange={set('email')} required />
          </label>
          <label className="field">
            <span>Password</span>
            <input type="password" value={form.password} onChange={set('password')} required />
          </label>
          <button className="btn" type="submit" disabled={busy}>
            {busy ? 'Please wait…' : mode === 'login' ? 'Log in' : 'Create account'}
          </button>
        </form>

        <div className="toggle-row">
          <span className="muted">{mode === 'login' ? 'New here?' : 'Already have an account?'}</span>
          <button
            type="button"
            className="btn btn-outline btn-small"
            onClick={() => {
              setError('');
              setMode(mode === 'login' ? 'register' : 'login');
            }}
          >
            {mode === 'login' ? 'Register' : 'Log in instead'}
          </button>
        </div>
      </div>
    </div>
  );
}
