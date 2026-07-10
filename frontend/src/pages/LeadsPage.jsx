import { useEffect, useMemo, useState } from 'react'
import { createLead, fetchLeads, updateLeadStatus } from '../api'

const INITIAL = {
  name: '',
  email: '',
  phone: '',
  budget: '',
  zone: '',
  property_type: 'casa',
  financing_status: 'nao_iniciado',
  timeline: 'pesquisando',
  visits_done: 0,
  motivation: 'primeira_moradia',
  returning_client: false,
}

const LABEL_CONFIG = {
  'Alta chance': { bg: '#DCFCE7', text: '#15803D' },
  'Media chance': { bg: '#FEF3C7', text: '#92400E' },
  'Baixa chance': { bg: '#FEE2E2', text: '#B91C1C' },
}

const STATUS_LABELS = {
  novo: 'Novo',
  contatado: 'Contatado',
  convertido: 'Convertido',
  perdido: 'Perdido',
}

function money(value) {
  if (!value) return '—'
  return Number(value).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })
}

function LeadCard({ lead, onStatusChange }) {
  const cfg = LABEL_CONFIG[lead.label] || LABEL_CONFIG['Baixa chance']
  return (
    <div className="opp-card">
      <div className="opp-card-header">
        <div>
          <div className="opp-zona">{lead.name}</div>
          <div className="opp-cell-id">{lead.email || lead.phone || 'Sem contato informado'}</div>
        </div>
        <div className="opp-badges">
          <span className="badge" style={{ background: cfg.bg, color: cfg.text }}>{lead.label}</span>
          <span style={{ fontSize: 11, color: '#A8A29E', fontWeight: 700 }}>{lead.score.toFixed(0)}/100</span>
        </div>
      </div>

      <div className="score-bars">
        <div className="score-row">
          <span className="score-row-label">Orcamento</span>
          <span style={{ fontWeight: 700, color: 'var(--navy)' }}>{money(lead.budget)}</span>
        </div>
        {lead.zone && (
          <div className="score-row">
            <span className="score-row-label">Bairro</span>
            <span>{lead.zone}</span>
          </div>
        )}
      </div>

      {lead.explain?.length > 0 && (
        <div className="explain-list">
          {lead.explain.map(item => (
            <div key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
            </div>
          ))}
        </div>
      )}

      <div style={{ marginTop: 2 }}>
        <select
          className="lead-status-select"
          value={lead.status}
          onChange={e => onStatusChange(lead.id, e.target.value)}
        >
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </div>
    </div>
  )
}

export default function LeadsPage() {
  const [leads, setLeads] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [form, setForm] = useState(INITIAL)
  const [submitting, setSubmitting] = useState(false)
  const [lastResult, setLastResult] = useState(null)
  const [statusFilter, setStatusFilter] = useState('')
  const [labelFilter, setLabelFilter] = useState('')

  const set = (key, value) => setForm(current => ({ ...current, [key]: value }))

  const load = () => {
    setLoading(true)
    fetchLeads({ status: statusFilter, label: labelFilter })
      .then(setLeads)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [statusFilter, labelFilter])

  const submit = async e => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const payload = { ...form, budget: form.budget ? Number(form.budget) : null, visits_done: Number(form.visits_done) }
      const created = await createLead(payload)
      setLastResult(created)
      setLeads(current => [created, ...current])
      setForm(INITIAL)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleStatusChange = async (id, status) => {
    const updated = await updateLeadStatus(id, status)
    setLeads(current => current.map(lead => (lead.id === id ? updated : lead)))
  }

  const kpis = useMemo(() => {
    const total = leads.length
    const alta = leads.filter(l => l.label === 'Alta chance').length
    const convertidos = leads.filter(l => l.status === 'convertido').length
    const taxa = total ? (convertidos / total) * 100 : 0
    return { total, alta, convertidos, taxa }
  }, [leads])

  const resultCfg = lastResult ? (LABEL_CONFIG[lastResult.label] || LABEL_CONFIG['Baixa chance']) : null

  return (
    <div className="page">
      <div className="page-header">
        <h2>Lead Scoring</h2>
        <p>Qualificação BANT de clientes — quem tem mais chance de fechar negócio agora.</p>
      </div>

      <div className="kpi-strip">
        <div className="kpi-card navy">
          <span className="kpi-value">{kpis.total}</span>
          <span className="kpi-label">Leads cadastrados</span>
        </div>
        <div className="kpi-card green">
          <span className="kpi-value">{kpis.alta}</span>
          <span className="kpi-label">Alta chance</span>
        </div>
        <div className="kpi-card gold">
          <span className="kpi-value">{kpis.convertidos}</span>
          <span className="kpi-label">Convertidos</span>
        </div>
        <div className="kpi-card red">
          <span className="kpi-value">{kpis.taxa.toFixed(0)}%</span>
          <span className="kpi-label">Taxa de conversão</span>
        </div>
      </div>

      <div className="valuation-wrapper">
        <div className="valuation-card">
          <h3>Novo Lead</h3>
          <form onSubmit={submit}>
            <div className="field-group">
              <div className="field-row">
                <div className="field">
                  <label>Nome</label>
                  <input type="text" required value={form.name} onChange={e => set('name', e.target.value)} />
                </div>
                <div className="field">
                  <label>Telefone</label>
                  <input type="text" value={form.phone} onChange={e => set('phone', e.target.value)} />
                </div>
              </div>

              <div className="field">
                <label>Email</label>
                <input type="email" value={form.email} onChange={e => set('email', e.target.value)} />
              </div>

              <div className="field-row">
                <div className="field">
                  <label>Orçamento (R$)</label>
                  <input type="number" min={0} value={form.budget} onChange={e => set('budget', e.target.value)} />
                </div>
                <div className="field">
                  <label>Bairro desejado</label>
                  <input type="text" value={form.zone} onChange={e => set('zone', e.target.value)} />
                </div>
              </div>

              <div className="field">
                <label>Tipo de imóvel</label>
                <div className="type-picker">
                  {['casa', 'apartamento', 'comercial', 'terreno'].map(t => (
                    <button
                      key={t}
                      type="button"
                      className={form.property_type === t ? 'active' : ''}
                      onClick={() => set('property_type', t)}
                    >
                      {t.charAt(0).toUpperCase() + t.slice(1)}
                    </button>
                  ))}
                </div>
              </div>

              <div className="field-row">
                <div className="field">
                  <label>Financiamento</label>
                  <select value={form.financing_status} onChange={e => set('financing_status', e.target.value)}>
                    <option value="nao_iniciado">Nao iniciado</option>
                    <option value="em_analise">Em análise</option>
                    <option value="aprovado">Aprovado</option>
                    <option value="a_vista">Compra à vista</option>
                  </select>
                </div>
                <div className="field">
                  <label>Prazo desejado</label>
                  <select value={form.timeline} onChange={e => set('timeline', e.target.value)}>
                    <option value="pesquisando">Sem prazo (pesquisando)</option>
                    <option value="3_6_meses">3 a 6 meses</option>
                    <option value="1_3_meses">1 a 3 meses</option>
                    <option value="imediato">Imediato (&lt;1 mês)</option>
                  </select>
                </div>
              </div>

              <div className="field-row">
                <div className="field">
                  <label>Visitas já realizadas</label>
                  <input type="number" min={0} max={20} value={form.visits_done} onChange={e => set('visits_done', e.target.value)} />
                </div>
                <div className="field">
                  <label>Motivação</label>
                  <select value={form.motivation} onChange={e => set('motivation', e.target.value)}>
                    <option value="apenas_pesquisando">Apenas pesquisando</option>
                    <option value="investimento">Investimento</option>
                    <option value="primeira_moradia">Primeira moradia</option>
                    <option value="mudanca_urgente">Mudança urgente</option>
                  </select>
                </div>
              </div>

              <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-2)' }}>
                <input
                  type="checkbox"
                  checked={form.returning_client}
                  onChange={e => set('returning_client', e.target.checked)}
                />
                Cliente recorrente ou indicado
              </label>
            </div>

            <button type="submit" className="submit-btn" disabled={submitting}>
              {submitting ? '⟳ Calculando…' : 'Cadastrar e pontuar lead'}
            </button>
            {error && <p className="error">{error}</p>}
          </form>
        </div>

        <div className="valuation-card">
          <h3>Resultado da Qualificação</h3>
          <div className="result-card">
            {!lastResult && (
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 40, marginBottom: 16 }}>🎯</div>
                <p className="result-empty">
                  Cadastre um lead ao lado para ver a chance de fechamento e os fatores que pesaram no score.
                </p>
              </div>
            )}
            {lastResult && (
              <>
                <div className="result-eyebrow">{lastResult.name}</div>
                <div className="result-price" style={{ color: resultCfg.text }}>{lastResult.score.toFixed(0)}/100</div>
                <div className="result-gold-line" />
                <span className="badge" style={{ background: resultCfg.bg, color: resultCfg.text }}>{lastResult.label}</span>
                {lastResult.explain?.length > 0 && (
                  <div className="explain-list" style={{ marginTop: 16 }}>
                    {lastResult.explain.map(item => (
                      <div key={item.label}>
                        <span>{item.label}</span>
                        <strong>{item.value}</strong>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      <div className="filters-bar">
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          <option value="">Todos os status</option>
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
        <select value={labelFilter} onChange={e => setLabelFilter(e.target.value)}>
          <option value="">Todas as chances</option>
          <option value="Alta chance">Alta chance</option>
          <option value="Media chance">Média chance</option>
          <option value="Baixa chance">Baixa chance</option>
        </select>
        <span className="count-tag">{leads.length} leads</span>
      </div>

      {loading
        ? <div style={{ textAlign: 'center', padding: '60px 20px', color: '#78716C' }}>Carregando…</div>
        : leads.length === 0
          ? (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: '#78716C' }}>
              <div style={{ fontSize: 32, marginBottom: 12 }}>🎯</div>
              <div style={{ fontSize: 15, fontWeight: 600 }}>Nenhum lead cadastrado ainda</div>
              <div style={{ fontSize: 13, marginTop: 6 }}>Use o formulário acima para cadastrar o primeiro.</div>
            </div>
          )
          : (
            <div className="card-grid">
              {leads.map(lead => <LeadCard key={lead.id} lead={lead} onStatusChange={handleStatusChange} />)}
            </div>
          )
      }
    </div>
  )
}
