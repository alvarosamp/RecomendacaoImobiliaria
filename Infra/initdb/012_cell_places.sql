-- Principais ruas de cada celula H3 (OpenStreetMap), para localizar uma area em linguagem de usuario.
CREATE TABLE IF NOT EXISTS geo.cell_places (
  h3_id TEXT PRIMARY KEY REFERENCES geo.grid_h3(h3_id) ON DELETE CASCADE,
  streets JSONB NOT NULL DEFAULT '[]'::jsonb,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
