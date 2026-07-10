import { useEffect, useMemo, useRef, useState } from 'react'
import DeckGL from '@deck.gl/react'
import { BitmapLayer, GeoJsonLayer, H3HexagonLayer, PolygonLayer, ScatterplotLayer, TextLayer, TileLayer } from 'deck.gl'
import { FlyToInterpolator } from '@deck.gl/core'
import { cellToLatLng } from 'h3-js'

const CITY = { longitude: -45.9489, latitude: -22.2303 }
const INITIAL_VIEW = { ...CITY, zoom: 12, pitch: 0, bearing: 0 }
// bbox aproximado de Pouso Alegre/MG, usado para priorizar resultados de busca de endereco
const CITY_VIEWBOX = '-46.05,-22.13,-45.83,-22.38'

const POI_LABEL_MIN_ZOOM = 15
const INFLUENCE_MIN_ZOOM = 10.8

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

const POI_LABELS = {
  pharmacy: 'Farmacia',
  supermarket: 'Mercado',
  school: 'Escola',
  clinic: 'Clinica',
  hospital: 'Hospital',
  park: 'Parque',
  restaurant: 'Restaurante',
  bus_stop: 'Onibus',
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

function shortPoiName(name) {
  const value = String(name || '').trim()
  if (!value) return ''
  return value
    .replace(/\b(supermercado|mercado|farmacia|drogaria|escola|colegio|hospital|clinica)\b/ig, match => {
      const m = match.toLowerCase()
      if (m === 'supermercado') return 'Sup.'
      if (m === 'farmacia') return 'Farm.'
      if (m === 'drogaria') return 'Drog.'
      if (m === 'colegio') return 'Col.'
      if (m === 'clinica') return 'Clin.'
      return match
    })
    .slice(0, 28)
}

function poiImportance(feature) {
  const type = poiType(feature)
  if (type === 'hospital') return 9
  if (type === 'school' || type === 'supermarket') return 7
  if (type === 'clinic' || type === 'pharmacy') return 6
  if (type === 'park') return 4
  return 2
}

function selectedCenter(cell) {
  if (!cell?.h3_id) return null
  try {
    const [lat, lng] = cellToLatLng(cell.h3_id)
    return { longitude: lng, latitude: lat }
  } catch {
    return null
  }
}

function circlePolygon(center, radiusMeters) {
  const points = []
  const latRadius = radiusMeters / 111320
  const lngRadius = radiusMeters / (111320 * Math.cos(center.latitude * Math.PI / 180))
  for (let i = 0; i <= 96; i += 1) {
    const angle = (i / 96) * Math.PI * 2
    points.push([
      center.longitude + Math.cos(angle) * lngRadius,
      center.latitude + Math.sin(angle) * latRadius,
    ])
  }
  return points
}

export default function H3Map({
  data,
  timeData = [],
  selectedDate = null,
  zoning = null,
  pois = null,
  visibleLayers = { cells: true, zoning: true, pois: true },
  poiTypes = [],
  poiFilterDefs = [],
  mode = 'score',
  rawMode = mode,
  influenceRadius = 900,
  labelMode = 'smart',
  onOpenConcept = null,
  onModeChange = () => {},
  onToggleLayer = () => {},
  onTogglePoiType = () => {},
  onRadiusChange = () => {},
  onLabelModeChange = () => {},
  priorityFilter = '',
  onPriorityChange = () => {},
  riskFilter = '',
  onRiskChange = () => {},
  rankedZones = [],
}) {
  const [tooltip, setTooltip] = useState(null)
  const [selected, setSelected] = useState(null)
  const [viewState, setViewState] = useState(INITIAL_VIEW)
  const [searchPin, setSearchPin] = useState(null)
  const isNarrow = typeof window !== 'undefined' && window.innerWidth <= 900
  const [layersOpen, setLayersOpen] = useState(!isNarrow)
  const [rankingOpen, setRankingOpen] = useState(!isNarrow)

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

  const labeledPois = useMemo(() => {
    if (labelMode === 'hidden') return []
    const limit = viewState.zoom >= 16 ? 70 : viewState.zoom >= 15 ? 42 : 18
    return filteredPois
      .filter(feature => feature.properties?.name)
      .sort((a, b) => poiImportance(b) - poiImportance(a))
      .slice(0, labelMode === 'all' ? 120 : limit)
  }, [filteredPois, labelMode, viewState.zoom])

  const poiClusters = useMemo(() => {
    const buckets = new Map()
    const precision = viewState.zoom < 12 ? 1 : viewState.zoom < 14 ? 2 : 3
    filteredPois.forEach(feature => {
      const [lon, lat] = feature.geometry.coordinates
      const key = `${lon.toFixed(precision)}:${lat.toFixed(precision)}`
      const current = buckets.get(key) || { lon: 0, lat: 0, count: 0, types: new Set() }
      current.lon += lon
      current.lat += lat
      current.count += 1
      current.types.add(poiType(feature))
      buckets.set(key, current)
    })
    return [...buckets.values()].map(item => ({
      position: [item.lon / item.count, item.lat / item.count],
      count: item.count,
      label: String(item.count),
      types: [...item.types],
    })).filter(item => item.count > 1)
  }, [filteredPois, viewState.zoom])

  const poiLegend = useMemo(() => {
    if (!visibleLayers.pois) return []
    const present = new Set(filteredPois.map(poiType))
    return Object.keys(POI_LABELS)
      .filter(type => present.has(type))
      .map(type => ({ type, label: POI_LABELS[type], color: `rgb(${POI_COLORS[type].join(',')})` }))
  }, [filteredPois, visibleLayers.pois])

  const influenceCenter = useMemo(() => {
    if (searchPin) return { longitude: searchPin.lon, latitude: searchPin.lat }
    return selectedCenter(selected) || CITY
  }, [searchPin, selected])

  const influenceLayer = useMemo(() => new PolygonLayer({
    id: 'influence-radius',
    data: influenceRadius > 0 ? [{ polygon: circlePolygon(influenceCenter, influenceRadius) }] : [],
    getPolygon: d => d.polygon,
    filled: true,
    stroked: true,
    getFillColor: [37, 99, 235, 34],
    getLineColor: [27, 42, 74, 210],
    getLineWidth: 3,
    lineWidthUnits: 'pixels',
    visible: viewState.zoom >= INFLUENCE_MIN_ZOOM,
    pickable: false,
  }), [influenceCenter, influenceRadius, viewState.zoom])

  const zoningLayer = useMemo(() => new GeoJsonLayer({
    id: 'official-zoning',
    data: zoning || { type: 'FeatureCollection', features: [] },
    pickable: true,
    stroked: true,
    filled: mode === 'zoning',
    getFillColor: f => zoneColor(f.properties?.zona, 92),
    getLineColor: f => mode === 'zoning' ? [...zoneColor(f.properties?.zona, 224).slice(0, 3), 224] : [100, 116, 139, 140],
    getLineWidth: mode === 'zoning' ? 80 : 30,
    lineWidthMinPixels: mode === 'zoning' ? 1.6 : 0.6,
    autoHighlight: mode === 'zoning',
    highlightColor: [255, 255, 255, 70],
    updateTriggers: {
      filled: [mode],
      getLineColor: [mode],
      getLineWidth: [mode],
      lineWidthMinPixels: [mode],
    },
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
    visible: viewState.zoom >= 13.5,
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
  }), [filteredPois, viewState.zoom])

  const clusterLayer = useMemo(() => new ScatterplotLayer({
    id: 'poi-clusters',
    data: poiClusters,
    visible: viewState.zoom < 13.5,
    pickable: true,
    stroked: true,
    filled: true,
    radiusUnits: 'pixels',
    getPosition: d => d.position,
    getRadius: d => Math.min(28, 8 + d.count * 1.8),
    getFillColor: [219, 39, 119, 205],
    getLineColor: [255, 255, 255, 235],
    getLineWidth: 2,
    onHover: info => setTooltip(info.object ? { kind: 'cluster', object: info.object, x: info.x, y: info.y } : null),
  }), [poiClusters, viewState.zoom])

  const clusterLabelLayer = useMemo(() => new TextLayer({
    id: 'poi-cluster-labels',
    data: poiClusters,
    visible: viewState.zoom < 13.5,
    pickable: false,
    getPosition: d => d.position,
    getText: d => d.label,
    getSize: 12,
    getColor: [255, 255, 255, 255],
    fontWeight: 800,
  }), [poiClusters, viewState.zoom])

  const poiLabelLayer = useMemo(() => new TextLayer({
    id: 'poi-labels',
    data: labeledPois,
    visible: labelMode !== 'hidden' && viewState.zoom >= POI_LABEL_MIN_ZOOM,
    pickable: false,
    getPosition: feature => feature.geometry.coordinates,
    getText: feature => shortPoiName(feature.properties?.name),
    getSize: viewState.zoom >= 16 ? 12 : 11,
    getColor: [15, 23, 42, 245],
    getPixelOffset: [0, 16],
    background: true,
    getBackgroundColor: [255, 255, 255, 226],
    backgroundPadding: [5, 2],
    fontFamily: '"Segoe UI", sans-serif',
    fontWeight: 700,
    maxWidth: 96,
    getTextAnchor: 'middle',
    getAlignmentBaseline: 'top',
    updateTriggers: { visible: [viewState.zoom, labelMode] },
  }), [labeledPois, labelMode, viewState.zoom])

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

  const zoomBy = delta => setViewState(current => ({
    ...current,
    zoom: Math.max(2, Math.min(20, current.zoom + delta)),
    transitionDuration: 200,
  }))

  const resetView = () => setViewState({
    ...INITIAL_VIEW,
    transitionDuration: 600,
    transitionInterpolator: new FlyToInterpolator(),
  })

  const legend = legendFor(mode, selectedDate)
  const zoningCount = zoning?.features?.length || 0
  const layers = [
    BASE_TILES,
    influenceLayer,
    visibleLayers.zoning ? zoningLayer : null,
    visibleLayers.cells ? hexLayer : null,
    visibleLayers.pois ? clusterLayer : null,
    visibleLayers.pois ? clusterLabelLayer : null,
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

      <RankingPanel
        open={rankingOpen}
        onToggle={() => setRankingOpen(o => !o)}
        cellCount={data.length}
        zoningCount={zoningCount}
        poiCount={filteredPois.length}
        rankedZones={rankedZones}
      />

      <div className="atlas-right-stack">
        <LayersPanel
          open={layersOpen}
          onToggle={() => setLayersOpen(o => !o)}
          rawMode={rawMode}
          onModeChange={onModeChange}
          dateActive={!!selectedDate}
          visibleLayers={visibleLayers}
          onToggleLayer={onToggleLayer}
          cellCount={data.length}
          zoningCount={zoningCount}
          poiCount={filteredPois.length}
          poiFilterDefs={poiFilterDefs}
          poiTypes={poiTypes}
          onTogglePoiType={onTogglePoiType}
          influenceRadius={influenceRadius}
          onRadiusChange={onRadiusChange}
          labelMode={labelMode}
          onLabelModeChange={onLabelModeChange}
          priorityFilter={priorityFilter}
          onPriorityChange={onPriorityChange}
          riskFilter={riskFilter}
          onRiskChange={onRiskChange}
        />
        {selected && <SelectedPanel cell={selected} onClose={() => setSelected(null)} onOpenConcept={onOpenConcept} />}
      </div>

      <div className="atlas-zoom-controls">
        <button onClick={() => zoomBy(1)} title="Aumentar zoom">+</button>
        <button onClick={() => zoomBy(-1)} title="Diminuir zoom">−</button>
        <button onClick={resetView} title="Ver cidade inteira">⌂</button>
      </div>

      <div className="atlas-legend-group">
        <div className="atlas-legend">
          <span>{selectedDate ? `NDVI ${selectedDate}` : mode === 'zoning' ? 'Zoneamento PDPA' : mode === 'growth' ? 'Tendencia urbana' : 'Score'}</span>
          {legend.map(item => (
            <div key={item.label}>
              <i style={{ background: item.color }} />
              {item.label}
            </div>
          ))}
        </div>

        {poiLegend.length > 0 && (
          <div className="atlas-legend atlas-poi-legend">
            <span>Pontos urbanos</span>
            {poiLegend.map(item => (
              <div key={item.type}>
                <i style={{ background: item.color, borderRadius: '50%' }} />
                {item.label}
              </div>
            ))}
            <div className="atlas-poi-legend-cluster">
              <i style={{ background: 'rgb(219, 39, 119)', borderRadius: '50%' }} />
              Agrupamento (numero = qtde.)
            </div>
          </div>
        )}
      </div>

      {tooltip && <Tooltip tooltip={tooltip} />}

      <div className="atlas-map-attribution">
        © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors, © <a href="https://carto.com/attributions" target="_blank" rel="noreferrer">CARTO</a>
      </div>
    </div>
  )
}

const MODE_LABELS = { score: 'Score', zoning: 'Zoneamento', growth: 'Crescimento' }

function Chevron({ open }) {
  return (
    <svg className={`atlas-chevron${open ? ' open' : ''}`} width="10" height="10" viewBox="0 0 10 10" fill="none">
      <path d="M2 3.5L5 6.5L8 3.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function LayersPanel({
  open, onToggle, rawMode, onModeChange, dateActive,
  visibleLayers, onToggleLayer, cellCount, zoningCount, poiCount,
  poiFilterDefs, poiTypes, onTogglePoiType,
  influenceRadius, onRadiusChange, labelMode, onLabelModeChange,
  priorityFilter, onPriorityChange, riskFilter, onRiskChange,
}) {
  return (
    <div className={`atlas-floating-panel atlas-layers-panel${open ? '' : ' collapsed'}`}>
      <button className="atlas-panel-header" onClick={onToggle}>
        <span>Camadas &amp; filtros</span>
        <Chevron open={open} />
      </button>
      {open && (
        <div className="atlas-panel-body">
          <div className="atlas-mode-row">
            {Object.keys(MODE_LABELS).map(m => (
              <button
                key={m}
                className={rawMode === m ? 'active' : ''}
                onClick={() => onModeChange(m)}
              >
                {MODE_LABELS[m]}
              </button>
            ))}
          </div>
          {dateActive && <p className="atlas-panel-hint">Modo forcado para Crescimento pela linha do tempo (NDVI).</p>}

          <label className="atlas-layer-row">
            <input type="checkbox" checked={visibleLayers.cells} onChange={() => onToggleLayer('cells')} />
            Celulas <span>{cellCount}</span>
          </label>
          <label className="atlas-layer-row">
            <input type="checkbox" checked={visibleLayers.zoning} onChange={() => onToggleLayer('zoning')} />
            Zonas <span>{zoningCount}</span>
          </label>
          <label className="atlas-layer-row">
            <input type="checkbox" checked={visibleLayers.pois} onChange={() => onToggleLayer('pois')} />
            Pontos <span>{poiCount}</span>
          </label>

          {visibleLayers.pois && poiFilterDefs.length > 0 && (
            <div className="atlas-poi-chip-row">
              {poiFilterDefs.map(item => (
                <button
                  key={item.id}
                  className={poiTypes.includes(item.id) ? 'active' : ''}
                  onClick={() => onTogglePoiType(item.id)}
                >
                  {item.label}
                </button>
              ))}
            </div>
          )}

          <div className="atlas-panel-divider" />

          <div className="atlas-select-row">
            <select value={influenceRadius} onChange={e => onRadiusChange(Number(e.target.value))}>
              <option value={500}>Raio 500 m</option>
              <option value={900}>Raio 900 m</option>
              <option value={1500}>Raio 1,5 km</option>
              <option value={2500}>Raio 2,5 km</option>
            </select>
            <select value={labelMode} onChange={e => onLabelModeChange(e.target.value)}>
              <option value="smart">Nomes essenciais</option>
              <option value="all">Mais nomes</option>
              <option value="hidden">Sem nomes</option>
            </select>
          </div>
          <div className="atlas-select-row">
            <select value={priorityFilter} onChange={e => onPriorityChange(e.target.value)}>
              <option value="">Todas as prioridades</option>
              <option value="alta">Alta</option>
              <option value="media">Média</option>
              <option value="baixa">Baixa</option>
            </select>
            <select value={riskFilter} onChange={e => onRiskChange(e.target.value)}>
              <option value="">Todos os riscos</option>
              <option value="baixo">Baixo</option>
              <option value="medio">Médio</option>
              <option value="alto">Alto</option>
            </select>
          </div>
        </div>
      )}
    </div>
  )
}

function RankingPanel({ open, onToggle, cellCount, zoningCount, poiCount, rankedZones }) {
  return (
    <div className={`atlas-floating-panel atlas-ranking-panel${open ? '' : ' collapsed'}`}>
      <button className="atlas-panel-header" onClick={onToggle}>
        <span>Painel de oportunidades</span>
        <Chevron open={open} />
      </button>
      {open && (
        <div className="atlas-panel-body">
          <div className="atlas-ranking-stats">
            <div><strong>{cellCount}</strong><span>celulas</span></div>
            <div><strong>{zoningCount}</strong><span>zonas</span></div>
            <div><strong>{poiCount}</strong><span>pontos</span></div>
          </div>
          {rankedZones.length > 0 && (
            <ol className="atlas-ranking-list">
              {rankedZones.map((item, index) => (
                <li key={item.name}>
                  <span className="atlas-ranking-pos">#{index + 1}</span>
                  <span className="atlas-ranking-name">{item.name}</span>
                  <strong>{item.index.toFixed(0)}</strong>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
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

function SelectedPanel({ cell, onClose, onOpenConcept }) {
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
      {onOpenConcept && (
        <button className="atlas-concept-btn" onClick={() => onOpenConcept(cell)}>
          Gerar conceito e obra
        </button>
      )}
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
  if (kind === 'cluster') {
    return (
      <div className="atlas-tooltip" style={style}>
        <strong>{object.count} estabelecimentos</strong>
        <span>{object.types.join(', ')}</span>
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
