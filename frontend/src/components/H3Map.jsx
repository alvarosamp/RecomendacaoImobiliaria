import { useEffect, useMemo, useRef, useState } from 'react'
import DeckGL from '@deck.gl/react'
import { BitmapLayer, ColumnLayer, GeoJsonLayer, H3HexagonLayer, HeatmapLayer, PolygonLayer, ScatterplotLayer, TextLayer, TileLayer } from 'deck.gl'
import { FlyToInterpolator } from '@deck.gl/core'
import { cellToLatLng } from 'h3-js'

const CITY = { longitude: -45.9489, latitude: -22.2303 }
const INITIAL_VIEW = { ...CITY, zoom: 12, pitch: 0, bearing: 0 }

const POI_LABEL_MIN_ZOOM = 15
const INFLUENCE_MIN_ZOOM = 10.8

const TILE_SCALE = typeof window !== 'undefined' && window.devicePixelRatio > 1 ? '@2x' : ''

const BASE_TILES = new TileLayer({
  id: 'base-streets',
  // A base clara deixa ruas e bairros legiveis; as camadas analiticas ficam por cima.
  data: `https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}${TILE_SCALE}.png`,
  minZoom: 0,
  maxZoom: 20,
  tileSize: 256,
  renderSubLayers: props => {
    const { bbox: { west, south, east, north } } = props.tile
    return new BitmapLayer({ ...props, data: null }, {
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

const KERNEL_LEGEND = [
  { color: '#f59e0b', label: 'Maior procura' },
  { color: '#ef4444', label: 'Validar preco/risco' },
  { color: '#14b8a6', label: 'Zona favoravel' },
]

const VALIDATION_LEGEND = [
  { color: '#22c55e', label: 'Viavel' },
  { color: '#f59e0b', label: 'Validar' },
  { color: '#ef4444', label: 'Restricao' },
]

const RISK_LEGEND = [
  { color: '#b91c1c', label: 'Alerta alto' },
  { color: '#f59e0b', label: 'Alerta médio' },
  { color: '#2563eb', label: 'Em observação' },
  { color: '#94a3b8', label: 'Sem evidência' },
]

const LAND_COVER_LEGEND = [
  { color: '#7c3aed', label: 'Expansão observada' },
  { color: '#16a34a', label: 'Floresta / cobertura sensível' },
  { color: '#2563eb', label: 'Água / área alagada' },
  { color: '#ca8a04', label: 'Uso rural estável' },
  { color: '#94a3b8', label: 'Outras transições' },
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
  if (mode === 'kernel') return KERNEL_LEGEND
  if (mode === 'validation') return VALIDATION_LEGEND
  if (mode === 'zoning') return ZONING_LEGEND
  if (mode === 'risk') return RISK_LEGEND
  if (mode === 'landcover') return LAND_COVER_LEGEND
  return SCORE_LEGEND
}

function objectiveScore(row, objectiveConfig) {
  const metric = objectiveConfig?.primaryMetric
  if (metric && row?.[metric] !== undefined && row?.[metric] !== null) {
    return Number(row[metric] || 0)
  }
  return Math.max(Number(row?.score_residencial || 0), Number(row?.score_comercial || 0))
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

function poiDisplayType(feature) {
  const type = poiType(feature)
  return POI_LABELS[type] || feature?.properties?.subcategory || feature?.properties?.category || 'Equipamento urbano'
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

function cellCenter(row) {
  if (!row?.h3_id) return null
  try {
    const [lat, lng] = cellToLatLng(row.h3_id)
    return [lng, lat]
  } catch {
    return null
  }
}

function kernelWeight(row, objectiveConfig) {
  const score = objectiveScore(row, objectiveConfig)
  const confidence = Number(row.confidence ?? 0.65)
  const growth = Math.max(0, Number(row.growth_signal || row.ndbi_slope_180 || 0) * 100)
  const gap = Math.max(0, Number(row.commercial_gap || 0) * 35)
  const lowRiskBoost = row.risk_level === 'baixo' ? 14 : row.risk_level === 'alto' ? -18 : 0
  const highPriorityBoost = row.priority === 'alta' ? 18 : 0
  return Math.max(1, score * 0.72 + confidence * 18 + growth + gap + lowRiskBoost + highPriorityBoost)
}

function validationTone(row, objectiveConfig) {
  const score = objectiveScore(row, objectiveConfig)
  const risk = String(row.risk_level || '').toLowerCase()
  if (risk === 'alto' || /bloque|vetad/i.test(row.legal_notes || '')) return 'danger'
  if (score >= 70 && risk !== 'medio') return 'good'
  if (score >= 50) return 'watch'
  return 'neutral'
}

function validationColor(row, objectiveConfig, alpha = 210) {
  const tone = validationTone(row, objectiveConfig)
  if (tone === 'good') return [34, 197, 94, alpha]
  if (tone === 'watch') return [245, 158, 11, alpha]
  if (tone === 'danger') return [239, 68, 68, alpha]
  return [100, 116, 139, alpha]
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
  cityConfig = null,
  cities = [],
  onCityChange = () => {},
  objectiveConfig = null,
  objectives = [],
  onObjectiveChange = () => {},
  cockpit = null,
  zoning = null,
  pois = null,
  officialRisk = null,
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
  const [layersOpen, setLayersOpen] = useState(false)
  const [rankingOpen, setRankingOpen] = useState(!isNarrow)

  useEffect(() => {
    if (!cityConfig?.center) return
    setViewState(current => ({
      ...current,
      longitude: cityConfig.center.longitude,
      latitude: cityConfig.center.latitude,
      zoom: cityConfig.center.zoom || current.zoom,
      transitionDuration: 500,
      transitionInterpolator: new FlyToInterpolator(),
    }))
    setSearchPin(null)
    setSelected(null)
  }, [cityConfig?.id])

  useEffect(() => {
    setViewState(current => ({
      ...current,
      pitch: mode === 'validation' ? 48 : 0,
      bearing: mode === 'validation' ? -18 : 0,
      transitionDuration: 500,
      transitionInterpolator: new FlyToInterpolator(),
    }))
  }, [mode])

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

  const kernelPoints = useMemo(() => data
    .map(row => {
      const position = cellCenter(row)
      return position ? { ...row, position, weight: kernelWeight(row, objectiveConfig) } : null
    })
    .filter(Boolean), [data, objectiveConfig])

  const influenceCenter = useMemo(() => {
    if (searchPin) return { longitude: searchPin.lon, latitude: searchPin.lat }
    return selectedCenter(selected) || cityConfig?.center || CITY
  }, [searchPin, selected, cityConfig])

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
    filled: mode === 'zoning' || mode === 'kernel' || mode === 'validation',
    getFillColor: f => mode === 'kernel' || mode === 'validation' ? zoneColor(f.properties?.zona, 30) : zoneColor(f.properties?.zona, 92),
    getLineColor: f => mode === 'zoning' ? [...zoneColor(f.properties?.zona, 224).slice(0, 3), 224] : [15, 23, 42, 118],
    getLineWidth: mode === 'zoning' ? 80 : mode === 'kernel' || mode === 'validation' ? 54 : 30,
    lineWidthMinPixels: mode === 'zoning' ? 1.6 : mode === 'kernel' || mode === 'validation' ? 1.15 : 0.6,
    autoHighlight: mode === 'zoning' || mode === 'kernel' || mode === 'validation',
    highlightColor: [255, 255, 255, 70],
    updateTriggers: {
      filled: [mode],
      getLineColor: [mode],
      getLineWidth: [mode],
      lineWidthMinPixels: [mode],
    },
    onHover: info => setTooltip(info.object ? { kind: 'zone', object: info.object, x: info.x, y: info.y } : null),
  }), [zoning, mode])

  const officialRiskLayer = useMemo(() => new GeoJsonLayer({
    id: 'sgb-official-susceptibility',
    data: officialRisk || { type: 'FeatureCollection', features: [] },
    visible: !!visibleLayers.officialRisk,
    pickable: true,
    stroked: true,
    filled: true,
    getFillColor: feature => {
      const value = String(feature.properties?.susceptibility_class || '').toLowerCase()
      if (value.includes('alta')) return [185, 28, 28, 92]
      if (value.includes('média') || value.includes('media')) return [245, 158, 11, 72]
      return [34, 197, 94, 46]
    },
    getLineColor: feature => String(feature.properties?.susceptibility_class || '').toLowerCase().includes('alta') ? [153, 27, 27, 210] : [161, 98, 7, 150],
    getLineWidth: 42,
    lineWidthMinPixels: 0.7,
    onHover: info => setTooltip(info.object ? { kind: 'official-risk', object: info.object, x: info.x, y: info.y } : null),
  }), [officialRisk, visibleLayers.officialRisk])

  const kernelLayer = useMemo(() => new HeatmapLayer({
    id: 'opportunity-kernel',
    data: kernelPoints,
    visible: mode === 'kernel',
    getPosition: d => d.position,
    getWeight: d => d.weight,
    radiusPixels: 58,
    intensity: 1.15,
    threshold: 0.04,
    colorRange: [
      [20, 184, 166, 0],
      [20, 184, 166, 90],
      [245, 158, 11, 145],
      [249, 115, 22, 185],
      [239, 68, 68, 218],
    ],
    aggregation: 'SUM',
    updateTriggers: { getWeight: [objectiveConfig] },
  }), [kernelPoints, mode, objectiveConfig])

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
      if (mode === 'risk') {
        const alert = String(d.satellite_risk_alert || 'dados_insuficientes')
        if (alert === 'alto') return [185, 28, 28, 155]
        if (alert === 'medio') return [245, 158, 11, 145]
        if (alert === 'em_observacao') return [37, 99, 235, 125]
        return [148, 163, 184, 70]
      }
      if (mode === 'landcover') {
        if (d.observed_urban_expansion) return [124, 58, 237, 175]
        const cover = String(d.land_cover_class || '').toLowerCase()
        if (cover.includes('florestal') || cover.includes('campo alagado')) return [22, 163, 74, 155]
        if (cover.includes('agua')) return [37, 99, 235, 165]
        if (cover.includes('pastagem') || cover.includes('lavoura') || cover.includes('agricultura')) return [202, 138, 4, 135]
        return [148, 163, 184, 105]
      }
      if (mode === 'kernel') return scoreToRgba(objectiveScore(d, objectiveConfig), 42)
      if (mode === 'validation') return validationColor(d, objectiveConfig, 76)
      return scoreToRgba(objectiveScore(d, objectiveConfig), 62)
    },
    getLineColor: d => selected?.h3_id === d.h3_id ? [15, 23, 42, 255] : [255, 255, 255, 82],
    lineWidthMinPixels: d => selected?.h3_id === d.h3_id ? 2 : 0.25,
    filled: true,
    stroked: true,
    extruded: false,
    coverage: mode === 'zoning' ? 0.45 : mode === 'kernel' ? 0.34 : mode === 'validation' ? 0.76 : 0.9,
    pickable: true,
    autoHighlight: true,
    highlightColor: [15, 23, 42, 48],
    updateTriggers: {
      getFillColor: [mode, selectedDate, ndviByCell, objectiveConfig],
      getLineColor: [selected],
      lineWidthMinPixels: [selected],
      coverage: [mode],
    },
    onHover: info => setTooltip(info.object ? { kind: 'cell', object: info.object, x: info.x, y: info.y } : null),
    onClick: info => setSelected(info.object || null),
  }), [data, mode, selectedDate, ndviByCell, selected, objectiveConfig])

  const validationLayer = useMemo(() => new ColumnLayer({
    id: 'validation-columns',
    data: kernelPoints,
    visible: mode === 'validation',
    diskResolution: 6,
    radius: 68,
    extruded: true,
    pickable: true,
    getPosition: d => d.position,
    getElevation: d => Math.max(28, objectiveScore(d, objectiveConfig) * 5.2),
    getFillColor: d => validationColor(d, objectiveConfig, 198),
    getLineColor: [255, 255, 255, 170],
    lineWidthMinPixels: 0.6,
    onHover: info => setTooltip(info.object ? { kind: 'validation', object: info.object, x: info.x, y: info.y } : null),
    onClick: info => setSelected(info.object || null),
    updateTriggers: {
      getElevation: [objectiveConfig],
      getFillColor: [objectiveConfig],
    },
  }), [kernelPoints, mode, objectiveConfig])

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
    getFillColor: [30, 64, 175, 205],
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
    officialRiskLayer,
    kernelLayer,
    visibleLayers.cells ? hexLayer : null,
    validationLayer,
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
        viewbox={cityConfig?.searchViewbox}
        cityName={cityConfig?.name}
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
        cityConfig={cityConfig}
        objectiveConfig={objectiveConfig}
        cockpit={cockpit}
        onSelectCell={cell => {
          setSelected(cell)
          const center = selectedCenter(cell)
          if (center) {
            setViewState(current => ({
              ...current,
              ...center,
              zoom: Math.max(current.zoom, 14.5),
              transitionDuration: 650,
              transitionInterpolator: new FlyToInterpolator(),
            }))
          }
        }}
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
          officialRiskCount={officialRisk?.features?.length || 0}
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
          cities={cities}
          cityId={cityConfig?.id}
          onCityChange={onCityChange}
          objectives={objectives}
          objectiveId={objectiveConfig?.id}
          onObjectiveChange={onObjectiveChange}
        />
        {selected && (
          <SelectedPanel
            cell={selected}
            objectiveConfig={objectiveConfig}
            onClose={() => setSelected(null)}
            onOpenConcept={onOpenConcept}
          />
        )}
      </div>

      <div className="atlas-zoom-controls">
        <button onClick={() => zoomBy(1)} title="Aumentar zoom">+</button>
        <button onClick={() => zoomBy(-1)} title="Diminuir zoom">−</button>
        <button onClick={resetView} title="Ver cidade inteira">⌂</button>
      </div>

      <div className="atlas-legend-group">
        <div className="atlas-legend">
          <span>{selectedDate ? `NDVI ${selectedDate}` : mode === 'zoning' ? 'Zoneamento PDPA' : mode === 'growth' ? 'Tendencia urbana' : mode === 'landcover' ? 'MapBiomas 2019–2024' : mode === 'kernel' ? 'Kernels de oportunidade' : mode === 'validation' ? 'Validacao 3D' : 'Score'}</span>
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
              <i style={{ background: 'rgb(30, 64, 175)', borderRadius: '50%' }} />
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

const MODE_LABELS = {
  score: 'Score',
  landcover: 'Uso do solo',
  risk: 'Alerta territorial',
  kernel: 'Kernels',
  validation: '3D',
  zoning: 'Zonas',
  growth: 'Tempo',
}

function Chevron({ open }) {
  return (
    <svg className={`atlas-chevron${open ? ' open' : ''}`} width="10" height="10" viewBox="0 0 10 10" fill="none">
      <path d="M2 3.5L5 6.5L8 3.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function LayersPanel({
  open, onToggle, rawMode, onModeChange, dateActive,
  visibleLayers, onToggleLayer, cellCount, zoningCount, poiCount, officialRiskCount,
  poiFilterDefs, poiTypes, onTogglePoiType,
  influenceRadius, onRadiusChange, labelMode, onLabelModeChange,
  priorityFilter, onPriorityChange, riskFilter, onRiskChange,
  cities, cityId, onCityChange,
  objectives, objectiveId, onObjectiveChange,
}) {
  return (
    <div className={`atlas-floating-panel atlas-layers-panel${open ? '' : ' collapsed'}`}>
      <button className="atlas-panel-header" onClick={onToggle}>
        <span>Controles do mapa</span>
        <Chevron open={open} />
      </button>
      {open && (
        <div className="atlas-panel-body">
          <div className="atlas-field-stack">
            <label>Cidade analisada</label>
            <select value={cityId || ''} onChange={e => onCityChange(e.target.value)}>
              {cities.map(city => (
                <option key={city.id} value={city.id} disabled={city.status !== 'operational'}>
                  {city.name} - {city.state}{city.status !== 'operational' ? ' (preparar dados)' : ''}
                </option>
              ))}
            </select>
          </div>

          <div className="atlas-objective-row">
            {objectives.map(item => (
              <button
                key={item.id}
                className={objectiveId === item.id ? 'active' : ''}
                onClick={() => onObjectiveChange(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>

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
          <label className="atlas-layer-row">
            <input type="checkbox" checked={visibleLayers.officialRisk} onChange={() => onToggleLayer('officialRisk')} />
            Carta oficial SGB <span>{officialRiskCount}</span>
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

function RankingPanel({ open, onToggle, cellCount, zoningCount, poiCount, rankedZones, cityConfig, objectiveConfig, cockpit, onSelectCell }) {
  return (
    <div className={`atlas-floating-panel atlas-ranking-panel${open ? '' : ' collapsed'}`}>
      <button className="atlas-panel-header" onClick={onToggle}>
        <span>Resumo da análise</span>
        <Chevron open={open} />
      </button>
      {open && (
        <div className="atlas-panel-body">
          <div className="atlas-cockpit-title">
            <strong>{cityConfig?.name || 'Cidade'}</strong>
            <span>{objectiveConfig?.shortLabel || 'Analise'} - {cityConfig?.status === 'operational' ? 'dados ativos' : 'dados pendentes'}</span>
          </div>
          <div className="atlas-ranking-stats">
            <div><strong>{cellCount}</strong><span>celulas</span></div>
            <div><strong>{zoningCount}</strong><span>zonas</span></div>
            <div><strong>{poiCount}</strong><span>pontos</span></div>
          </div>
          {cockpit && (
            <div className="atlas-cockpit-grid">
              <div><strong>{cockpit.highPriority}</strong><span>alta prioridade</span></div>
              <div><strong>{cockpit.legalRisk}</strong><span>alerta legal</span></div>
              <div><strong>{cockpit.growthSignals}</strong><span>sinal satelite</span></div>
              <div><strong>{cockpit.avgPrimary.toFixed(1)}</strong><span>score medio</span></div>
            </div>
          )}
          <div className="atlas-decision-note">
            <strong>{objectiveConfig?.decisionTitle || 'Decisao'}</strong>
            <span>{cockpit?.highPriority ? objectiveConfig?.goodSignal : objectiveConfig?.emptySignal}</span>
          </div>
          {cockpit?.best?.length > 0 && (
            <div className="atlas-best-cells">
            <span>Melhores regiões para investigar</span>
            {cockpit.best.map((cell, index) => (
              <button key={cell.h3_id || index} type="button" title={cell.h3_id} onClick={() => onSelectCell(cell)}>
                <strong>#{index + 1}</strong>
                  <span>{cell.neighborhood || cell.zona || cell.primary_use || 'Região em análise'}</span>
                  <b>{formatNumber(objectiveScore(cell, objectiveConfig), 0)}</b>
                </button>
              ))}
            </div>
          )}
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

function AddressSearch({ onSelect, viewbox, cityName }) {
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
          viewbox: viewbox || '',
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
  }, [query, viewbox])

  const pick = place => {
    onSelect({ lon: Number(place.lon), lat: Number(place.lat) })
    setQuery(place.display_name)
    setOpen(false)
  }

  return (
    <div className="atlas-search">
      <input
        type="text"
        placeholder={`Buscar em ${cityName || 'cidade'}...`}
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

function SelectedPanel({ cell, objectiveConfig, onClose, onOpenConcept }) {
  const decision = buildCellDecision(cell, objectiveConfig)
  const factors = [
    ...(Array.isArray(cell.positive_factors) ? cell.positive_factors : []),
    ...(Array.isArray(cell.negative_factors) ? cell.negative_factors.map(item => `Atencao: ${item}`) : []),
  ].slice(0, 5)
  const explainability = Array.isArray(cell.explainability) ? cell.explainability.slice(0, 5) : []

  return (
    <aside className="atlas-selected-panel">
      <button className="atlas-panel-close" onClick={onClose}>x</button>
      <div className="atlas-panel-kicker">{objectiveConfig?.decisionTitle || 'Analise da area'}</div>
      <h3>{decision.title}</h3>
      <div className={`atlas-decision-badge ${decision.tone}`}>
        <strong>{decision.score}</strong>
        <span>{decision.label}</span>
      </div>
      <p className="atlas-decision-copy">{decision.summary}</p>
      <Metric label="Prioridade" value={cell.priority} strong />
      <Metric label="Risco" value={cell.risk_level} />
      {cell.official_susceptibility && <Metric label="Carta oficial SGB" value={cell.official_susceptibility} />}
      <Metric label="Zona" value={cell.zona || cell.zoning?.zona || 'sem cruzamento'} />
      <Metric label="Cobertura do solo" value={cell.land_cover_class ? `${cell.land_cover_class} (${cell.land_cover_year})` : '-'} />
      {cell.land_cover_class_2019 && <Metric label="Cobertura em 2019" value={cell.land_cover_class_2019} />}
      {cell.land_cover_transition && <Metric label="Transição observada" value={cell.land_cover_transition} />}
      <Metric label="Score residencial" value={formatNumber(cell.score_residencial)} />
      <Metric label="Score comercial" value={formatNumber(cell.score_comercial)} />
      <Metric label="Referência de mercado" value={cell.market_price_m2 ? `R$ ${formatNumber(cell.market_price_m2, 0)} / m² (${cell.market_comparables} comparáveis)` : '-'} />
      <Metric label="NDVI 90d" value={formatNumber(cell.ndvi_mean_90, 3)} />
      <Metric label="NDBI 90d" value={formatNumber(cell.ndbi_mean_90, 3)} />
      <Metric label="Confianca" value={formatPercent(cell.confidence)} />

      {factors.length > 0 && (
        <div className="atlas-insight-list">
          <span>Fatores da recomendacao</span>
          {factors.map(item => <p key={item}>{item}</p>)}
        </div>
      )}

      {explainability.length > 0 && (
        <div className="atlas-explainability-list">
          <span>Evidencias auditaveis</span>
          {explainability.map(item => (
            <div key={item.label}>
              <strong>{item.label}</strong>
              <small>{item.value}</small>
            </div>
          ))}
        </div>
      )}

      {cell.legal_notes && <p className="atlas-legal-note">{cell.legal_notes}</p>}
      <button
        className="atlas-report-btn"
        onClick={() => downloadAreaReport(cell, objectiveConfig, decision, factors, explainability)}
      >
        Baixar relatorio da area
      </button>
      {onOpenConcept && (
        <button className="atlas-concept-btn" onClick={() => onOpenConcept(cell)}>
          Gerar conceito e obra
        </button>
      )}
    </aside>
  )
}

function downloadAreaReport(cell, objectiveConfig, decision, factors, explainability) {
  const lines = [
    `# Relatorio territorial - ${decision.title}`,
    '',
    `Objetivo: ${objectiveConfig?.label || 'Analise territorial'}`,
    `Celula H3: ${cell.h3_id || '-'}`,
    `Score principal: ${decision.score}`,
    `Decisao: ${decision.label}`,
    '',
    '## Resumo',
    decision.summary,
    '',
    '## Indicadores',
    `- Prioridade: ${cell.priority || '-'}`,
    `- Risco: ${cell.risk_level || '-'}`,
    `- Zona: ${cell.zona || cell.zoning?.zona || 'sem cruzamento'}`,
    `- Score residencial: ${formatNumber(cell.score_residencial)}`,
    `- Score comercial: ${formatNumber(cell.score_comercial)}`,
    `- Confianca: ${formatPercent(cell.confidence)}`,
    `- NDVI 90d: ${formatNumber(cell.ndvi_mean_90, 3)}`,
    `- NDBI 90d: ${formatNumber(cell.ndbi_mean_90, 3)}`,
    `- Cobertura do solo: ${cell.land_cover_class || '-' } (${cell.land_cover_year || '-'})`,
    `- Cobertura em 2019: ${cell.land_cover_class_2019 || '-'}`,
    `- Transição observada: ${cell.land_cover_transition || '-'}`,
    '',
    '## Fatores',
    ...(factors.length ? factors.map(item => `- ${item}`) : ['- Sem fatores destacados nos dados atuais.']),
    '',
    '## Evidencias',
    ...(explainability.length
      ? explainability.map(item => `- ${item.label}: ${item.value}`)
      : ['- Sem evidencias detalhadas disponiveis.']),
    '',
    '## Observacao legal',
    cell.legal_notes || 'Sem nota legal especifica para esta celula.',
    '',
    '## Fontes territoriais',
    '- MapBiomas Brasil, Coleção 10: cobertura e uso do solo (2019 e 2024).',
    '- Serviço Geológico do Brasil (SGB/CPRM): carta de suscetibilidade, quando aplicável.',
    '',
    'Gerado pela plataforma de inteligencia territorial.',
  ]
  const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `relatorio-${cell.h3_id || 'area'}.md`
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

function buildCellDecision(cell, objectiveConfig) {
  const primaryMetric = objectiveConfig?.primaryMetric || 'score_residencial'
  const score = Number(cell[primaryMetric] || 0)
  const risk = String(cell.risk_level || '').toLowerCase()
  const blocked = risk === 'alto' || /bloque|vetad/i.test(cell.legal_notes || '')
  const title = cell.neighborhood
    ? `${cell.neighborhood}${cell.zona ? ` · ${cell.zona}` : ''}`
    : cell.zona || cell.h3_id

  if (blocked) {
    return {
      title,
      score: formatNumber(score),
      label: 'investigar antes de agir',
      tone: 'danger',
      summary: 'A area tem restricao ou risco elevado. Use a recomendacao como triagem e valide o Plano Diretor antes de qualquer decisao.',
    }
  }
  if (score >= 70) {
    return {
      title,
      score: formatNumber(score),
      label: 'prioridade alta',
      tone: 'good',
      summary: 'Boa candidata para analise detalhada: combina score alto, sinais urbanos e risco controlado dentro dos dados disponiveis.',
    }
  }
  if (score >= 50) {
    return {
      title,
      score: formatNumber(score),
      label: 'potencial moderado',
      tone: 'watch',
      summary: 'Existe potencial, mas a area depende de validacao de entorno, preco, servicos proximos e compatibilidade urbanistica.',
    }
  }
  return {
    title,
    score: formatNumber(score),
    label: 'baixa prioridade',
    tone: 'neutral',
    summary: 'A area nao aparece entre as melhores candidatas nos criterios atuais. Pode servir como comparativo ou monitoramento futuro.',
  }
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
  if (kind === 'official-risk') {
    const props = object.properties || {}
    return (
      <div className="atlas-tooltip" style={style}>
        <strong>SGB/CPRM · {props.susceptibility_class || 'classe não informada'}</strong>
        <span>{props.process_type || 'Suscetibilidade territorial'}</span>
        <span>{props.reference_year || 'Ano não informado'}</span>
      </div>
    )
  }
  if (kind === 'poi') {
    const props = object.properties || {}
    return (
      <div className="atlas-tooltip" style={style}>
        <strong>{props.name || props.subcategory || 'Ponto urbano'}</strong>
        <span>{poiDisplayType(object)}</span>
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
  if (kind === 'validation') {
    const tone = validationTone(object, {})
    const label = tone === 'good' ? 'Viavel' : tone === 'watch' ? 'Validar dados' : tone === 'danger' ? 'Restricao' : 'Baixa prioridade'
    return (
      <div className="atlas-tooltip" style={style}>
        <strong>{object.zona || object.h3_id}</strong>
        <span>{label}</span>
        <span>Score: {formatNumber(Math.max(Number(object.score_residencial || 0), Number(object.score_comercial || 0)))}</span>
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

function formatPercent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-'
  const n = Number(value)
  return `${(n <= 1 ? n * 100 : n).toFixed(0)}%`
}
