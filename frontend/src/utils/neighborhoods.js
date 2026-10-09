import { cellToLatLng } from 'h3-js'

// Ponto de bairro (OSM place=neighbourhood) só nomeia células próximas a ele.
const POINT_MAX_DISTANCE_M = 1200

function pointInRing([x, y], ring) {
  let inside = false
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i, i += 1) {
    const [xi, yi] = ring[i]
    const [xj, yj] = ring[j]
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside
  }
  return inside
}

function pointInGeometry(point, geometry) {
  const polygons = geometry.type === 'Polygon' ? [geometry.coordinates]
    : geometry.type === 'MultiPolygon' ? geometry.coordinates
      : []
  return polygons.some(([outer, ...holes]) => pointInRing(point, outer) && !holes.some(hole => pointInRing(point, hole)))
}

function distanceMeters([lon1, lat1], [lon2, lat2]) {
  const kx = 111320 * Math.cos(((lat1 + lat2) / 2) * Math.PI / 180)
  return Math.hypot((lon1 - lon2) * kx, (lat1 - lat2) * 110540)
}

/** Resolve o nome do bairro de uma coordenada [lon, lat]. */
export function makeNeighborhoodResolver(collection) {
  const features = collection?.features || []
  const polygons = features.filter(f => f.properties?.kind !== 'quadrante' && f.geometry?.type !== 'Point')
  const points = features.filter(f => f.geometry?.type === 'Point')
  const quadrants = features.filter(f => f.properties?.kind === 'quadrante')
  if (!features.length) return () => null

  return position => {
    const polygon = polygons.find(f => pointInGeometry(position, f.geometry))
    if (polygon) return { name: polygon.properties.name, source: polygon.properties.approximate ? 'cep' : 'limite' }
    let nearest = null
    let best = POINT_MAX_DISTANCE_M
    points.forEach(f => {
      const d = distanceMeters(position, f.geometry.coordinates)
      if (d < best) { best = d; nearest = f }
    })
    if (nearest) return { name: nearest.properties.name, source: 'proximidade' }
    const quadrant = quadrants.find(f => pointInGeometry(position, f.geometry))
    if (quadrant) return { name: quadrant.properties.name, source: 'quadrante' }
    // Fora de bairros, quadrantes e localidades conhecidas: área rural do município.
    return { name: 'Zona rural', source: 'rural' }
  }
}

// Nome herdado do anúncio mais próximo (inclui anúncios sintéticos): não é bairro de verdade.
const isListingReference = row => /an[uú]ncio/i.test(String(row.neighborhood_source || ''))

/** Preenche `neighborhood` nas células que não têm bairro de fonte oficial importada. */
export function withNeighborhoods(rows, collection) {
  if (!collection?.features?.length) return rows
  const resolve = makeNeighborhoodResolver(collection)
  return rows.map(row => {
    if (!row.h3_id || (row.neighborhood && !isListingReference(row))) return row
    let match = null
    try {
      const [lat, lng] = cellToLatLng(row.h3_id)
      match = resolve([lng, lat])
    } catch {
      match = null
    }
    const base = isListingReference(row)
      ? { ...row, listing_neighborhood: row.neighborhood, neighborhood: null, neighborhood_source: null }
      : row
    return match ? { ...base, neighborhood: match.name, neighborhood_source: match.source } : base
  })
}
