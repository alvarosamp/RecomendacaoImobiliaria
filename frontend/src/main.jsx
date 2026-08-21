import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import App from './App'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import LandingPage from './pages/LandingPage'
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

function GuestOnly({ children }) {
  const { user, loading } = React.useContext(AuthContext);

  if (loading) {
    return (
      <div className="loading" style={{height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
        <div className="loading-spinner" />
        Carregando sessÃ£oâ€¦
      </div>
    );
  }

  if (user) {
    return <Navigate to="/app" replace />;
  }

  return children;
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<GuestOnly><LoginPage /></GuestOnly>} />
          <Route path="/register" element={<GuestOnly><RegisterPage /></GuestOnly>} />
          <Route 
            path="/app/*"
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
