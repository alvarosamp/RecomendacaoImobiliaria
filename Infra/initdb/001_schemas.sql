-- Extensões e schema
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA IF NOT EXISTS geo;

-- Limite municipal
CREATE TABLE IF NOT EXISTS geo.city_boundary (
  id   SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  geom geometry(MultiPolygon,4326) NOT NULL
);

-- Grid H3
CREATE TABLE IF NOT EXISTS geo.grid_h3 (
  h3_id TEXT PRIMARY KEY,
  res   INT NOT NULL,
  geom  geometry(Polygon,4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_grid_h3_gist ON geo.grid_h3 USING GIST(geom);

-- POIs normalizados
CREATE TABLE IF NOT EXISTS geo.osm_pois (
  id BIGSERIAL PRIMARY KEY,
  name TEXT,
  category TEXT,
  subcategory TEXT,
  geom geometry(Point,4326) NOT NULL,
  source_ts TIMESTAMP DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_osm_pois_gist ON geo.osm_pois USING GIST(geom);
