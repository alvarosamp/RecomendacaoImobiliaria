CREATE TABLE IF NOT EXISTS geo.land_cover_h3 (
  h3_id TEXT PRIMARY KEY REFERENCES geo.grid_h3(h3_id) ON DELETE CASCADE,
  class_code INTEGER NOT NULL,
  class_name TEXT NOT NULL,
  reference_year INTEGER NOT NULL,
  source_name TEXT NOT NULL DEFAULT 'MapBiomas Brasil Colecao 10',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
