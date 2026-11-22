import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import * as api from './api.js';

const AuthContext = createContext(null);
const TOKEN_KEY = 'cc_token';
const USER_KEY = 'cc_user';

function readUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || 'null');
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(readUser);

  const startSession = useCallback(async (res) => {
    const tok = res?.access_token ?? res?.token;
    if (!tok) throw new Error('Server did not return an access token.');
    localStorage.setItem(TOKEN_KEY, tok);
    setToken(tok);
    const u = res.user ?? (await api.me());
    localStorage.setItem(USER_KEY, JSON.stringify(u));
    setUser(u);
  }, []);

  const login = useCallback((email, password) => api.login(email, password).then(startSession), [startSession]);

  const register = useCallback(
    (full_name, email, password, city) =>
      api.register(full_name, email, password, city).then(startSession),
    [startSession]
  );

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ token, user, login, register, logout }),
    [token, user, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
