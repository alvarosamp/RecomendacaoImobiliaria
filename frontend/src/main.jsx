import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import App from './App'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import { AuthProvider, AuthContext } from './contexts/AuthContext'
import './index.css'

function AuthGuard({ children }) {
  const { user, loading } = React.useContext(AuthContext);
  
  if (loading) {
    return (
      <div className="loading" style={{height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <div className="loading-spinner" />
        Carregando sessão…
      </div>
    );
  }
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route 
            path="/*" 
            element={
              <AuthGuard>
                <App />
              </AuthGuard>
            } 
          />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
)
