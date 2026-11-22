import { useCallback, useEffect, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { addMember, listMembers, removeMember, updateMember } from '../api.js';
import { asList } from '../format.js';
import { Card, Empty, ErrorBox, Loading } from '../components/ui.jsx';

const ROLE_OPTIONS = ['coordinator', 'caregiver', 'viewer'];

export default function Team() {
  const { recipientId, role } = useOutletContext();
  const isCoordinator = role === 'coordinator';
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionError, setActionError] = useState('');
  const [email, setEmail] = useState('');
  const [newRole, setNewRole] = useState('caregiver');
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await listMembers(recipientId);
      setMembers(asList(data, 'items'));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [recipientId]);

  useEffect(() => {
    load();
  }, [load]);

  const membershipId = (m) => m.membership_id ?? m.id;

  async function handleAdd(e) {
    e.preventDefault();
    setActionError('');
    if (!email.trim()) {
      setActionError('Enter an email address.');
      return;
    }
    setSaving(true);
    try {
      await addMember(recipientId, { email: email.trim(), role: newRole });
      setEmail('');
      await load();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleRoleChange(m, nextRole) {
    setActionError('');
    try {
      await updateMember(recipientId, membershipId(m), { role: nextRole });
      await load();
    } catch (err) {
      setActionError(err.message);
    }
  }

  async function handleRemove(m) {
    if (!window.confirm(`Remove ${m.full_name ?? m.email} from this care circle?`)) return;
    setActionError('');
    try {
      await removeMember(recipientId, membershipId(m));
      await load();
    } catch (err) {
      setActionError(err.message);
    }
  }

  return (
    <div className="stack">
      <Card title="Care team">
        {actionError && <ErrorBox message={actionError} />}
        {loading && <Loading />}
        {!loading && error && <ErrorBox message={error} onRetry={load} />}
        {!loading && !error && members.length === 0 && <Empty>No members yet.</Empty>}
        {!loading && !error && members.length > 0 && (
          <ul className="list">
            {members.map((m) => (
              <li key={membershipId(m)} className="list-item">
                <div>
                  <strong>{m.full_name ?? m.user?.full_name ?? 'Member'}</strong>
                  <div className="muted small">{m.email ?? m.user?.email ?? ''}</div>
                </div>
                <div className="row-gap">
                  {isCoordinator ? (
                    <>
                      <select value={m.role} onChange={(e) => handleRoleChange(m, e.target.value)}>
                        {ROLE_OPTIONS.map((r) => (
                          <option key={r} value={r}>{r}</option>
                        ))}
                      </select>
                      <button className="btn btn-danger btn-small" onClick={() => handleRemove(m)}>
                        Remove
                      </button>
                    </>
                  ) : (
                    <span className="badge">{m.role}</span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {isCoordinator && (
        <Card title="Add a team member by email">
          <form className="form" onSubmit={handleAdd}>
            <label className="field">
              <span>Email</span>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </label>
            <label className="field">
              <span>Role</span>
              <select value={newRole} onChange={(e) => setNewRole(e.target.value)}>
                {ROLE_OPTIONS.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>
            </label>
            <div>
              <button className="btn" type="submit" disabled={saving}>
                {saving ? 'Adding…' : 'Add member'}
              </button>
            </div>
          </form>
        </Card>
      )}
    </div>
  );
}
