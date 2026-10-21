const SERVICES = { road_access: 'Acesso viário', water: 'Água', sewer: 'Esgoto', power: 'Energia', drainage: 'Drenagem' }
const REFERENCES = { registry_reference: 'Referência cadastral ou matrícula', topography_reference: 'Levantamento topográfico', geotechnical_reference: 'Investigação geotécnica' }
const STATUS = { unknown: 'Não informado', reported_available: 'Disponível segundo informação do responsável', reported_unavailable: 'Indisponível segundo informação do responsável', provided: 'Referência informada' }
const RESULT = { evidence_pending: 'Evidências pendentes', constraints_reported: 'Indisponibilidades declaradas', ready_for_review: 'Informações preenchidas para revisão profissional' }
export function TechnicalPremises({ value, onChange, disabled }) {
  const set = (key, next) => onChange({ ...value, [key]: next })
  return <fieldset className="study-fields" disabled={disabled}><legend>Evidências técnicas do terreno</legend><label className="financial-toggle"><input type="checkbox" checked={value != null} onChange={event => onChange(event.target.checked ? {} : null)} />Incluir diagnóstico técnico</label>
    {value != null && <><p className="study-notes">Registre levantamentos e condições informadas pelo responsável. A plataforma organiza as pendências, mas não autentica documentos ou confirma redes de infraestrutura.</p>
      {Object.entries(SERVICES).map(([key, label]) => <label key={key}>{label}<select aria-label={label} value={value[key] || 'unknown'} onChange={event => set(key, event.target.value)}>{Object.entries(STATUS).filter(([status]) => status !== 'provided').map(([status, text]) => <option key={status} value={status}>{text}</option>)}</select></label>)}
      <label>Declividade medida (%)<input type="number" min="0" max="1000" step="any" value={value.slope_pct ?? ''} onChange={event => set('slope_pct', event.target.value === '' ? null : Number(event.target.value))} /></label>
      {Object.entries(REFERENCES).map(([key, label]) => <label key={key}>{label}<input maxLength={2000} value={value[key] || ''} onChange={event => set(key, event.target.value)} placeholder="Identificação e origem do documento" /></label>)}
      <label>Data das evidências técnicas<input type="date" value={value.reference_date || ''} onChange={event => set('reference_date', event.target.value || null)} /></label>
      <label className="study-notes">Origem das informações técnicas<textarea rows={3} maxLength={4000} value={value.source_note || ''} onChange={event => set('source_note', event.target.value)} /></label>
    </>}
  </fieldset>
}
export function TechnicalResults({ result }) {
  if (!result || result.status === 'not_requested') return null
  return <section className="financial-results"><h3>Diagnóstico de evidências técnicas</h3><p><strong>{RESULT[result.status]}</strong>. Este estado não equivale à aprovação ou viabilidade do terreno.</p>
    {!!result.pending.length && <p>Falta obter: {result.pending.join(', ')}.</p>}{!!result.unavailable.length && <p>Indisponibilidades declaradas: {result.unavailable.join(', ')}.</p>}
    <ul>{result.alerts.map(item => <li key={item}>{item}</li>)}</ul>
    <div className="comparison-table-wrap"><table className="comparison-table"><thead><tr><th>Evidência</th><th>Registro</th></tr></thead><tbody>{result.checks.map(item => <tr key={item.key}><td>{item.label}</td><td>{STATUS[item.status]}{item.key === 'slope_pct' && result.assumptions.slope_pct != null ? ` · ${result.assumptions.slope_pct}%` : ''}</td></tr>)}</tbody></table></div>
    <details><summary>Fontes e limites da análise técnica</summary><p>Referência: {result.assumptions.reference_date || 'não informada'} · {result.assumptions.source_note || 'Origem pendente'}</p><ul>{Object.entries(REFERENCES).map(([key,label]) => <li key={key}>{label}: {result.assumptions[key] || 'Não informado'}</li>)}</ul><ul>{result.limitations.map(item => <li key={item}>{item}</li>)}</ul></details>
  </section>
}
