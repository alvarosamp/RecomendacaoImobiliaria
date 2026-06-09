import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet'
import { cellToBoundary } from 'h3-js'
import 'leaflet/dist/leaflet.css'

const SCORE_COLORS = [
  { min: 70, color: '#16a34a', label: 'Alto (70+)' },
  { min: 50, color: '#ca8a04', label: 'Médio (50-70)' },
  { min: 30, color: '#ea580c', label: 'Baixo (30-50)' },
  { min: 0,  color: '#dc2626', label: 'Mínimo (<30)' },
]

function scoreColor(score) {
  return (SCORE_COLORS.find(c => score >= c.min) || SCORE_COLORS.at(-1)).color
}

function toGeoJson(data) {
  return {
    type: 'FeatureCollection',
    features: data
      .filter(r => r.h3_id)
      .map(r => {
        const boundary = cellToBoundary(r.h3_id, true) // [lng, lat]
        return {
          type: 'Feature',
          geometry: { type: 'Polygon', coordinates: [[...boundary, boundary[0]]] },
          properties: r,
        }
      }),
  }
}

export default function H3Map({ data }) {
  const geojson = toGeoJson(data)

  const style = (feature) => ({
    fillColor: scoreColor(Math.max(
      feature.properties.score_residencial || 0,
      feature.properties.score_comercial   || 0,
    )),
    fillOpacity: 0.65,
    color: '#fff',
    weight: 0.8,
  })

  const onEachFeature = (feature, layer) => {
    const p = feature.properties
    layer.bindTooltip(
      `<b style="font-size:12px">${p.h3_id}</b><br/>` +
      `Residencial: <b>${p.score_residencial?.toFixed(1) ?? '-'}</b><br/>` +
      `Comercial: <b>${p.score_comercial?.toFixed(1) ?? '-'}</b><br/>` +
      `Prioridade: <b>${p.priority ?? '-'}</b> | Risco: <b>${p.risk_level ?? '-'}</b><br/>` +
      `NDVI: ${p.ndvi_mean_90?.toFixed(3) ?? '-'}`,
      { sticky: true, opacity: 0.92 }
    )
  }

  return (
    <div className="map-container">
      <div className="map-legend">
        {SCORE_COLORS.map(c => (
          <span key={c.color} style={{ color: c.color }}>● {c.label}</span>
        ))}
      </div>
      <MapContainer
        center={[-22.230278, -45.948889]}
        zoom={12}
        style={{ height: '600px', width: '100%', borderRadius: 8 }}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://openstreetmap.org">OpenStreetMap</a>'
        />
        {data.length > 0 && (
          <GeoJSON
            key={data.length}
            data={geojson}
            style={style}
            onEachFeature={onEachFeature}
          />
        )}
      </MapContainer>
    </div>
  )
}
