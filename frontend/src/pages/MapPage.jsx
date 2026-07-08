import { useEffect, useMemo, useState } from 'react'
import H3Map from '../components/H3Map'
import TimeSlider from '../components/TimeSlider'
import { fetchPoisGeojson, fetchZoningGeojson } from '../api'

const POI_FILTERS = [
  { id: 'pharmacy', label: 'Farmacias' },
  { id: 'supermarket', label: 'Mercados' },
  { id: 'school', label: 'Escolas' },
  { id: 'clinic', label: 'Clinicas' },
  { id: 'hospital', label: 'Hospitais' },
  { id: 'park', label: 'Parques' },
  { id: 'restaurant', label: 'Restaurantes' },
  { id: 'bus_stop', label: 'Onibus' },
]

export default function MapPage({ scores, timeDates, timeRecords, selectedDate, onDateChange }) {
  const [priorityFilter, setPriorityFilter] = useState('')
  const [riskFilter, setRiskFilter]         = useState('')
  const [mapMode, setMapMode]               = useState('score')
  const [zoning, setZoning]                 = useState(null)
  const [pois, setPois]                     = useState(null)
  const [visibleLayers, setVisibleLayers]   = useState({ cells: true, zoning: true, pois: true })
  const [poiTypes, setPoiTypes]             = useState(['pharmacy', 'supermarket', 'school', 'clinic', 'hospital'])
  const [influenceRadius, setInfluenceRadius] = useState(900)
  const [labelMode, setLabelMode]           = useState('smart')

  const filtered = scores.filter(r => {
    if (priorityFilter && r.priority !== priorityFilter) return false
    if (riskFilter     && r.risk_level !== riskFilter)  return false
    return true
  })

  const rankedZones = useMemo(() => {
    const groups = new Map()
    filtered.forEach(row => {
      const key = row.zona || 'Area sem zona'
      const current = groups.get(key) || { name: key, count: 0, total: 0, high: 0, growth: 0 }
      current.count += 1
      current.total += Math.max(row.score_residencial || 0, row.score_comercial || 0)
      current.high += row.priority === 'alta' ? 1 : 0
      current.growth += Number(row.growth_signal || row.ndbi_slope_180 || 0)
      groups.set(key, current)
    })
    return [...groups.values()]
      .map(item => ({
        ...item,
        avg: item.total / Math.max(item.count, 1),
        growthAvg: item.growth / Math.max(item.count, 1),
      }))
      .sort((a, b) => b.avg - a.avg)
      .slice(0, 5)
  }, [filtered])

  useEffect(() => {
    let active = true
    fetchZoningGeojson()
      .then(data => {
        if (active) setZoning(data)
      })
      .catch(() => {
        if (active) setZoning({ type: 'FeatureCollection', features: [] })
      })
    return () => { active = false }
  }, [])

  useEffect(() => {
    let active = true
    fetchPoisGeojson()
      .then(data => {
        if (active) setPois(data)
      })
      .catch(() => {
        if (active) setPois({ type: 'FeatureCollection', features: [] })
      })
    return () => { active = false }
  }, [])

  const toggleLayer = layer => {
    setVisibleLayers(current => ({ ...current, [layer]: !current[layer] }))
  }

  const togglePoiType = type => {
    setPoiTypes(current => (
      current.includes(type)
        ? current.filter(item => item !== type)
        : [...current, type]
    ))
  }

  return (
    <div className="map-page">
      <div className="map-topbar">
        <span className="map-topbar-title">Mapa de Oportunidades</span>
        <div className="map-mode-group">
          <button className={mapMode === 'score' ? 'active' : ''} onClick={() => setMapMode('score')}>Score</button>
          <button className={mapMode === 'zoning' ? 'active' : ''} onClick={() => setMapMode('zoning')}>Zoneamento</button>
          <button className={mapMode === 'growth' ? 'active' : ''} onClick={() => setMapMode('growth')}>Crescimento</button>
        </div>
        <div className="map-layer-toggles">
          <button className={visibleLayers.cells ? 'active' : ''} onClick={() => toggleLayer('cells')}>Celulas</button>
          <button className={visibleLayers.zoning ? 'active' : ''} onClick={() => toggleLayer('zoning')}>Zonas</button>
          <button className={visibleLayers.pois ? 'active' : ''} onClick={() => toggleLayer('pois')}>Pontos</button>
        </div>
        <select value={influenceRadius} onChange={e => setInfluenceRadius(Number(e.target.value))}>
          <option value={500}>Raio 500 m</option>
          <option value={900}>Raio 900 m</option>
          <option value={1500}>Raio 1,5 km</option>
          <option value={2500}>Raio 2,5 km</option>
        </select>
        <select value={labelMode} onChange={e => setLabelMode(e.target.value)}>
          <option value="smart">Nomes essenciais</option>
          <option value="all">Mais nomes</option>
          <option value="hidden">Sem nomes</option>
        </select>
        <select value={priorityFilter} onChange={e => setPriorityFilter(e.target.value)}>
          <option value="">Todas as prioridades</option>
          <option value="alta">Alta</option>
          <option value="media">Média</option>
          <option value="baixa">Baixa</option>
        </select>
        <select value={riskFilter} onChange={e => setRiskFilter(e.target.value)}>
          <option value="">Todos os riscos</option>
          <option value="baixo">Baixo</option>
          <option value="medio">Médio</option>
          <option value="alto">Alto</option>
        </select>
        <span className="count-tag">{filtered.length} áreas</span>
      </div>

      <div className="map-filter-strip">
        {POI_FILTERS.map(item => (
          <button
            key={item.id}
            className={poiTypes.includes(item.id) ? 'active' : ''}
            onClick={() => togglePoiType(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className="map-ranking-strip">
        {rankedZones.map((item, index) => (
          <div key={item.name} className="map-ranking-item">
            <span>#{index + 1} {item.name}</span>
            <strong>{item.avg.toFixed(0)}/100</strong>
            <small>{item.count} areas · {item.high} alta prioridade</small>
          </div>
        ))}
      </div>

      <div className="map-area">
        <H3Map
          data={filtered}
          timeData={timeRecords}
          selectedDate={selectedDate}
          zoning={zoning}
          pois={pois}
          visibleLayers={visibleLayers}
          poiTypes={poiTypes}
          mode={selectedDate ? 'growth' : mapMode}
          influenceRadius={influenceRadius}
          labelMode={labelMode}
        />
      </div>

      <TimeSlider
        dates={timeDates}
        selectedDate={selectedDate}
        onChange={onDateChange}
      />
    </div>
  )
}
