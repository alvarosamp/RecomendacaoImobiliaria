import { createContext, useState, useEffect } from 'react';
import { api } from '../api';

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      api.get('/auth/me')
        .then(res => {
          setUser(res);
          localStorage.setItem('user', JSON.stringify(res));
        })
        .catch(() => {
          localStorage.removeItem('token');
          localStorage.removeItem('user');
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email, password) => {
    const res = await api.post('/auth/login', { email, password });
    localStorage.setItem('token', res.access_token);
    const meRes = await api.get('/auth/me');
    setUser(meRes);
    localStorage.setItem('user', JSON.stringify(meRes));
  };

  const register = async (name, email, password, profile) => {
    await api.post('/auth/register', { name, email, password, profile });
    await login(email, password);
  };

  const updateProfile = async (profile) => {
    const updatedUser = await api.patch('/auth/me/profile', { profile });
    setUser(updatedUser);
    localStorage.setItem('user', JSON.stringify(updatedUser));
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, updateProfile, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
