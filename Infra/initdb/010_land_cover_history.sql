CREATE TABLE IF NOT EXISTS geo.land_cover_h3_history (
  h3_id TEXT REFERENCES geo.grid_h3(h3_id) ON DELETE CASCADE,
  reference_year INTEGER NOT NULL,
  class_code INTEGER NOT NULL,
  class_name TEXT NOT NULL,
  source_name TEXT NOT NULL DEFAULT 'MapBiomas Brasil Colecao 10',
  collected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (h3_id, reference_year)
);
