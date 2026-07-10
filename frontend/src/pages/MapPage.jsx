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

export default function MapPage({ scores, timeDates, timeRecords, selectedDate, onDateChange, onOpenConcept }) {
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
      const current = groups.get(key) || { name: key, count: 0, total: 0, high: 0, growth: 0, lowRisk: 0, gap: 0, zoning: 0 }
      current.count += 1
      current.total += Math.max(row.score_residencial || 0, row.score_comercial || 0)
      current.high += row.priority === 'alta' ? 1 : 0
      current.growth += Number(row.growth_signal || row.ndbi_slope_180 || 0)
      current.lowRisk += row.risk_level === 'baixo' ? 1 : 0
      current.gap += Number(row.commercial_gap || 0)
      current.zoning += /ZC|ZM|ZMU|ZMC/i.test(row.zona || '') ? 1 : 0
      groups.set(key, current)
    })
    return [...groups.values()]
      .map(item => {
        const count = Math.max(item.count, 1)
        const avg = item.total / count
        const growthNorm = Math.min(1, Math.max(0, (item.growth / count) * 180))
        const index = (
          avg * 0.42
          + Math.min(100, item.count * 8) * 0.16
          + growthNorm * 100 * 0.13
          + (item.lowRisk / count) * 100 * 0.12
          + (item.gap / count) * 100 * 0.1
          + (item.zoning / count) * 100 * 0.07
        )
        return { ...item, avg, index, growthAvg: item.growth / count }
      })
      .sort((a, b) => b.index - a.index)
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
    <div className="map-page-full">
      <H3Map
        data={filtered}
        timeData={timeRecords}
        selectedDate={selectedDate}
        zoning={zoning}
        pois={pois}
        visibleLayers={visibleLayers}
        poiTypes={poiTypes}
        poiFilterDefs={POI_FILTERS}
        mode={selectedDate ? 'growth' : mapMode}
        rawMode={mapMode}
        influenceRadius={influenceRadius}
        labelMode={labelMode}
        onOpenConcept={onOpenConcept}
        onModeChange={setMapMode}
        onToggleLayer={toggleLayer}
        onTogglePoiType={togglePoiType}
        onRadiusChange={setInfluenceRadius}
        onLabelModeChange={setLabelMode}
        priorityFilter={priorityFilter}
        onPriorityChange={setPriorityFilter}
        riskFilter={riskFilter}
        onRiskChange={setRiskFilter}
        rankedZones={rankedZones}
      />

      <TimeSlider
        dates={timeDates}
        selectedDate={selectedDate}
        onChange={onDateChange}
      />
    </div>
  )
}
