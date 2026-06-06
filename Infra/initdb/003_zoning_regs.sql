-- Zoneamento espacial e base textual para consultas urbanisticas.
CREATE TABLE IF NOT EXISTS geo.zoning (
  id SERIAL PRIMARY KEY,
  zona TEXT NOT NULL,
  usos_permitidos TEXT[],
  usos_condicionados TEXT[],
  usos_vetados TEXT[],
  gabarito INT,
  coef_aprov NUMERIC,
  recuos JSONB,
  observacoes TEXT,
  geom geometry(MultiPolygon,4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_zoning_gist ON geo.zoning USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_zoning_zona ON geo.zoning (zona);

-- Camadas de restricao/overlay (APP, UC, ZEIS, eixos especiais).
CREATE TABLE IF NOT EXISTS geo.overlays (
  id SERIAL PRIMARY KEY,
  tipo TEXT NOT NULL,
  regras JSONB,
  geom geometry(MultiPolygon,4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_overlays_gist ON geo.overlays USING GIST(geom);
CREATE INDEX IF NOT EXISTS idx_overlays_tipo ON geo.overlays (tipo);

-- Base textual para RAG. Embeddings ficam em JSONB para o container iniciar
-- mesmo quando a extensao pgvector nao estiver instalada.
CREATE TABLE IF NOT EXISTS public.regs (
  id SERIAL PRIMARY KEY,
  doc TEXT NOT NULL,
  artigo TEXT,
  sumario TEXT,
  texto TEXT NOT NULL,
  url TEXT,
  embedding JSONB
);
CREATE INDEX IF NOT EXISTS idx_regs_doc ON public.regs (doc);
