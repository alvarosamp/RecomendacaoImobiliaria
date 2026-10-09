import { useEffect, useRef } from 'react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'

// OpenFreeMap: tiles vetoriais do OpenStreetMap, sem chave de API nem limite de uso.
const OFM = 'https://tiles.openfreemap.org/styles'

export const BASEMAPS = {
  streets: { label: 'Ruas', style: `${OFM}/liberty`, theme: 'light' },
  light: { label: 'Claro', style: `${OFM}/positron`, theme: 'light' },
  satellite: { label: 'Satélite', style: `${OFM}/liberty`, theme: 'dark', imagery: true },
}

const SATELLITE_STYLE = {
  version: 8,
  sources: {
    imagery: {
      type: 'raster',
      tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
      tileSize: 256,
      maxzoom: 19,
    },
  },
  layers: [{ id: 'imagery', type: 'raster', source: 'imagery' }],
}

// Pontos de interesse e nomes de bairro já vêm das camadas próprias do produto.
const HIDDEN_LABEL_LAYERS = /^(poi|label_other)/

function labelsOnly(style, dark) {
  return {
    ...style,
    layers: style.layers
      .filter(layer => layer.type === 'symbol' && !HIDDEN_LABEL_LAYERS.test(layer.id))
      .map(layer => (dark && layer.layout?.['text-field'] ? {
        ...layer,
        paint: {
          ...layer.paint,
          'text-color': '#ffffff',
          'text-halo-color': 'rgba(15, 23, 42, 0.85)',
          'text-halo-width': 1.4,
        },
      } : layer)),
  }
}

function withoutLabels(style) {
  return { ...style, layers: style.layers.filter(layer => layer.type !== 'symbol') }
}

function cameraFrom(viewState) {
  return {
    center: [viewState.longitude, viewState.latitude],
    zoom: viewState.zoom,
    bearing: viewState.bearing || 0,
    pitch: viewState.pitch || 0,
  }
}

/**
 * Mapa base vetorial guiado pela câmera do deck.gl.
 * part="base" desenha só o fundo (embaixo dos dados);
 * part="labels" desenha só ruas e lugares (acima dos dados).
 */
export default function VectorBasemap({ viewState, basemap = 'streets', part = 'base', className = '' }) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)

  useEffect(() => {
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: { version: 8, sources: {}, layers: [] },
      interactive: false,
      attributionControl: false,
      fadeDuration: 0,
      maxPitch: 85,
      ...cameraFrom(viewState),
    })
    mapRef.current = map
    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    const config = BASEMAPS[basemap] || BASEMAPS.streets
    if (!map) return
    if (part === 'base' && config.imagery) {
      map.setStyle(SATELLITE_STYLE, { diff: false })
      return
    }
    map.setStyle(config.style, {
      diff: false,
      transformStyle: (_previous, next) => (part === 'labels' ? labelsOnly(next, config.theme === 'dark') : withoutLabels(next)),
    })
  }, [basemap, part])

  useEffect(() => {
    mapRef.current?.jumpTo(cameraFrom(viewState))
  }, [viewState.longitude, viewState.latitude, viewState.zoom, viewState.bearing, viewState.pitch])

  return <div ref={containerRef} className={`atlas-basemap atlas-basemap-${part} ${className}`} aria-hidden="true" />
}
