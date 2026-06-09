import { useState, useMemo, useCallback } from 'react'
import DeckGL from '@deck.gl/react'
import { H3HexagonLayer, TileLayer } from 'deck.gl'
import { BitmapLayer } from 'deck.gl'

const CITY = { longitude: -45.9489, latitude: -22.2303 }

const VIEW_FLAT = { ...CITY, zoom: 11, pitch: 0,  bearing: 0 }
const VIEW_3D   = { ...CITY, zoom: 11, pitch: 45, bearing: -15 }

function scoreToRgba(score, alpha = 210) {
  if (score >= 70) return [22,  163, 74,  alpha]
  if (score >= 50) return [202, 138, 4,   alpha]
  if (score >= 30) return [234, 88,  12,  alpha]
  return               [220, 38,  38,  alpha]
}

function ndviToRgba(ndvi, alpha = 210) {
  // red (bare soil / urban) → green (vegetation)
  const t = Math.max(0, Math.min(1, (ndvi + 0.1) / 0.7))
  return [
    Math.round(220 * (1 - t) + 30 * t),
    Math.round(40  * (1 - t) + 160 * t),
    Math.round(40  * (1 - t) + 74  * t),
    alpha,
  ]
}

const OSM_TILES = new TileLayer({
  id: 'osm',
  data: 'https://c.tile.openstreetmap.org/{z}/{x}/{y}.png',
  minZoom: 0,
  maxZoom: 19,
  tileSize: 256,
  renderSubLayers: props => {
    const { bbox: { west, south, east, north } } = props.tile
    return new BitmapLayer(props, {
      image: props.data,
      bounds: [west, south, east, north],
    })
  },
})

const LEGEND_SCORE = [
  { color: '#16a34a', label: 'Alto  ≥70' },
  { color: '#ca8a04', label: 'Médio 50–70' },
  { color: '#ea580c', label: 'Baixo 30–50' },
  { color: '#dc2626', label: 'Mínimo <30' },
]
const LEGEND_NDVI = [
  { color: '#dc2626', label: 'Solo/Urbano' },
  { color: '#ca8a04', label: 'Vegetação baixa' },
  { color: '#16a34a', label: 'Vegetação densa' },
]

export default function H3Map({ data, timeData = [], selectedDate = null }) {
  const [is3D, setIs3D]         = useState(true)
  const [tooltip, setTooltip]   = useState(null)
  const [viewState, setViewState] = useState(VIEW_3D)

  // Lookup time-series NDVI for the selected date
  const ndviByCell = useMemo(() => {
    if (!selectedDate || !timeData.length) return {}
    return Object.fromEntries(
      timeData
        .filter(r => r.date === selectedDate)
        .map(r => [r.h3_id, r.ndvi])
    )
  }, [timeData, selectedDate])

  const toggle3D = useCallback(() => {
    const next = !is3D
    setIs3D(next)
    setViewState(prev => ({ ...prev, pitch: next ? 45 : 0, bearing: next ? -15 : 0 }))
  }, [is3D])

  const hexLayer = useMemo(() => new H3HexagonLayer({
    id: 'h3',
    data,
    getHexagon: d => d.h3_id,
    getFillColor: d => {
      if (selectedDate) {
        const ndvi = ndviByCell[d.h3_id]
        return ndvi != null ? ndviToRgba(ndvi) : [100, 100, 100, 80]
      }
      return scoreToRgba(Math.max(d.score_residencial || 0, d.score_comercial || 0))
    },
    getElevation: d => Math.max(d.score_residencial || 0, d.score_comercial || 0),
    extruded: is3D,
    elevationScale: is3D ? 35 : 0,
    coverage: 0.9,
    pickable: true,
    autoHighlight: true,
    highlightColor: [255, 255, 255, 60],
    updateTriggers: {
      getFillColor: [selectedDate, ndviByCell],
      extruded:     [is3D],
      elevationScale: [is3D],
    },
    transitions: {
      getFillColor:   { duration: 400 },
      getElevation:   { duration: 400 },
      elevationScale: { duration: 400 },
    },
    onHover: ({ object, x, y }) => setTooltip(object ? { object, x, y } : null),
  }), [data, is3D, selectedDate, ndviByCell])

  const legend = selectedDate ? LEGEND_NDVI : LEGEND_SCORE

  return (
    <div style={{ position: 'relative', height: 600, borderRadius: 10, overflow: 'hidden', border: '1px solid #e2e8f0' }}>
      {/* Controls */}
      <div style={{
        position: 'absolute', top: 12, right: 12, zIndex: 10,
        display: 'flex', flexDirection: 'column', gap: 8,
      }}>
        <button onClick={toggle3D} style={btnStyle}>
          {is3D ? '2D' : '3D'}
        </button>
      </div>

      {/* Legend */}
      <div style={{
        position: 'absolute', bottom: 12, left: 12, zIndex: 10,
        background: 'rgba(15,23,42,0.82)', borderRadius: 8,
        padding: '8px 12px', display: 'flex', flexDirection: 'column', gap: 4,
      }}>
        <span style={{ fontSize: 10, color: '#94a3b8', fontWeight: 600, marginBottom: 2 }}>
          {selectedDate ? `NDVI · ${selectedDate}` : 'Score de oportunidade'}
        </span>
        {legend.map(({ color, label }) => (
          <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 10, height: 10, borderRadius: 2, background: color, display: 'block' }} />
            <span style={{ fontSize: 11, color: '#e2e8f0' }}>{label}</span>
          </div>
        ))}
      </div>

      <DeckGL
        viewState={viewState}
        onViewStateChange={({ viewState: vs }) => setViewState(vs)}
        controller={true}
        layers={[OSM_TILES, hexLayer]}
        style={{ position: 'absolute', inset: 0 }}
        getCursor={({ isHovering }) => isHovering ? 'pointer' : 'grab'}
      />

      {/* Tooltip */}
      {tooltip && (
        <TooltipBox tooltip={tooltip} selectedDate={selectedDate} ndvi={ndviByCell[tooltip.object.h3_id]} />
      )}
    </div>
  )
}

function TooltipBox({ tooltip, selectedDate, ndvi }) {
  const { object: p, x, y } = tooltip
  return (
    <div style={{
      position: 'absolute',
      left: Math.min(x + 14, window.innerWidth - 230),
      top: Math.max(y - 10, 0),
      background: 'rgba(15,23,42,0.93)',
      color: '#f1f5f9',
      borderRadius: 8,
      padding: '10px 14px',
      fontSize: 13,
      pointerEvents: 'none',
      zIndex: 20,
      minWidth: 210,
      boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
    }}>
      <div style={{ fontFamily: 'monospace', fontSize: 11, color: '#94a3b8', marginBottom: 6 }}>
        {p.h3_id}
      </div>
      <Row label="Residencial" value={p.score_residencial?.toFixed(1)} />
      <Row label="Comercial"   value={p.score_comercial?.toFixed(1)} />
      <Row label="Prioridade"  value={p.priority} highlight />
      <Row label="Risco"       value={p.risk_level} />
      {selectedDate
        ? <Row label={`NDVI (${selectedDate})`} value={ndvi?.toFixed(3)} />
        : <Row label="NDVI médio 90d" value={p.ndvi_mean_90?.toFixed(3)} />
      }
      <Row label="NDBI médio 90d" value={p.ndbi_mean_90?.toFixed(3)} />
    </div>
  )
}

function Row({ label, value, highlight }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 2 }}>
      <span style={{ color: '#94a3b8', fontSize: 12 }}>{label}</span>
      <span style={{ fontWeight: highlight ? 700 : 500, color: highlight ? '#86efac' : '#f1f5f9' }}>
        {value ?? '–'}
      </span>
    </div>
  )
}

const btnStyle = {
  width: 40, height: 40,
  background: 'rgba(15,23,42,0.85)',
  color: '#f1f5f9',
  border: '1px solid rgba(255,255,255,0.15)',
  borderRadius: 8,
  cursor: 'pointer',
  fontWeight: 700,
  fontSize: 13,
  display: 'flex', alignItems: 'center', justifyContent: 'center',
}
