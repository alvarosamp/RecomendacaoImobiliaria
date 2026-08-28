-- Evidencias para suscetibilidade territorial. Nao substitui mapeamento oficial de risco.
CREATE TABLE IF NOT EXISTS geo.risk_inputs (
  h3_id TEXT PRIMARY KEY REFERENCES geo.grid_h3(h3_id) ON DELETE CASCADE,
  slope_pct DOUBLE PRECISION,
  drainage_distance_m DOUBLE PRECISION,
  water_observation_rate DOUBLE PRECISION,
  source_name TEXT NOT NULL DEFAULT 'manual_or_external',
  reference_date DATE,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS geo.risk_signals (
  h3_id TEXT PRIMARY KEY REFERENCES geo.grid_h3(h3_id) ON DELETE CASCADE,
  susceptibility_score DOUBLE PRECISION NOT NULL,
  alert_level TEXT NOT NULL,
  confidence DOUBLE PRECISION NOT NULL,
  components JSONB NOT NULL DEFAULT '{}'::jsonb,
  evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
  calculated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_risk_signals_alert_level ON geo.risk_signals(alert_level);
