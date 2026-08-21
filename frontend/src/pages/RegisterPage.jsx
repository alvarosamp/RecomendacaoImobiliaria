import { useState, useContext } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { AuthContext } from '../contexts/AuthContext';

const PROFILES = [
  { id: 'investidor',    icon: '📈', label: 'Investidor' },
  { id: 'corretor',     icon: '🏠', label: 'Corretor' },
  { id: 'incorporadora', icon: '🏗️', label: 'Incorporadora' },
  { id: 'governo',      icon: '🏛️', label: 'Poder Público' },
]

export default function RegisterPage() {
  const [name, setName]         = useState('');
  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [profile, setProfile]   = useState('');
  const [error, setError]       = useState(null);
  const [loading, setLoading]   = useState(false);
  const { register } = useContext(AuthContext);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await register(name, email, password);
      navigate('/app');
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao criar conta. Tente novamente.');
    } finally {
      setLoading(false);
    }
  };

  const profileMessages = {
    investidor:    'Você verá rankings de oportunidades e análise de risco.',
    corretor:      'Você terá acesso a leads, avaliações e conceitos de imóveis.',
    incorporadora: 'Você explorará zonas com potencial construtivo e Plano Diretor.',
    governo:       'Você analisará carências de serviços e expansão urbana.',
  }

  return (
    <div className="auth-split">
      {/* Left */}
      <div className="auth-split-left">
        <div className="auth-split-left-bg" />
        <div className="auth-hex-grid" />

        <div className="auth-split-left-content">
          <div className="auth-brand-mark">
            <div className="auth-logo-badge">Ur</div>
            <span className="auth-brand-name-text">Urbia</span>
          </div>

          <h2 className="auth-split-tagline">
            Dados territoriais<br />
            para quem<br />
            <em>toma decisões reais.</em>
          </h2>

          <p className="auth-split-desc">
            Crie sua conta e escolha seu perfil de acesso. A plataforma vai
            organizar as informações do jeito certo para o seu uso.
          </p>

          <div className="auth-features-list">
            {[
              'Acesso completo ao mapa territorial',
              'Score por área com justificativa',
              'Análise de comércios e serviços',
              'Previsão de preços e leads',
            ].map(f => (
              <div key={f} className="auth-feature-item">
                <div className="auth-feature-dot" />
                {f}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right */}
      <div className="auth-split-right">
        <div className="auth-form-box">
          <h2>Criar conta</h2>
          <p className="auth-subtitle">Plataforma de Inteligência Territorial</p>

          {error && <div className="auth-error">{error}</div>}

          <form onSubmit={handleSubmit}>
            {/* Profile selector */}
            <div className="form-group">
              <label>Seu perfil</label>
              <div className="profile-grid">
                {PROFILES.map(p => (
                  <div
                    key={p.id}
                    className={`profile-card${profile === p.id ? ' selected' : ''}`}
                    onClick={() => setProfile(p.id)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={e => e.key === 'Enter' && setProfile(p.id)}
                  >
                    <div className="profile-card-icon">{p.icon}</div>
                    <div className="profile-card-label">{p.label}</div>
                  </div>
                ))}
              </div>
              {profile && (
                <p style={{ fontSize: 11.5, color: 'var(--muted)', marginTop: 8, lineHeight: 1.5 }}>
                  {profileMessages[profile]}
                </p>
              )}
            </div>

            <div className="form-group">
              <label>Nome completo</label>
              <input
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="João Silva"
                required
                autoComplete="name"
              />
            </div>

            <div className="form-group">
              <label>Email</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="seu@email.com"
                required
                autoComplete="email"
              />
            </div>

            <div className="form-group">
              <label>Senha</label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Mínimo 6 caracteres"
                required
                minLength={6}
                autoComplete="new-password"
              />
            </div>

            <button
              type="submit"
              className="auth-btn"
              disabled={loading}
              style={{ marginTop: 4 }}
            >
              {loading ? 'Criando conta…' : 'Solicitar acesso'}
            </button>
          </form>

          <div className="auth-form-divider" />

          <div className="auth-form-footer">
            Já tem uma conta? <Link to="/login">Fazer login</Link>
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
