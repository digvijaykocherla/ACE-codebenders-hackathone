import { useCallback, useEffect, useMemo, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { createPrescription, getRefills, listPrescriptions } from '../api.js';
import { asList, fmtDate } from '../format.js';
import { Card, Empty, ErrorBox, Loading } from '../components/ui.jsx';

const EMPTY_FORM = { medication: '', dosage: '', instructions: '', prescriber: '', refills_remaining: '0' };

export default function Prescriptions() {
  const { recipientId, canWrite } = useOutletContext();
  const [items, setItems] = useState([]);
  const [refills, setRefills] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [form, setForm] = useState(EMPTY_FORM);
  const [formError, setFormError] = useState('');
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [p, r] = await Promise.all([listPrescriptions(recipientId), getRefills(recipientId)]);
      setItems(asList(p, 'items'));
      setRefills(asList(r, 'items'));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [recipientId]);

  useEffect(() => {
    load();
  }, [load]);

  // Prescription ids flagged by the refills endpoint.
  const flagged = useMemo(
    () => new Set(refills.map((r) => r.prescription_id ?? r.id)),
    [refills]
  );

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  async function handleCreate(e) {
    e.preventDefault();
    setFormError('');
    if (!form.medication.trim()) {
      setFormError('Medication name is required.');
      return;
    }
    setSaving(true);
    try {
      const now = new Date();
      const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
      await createPrescription(recipientId, {
        medicine_name: form.medication.trim(),
        dosage_text: form.dosage.trim() || null,
        prescribed_by: form.prescriber.trim() || null,
        refills_remaining: Number(form.refills_remaining) || 0,
        start_date: today,
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
      <Card title="Prescriptions">
        {loading && <Loading />}
        {!loading && error && <ErrorBox message={error} onRetry={load} />}
        {!loading && !error && items.length === 0 && <Empty>No prescriptions recorded.</Empty>}
        {!loading && !error && items.length > 0 && (
          <ul className="list">
            {items.map((p) => (
              <li key={p.id} className="list-item">
                <div>
                  <strong>{p.medicine_name}</strong>
                  {p.dosage_text && <span className="muted"> · {p.dosage_text}</span>}
                  <div className="muted small">
                    Refills remaining: {p.refills_remaining ?? '—'}
                    {p.prescribed_by ? ` · ${p.prescribed_by}` : ''}
                  </div>
                </div>
                <div className="row-gap">
                  {flagged.has(p.id) && <span className="badge badge-warn">Refill due</span>}
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {!loading && !error && refills.length > 0 && (
        <Card title="Refills flagged">
          <ul className="list">
            {refills.map((r, i) => (
              <li key={r.id ?? i} className="small">
                {r.prescription.medicine_name ?? 'Prescription'} · due {fmtDate(r.refill_due_at ?? r.due_at)}
              </li>
            ))}
          </ul>
        </Card>
      )}

      {canWrite && (
        <Card title="Add a prescription">
          {formError && <div className="alert error">{formError}</div>}
          <form className="form" onSubmit={handleCreate}>
            <label className="field">
              <span>Medication</span>
              <input value={form.medication} onChange={set('medication')} required />
            </label>
            <label className="field">
              <span>Dosage</span>
              <input value={form.dosage} onChange={set('dosage')} />
            </label>
            <label className="field">
              <span>Prescriber</span>
              <input value={form.prescriber} onChange={set('prescriber')} />
            </label>
            <label className="field">
              <span>Refills remaining</span>
              <input type="number" min="0" value={form.refills_remaining} onChange={set('refills_remaining')} />
            </label>
            <label className="field wide">
              <span>Instructions (as written on the label)</span>
              <textarea value={form.instructions} onChange={set('instructions')} />
            </label>
            <div>
              <button className="btn" type="submit" disabled={saving}>
                {saving ? 'Saving…' : 'Add prescription'}
              </button>
            </div>
          </form>
        </Card>
      )}
    </div>
  );
}
