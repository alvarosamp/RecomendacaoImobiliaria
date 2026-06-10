-- Series temporais, acessibilidade, features e scores.
CREATE SCHEMA IF NOT EXISTS geo;

-- Indices espectrais por H3 e data (NDVI/NDBI/BAI).
CREATE TABLE IF NOT EXISTS geo.indices (
  h3_id TEXT NOT NULL,
  date DATE NOT NULL,
  ndvi DOUBLE PRECISION,
  ndbi DOUBLE PRECISION,
  bai DOUBLE PRECISION,
  cloud_pct DOUBLE PRECISION,
  created_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (h3_id, date),
  CONSTRAINT fk_indices_h3
    FOREIGN KEY (h3_id) REFERENCES geo.grid_h3(h3_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_indices_h3_date ON geo.indices (h3_id, date);

-- Distancias e metricas de acessibilidade por H3.
CREATE TABLE IF NOT EXISTS geo.access (
  h3_id TEXT NOT NULL,
  metric TEXT NOT NULL,
  value DOUBLE PRECISION NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (h3_id, metric),
  CONSTRAINT fk_access_h3
    FOREIGN KEY (h3_id) REFERENCES geo.grid_h3(h3_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_access_metric ON geo.access (metric);

-- Features agregadas por H3 para scoring e ML.
CREATE TABLE IF NOT EXISTS geo.features (
  h3_id TEXT PRIMARY KEY,
  -- Indices espectrais (Sentinel-2)
  ndvi_mean_90 DOUBLE PRECISION,
  ndvi_slope_180 DOUBLE PRECISION,
  ndbi_mean_90 DOUBLE PRECISION,
  ndbi_slope_180 DOUBLE PRECISION,
  -- POIs basicos (OSM)
  poi_supermarket_cnt INT,
  poi_pharmacy_cnt INT,
  poi_school_cnt INT,
  dist_min_supermarket_m DOUBLE PRECISION,
  dist_min_pharmacy_m DOUBLE PRECISION,
  dist_min_school_m DOUBLE PRECISION,
  -- POIs estendidos (OSM + CNES)
  poi_hospital_cnt INT,
  poi_restaurant_cnt INT,
  poi_bank_cnt INT,
  poi_leisure_cnt INT,
  dist_min_hospital_m DOUBLE PRECISION,
  dist_min_park_m DOUBLE PRECISION,
  dist_min_bus_stop_m DOUBLE PRECISION,
  -- Populacao estimada (IBGE Censo 2022)
  pop_estimated INT,
  updated_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT fk_features_h3
    FOREIGN KEY (h3_id) REFERENCES geo.grid_h3(h3_id) ON DELETE CASCADE
);

-- Scores explicaveis por H3.
CREATE TABLE IF NOT EXISTS geo.scores (
  h3_id TEXT PRIMARY KEY,
  score_residencial DOUBLE PRECISION,
  score_comercial DOUBLE PRECISION,
  explain_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_at TIMESTAMPTZ DEFAULT now(),
  CONSTRAINT fk_scores_h3
    FOREIGN KEY (h3_id) REFERENCES geo.grid_h3(h3_id) ON DELETE CASCADE
);
