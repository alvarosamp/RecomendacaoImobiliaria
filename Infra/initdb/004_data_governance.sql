-- Governança de dados; a aplicação também garante estes objetos em bancos já existentes.
CREATE SCHEMA IF NOT EXISTS market;
CREATE SCHEMA IF NOT EXISTS ops;

CREATE TABLE IF NOT EXISTS ops.data_sources (
  id BIGSERIAL PRIMARY KEY,
  dataset TEXT NOT NULL,
  source_name TEXT NOT NULL,
  source_uri TEXT,
  reference_date DATE,
  collected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  row_count INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'ok',
  details JSONB NOT NULL DEFAULT '{}'::jsonb,
  checksum_sha256 TEXT,
  license_name TEXT,
  schema_version TEXT,
  legal_basis TEXT
);

ALTER TABLE ops.data_sources ADD COLUMN IF NOT EXISTS checksum_sha256 TEXT;
ALTER TABLE ops.data_sources ADD COLUMN IF NOT EXISTS license_name TEXT;
ALTER TABLE ops.data_sources ADD COLUMN IF NOT EXISTS schema_version TEXT;
ALTER TABLE ops.data_sources ADD COLUMN IF NOT EXISTS legal_basis TEXT;
