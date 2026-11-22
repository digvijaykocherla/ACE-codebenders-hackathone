export const ROLES = ['coordinator', 'caregiver', 'viewer'];

export function fmtDate(value) {
  if (!value) return '—';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleDateString();
}

export function fmtDateTime(value) {
  if (!value) return '—';
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString();
}

/** Converts a <input type="datetime-local"> value to ISO, or null when empty. */
export function toIso(localValue) {
  if (!localValue) return null;
  const d = new Date(localValue);
  return Number.isNaN(d.getTime()) ? null : d.toISOString();
}

export function isDone(task) {
  return task.status === 'done' || task.status === 'completed' || Boolean(task.completed_at);
}

export function isOverdue(task) {
  return !isDone(task) && Boolean(task.due_at) && new Date(task.due_at) < new Date();
}

/** The current user's role on a recipient (from the membership). */
export function roleOf(recipient) {
  return recipient?.role ?? recipient?.my_role ?? recipient?.membership?.role ?? null;
}

/** Viewers are read only; any other membership role may write. */
export function canWrite(role) {
  return Boolean(role) && role !== 'viewer';
}

/** Accepts either a bare array or an object wrapping one under `key`. */
export function asList(value, key) {
  if (Array.isArray(value)) return value;
  if (value && Array.isArray(value[key])) return value[key];
  return [];
}
