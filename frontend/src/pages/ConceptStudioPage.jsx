import { useEffect, useMemo, useState } from 'react'
import { analyzeConcept, downloadConceptReport, generateConceptImage } from '../api'

const INITIAL = {
  lotArea: 300,
  frontage: 10,
  buildArea: 165,
  floors: 2,
  typology: 'casa',
  finish: 'medio',
  style: 'contemporaneo',
  zone: '',
  residentialScore: 65,
  commercialScore: 48,
  riskLevel: 'medio',
  growthSignal: 0.0015,
}

function money(value) {
  return Number(value || 0).toLocaleString('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 0,
  })
}

function number(value, digits = 0) {
  return Number(value || 0).toLocaleString('pt-BR', { maximumFractionDigits: digits })
}

export default function ConceptStudioPage() {
  const [form, setForm] = useState(INITIAL)
  const [analysis, setAnalysis] = useState(null)
  const [selectedView, setSelectedView] = useState('exterior')
  const [images, setImages] = useState({ exterior: null, interior: null })
  const [imageStatus, setImageStatus] = useState(null)
  const [loadingImage, setLoadingImage] = useState(false)
  const [reporting, setReporting] = useState(false)
  const set = (key, value) => setForm(current => ({ ...current, [key]: value }))

  useEffect(() => {
    let active = true
    analyzeConcept(form)
      .then(data => { if (active) setAnalysis(data) })
      .catch(() => { if (active) setAnalysis(null) })
    return () => { active = false }
  }, [form])

  const plan = analysis?.plan
  const scenarios = analysis?.scenarios || []
  const bestScenario = useMemo(() => (
    [...scenarios].sort((a, b) => b.viabilityScore - a.viabilityScore)[0]
  ), [scenarios])

  const generate = async variation => {
    setLoadingImage(true)
    setImageStatus(null)
    try {
      const res = await generateConceptImage({ ...form, view: selectedView, variation })
      setImageStatus(res)
      if (res.image) setImages(current => ({ ...current, [selectedView]: res.image }))
    } catch (err) {
      setImageStatus({ status: 'error', message: err.message })
    } finally {
      setLoadingImage(false)
    }
  }

  const exportReport = async () => {
    setReporting(true)
    try {
      const blob = await downloadConceptReport({
        ...form,
        exteriorImage: images.exterior,
        interiorImage: images.interior,
      })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'relatorio-oportunidade.pdf'
      link.click()
      URL.revokeObjectURL(url)
    } finally {
      setReporting(false)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h2>Conceito e Obra</h2>
        <p>Comparador de cenarios, viabilidade construtiva, imagens exterior/interior via Hugging Face e relatorio PDF.</p>
      </div>

      <div className="concept-layout">
        <section className="valuation-card concept-card">
          <h3>Dados do Terreno</h3>
          <div className="field-group">
            <div className="field-row">
              <Field label="Area do terreno (m2)" value={form.lotArea} min={60} max={10000} onChange={v => set('lotArea', v)} />
              <Field label="Frente (m)" value={form.frontage} min={4} max={80} onChange={v => set('frontage', v)} />
            </div>
            <div className="field-row">
              <Field label="Area construida (m2)" value={form.buildArea} min={30} max={5000} onChange={v => set('buildArea', v)} />
              <Field label="Pavimentos" value={form.floors} min={1} max={20} onChange={v => set('floors', v)} />
            </div>
            <div className="field-row">
              <Select label="Tipologia" value={form.typology} onChange={v => set('typology', v)} options={[
                ['casa', 'Casa'],
                ['predio residencial', 'Predio residencial'],
                ['uso misto', 'Uso misto'],
                ['loja comercial', 'Loja comercial'],
              ]} />
              <Select label="Padrao" value={form.finish} onChange={v => set('finish', v)} options={[
                ['economico', 'Economico'],
                ['medio', 'Medio'],
                ['alto', 'Alto padrao'],
              ]} />
            </div>
            <div className="field-row">
              <Select label="Estilo visual" value={form.style} onChange={v => set('style', v)} options={[
                ['contemporaneo', 'Contemporaneo'],
                ['minimalista', 'Minimalista'],
                ['industrial', 'Industrial'],
                ['brasileiro tropical', 'Brasileiro tropical'],
              ]} />
              <Select label="Risco" value={form.riskLevel} onChange={v => set('riskLevel', v)} options={[
                ['baixo', 'Baixo'],
                ['medio', 'Medio'],
                ['alto', 'Alto'],
              ]} />
            </div>
            <div className="field">
              <label>Zona / bairro analisado</label>
              <input value={form.zone} placeholder="Ex.: ZM, ZC, bairro Centro..." onChange={e => set('zone', e.target.value)} />
            </div>
            <div className="field-row">
              <Field label="Score residencial" value={form.residentialScore} min={0} max={100} onChange={v => set('residentialScore', v)} />
              <Field label="Score comercial" value={form.commercialScore} min={0} max={100} onChange={v => set('commercialScore', v)} />
            </div>
          </div>
        </section>

        <section className="valuation-card concept-card">
          <h3>Viabilidade Construtiva</h3>
          {plan && (
            <>
              <div className="viability-meter">
                <div style={{ width: `${plan.viabilityScore}%` }} />
                <strong>{plan.viabilityScore}/100</strong>
              </div>
              <div className="concept-kpis">
                <div><span>Custo total</span><strong>{money(plan.total)}</strong></div>
                <div><span>Custo por m2</span><strong>{money(plan.costPerM2)}</strong></div>
                <div><span>Prazo</span><strong>{plan.months} meses</strong></div>
                <div><span>Payback</span><strong>{plan.paybackYears} anos</strong></div>
              </div>
              <div className="cost-breakdown">
                <Metric label="Valor potencial de venda" value={money(plan.saleValue)} />
                <Metric label="Aluguel potencial mensal" value={money(plan.monthlyRent)} />
                <Metric label="Ocupacao estimada" value={`${number(plan.occupancy, 1)}%`} />
              </div>
            </>
          )}
        </section>

        <section className="valuation-card concept-card concept-span">
          <h3>Comparador de Cenarios</h3>
          <div className="scenario-grid">
            {scenarios.map(item => (
              <div key={item.id} className={bestScenario?.id === item.id ? 'scenario-card active' : 'scenario-card'}>
                <span>{item.label}</span>
                <strong>{item.viabilityScore}/100</strong>
                <Metric label="Area" value={`${item.buildArea} m2`} />
                <Metric label="Custo" value={money(item.cost)} />
                <Metric label="Prazo" value={`${item.months} meses`} />
                <Metric label="ROI anual" value={`${item.roiYear}%`} />
              </div>
            ))}
          </div>
        </section>

        <section className="valuation-card concept-card">
          <h3>Visualizacao da Casa</h3>
          <div className="view-tabs">
            <button className={selectedView === 'exterior' ? 'active' : ''} onClick={() => setSelectedView('exterior')}>Exterior</button>
            <button className={selectedView === 'interior' ? 'active' : ''} onClick={() => setSelectedView('interior')}>Interior</button>
          </div>
          <div className="concept-preview">
            {images[selectedView]
              ? <img src={images[selectedView]} alt={`Imagem ${selectedView} gerada por IA`} />
              : <HouseSketch view={selectedView} floors={form.floors} />}
          </div>
          <div className="concept-actions">
            <button onClick={() => generate(false)} disabled={loadingImage}>
              {loadingImage ? 'Gerando...' : images[selectedView] ? 'Usar cache' : 'Gerar imagem'}
            </button>
            <button onClick={() => generate(true)} disabled={loadingImage}>
              Gerar variacao
            </button>
          </div>
          {imageStatus && (
            <p className="concept-note">
              {imageStatus.message || `Status: ${imageStatus.status}. Restantes hoje: ${imageStatus.remainingToday}`}
            </p>
          )}
        </section>

        <section className="valuation-card concept-card">
          <h3>Relatorio e Prompt</h3>
          <div className="prompt-box">
            <span>Prompt exterior</span>
            <p>{plan?.promptExterior}</p>
          </div>
          <div className="prompt-box">
            <span>Prompt interior</span>
            <p>{plan?.promptInterior}</p>
          </div>
          <button className="submit-btn" onClick={exportReport} disabled={reporting}>
            {reporting ? 'Gerando PDF...' : 'Exportar PDF da oportunidade'}
          </button>
        </section>
      </div>
    </div>
  )
}

function Field({ label, value, min, max, onChange }) {
  return (
    <div className="field">
      <label>{label}</label>
      <input type="number" value={value} min={min} max={max} onChange={e => onChange(+e.target.value)} />
    </div>
  )
}

function Select({ label, value, options, onChange }) {
  return (
    <div className="field">
      <label>{label}</label>
      <select value={value} onChange={e => onChange(e.target.value)}>
        {options.map(([id, labelText]) => <option key={id} value={id}>{labelText}</option>)}
      </select>
    </div>
  )
}

function Metric({ label, value }) {
  return (
    <div className="atlas-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function HouseSketch({ view, floors }) {
  if (view === 'interior') {
    return (
      <div className="floorplan-sketch">
        <div className="room living">Sala</div>
        <div className="room kitchen">Cozinha</div>
        <div className="room suite">Suite</div>
        <div className="room bath">Banho</div>
        <div className="room bedroom">Quarto</div>
      </div>
    )
  }
  return (
    <div className="house-sketch">
      <div className="house-sky" />
      <div className="house-building" style={{ height: `${Math.min(78, 34 + floors * 12)}%` }}>
        <div className="house-roof" />
        <div className="house-window" />
        <div className="house-window right" />
        <div className="house-door" />
      </div>
      <div className="house-ground" />
    </div>
  )
}
