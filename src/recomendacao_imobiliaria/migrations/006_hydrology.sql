CREATE TABLE IF NOT EXISTS geo.hydrology (
  id BIGSERIAL PRIMARY KEY,
  name TEXT,
  waterway_type TEXT,
  source_name TEXT NOT NULL DEFAULT 'openstreetmap',
  geom geometry(Geometry, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_hydrology_gist ON geo.hydrology USING GIST(geom);
