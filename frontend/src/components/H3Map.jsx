import { useEffect, useMemo, useRef, useState } from 'react'
import DeckGL from '@deck.gl/react'
import { BitmapLayer, GeoJsonLayer, H3HexagonLayer, ScatterplotLayer, TextLayer, TileLayer } from 'deck.gl'
import { FlyToInterpolator } from '@deck.gl/core'

const CITY = { longitude: -45.9489, latitude: -22.2303 }
const INITIAL_VIEW = { ...CITY, zoom: 12, pitch: 0, bearing: 0 }
// bbox aproximado de Pouso Alegre/MG, usado para priorizar resultados de busca de endereco
const CITY_VIEWBOX = '-46.05,-22.13,-45.83,-22.38'

const POI_LABEL_MIN_ZOOM = 15

const TILE_SCALE = typeof window !== 'undefined' && window.devicePixelRatio > 1 ? '@2x' : ''

const BASE_TILES = new TileLayer({
  id: 'base-streets',
  data: [
    `https://a.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}${TILE_SCALE}.png`,
    `https://b.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}${TILE_SCALE}.png`,
    `https://c.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}${TILE_SCALE}.png`,
    `https://d.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}${TILE_SCALE}.png`,
  ],
  minZoom: 0,
  maxZoom: 20,
  tileSize: 256,
  renderSubLayers: props => {
    const { bbox: { west, south, east, north } } = props.tile
    return new BitmapLayer(props, {
      image: props.data,
      bounds: [west, south, east, north],
      opacity: 1,
    })
  },
})

const SCORE_LEGEND = [
  { color: '#15803d', label: 'Alto' },
  { color: '#ca8a04', label: 'Medio' },
  { color: '#ea580c', label: 'Baixo' },
  { color: '#b91c1c', label: 'Critico' },
]

const GROWTH_LEGEND = [
  { color: '#2563eb', label: 'Mais construido' },
  { color: '#16a34a', label: 'Mais verde' },
  { color: '#64748b', label: 'Estavel' },
]

const ZONING_LEGEND = [
  { color: '#0f766e', label: 'Centrais/mistas' },
  { color: '#7c3aed', label: 'Expansao/projetos' },
  { color: '#15803d', label: 'Ambientais' },
  { color: '#c2410c', label: 'Especiais' },
]

const POI_COLORS = {
  pharmacy: [220, 38, 38],
  supermarket: [22, 163, 74],
  school: [37, 99, 235],
  clinic: [14, 165, 233],
  hospital: [147, 51, 234],
  park: [21, 128, 61],
  restaurant: [234, 88, 12],
  bus_stop: [71, 85, 105],
}

function scoreToRgba(score, alpha = 96) {
  if (score >= 70) return [21, 128, 61, alpha]
  if (score >= 50) return [202, 138, 4, alpha]
  if (score >= 30) return [234, 88, 12, alpha]
  return [185, 28, 28, alpha]
}

function growthToRgba(row, alpha = 110) {
  const ndbi = Number(row.ndbi_slope_180 || 0)
  const ndvi = Number(row.ndvi_slope_180 || 0)
  if (ndbi > 0.0005) return [37, 99, 235, alpha]
  if (ndvi > 0.0005) return [22, 163, 74, alpha]
  if (ndvi < -0.001) return [202, 138, 4, alpha]
  return [100, 116, 139, 92]
}

function ndviToRgba(ndvi, alpha = 132) {
  const t = Math.max(0, Math.min(1, (Number(ndvi) + 0.1) / 0.7))
  return [
    Math.round(190 * (1 - t) + 22 * t),
    Math.round(68 * (1 - t) + 163 * t),
    Math.round(62 * (1 - t) + 74 * t),
    alpha,
  ]
}

function zoneColor(zone, alpha = 92) {
  const value = String(zone || '').toUpperCase()
  if (value.startsWith('ZEPAM')) return [21, 128, 61, alpha]
  if (value.startsWith('ZEIS') || value.startsWith('ZEPEC') || value.startsWith('ZER')) return [194, 65, 12, alpha]
  if (value.startsWith('ZEP') || value.startsWith('ZEU') || value.startsWith('ZEPU') || value === 'ZEEP') return [124, 58, 237, alpha]
  if (value.startsWith('ZM') || value === 'ZC' || value === 'ZMV') return [15, 118, 110, alpha]
  return [71, 85, 105, alpha]
}

function poiType(feature) {
  const subcategory = String(feature?.properties?.subcategory || '').toLowerCase()
  const category = String(feature?.properties?.category || '').toLowerCase()
  if (subcategory.includes('pharmacy')) return 'pharmacy'
  if (subcategory.includes('supermarket') || subcategory.includes('convenience') || subcategory.includes('bakery')) return 'supermarket'
  if (subcategory.includes('school') || subcategory.includes('kindergarten')) return 'school'
  if (subcategory.includes('hospital')) return 'hospital'
  if (subcategory.includes('clinic')) return 'clinic'
  if (subcategory.includes('park') || subcategory.includes('garden')) return 'park'
  if (subcategory.includes('restaurant') || subcategory.includes('cafe')) return 'restaurant'
  if (subcategory.includes('bus') || category.includes('transport')) return 'bus_stop'
  return subcategory || category || 'poi'
}

function legendFor(mode, selectedDate) {
  if (selectedDate || mode === 'growth') return GROWTH_LEGEND
  if (mode === 'zoning') return ZONING_LEGEND
  return SCORE_LEGEND
}

export default function H3Map({
  data,
  timeData = [],
  selectedDate = null,
  zoning = null,
  pois = null,
  visibleLayers = { cells: true, zoning: true, pois: true },
  poiTypes = [],
  mode = 'score',
}) {
  const [tooltip, setTooltip] = useState(null)
  const [selected, setSelected] = useState(null)
  const [viewState, setViewState] = useState(INITIAL_VIEW)
  const [searchPin, setSearchPin] = useState(null)

  const ndviByCell = useMemo(() => {
    if (!selectedDate || !timeData.length) return {}
    return Object.fromEntries(timeData.filter(r => r.date === selectedDate).map(r => [r.h3_id, r.ndvi]))
  }, [timeData, selectedDate])

  const filteredPois = useMemo(() => {
    const features = pois?.features || []
    if (!visibleLayers.pois) return []
    if (!poiTypes.length) return features
    return features.filter(feature => poiTypes.includes(poiType(feature)))
  }, [pois, poiTypes, visibleLayers.pois])

  const zoningLayer = useMemo(() => new GeoJsonLayer({
    id: 'official-zoning',
    data: zoning || { type: 'FeatureCollection', features: [] },
    pickable: true,
    stroked: true,
    filled: true,
    getFillColor: f => zoneColor(f.properties?.zona, mode === 'zoning' ? 92 : 28),
    getLineColor: f => zoneColor(f.properties?.zona, 224).slice(0, 3),
    getLineWidth: mode === 'zoning' ? 80 : 36,
    lineWidthMinPixels: mode === 'zoning' ? 1.6 : 0.8,
    autoHighlight: true,
    highlightColor: [255, 255, 255, 70],
    onHover: info => setTooltip(info.object ? { kind: 'zone', object: info.object, x: info.x, y: info.y } : null),
  }), [zoning, mode])

  const hexLayer = useMemo(() => new H3HexagonLayer({
    id: 'h3-readable',
    data,
    getHexagon: d => d.h3_id,
    getFillColor: d => {
      if (selectedDate) {
        const ndvi = ndviByCell[d.h3_id]
        return ndvi != null ? ndviToRgba(ndvi) : [100, 116, 139, 54]
      }
      if (mode === 'growth') return growthToRgba(d)
      if (mode === 'zoning') return [15, 23, 42, 18]
      return scoreToRgba(Math.max(d.score_residencial || 0, d.score_comercial || 0))
    },
    getLineColor: d => selected?.h3_id === d.h3_id ? [15, 23, 42, 255] : [255, 255, 255, 190],
    lineWidthMinPixels: d => selected?.h3_id === d.h3_id ? 2 : 0.55,
    filled: true,
    stroked: true,
    extruded: false,
    coverage: mode === 'zoning' ? 0.38 : 0.52,
    pickable: true,
    autoHighlight: true,
    highlightColor: [15, 23, 42, 48],
    updateTriggers: {
      getFillColor: [mode, selectedDate, ndviByCell],
      getLineColor: [selected],
      lineWidthMinPixels: [selected],
      coverage: [mode],
    },
    onHover: info => setTooltip(info.object ? { kind: 'cell', object: info.object, x: info.x, y: info.y } : null),
    onClick: info => setSelected(info.object || null),
  }), [data, mode, selectedDate, ndviByCell, selected])

  const poiLayer = useMemo(() => new ScatterplotLayer({
    id: 'osm-pois',
    data: filteredPois,
    pickable: true,
    stroked: true,
    filled: true,
    radiusUnits: 'pixels',
    getPosition: feature => feature.geometry.coordinates,
    getRadius: feature => poiType(feature) === 'hospital' ? 7 : 5,
    getFillColor: feature => [...(POI_COLORS[poiType(feature)] || [15, 23, 42]), 225],
    getLineColor: [255, 255, 255, 245],
    getLineWidth: 1.5,
    autoHighlight: true,
    highlightColor: [15, 23, 42, 60],
    onHover: info => setTooltip(info.object ? { kind: 'poi', object: info.object, x: info.x, y: info.y } : null),
  }), [filteredPois])

  const poiLabelLayer = useMemo(() => new TextLayer({
    id: 'poi-labels',
    data: filteredPois,
    visible: viewState.zoom >= POI_LABEL_MIN_ZOOM,
    pickable: false,
    getPosition: feature => feature.geometry.coordinates,
    getText: feature => feature.properties?.name || '',
    getSize: 12,
    getColor: [30, 41, 59, 235],
    getPixelOffset: [0, 14],
    background: true,
    getBackgroundColor: [255, 255, 255, 200],
    backgroundPadding: [3, 1],
    fontFamily: '"Segoe UI", sans-serif',
    updateTriggers: { visible: [viewState.zoom] },
  }), [filteredPois, viewState.zoom])

  const searchPinLayer = useMemo(() => new ScatterplotLayer({
    id: 'search-pin',
    data: searchPin ? [searchPin] : [],
    pickable: false,
    radiusUnits: 'pixels',
    getPosition: d => [d.lon, d.lat],
    getRadius: 9,
    getFillColor: [201, 168, 76, 235],
    getLineColor: [27, 42, 74, 255],
    getLineWidth: 2,
    stroked: true,
  }), [searchPin])

  const legend = legendFor(mode, selectedDate)
  const zoningCount = zoning?.features?.length || 0
  const layers = [
    BASE_TILES,
    visibleLayers.zoning ? zoningLayer : null,
    visibleLayers.cells ? hexLayer : null,
    visibleLayers.pois ? poiLayer : null,
    visibleLayers.pois ? poiLabelLayer : null,
    searchPinLayer,
  ].filter(Boolean)

  return (
    <div className="atlas-map-shell">
      <DeckGL
        viewState={viewState}
        onViewStateChange={({ viewState: next }) => setViewState(next)}
        controller={true}
        layers={layers}
        getCursor={({ isDragging, isHovering }) => isDragging ? 'grabbing' : isHovering ? 'pointer' : 'grab'}
      />

      <AddressSearch
        onSelect={place => {
          setSearchPin({ lon: place.lon, lat: place.lat })
          setViewState(current => ({
            ...current,
            longitude: place.lon,
            latitude: place.lat,
            zoom: 17,
            transitionDuration: 800,
            transitionInterpolator: new FlyToInterpolator(),
          }))
        }}
      />

      <div className="atlas-map-summary">
        <strong>{data.length}</strong>
        <span>celulas</span>
        <strong>{zoningCount}</strong>
        <span>zonas</span>
        <strong>{filteredPois.length}</strong>
        <span>pontos</span>
      </div>

      <div className="atlas-legend">
        <span>{selectedDate ? `NDVI ${selectedDate}` : mode === 'zoning' ? 'Zoneamento PDPA' : mode === 'growth' ? 'Tendencia urbana' : 'Score'}</span>
        {legend.map(item => (
          <div key={item.label}>
            <i style={{ background: item.color }} />
            {item.label}
          </div>
        ))}
      </div>

      {selected && <SelectedPanel cell={selected} onClose={() => setSelected(null)} />}
      {tooltip && <Tooltip tooltip={tooltip} />}

      <div className="atlas-map-attribution">
        © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors, © <a href="https://carto.com/attributions" target="_blank" rel="noreferrer">CARTO</a>
      </div>
    </div>
  )
}

function AddressSearch({ onSelect }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const debounceRef = useRef(null)

  useEffect(() => {
    clearTimeout(debounceRef.current)
    if (query.trim().length < 3) {
      setResults([])
      return
    }
    debounceRef.current = setTimeout(async () => {
      setLoading(true)
      try {
        const params = new URLSearchParams({
          q: query,
          format: 'jsonv2',
          limit: '6',
          viewbox: CITY_VIEWBOX,
          bounded: '1',
        })
        const res = await fetch(`https://nominatim.openstreetmap.org/search?${params}`, {
          headers: { Accept: 'application/json' },
        })
        const json = res.ok ? await res.json() : []
        setResults(json)
      } catch {
        setResults([])
      } finally {
        setLoading(false)
      }
    }, 450)
    return () => clearTimeout(debounceRef.current)
  }, [query])

  const pick = place => {
    onSelect({ lon: Number(place.lon), lat: Number(place.lat) })
    setQuery(place.display_name)
    setOpen(false)
  }

  return (
    <div className="atlas-search">
      <input
        type="text"
        placeholder="Buscar rua, bairro ou comercio..."
        value={query}
        onChange={e => { setQuery(e.target.value); setOpen(true) }}
        onFocus={() => setOpen(true)}
      />
      {open && (loading || results.length > 0) && (
        <ul className="atlas-search-results">
          {loading && <li className="atlas-search-loading">Buscando...</li>}
          {!loading && results.map(place => (
            <li key={place.place_id} onClick={() => pick(place)}>
              {place.display_name}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function SelectedPanel({ cell, onClose }) {
  return (
    <aside className="atlas-selected-panel">
      <button className="atlas-panel-close" onClick={onClose}>x</button>
      <div className="atlas-panel-kicker">Celula H3</div>
      <h3>{cell.h3_id}</h3>
      <Metric label="Prioridade" value={cell.priority} strong />
      <Metric label="Risco" value={cell.risk_level} />
      <Metric label="Zona" value={cell.zona || cell.zoning?.zona || 'sem cruzamento'} />
      <Metric label="Score residencial" value={formatNumber(cell.score_residencial)} />
      <Metric label="Score comercial" value={formatNumber(cell.score_comercial)} />
      <Metric label="NDVI 90d" value={formatNumber(cell.ndvi_mean_90, 3)} />
      <Metric label="NDBI 90d" value={formatNumber(cell.ndbi_mean_90, 3)} />
      {cell.legal_notes && <p>{cell.legal_notes}</p>}
    </aside>
  )
}

function Tooltip({ tooltip }) {
  const { kind, object, x, y } = tooltip
  const style = { left: x + 14, top: y + 14 }
  if (kind === 'zone') {
    const props = object.properties || {}
    return (
      <div className="atlas-tooltip" style={style}>
        <strong>{props.zona || 'Zona'}</strong>
        <span>{props.observacoes || 'Zoneamento oficial'}</span>
      </div>
    )
  }
  if (kind === 'poi') {
    const props = object.properties || {}
    return (
      <div className="atlas-tooltip" style={style}>
        <strong>{props.name || props.subcategory || 'Ponto urbano'}</strong>
        <span>{props.subcategory || props.category || 'equipamento'}</span>
      </div>
    )
  }
  return (
    <div className="atlas-tooltip" style={style}>
      <strong>{object.h3_id}</strong>
      <span>Residencial: {formatNumber(object.score_residencial)}</span>
      <span>Comercial: {formatNumber(object.score_comercial)}</span>
    </div>
  )
}

function Metric({ label, value, strong = false }) {
  return (
    <div className="atlas-metric">
      <span>{label}</span>
      <strong className={strong ? 'accent' : ''}>{value ?? '-'}</strong>
    </div>
  )
}

function formatNumber(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-'
  return Number(value).toFixed(digits)
}
