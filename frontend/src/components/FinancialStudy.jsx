const FIELDS = [
  ['land_cost', 'Aquisição do terreno (R$)', 0, 'any'],
  ['construction_cost_m2', 'Construção por m² (R$)', 0.01, 'any'],
  ['other_costs', 'Outros custos fixos (R$)', 0, 'any'],
  ['contingency_pct', 'Contingência sobre construção (%)', 0, 'any', 100],
  ['saleable_area_m2', 'Área vendável (m²)', 0.01, 'any'],
  ['sale_price_m2', 'Preço de venda por m² (R$)', 0.01, 'any'],
  ['sales_expenses_pct', 'Despesas e tributos sobre vendas (%)', 0, 'any', 100],
  ['months', 'Prazo até a venda integral (meses)', 1, 1, 600],
  ['annual_discount_pct', 'Taxa anual de desconto (%)', 0, 'any', 100],
  ['cost_variation_pct', 'Sensibilidade do custo de construção (%)', 0, 'any', 100],
  ['price_variation_pct', 'Sensibilidade do preço de venda (%)', 0, 'any', 100],
]
const LABELS = Object.fromEntries(FIELDS.map(([key, label]) => [key, label]))
LABELS.reference_date = 'Data de referência'
LABELS.source_note = 'Origem das premissas'
const money = value => value == null ? 'Não calculável' : Number(value).toLocaleString('pt-BR', {style:'currency',currency:'BRL'})
const percent = value => value == null ? 'Não calculável' : `${Number(value).toLocaleString('pt-BR', {maximumFractionDigits:2})}%`

export function FinancialPremises({ value, onChange, disabled }) {
  const set = (key, next) => onChange({ ...value, [key]: next })
  return <fieldset className="study-fields" disabled={disabled}><legend>Estudo financeiro com premissas informadas</legend>
    <label className="financial-toggle"><input type="checkbox" checked={value != null} onChange={event => onChange(event.target.checked ? {} : null)} />Incluir análise financeira</label>
    {value != null && <><p className="study-notes">Preencha todos os campos para calcular. Informe zero quando não houver custo ou variação; campos vazios ficam pendentes. Inclua despesas e tributos estimados sem duplicar valores. Nenhum preço é preenchido automaticamente.</p>
      {FIELDS.map(([key, label, min, step, max]) => <label key={key}>{label}<input type="number" min={min} step={step} max={max} value={value[key] ?? ''} onChange={event => set(key, event.target.value === '' ? null : Number(event.target.value))} /></label>)}
      <label>Data de referência<input type="date" value={value.reference_date || ''} onChange={event => set('reference_date', event.target.value || null)} /></label>
      <label className="study-notes">Origem das premissas<textarea maxLength={4000} rows={3} value={value.source_note || ''} onChange={event => set('source_note', event.target.value)} placeholder="Descreva as cotações, comparáveis ou estimativas próprias usados, com suas limitações." /></label>
    </>}
  </fieldset>
}

export function FinancialResults({ result }) {
  if (!result || result.status === 'not_requested') return null
  return <section className="financial-results"><h3>Estudo financeiro informado</h3>
    {result.status === 'pending' ? <p>Premissas pendentes: {result.missing.map(key => LABELS[key] || key).join(', ')}. Preencha na etapa Premissas e recalcule.</p> : <>
      <p>Área construída informada: {result.build_area_m2} m² · área vendável: {result.assumptions.saleable_area_m2} m² · prazo: {result.assumptions.months} meses. Os cenários financeiros mantêm essas áreas; as tipologias heurísticas acima são outra comparação.</p>
      <p>Referência: {result.assumptions.reference_date} · Origem declarada: {result.assumptions.source_note}</p>
      <div className="workspace-grid">{result.scenarios.map(item => <article className="workspace-card" key={item.id}><h4>{item.label}</h4><dl>{[
        ['Custo total', money(item.total_cost)], ['Receita líquida de venda', money(item.net_revenue)],
        ['Lucro estimado', money(item.profit)], ['Valor presente líquido (VPL)', money(item.npv)], ['Margem sobre venda bruta', percent(item.margin_pct)],
        ['ROI do empreendimento', percent(item.roi_pct)], ['Preço de equilíbrio por m²', money(item.break_even_price_m2)],
        ['Déficit máximo do fluxo mensal', money(item.peak_monthly_deficit)],
      ].map(([label, text]) => <div key={label}><dt>{label}</dt><dd>{text}</dd></div>)}</dl></article>)}</div>
      <details><summary>Fluxo mensal do cenário base</summary><div className="comparison-table-wrap"><table className="comparison-table"><thead><tr><th>Mês</th><th>Custos</th><th>Receita líquida</th><th>Fluxo líquido</th><th>Saldo acumulado</th></tr></thead><tbody>{result.scenarios[0].cash_flow.map(item => <tr key={item.month}><td>{item.month}</td><td>{money(item.cost)}</td><td>{money(item.revenue)}</td><td>{money(item.net)}</td><td>{money(item.cumulative)}</td></tr>)}</tbody></table></div></details>
    </>}
    <details><summary>Hipóteses e limitações do cálculo</summary><ul>{result.limitations.map(item => <li key={item}>{item}</li>)}</ul></details>
  </section>
}
