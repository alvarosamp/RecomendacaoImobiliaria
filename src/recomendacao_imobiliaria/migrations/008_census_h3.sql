-- Resultados agregados e públicos do Censo Demográfico 2022 por célula H3.
CREATE TABLE IF NOT EXISTS geo.census_h3 (
  h3_id TEXT PRIMARY KEY REFERENCES geo.grid_h3(h3_id) ON DELETE CASCADE,
  population_2022 DOUBLE PRECISION NOT NULL DEFAULT 0,
  occupied_households_2022 DOUBLE PRECISION NOT NULL DEFAULT 0,
  source_name TEXT NOT NULL DEFAULT 'IBGE Censo Demografico 2022',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
