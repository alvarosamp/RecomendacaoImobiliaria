import { ProductIcon } from '../components/ProductVisuals';
import { useState, useContext } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { AuthContext } from '../contexts/AuthContext';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const { login } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email, password);
      navigate('/app');
    } catch {
      setError('Email ou senha inválidos. Verifique suas credenciais.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-split">
      {/* Left — branding */}
      <div className="auth-split-left">
        <div className="auth-split-left-bg" />
        <div className="auth-hex-grid" />

        <div className="auth-split-left-content">
          <div className="auth-brand-mark">
            <div className="auth-logo-badge"><ProductIcon name="building" size={25}/></div>
            <span className="auth-brand-name-text">urbia.</span>
          </div>

          <h2 className="auth-split-tagline">
            Desvende o lugar.<br />
            Encontre seu<br />
            <em>próximo passo.</em>
          </h2>

          <p className="auth-split-desc">
            Seis ambientes para organizar informações e avançar com mais clareza.
            Começando por Pouso Alegre, com a cobertura de cada fonte à vista.
          </p>

          <div className="auth-features-list">
            {[
              'Um ambiente para cada tipo de decisão',
              'Análises guiadas com pendências claras',
              'Casos salvos para retomar depois',
              'Relatórios para a próxima conversa',
            ].map(f => (
              <div key={f} className="auth-feature-item">
                <div className="auth-feature-dot" />
                {f}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right — form */}
      <div className="auth-split-right">
        <div className="auth-form-box">
          <h2>Bem-vindo de volta</h2>
          <p className="auth-subtitle">Acesse sua plataforma territorial</p>

          {error && <div className="auth-error">{error}</div>}

          <Link to="/recover">Preciso recuperar meu acesso</Link>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="login-email">Email</label>
              <input
                id="login-email"
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="seu@email.com"
                required
                autoComplete="email"
              />
            </div>
            <div className="form-group">
              <label htmlFor="login-password">Senha</label>
              <input
                id="login-password"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                autoComplete="current-password"
              />
            </div>

            <button
              type="submit"
              className="auth-btn"
              disabled={loading}
              style={{ marginTop: 8 }}
            >
              {loading ? (
                <>
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" style={{ animation: 'spin 0.75s linear infinite' }}>
                    <path d="M7 1a6 6 0 1 0 6 6"/>
                  </svg>
                  Entrando…
                </>
              ) : (
                <>
                  Acessar plataforma
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M3 7h8M7 3l4 4-4 4"/>
                  </svg>
                </>
              )}
            </button>
          </form>

          <div className="auth-form-divider" />

          <div className="auth-form-footer">
            Ainda não tem conta?{' '}
            <Link to="/register">Solicitar acesso</Link>
          </div>

          <div style={{ marginTop: 16, textAlign: 'center' }}>
            <Link to="/" style={{ fontSize: 12, color: 'var(--muted-light)', textDecoration: 'none' }}>
              ← Voltar para a página inicial
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
