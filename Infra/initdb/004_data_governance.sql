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
  details JSONB NOT NULL DEFAULT '{}'::jsonb
);
