const API_BASE = (import.meta.env.VITE_API_BASE || '/api').replace(/\/$/, '');
const TOKEN_KEY = 'cc_token';
const USER_KEY = 'cc_user';

function extractDetail(data, status) {
  const detail = data && typeof data === 'object' ? data.detail : null;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg || JSON.stringify(d)).join('; ');
  return `Request failed (HTTP ${status})`;
}

/**
 * Low-level fetch wrapper. `path` is relative to the API base, e.g. '/auth/login'.
 * Adds the bearer token, sends and parses JSON, and throws Error(detail) on failure.
 */
export async function request(path, options = {}) {
  const { method = 'GET', body } = options;
  const headers = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) headers.Authorization = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error('Cannot reach the server. Is the backend running on port 8000?');
  }

  const text = await res.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!res.ok) {
    const isAuthCall = path.startsWith('/auth/login') || path.startsWith('/auth/register');
    if (res.status === 401 && !isAuthCall) {
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(USER_KEY);
      if (window.location.pathname !== '/login') window.location.assign('/login');
    }
    throw new Error(extractDetail(data, res.status));
  }
  return data;
}

const get = (path) => request(path);
const post = (path, body) => request(path, { method: 'POST', body });
const patch = (path, body) => request(path, { method: 'PATCH', body });
const del = (path) => request(path, { method: 'DELETE' });

// Auth
export const login = (email, password) => post('/auth/login', { email, password });
export const register = (full_name, email, password, city) =>
  post('/auth/register', { full_name, email, password, city });
export const me = () => get('/auth/me');

// Care recipients
export const listRecipients = () => get('/care-recipients');
export const createRecipient = (data) => post('/care-recipients', data);
export const getDashboard = (rid) => get(`/care-recipients/${rid}/dashboard`);
export const getReminders = (rid) => get(`/care-recipients/${rid}/reminders`);
export const getTimeline = (rid) => get(`/care-recipients/${rid}/timeline`);

// Appointments
export const listAppointments = (rid) => get(`/care-recipients/${rid}/appointments`);
export const createAppointment = (rid, data) => post(`/care-recipients/${rid}/appointments`, data);
export const updateAppointment = (rid, itemId, data) =>
  patch(`/care-recipients/${rid}/appointments/${itemId}`, data);

// Prescriptions and refills
export const listPrescriptions = (rid) => get(`/care-recipients/${rid}/prescriptions`);
export const createPrescription = (rid, data) => post(`/care-recipients/${rid}/prescriptions`, data);
export const getRefills = (rid) => get(`/care-recipients/${rid}/prescriptions/refills`);

// Reports
export const listReports = (rid) => get(`/care-recipients/${rid}/reports`);
export const createReport = (rid, data) => post(`/care-recipients/${rid}/reports`, data);

// Tasks
export const listTasks = (rid) => get(`/care-recipients/${rid}/tasks`);
export const createTask = (rid, data) => post(`/care-recipients/${rid}/tasks`, data);
export const completeTask = (rid, itemId) => post(`/care-recipients/${rid}/tasks/${itemId}/complete`);
export const updateTask = (rid, itemId, data) => patch(`/care-recipients/${rid}/tasks/${itemId}`, data);

// Team membership
export const listMembers = (rid) => get(`/care-recipients/${rid}/members`);
export const addMember = (rid, data) => post(`/care-recipients/${rid}/members`, data);
export const updateMember = (rid, membershipId, data) =>
  patch(`/care-recipients/${rid}/members/${membershipId}`, data);
export const removeMember = (rid, membershipId) => del(`/care-recipients/${rid}/members/${membershipId}`);

// Activity feed
export const getActivity = (rid, limit = 50) => get(`/care-recipients/${rid}/activity?limit=${limit}`);
