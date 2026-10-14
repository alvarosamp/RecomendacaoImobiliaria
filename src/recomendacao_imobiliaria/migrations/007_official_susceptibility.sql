-- Camadas oficiais do Servico Geologico do Brasil (SGB/CPRM).
CREATE TABLE IF NOT EXISTS geo.official_susceptibility (
  id BIGSERIAL PRIMARY KEY,
  process_type TEXT NOT NULL,
  susceptibility_class TEXT NOT NULL,
  source_name TEXT NOT NULL DEFAULT 'SGB/CPRM',
  reference_year INTEGER,
  source_url TEXT NOT NULL,
  properties JSONB NOT NULL DEFAULT '{}'::jsonb,
  geom geometry(Geometry, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_official_susceptibility_gist
  ON geo.official_susceptibility USING GIST(geom);
