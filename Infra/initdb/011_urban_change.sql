-- Mudanca ano-contra-ano detectada em Sentinel-2 (10 m), agregada por celula H3.
-- changed_* = nivel "alta confianca" (regra); probable_* = nivel "provavel" (classificador).
CREATE TABLE IF NOT EXISTS geo.urban_change_h3 (
  h3_id TEXT NOT NULL REFERENCES geo.grid_h3(h3_id) ON DELETE CASCADE,
  year_before INTEGER NOT NULL,
  year_after INTEGER NOT NULL,
  cell_area_ha DOUBLE PRECISION NOT NULL,
  valid_area_ha DOUBLE PRECISION NOT NULL,
  changed_area_ha DOUBLE PRECISION NOT NULL,
  valid_fraction DOUBLE PRECISION NOT NULL,
  changed_fraction DOUBLE PRECISION NOT NULL,
  probable_area_ha DOUBLE PRECISION,
  probable_fraction DOUBLE PRECISION,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (h3_id, year_before, year_after)
);
